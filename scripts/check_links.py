#!/usr/bin/env python3
"""Probe every URL in data/links.json; remove entries that are clearly dead.

Conservative auto-remove (default):
  - Remove only DNS failures, ConnectionRefused, and HTTP 404/410.
  - Keep timeouts, 5xx, 401/403/405/429 — these usually mean the host is
    alive but rate-limiting / cloudflare-challenging us.

Pass --strict to also drop timeouts (matches the original auto-remove ask).
Pass --probe N to limit to N urls (smoke test).
Pass --resume to skip URLs whose last_checked is within --cache-days.
Pass --no-write to keep links.json untouched (only writes the report).
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
LINKS = ROOT / "data" / "links.json"
DEAD = ROOT / "data" / "dead-links.txt"

USER_AGENT = "Mozilla/5.0 (compatible; AwesomeWarezLinkCheck/1.0; +https://lkrjangid1.github.io/Awesome-Warez/)"
TIMEOUT = 8.0

# Hosts we don't probe — they don't behave well with HEAD/GET from a script.
SKIP_PROBE_HOSTS = {
    "t.me", "telegram.me", "telegram.org",
    "discord.gg", "discord.com", "discordapp.com",
    "twitter.com", "x.com",
    "facebook.com", "instagram.com",
    "reddit.com", "old.reddit.com", "redd.it",
    "github.com",  # rate-limits aggressively; mostly stable anyway
    "raw.githubusercontent.com",
}

# Considered "alive" — host responded with something interpretable
ALIVE_STATUSES = {200, 201, 202, 203, 204, 206, 300, 301, 302, 303, 304, 307, 308,
                  401, 403, 405, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526, 530}

# Definite dead in conservative mode
DEAD_STATUSES_CONSERVATIVE = {404, 410}


def host_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except ValueError:
        return ""


def _probe_once(url: str, method: str = "HEAD") -> tuple[int | None, str | None]:
    """Return (status, error). status is None on socket/DNS/conn errors."""
    req = urlrequest.Request(url, method=method, headers={
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    })
    try:
        with urlrequest.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, None
    except HTTPError as e:
        return e.code, None
    except (URLError, socket.timeout, ConnectionResetError, OSError) as e:
        msg = str(getattr(e, "reason", e)) or e.__class__.__name__
        return None, msg


def probe(url: str) -> dict:
    host = host_of(url)
    if host in SKIP_PROBE_HOSTS:
        return {"url": url, "status": "skip", "code": None, "error": None}
    # scheme not http(s)? assume alive
    scheme = urlparse(url).scheme
    if scheme not in ("http", "https"):
        return {"url": url, "status": "skip", "code": None, "error": None}
    code, err = _probe_once(url, "HEAD")
    # Many sites reject HEAD — retry as GET if HEAD looked confused
    if code in (400, 405, 501) or (code is None and err and "timed out" not in err.lower()):
        code, err = _probe_once(url, "GET")
    return {"url": url, "code": code, "error": err}


def classify(result: dict, strict: bool) -> str:
    """Return one of: alive | dead | unknown."""
    if result.get("status") == "skip":
        return "alive"
    code = result.get("code")
    err = result.get("error")
    if code is not None:
        if code in ALIVE_STATUSES:
            return "alive"
        if code in DEAD_STATUSES_CONSERVATIVE:
            return "dead"
        return "unknown"
    # socket / DNS / connection errors
    el = (err or "").lower()
    if any(s in el for s in ("name or service not known", "nodename nor servname",
                              "name resolution", "getaddrinfo", "no address associated")):
        return "dead"  # DNS failure
    if "refused" in el or "no route to host" in el or "unreachable" in el:
        return "dead"
    if "timed out" in el or "timeout" in el:
        return "dead" if strict else "unknown"
    if "ssl" in el or "certificate" in el:
        return "alive"  # cert issue but host exists
    return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--strict", action="store_true",
                    help="Drop timeouts too (matches the original auto-remove plan).")
    ap.add_argument("--probe", type=int, default=0,
                    help="Limit to N urls for smoke test (0 = all).")
    ap.add_argument("--no-write", action="store_true",
                    help="Don't rewrite links.json — only write dead-links.txt.")
    ap.add_argument("--resume", action="store_true",
                    help="Skip urls whose last_checked < --cache-days ago.")
    ap.add_argument("--cache-days", type=int, default=7)
    args = ap.parse_args()

    data = json.loads(LINKS.read_text(encoding="utf-8"))
    links = data["links"]

    today = date.today().isoformat()
    cutoff = None
    if args.resume:
        cutoff = (date.today() - timedelta(days=args.cache_days)).isoformat()

    to_probe = []
    for i, link in enumerate(links):
        if cutoff and link.get("last_checked", "") >= cutoff and link.get("last_status") == "alive":
            continue
        to_probe.append((i, link["url"]))

    if args.probe:
        to_probe = to_probe[: args.probe]

    print(f"probing {len(to_probe)}/{len(links)} urls (workers={args.workers}, strict={args.strict})")
    start = time.time()
    results: dict[int, dict] = {}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(probe, url): (i, url) for i, url in to_probe}
        done = 0
        for fut in as_completed(futures):
            i, url = futures[fut]
            try:
                r = fut.result()
            except Exception as e:  # safety net
                r = {"url": url, "code": None, "error": f"{type(e).__name__}: {e}"}
            results[i] = r
            done += 1
            if done % 200 == 0 or done == len(to_probe):
                elapsed = time.time() - start
                rate = done / elapsed if elapsed else 0
                remaining = (len(to_probe) - done) / rate if rate else 0
                print(f"  {done}/{len(to_probe)}  ({rate:.1f}/s, ~{int(remaining)}s left)")

    alive = dead = unknown = 0
    dead_lines = []
    for i, link in enumerate(links):
        r = results.get(i)
        if r is None:
            continue  # skipped via --resume
        cls = classify(r, args.strict)
        link["last_checked"] = today
        link["last_status"] = cls
        if cls == "alive":
            alive += 1
        elif cls == "dead":
            dead += 1
            dead_lines.append(
                f"[{r.get('code') or 'NET'}] {link['url']}  ({link['category']}/{link['subcategory']})  "
                f"-- {link['title']}  -- {r.get('error') or ''}"
            )
        else:
            unknown += 1

    print(f"\nalive: {alive}   dead: {dead}   unknown: {unknown}   skipped: {len(links) - len(results)}")

    # remove dead
    kept = [l for l in links if l.get("last_status") != "dead"]
    removed = len(links) - len(kept)
    print(f"removed {removed} dead entries from links.json")

    DEAD.parent.mkdir(parents=True, exist_ok=True)
    DEAD.write_text(
        f"# generated {datetime.now(timezone.utc).isoformat()}\n"
        f"# strict={args.strict}\n"
        f"# alive={alive}  dead={dead}  unknown={unknown}\n\n"
        + "\n".join(dead_lines) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {DEAD}")

    if args.no_write:
        print("(skipping links.json rewrite)")
        return

    data["links"] = kept
    # refresh per-category counts
    counts: dict[str, int] = {}
    for l in kept:
        counts[l["category"]] = counts.get(l["category"], 0) + 1
    for cat in data["categories"]:
        cat["count"] = counts.get(cat["slug"], 0)
    data["generated_at"] = today

    LINKS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {LINKS}")


if __name__ == "__main__":
    main()
