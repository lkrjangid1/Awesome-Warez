#!/usr/bin/env python3
"""Parse index.md (HTML/Markdown hybrid) into data/links.json.

One-time tool. Reads ../index.md, writes ../data/links.json and
../data/extract-report.txt. Stdlib-only.
"""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urlunparse


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "index.md"
OUT = ROOT / "data" / "links.json"
REPORT = ROOT / "data" / "extract-report.txt"

# ---------- 14-category mapping ----------
CATEGORIES = [
    ("trackers",            "Trackers & Torrents",   "Private, public, and semi-private torrent trackers plus search tools."),
    ("usenet",              "Usenet",                "Usenet providers, indexers, and forums."),
    ("seedboxes",           "Seedboxes",             "Seedbox hosting providers and frameworks."),
    ("streaming",           "Streaming",             "Movie, TV, anime, cartoon, sports, and adult streaming sites."),
    ("music-audio",         "Music & Audio",         "Music downloads, audio torrents, podcasts, and sample packs."),
    ("games",               "Games",                 "PC games, console games, ROMs, repacks, cheats, and emulators."),
    ("apps-software",       "Apps & Software",       "Android APKs, iOS apps, nulled scripts, Windows/Mac software, and desktop tools."),
    ("books-reading",       "Books, Comics & Manga", "eBooks, comics, manga, magazines, light novels, and academic papers."),
    ("education-learning",  "Education & Learning",  "Courses, language learning, documentaries, references, and study tools."),
    ("cloud-hosting",       "Cloud & File Hosting",  "Cloud drives, file hosters, premium link generators, DDL sites, and VPS."),
    ("media-servers",       "Media Servers",         "Kodi, Plex, Stremio, and media-center applications."),
    ("privacy-security",    "Privacy & Security",    "VPNs, secure email, temp mail, data-leak checks, and hardened OSes."),
    ("tools-utilities",     "Tools & Utilities",     "Checksum, ad-blockers, NFO viewers, archiving, custom search, and dev tools."),
    ("communities-info",    "Communities & Info",    "News, forums, archives, scene groups, IRC, and legal/country information."),
]

# Map a (lower-cased) heading-text keyword -> category slug.
# Order matters: longer/more specific phrases first.
KEYWORD_MAP: list[tuple[str, str]] = [
    # books, comics & manga (specific first so they don't get absorbed by 'manga' -> apps)
    ("ebook",                    "books-reading"),
    ("e-book",                   "books-reading"),
    ("comicbook",                "books-reading"),
    ("comic site",               "books-reading"),
    ("manga site",               "books-reading"),
    ("manga downloader",         "books-reading"),
    ("light novel",              "books-reading"),
    ("magazine",                 "books-reading"),
    ("newspaper",                "books-reading"),
    ("academic paper",           "books-reading"),
    ("college textbook",         "books-reading"),
    ("textbook",                 "books-reading"),
    ("calibre librar",           "books-reading"),
    ("reading site",             "books-reading"),
    ("request book",             "books-reading"),
    ("manual site",              "books-reading"),
    ("history site",             "books-reading"),
    ("religion / esoterica",     "books-reading"),
    ("cooking site",             "books-reading"),
    ("children's site",          "books-reading"),
    ("documents / articles",     "books-reading"),
    ("documents downloader",     "books-reading"),
    ("manga",                    "books-reading"),
    ("comic",                    "books-reading"),
    # education & learning
    ("language learning",        "education-learning"),
    ("educational",              "education-learning"),
    ("courses",                  "education-learning"),
    ("homework",                 "education-learning"),
    ("reference site",           "education-learning"),
    ("programming site",         "education-learning"),
    ("documentaries",            "education-learning"),
    ("documentary",              "education-learning"),
    ("guides",                   "education-learning"),
    # streaming
    ("anime",                    "streaming"),
    ("cartoon",                  "streaming"),
    ("sports streaming",         "streaming"),
    ("live tv",                  "streaming"),
    ("live sport",               "streaming"),
    ("movie/tv",                 "streaming"),
    ("movie / tv",               "streaming"),
    ("streaming forum",          "streaming"),
    ("paid tv",                  "streaming"),
    ("pay-tv",                   "streaming"),
    ("tv-show calendar",         "streaming"),
    ("tv show calendar",         "streaming"),
    ("specialty site",           "streaming"),
    ("subtitles",                "streaming"),
    ("subtitle",                 "streaming"),
    ("full movies on",           "streaming"),
    ("full tv shows on",         "streaming"),
    ("4k/hdr",                   "streaming"),
    ("60 fps movies",            "streaming"),
    ("h265 encoded",             "streaming"),
    ("rare films",               "streaming"),
    ("track upcoming movies",    "streaming"),
    ("wrestling",                "streaming"),
    ("mma",                      "streaming"),
    ("pornhub",                  "streaming"),
    ("porn",                     "streaming"),
    ("xxx",                      "streaming"),
    ("iptv",                     "streaming"),
    ("stream",                   "streaming"),
    # trackers
    ("private tracker",          "trackers"),
    ("semi-private tracker",     "trackers"),
    ("public tracker",           "trackers"),
    ("torrent search",           "trackers"),
    ("torrent invite",           "trackers"),
    ("tracker invite",           "trackers"),
    ("tracker aggregator",       "trackers"),
    ("tracker proxie",           "trackers"),
    ("tracker proxy",            "trackers"),
    ("tracker framework",        "trackers"),
    ("torrent to magnet",        "trackers"),
    ("magnet uri",               "trackers"),
    ("convert torrent",          "trackers"),
    ("rtorrent",                 "trackers"),
    ("webtorrent",               "trackers"),
    ("i2p tracker",              "trackers"),
    ("torrenting",               "trackers"),
    ("torrent",                  "trackers"),
    # usenet
    ("usenet",                   "usenet"),
    # seedboxes
    ("seedbox",                  "seedboxes"),
    # music / audio
    ("audio torrent",            "music-audio"),
    ("podcast download",         "music-audio"),
    ("landr",                    "music-audio"),
    ("music",                    "music-audio"),
    ("video game music",         "music-audio"),
    ("audio",                    "music-audio"),
    # games
    ("pc game",                  "games"),
    ("game repack",              "games"),
    ("game cheat",               "games"),
    ("game achievement",         "games"),
    ("rom bios",                 "games"),
    ("playstation",              "games"),
    ("gamecube",                 "games"),
    ("console game",             "games"),
    ("retro game",               "games"),
    ("emu",                      "games"),
    ("roms",                     "games"),
    ("gaming",                   "games"),
    ("game",                     "games"),
    # apps & software
    ("apk forum",                "apps-software"),
    ("apk platform",             "apps-software"),
    ("nulled script",            "apps-software"),
    ("portables & repack",       "apps-software"),
    ("portables and repack",     "apps-software"),
    ("anti-drm",                 "apps-software"),
    ("anti drm",                 "apps-software"),
    ("android podcast",          "apps-software"),
    ("android radio",            "apps-software"),
    ("android apk",              "apps-software"),
    ("android adblock",          "apps-software"),
    ("android tool",             "apps-software"),
    ("android privacy",          "apps-software"),
    ("android manga",            "books-reading"),
    ("ios apps",                 "apps-software"),
    ("ios app",                  "apps-software"),
    ("ios tool",                 "apps-software"),
    ("ios adblock",              "apps-software"),
    ("ios jailbreak",            "apps-software"),
    ("ios privacy",              "apps-software"),
    ("ios manga",                "books-reading"),
    ("adblocking extension",     "apps-software"),
    ("antivirus",                "apps-software"),
    ("discord client",           "apps-software"),
    ("discord tool",             "apps-software"),
    ("discord alternative",      "apps-software"),
    ("macos",                    "apps-software"),
    ("windows ",                 "apps-software"),
    ("microsoft windows",        "apps-software"),
    ("bypass windows",           "apps-software"),
    ("windows 10",               "apps-software"),
    ("windows hotfix",           "apps-software"),
    ("windows file system",      "apps-software"),
    ("driver website",           "apps-software"),
    ("jetbrains",                "apps-software"),
    ("steam client",             "apps-software"),
    ("steam workshop",           "apps-software"),
    ("seam workshop",            "apps-software"),
    ("pokemon",                  "apps-software"),
    ("wordpress plugin",         "apps-software"),
    ("file sharing app",         "apps-software"),
    ("spotify",                  "music-audio"),
    ("soundcloud",               "music-audio"),
    ("sound effect",             "music-audio"),
    ("vst plugin",               "music-audio"),
    ("album art",                "music-audio"),
    ("youtube tool",             "apps-software"),
    ("twitter tool",             "apps-software"),
    ("reddit downloader",        "apps-software"),
    ("reddit tool",              "apps-software"),
    ("reddit history",           "apps-software"),
    ("reddit hoster tool",       "apps-software"),
    ("adobe",                    "apps-software"),
    ("nfo viewer",               "apps-software"),
    ("keygen",                   "apps-software"),
    ("browser",                  "apps-software"),
    ("all-in-one (electron",     "apps-software"),
    ("messenger app",            "apps-software"),
    ("software",                 "apps-software"),
    # cloud & file hosting
    ("team drive",               "cloud-hosting"),
    ("share drive",              "cloud-hosting"),
    ("google drive",             "cloud-hosting"),
    ("google colab",             "cloud-hosting"),
    ("colaborator",              "cloud-hosting"),
    ("onedrive",                 "cloud-hosting"),
    ("drive indexer",            "cloud-hosting"),
    ("drive link",               "cloud-hosting"),
    ("drive file",               "cloud-hosting"),
    ("ddl",                      "cloud-hosting"),
    ("file hoster",              "cloud-hosting"),
    ("file host",                "cloud-hosting"),
    ("premium link",             "cloud-hosting"),
    ("premium leech",            "cloud-hosting"),
    ("sharehoster",              "cloud-hosting"),
    ("share host",               "cloud-hosting"),
    ("firefox send",             "cloud-hosting"),
    ("send media",               "cloud-hosting"),
    ("send file",                "cloud-hosting"),
    ("content aggregator",       "cloud-hosting"),
    ("link site",                "cloud-hosting"),
    ("free & file",              "cloud-hosting"),
    ("vps hosting",              "cloud-hosting"),
    ("dedicated host",           "cloud-hosting"),
    ("multi host",               "cloud-hosting"),
    ("cloud storage",            "cloud-hosting"),
    ("rapidleech",               "cloud-hosting"),
    ("file leech",               "cloud-hosting"),
    ("upload files for free",    "cloud-hosting"),
    ("image hosting",            "cloud-hosting"),
    ("legal host",                "cloud-hosting"),
    ("email hosting provider",   "cloud-hosting"),
    ("email service",            "privacy-security"),
    ("email site",               "privacy-security"),
    # media servers
    ("kodi",                     "media-servers"),
    ("plex",                     "media-servers"),
    ("stremio",                  "media-servers"),
    ("media centre",             "media-servers"),
    ("media center",             "media-servers"),
    # privacy & security
    ("vpn",                      "privacy-security"),
    ("secure email",             "privacy-security"),
    ("email self-hosting",       "privacy-security"),
    ("email alias",              "privacy-security"),
    ("temp email",               "privacy-security"),
    ("temp mail",                "privacy-security"),
    ("data leak",                "privacy-security"),
    ("database leak",            "privacy-security"),
    ("penetration test",         "privacy-security"),
    ("pen test",                 "privacy-security"),
    ("hardened operating",       "privacy-security"),
    ("hardened os",              "privacy-security"),
    ("anti-spammer",             "privacy-security"),
    ("encryption",               "privacy-security"),
    ("privacy tool",             "privacy-security"),
    ("privacy extension",        "privacy-security"),
    ("hardware security",        "privacy-security"),
    ("cve database",             "privacy-security"),
    ("badusb",                   "privacy-security"),
    ("sim spoofing",             "privacy-security"),
    ("sms bomber",               "privacy-security"),
    ("wifi jammer",              "privacy-security"),
    ("virtual phone",            "privacy-security"),
    ("phone reverse lookup",     "privacy-security"),
    ("reverse proxie",           "privacy-security"),
    ("reverse proxy",            "privacy-security"),
    ("proxy app",                "privacy-security"),
    ("proxy site",               "privacy-security"),
    ("proxies & alternative",    "privacy-security"),
    ("hashcat",                  "privacy-security"),
    ("dns adblock",              "privacy-security"),
    ("cloud based dns",          "privacy-security"),
    ("anonymous cryptocurrency", "privacy-security"),
    ("paypal alternative",       "privacy-security"),
    ("unblock blocked",          "privacy-security"),
    ("tdos",                     "privacy-security"),
    ("real time monitoring of secrets", "privacy-security"),
    # tools & utilities
    ("checksum",                 "tools-utilities"),
    ("ad-blocker",               "tools-utilities"),
    ("ad blocker",               "tools-utilities"),
    ("website archiv",           "tools-utilities"),
    ("media database scraper",   "tools-utilities"),
    ("custom \"google\"",        "tools-utilities"),
    ("custom google",            "tools-utilities"),
    ("domain name",              "tools-utilities"),
    ("edu mail",                 "tools-utilities"),
    ("account",                  "tools-utilities"),
    ("link shortener",           "tools-utilities"),
    ("url shortener",            "tools-utilities"),
    ("url tool",                 "tools-utilities"),
    ("upload a file to",         "tools-utilities"),
    ("convert google drive",     "cloud-hosting"),
    ("automation tool",          "tools-utilities"),
    ("developer tool",           "tools-utilities"),
    ("file tool",                "tools-utilities"),
    ("file renaming",            "tools-utilities"),
    ("image tool",               "tools-utilities"),
    ("image downloader",         "tools-utilities"),
    ("internet tool",            "tools-utilities"),
    ("map tool",                 "tools-utilities"),
    ("screen recorder",          "tools-utilities"),
    ("system tool",              "tools-utilities"),
    ("text tool",                "tools-utilities"),
    ("video tool",               "tools-utilities"),
    ("web page testing",         "tools-utilities"),
    ("online pdf to word",       "tools-utilities"),
    ("convert html to pdf",      "tools-utilities"),
    ("online video converter",   "tools-utilities"),
    ("ripping, transcoding",     "tools-utilities"),
    ("search engine",            "tools-utilities"),
    ("search tool",              "tools-utilities"),
    ("search site",              "tools-utilities"),
    ("search host",              "tools-utilities"),
    ("alternative (private)",    "tools-utilities"),
    ("secure pastebin",          "tools-utilities"),
    ("fake data generator",      "tools-utilities"),
    ("free graphic",             "tools-utilities"),
    ("fonts, icons",             "tools-utilities"),
    ("font site",                "tools-utilities"),
    ("google (web)font",         "tools-utilities"),
    ("gfx",                      "tools-utilities"),
    ("business name generator",  "tools-utilities"),
    ("seo keyword",              "tools-utilities"),
    ("toplist",                  "tools-utilities"),
    ("test linux operating",     "tools-utilities"),
    ("fun site",                 "tools-utilities"),
    ("helpful site",             "tools-utilities"),
    ("free stuff",               "tools-utilities"),
    ("giveaway",                 "tools-utilities"),
    ("tracking / discovery",     "tools-utilities"),
    ("router firmware",          "tools-utilities"),
    ("google docs",              "tools-utilities"),
    ("google sheets",            "tools-utilities"),
    ("google calendar",          "tools-utilities"),
    ("google translate",         "tools-utilities"),
    ("google maps",              "tools-utilities"),
    ("google earth",             "tools-utilities"),
    ("google home",              "tools-utilities"),
    ("google gmail",             "tools-utilities"),
    ("google hangouts",          "tools-utilities"),
    ("google voice",             "tools-utilities"),
    ("google search",            "tools-utilities"),
    ("google play store",        "tools-utilities"),
    ("google domain",            "tools-utilities"),
    ("google analytics",         "tools-utilities"),
    ("google recaptcha",         "tools-utilities"),
    ("google form",              "tools-utilities"),
    ("google ",                  "tools-utilities"),
    # communities & info
    ("piracy archive",           "communities-info"),
    ("the-eye",                  "communities-info"),
    ("open director",            "communities-info"),
    ("ftp indexer",              "communities-info"),
    ("pirate news",              "communities-info"),
    ("pirate blog",              "communities-info"),
    ("scene group",              "communities-info"),
    ("reverse & cracking",       "communities-info"),
    ("reverse and cracking",     "communities-info"),
    ("cracking forum",           "communities-info"),
    ("general filesharing",      "communities-info"),
    ("card sharing",             "communities-info"),
    ("social media alternative", "communities-info"),
    ("darknet",                  "communities-info"),
    ("dvb",                      "communities-info"),
    ("decentralized network",    "communities-info"),
    ("decentralized vpn",        "privacy-security"),
    ("self-hosted vpn",          "privacy-security"),
    ("liability",                "communities-info"),
    ("isp info",                 "communities-info"),
    ("isps you should",          "communities-info"),
    ("tor info",                 "communities-info"),
    ("public dmca",              "communities-info"),
    ("dmca",                     "communities-info"),
    ("countries where",          "communities-info"),
    ("geoip block",              "communities-info"),
    ("predb",                    "communities-info"),
    ("filesharing discussion",   "communities-info"),
    ("piracy discussion",        "communities-info"),
    ("emby server",              "media-servers"),
    ("htcp",                     "privacy-security"),
    ("indexes",                  "tools-utilities"),
    ("reading",                  "books-reading"),
    ("request video",            "streaming"),
    ("sms",                      "privacy-security"),
    ("downloading",              "tools-utilities"),
    ("discord server",           "communities-info"),
    ("irc network",              "communities-info"),
    ("irc search",               "communities-info"),
    ("irc",                      "communities-info"),
    ("dc++",                     "communities-info"),
    ("ipfs",                     "communities-info"),
    ("decentralized local git",  "communities-info"),
    ("big media librar",         "communities-info"),
    ("classic site",             "communities-info"),
    ("download director",        "communities-info"),
    ("download site",            "communities-info"),
    ("content discovery",        "communities-info"),
    ("other languages",          "communities-info"),
    ("special interest",         "communities-info"),
    ("russian",                  "communities-info"),
    ("spanish",                  "communities-info"),
    ("french",                   "communities-info"),
    ("german",                   "communities-info"),
    ("portuguese",               "communities-info"),
    ("korean",                   "communities-info"),
    ("chinese",                  "communities-info"),
    ("finnish",                  "communities-info"),
    ("persian",                  "communities-info"),
    ("forum",                    "communities-info"),
]


def map_category(headings: dict[int, str]) -> tuple[str, str]:
    """Return (category_slug, subcategory_title) for the given heading stack."""
    # Walk from deepest to shallowest, return the most specific match.
    candidates = []
    for level in (4, 3, 2, 1):
        if headings.get(level):
            candidates.append(headings[level])
    sub = candidates[0] if candidates else ""
    for text in candidates:
        lower = text.lower()
        for keyword, slug in KEYWORD_MAP:
            if keyword in lower:
                return slug, sub
    return "communities-info", sub


# ---------- HTML parser ----------

LINK_SKIP_HOSTS = {
    # boilerplate / repo plumbing — not real content
    "googletagmanager.com",
    "img.shields.io",
    "imgur.com",
    "i.imgur.com",
    "awesomeopensource.com",
}

LINK_SKIP_HREF_FRAGMENTS = (
    "#",  # internal anchor links only
)


def normalize_url(href: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if not href:
        return None
    if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
        return None
    # Allow protocol-relative
    if href.startswith("//"):
        href = "https:" + href
    # Coerce missing protocol like "www.example.com/..."
    if not re.match(r"^[a-z][a-z0-9+\-.]*://", href, re.I):
        if href.startswith("www."):
            href = "https://" + href
        else:
            return None
    try:
        parts = urlparse(href)
    except ValueError:
        return None
    if not parts.netloc:
        return None
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https", "ftp", "magnet"):
        return None
    netloc = parts.netloc.lower()
    # strip default ports
    if (scheme == "http" and netloc.endswith(":80")) or (scheme == "https" and netloc.endswith(":443")):
        netloc = netloc.rsplit(":", 1)[0]
    # drop common tracking params
    query = parts.query
    if query:
        kept = []
        for pair in query.split("&"):
            key = pair.split("=", 1)[0].lower()
            if key.startswith("utm_") or key in {"fbclid", "gclid", "ref_src", "ref_url"}:
                continue
            kept.append(pair)
        query = "&".join(kept)
    # trim trailing whitespace from path
    path = parts.path.rstrip()
    normalized = urlunparse((scheme, netloc, path, parts.params, query, parts.fragment))
    return normalized


def host_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except ValueError:
        return ""


class Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: dict[int, str] = {}
        self._heading_level: int | None = None
        self._heading_buf: list[str] = []
        self._in_li: int = 0
        self._li_buf: list[dict] = []  # token stream for current <li>: {kind, data}
        self._link_open: bool = False
        self._link_href: str = ""
        self._link_text_buf: list[str] = []
        self._li_depth_in_li: int = 0  # how many <li>s are currently nested (handle nesting)
        # outputs
        self.entries: list[dict] = []
        self.stats = defaultdict(int)
        self.dropped: list[tuple[str, str]] = []  # (url-or-blank, reason)
        self.unmatched_subcats: set[str] = set()

    # ----- heading -----
    def _maybe_start_heading(self, tag: str) -> None:
        if tag in ("h1", "h2", "h3", "h4"):
            self._heading_level = int(tag[1])
            self._heading_buf = []

    def _maybe_end_heading(self, tag: str) -> None:
        if self._heading_level is not None and tag == f"h{self._heading_level}":
            text = "".join(self._heading_buf).strip()
            # strip leading ► ▷ ► glyphs and surrounding whitespace
            text = re.sub(r"^[►▷▶➤\s]+", "", text)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                self.headings[self._heading_level] = text
                # clear deeper levels
                for lvl in (1, 2, 3, 4):
                    if lvl > self._heading_level:
                        self.headings.pop(lvl, None)
            self._heading_level = None
            self._heading_buf = []

    # ----- list items -----
    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag in ("h1", "h2", "h3", "h4"):
            self._maybe_start_heading(tag)
            return
        if tag == "li":
            if self._in_li:
                # nested <li> — keep tracking depth; treat as text/marker
                self._li_depth_in_li += 1
                self._li_buf.append({"kind": "nested_li_open"})
            else:
                self._in_li = 1
                self._li_buf = []
            return
        if self._in_li and tag == "a":
            href = attrs_d.get("href", "")
            # skip the anchor-style decorative links: <a class="anchor"...>
            classes = attrs_d.get("class", "")
            if "anchor" in classes:
                return
            self._link_open = True
            self._link_href = href
            self._link_text_buf = []
            return
        if self._in_li and tag in ("strong", "em", "code", "span", "p", "br", "ul", "ol"):
            # these don't affect extraction — just pass through
            return

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3", "h4"):
            self._maybe_end_heading(tag)
            return
        if tag == "li":
            if self._li_depth_in_li > 0:
                self._li_depth_in_li -= 1
                self._li_buf.append({"kind": "nested_li_close"})
                return
            if self._in_li:
                self._finalize_li()
                self._in_li = 0
                self._li_buf = []
            return
        if self._in_li and tag == "a" and self._link_open:
            text = "".join(self._link_text_buf).strip()
            self._li_buf.append({
                "kind": "link",
                "href": self._link_href,
                "text": text,
            })
            self._link_open = False
            self._link_href = ""
            self._link_text_buf = []
            return

    def handle_data(self, data):
        if self._heading_level is not None:
            self._heading_buf.append(data)
            return
        if self._link_open:
            self._link_text_buf.append(data)
            return
        if self._in_li:
            self._li_buf.append({"kind": "text", "data": data})

    # ----- finalize -----
    def _finalize_li(self) -> None:
        # Collect links + the trailing text segments after each link.
        links: list[dict] = []
        current: dict | None = None
        post_segments: list[list[str]] = []
        leading_text: list[str] = []
        for tok in self._li_buf:
            if tok["kind"] == "link":
                links.append({"href": tok["href"], "text": tok["text"]})
                post_segments.append([])
                current = post_segments[-1]
            elif tok["kind"] == "text":
                if current is not None:
                    current.append(tok["data"])
                else:
                    leading_text.append(tok["data"])
            # nested_li_open/close: ignore for now

        if not links:
            self.stats["li_no_link"] += 1
            return

        # Use the trailing text after the FIRST link as the entry description.
        # For now, emit one entry per <a> in the <li> — extra links become
        # additional entries inheriting the same description.
        trailing = "".join(post_segments[0]).strip() if post_segments else ""
        # Strip leading separator: " - ", " — ", " or ", " / "
        m = re.match(r"^[\s\-—–]*(?:or|/|,)?\s*(.*)$", trailing, re.S)
        if m:
            trailing = m.group(1)
        # collapse whitespace
        trailing = re.sub(r"\s+", " ", trailing).strip()
        # discard sentinel placeholders
        if trailing in {"/", "//"}:
            trailing = ""

        cat_slug, sub_title = map_category(self.headings)
        if cat_slug == "communities-info":
            # remember unmatched subcategories so the user can re-tune the map
            if sub_title:
                # only flag as unmatched if no keyword matched at all
                matched = False
                for level_text in self.headings.values():
                    if level_text:
                        lt = level_text.lower()
                        for kw, _ in KEYWORD_MAP:
                            if kw in lt:
                                matched = True
                                break
                    if matched:
                        break
                if not matched and sub_title not in {"", "Awesome Warez", "Warez"}:
                    self.unmatched_subcats.add(sub_title)

        for idx, link in enumerate(links):
            url = normalize_url(link["href"])
            if url is None:
                self.dropped.append((link["href"], "invalid url"))
                continue
            host = host_of(url)
            if host in LINK_SKIP_HOSTS:
                self.dropped.append((url, f"boilerplate host {host}"))
                continue
            title = (link["text"] or "").strip()
            title = re.sub(r"\s+", " ", title)
            if not title:
                # try first ~50 chars of trailing/leading text
                title = (trailing or "".join(leading_text).strip())[:60].strip()
            if not title:
                title = host or url
            # description = trailing on first link; subsequent links share it but
            # also append a hint like "mirror of <first title>"
            description = trailing
            if idx > 0 and links[0]["text"]:
                description = (description + (" — mirror of " + links[0]["text"]).strip()).strip(" —")
            self.entries.append({
                "category": cat_slug,
                "subcategory": sub_title,
                "title": html.unescape(title),
                "url": url,
                "description": html.unescape(description) if description else "",
            })


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"missing {SRC}")
    text = SRC.read_text(encoding="utf-8", errors="replace")
    parser = Extractor()
    parser.feed(text)
    parser.close()

    # Dedupe by URL — keep the entry with the longest description, then longest title.
    by_url: dict[str, dict] = {}
    for e in parser.entries:
        prev = by_url.get(e["url"])
        if prev is None:
            by_url[e["url"]] = e
            continue
        # If a later entry has a better category, prefer it (more specific cat
        # is one that isn't communities-info catch-all).
        prev_specific = prev["category"] != "communities-info"
        new_specific = e["category"] != "communities-info"
        if new_specific and not prev_specific:
            by_url[e["url"]] = {**e, "description": prev["description"] or e["description"]}
            continue
        if (len(e["description"]) > len(prev["description"])) or (
            len(e["title"]) > len(prev["title"]) and not prev["description"]
        ):
            by_url[e["url"]] = e

    deduped = list(by_url.values())
    deduped.sort(key=lambda x: (x["category"], x["subcategory"].lower(), x["title"].lower()))

    # assign stable ids
    counters: dict[str, int] = defaultdict(int)
    cat_prefix = {slug: slug[:3] for slug, _, _ in CATEGORIES}
    for e in deduped:
        counters[e["category"]] += 1
        e["id"] = f"{cat_prefix.get(e['category'], 'xxx')}-{counters[e['category']]:04d}"

    # per-category counts
    per_cat = defaultdict(int)
    for e in deduped:
        per_cat[e["category"]] += 1

    out = {
        "generated_at": str(date.today()),
        "categories": [
            {"slug": slug, "title": title, "description": desc, "count": per_cat[slug]}
            for slug, title, desc in CATEGORIES
        ],
        "links": deduped,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # report
    lines = []
    lines.append(f"raw entries:        {len(parser.entries)}")
    lines.append(f"after dedupe:       {len(deduped)}")
    lines.append(f"dropped (invalid/boilerplate): {len(parser.dropped)}")
    lines.append("")
    lines.append("per-category counts:")
    for slug, title, _ in CATEGORIES:
        lines.append(f"  {slug:20s} {per_cat[slug]:5d}   {title}")
    lines.append("")
    if parser.unmatched_subcats:
        lines.append(f"unmatched subcategories ({len(parser.unmatched_subcats)}) — fell back to communities-info:")
        for s in sorted(parser.unmatched_subcats):
            lines.append(f"  - {s}")
        lines.append("")
    if parser.dropped:
        lines.append("first 30 dropped:")
        for url, reason in parser.dropped[:30]:
            lines.append(f"  [{reason}] {url}")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nwrote {OUT}")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
