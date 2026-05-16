#!/usr/bin/env python3
"""Render data/links.json into static HTML pages for the site."""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
LINKS = ROOT / "data" / "links.json"

# absolute URL for sitemap.xml / OG tags only; on-page links are all relative
SITE_BASE = "https://lkrjangid1.github.io/Awesome-Warez"


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s or "section"


# --- shared template fragments ---

def head(title: str, description: str, *, depth: int) -> str:
    """`depth` is 0 for repo-root pages, 1 for `categories/*.html`."""
    prefix = "../" if depth else ""
    canonical_path = ""  # filled in by caller via additional <link>
    return f"""<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="color-scheme" content="dark light">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="website">
<link rel="icon" type="image/svg+xml" href="{prefix}assets/img/favicon.svg">
<link rel="stylesheet" href="{prefix}assets/css/style.css">
<script>(function(){{var t=localStorage.getItem('theme');if(!t){{t=matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'}}document.documentElement.setAttribute('data-theme',t)}})();</script>
</head>
<body>"""


def header(*, depth: int, current: str = "") -> str:
    prefix = "../" if depth else ""
    def link(slug: str, label: str) -> str:
        active = ' aria-current="page"' if slug == current else ""
        return f'<a href="{prefix}categories/{slug}.html"{active}>{esc(label)}</a>'
    home_active = ' aria-current="page"' if current == "home" else ""
    about_active = ' aria-current="page"' if current == "about" else ""
    return f"""
<header class="site-header">
  <div class="bar">
    <a class="brand" href="{prefix}index.html"{home_active}>
      <img src="{prefix}assets/img/logo.svg" alt="" width="28" height="28">
      <span>Awesome Warez</span>
    </a>
    <form class="search-form" role="search" action="{prefix}search.html" method="get">
      <input type="search" name="q" placeholder="Search 10,000+ links…   press /" aria-label="Search" autocomplete="off">
      <button type="submit" aria-label="Search">Search</button>
    </form>
    <nav class="nav-actions">
      <a class="nav-link" href="{prefix}about.html"{about_active}>About</a>
      <button class="theme-toggle" type="button" aria-label="Toggle theme">
        <span class="theme-icon" data-icon="dark">☾</span>
        <span class="theme-icon" data-icon="light">☀</span>
      </button>
    </nav>
  </div>
</header>
<script src="{prefix}assets/js/theme.js" defer></script>
"""


def footer(depth: int) -> str:
    prefix = "../" if depth else ""
    today = date.today().isoformat()
    return f"""
<footer class="site-footer">
  <div class="bar">
    <p>An index of warez resources — pure static HTML, no tracking. <a href="{prefix}about.html">About &amp; legal</a>.</p>
    <p class="muted">Updated {today} · <a href="https://github.com/lkrjangid1/Awesome-Warez">Source on GitHub</a></p>
  </div>
</footer>
</body></html>
"""


# --- pages ---

def render_home(data: dict) -> str:
    cats = data["categories"]
    total = sum(c["count"] for c in cats)
    cards = []
    for c in cats:
        cards.append(f"""
    <a class="cat-card" href="categories/{c['slug']}.html">
      <h3>{esc(c['title'])}</h3>
      <p>{esc(c['description'])}</p>
      <span class="count">{c['count']:,} links</span>
    </a>""")
    return (
        head("Awesome Warez — categorized index of warez resources",
             "A categorized, deduplicated, searchable index of warez resources — torrents, usenet, streaming, books, games, software, privacy tools, and more.",
             depth=0)
        + header(depth=0, current="home")
        + f"""
<main class="container">
  <section class="hero">
    <h1>Awesome Warez</h1>
    <p class="lede">A curated, searchable index of <strong>{total:,}</strong> warez and freedom-of-information resources across <strong>{len(cats)}</strong> categories.</p>
    <form class="hero-search" role="search" action="search.html" method="get">
      <input type="search" name="q" placeholder="Search across every category…" autocomplete="off" aria-label="Search">
      <button type="submit">Search</button>
    </form>
    <p class="muted small">Press <kbd>/</kbd> anywhere to focus search.</p>
  </section>
  <section class="cat-grid">
    {''.join(cards)}
  </section>
</main>
"""
        + footer(0)
    )


def render_category(data: dict, cat: dict) -> str:
    cat_links = [l for l in data["links"] if l["category"] == cat["slug"]]
    # group by subcategory, preserving original list order within group
    groups: dict[str, list[dict]] = defaultdict(list)
    for l in cat_links:
        groups[l["subcategory"] or "Other"].append(l)
    sub_order = sorted(groups.keys(), key=lambda s: (s.lower() == "other", s.lower()))

    toc_items = []
    sections = []
    for sub in sub_order:
        items = groups[sub]
        sid = slugify(sub)
        toc_items.append(f'<li><a href="#{sid}">{esc(sub)} <span class="muted">({len(items)})</span></a></li>')
        lis = []
        for l in items:
            host = urlparse(l["url"]).netloc
            desc = f' <span class="desc">— {esc(l["description"])}</span>' if l["description"] else ""
            lis.append(
                f'  <li><a href="{esc(l["url"])}" rel="nofollow noopener" target="_blank">{esc(l["title"])}</a>'
                f' <span class="host">{esc(host)}</span>{desc}</li>'
            )
        sections.append(
            f'<section class="sub-section" id="{sid}">'
            f'<h2>{esc(sub)} <span class="muted">({len(items)})</span></h2>'
            f'<ul class="link-list">\n' + "\n".join(lis) + "\n</ul></section>"
        )

    return (
        head(f"{cat['title']} — Awesome Warez",
             cat["description"],
             depth=1)
        + header(depth=1, current=cat["slug"])
        + f"""
<main class="container">
  <nav class="breadcrumb"><a href="../index.html">Home</a> / <span>{esc(cat['title'])}</span></nav>
  <h1>{esc(cat['title'])}</h1>
  <p class="lede">{esc(cat['description'])} <strong>{len(cat_links):,}</strong> links across <strong>{len(groups)}</strong> sub-sections.</p>
  <div class="page-tools">
    <input type="search" id="page-filter" placeholder="Filter this category…" aria-label="Filter this category" autocomplete="off">
    <span class="muted small">Showing <span data-count-visible>{len(cat_links):,}</span> of <span data-count-total>{len(cat_links):,}</span></span>
  </div>
  <details class="toc">
    <summary>Jump to sub-section ({len(groups)})</summary>
    <ul>{''.join(toc_items)}</ul>
  </details>
  <div class="sections">
    {''.join(sections)}
  </div>
</main>
<script src="../assets/js/filter.js" defer></script>
"""
        + footer(1)
    )


def render_search() -> str:
    return (
        head("Search — Awesome Warez",
             "Search across all warez resources indexed on this site.",
             depth=0)
        + header(depth=0, current="search")
        + """
<main class="container">
  <h1>Search</h1>
  <form class="hero-search" id="search-form" role="search">
    <input type="search" id="q" name="q" placeholder="Type to search…" autocomplete="off" autofocus aria-label="Search query">
    <button type="submit">Search</button>
  </form>
  <p class="muted small" id="status">Loading index…</p>
  <noscript><p>Search requires JavaScript. <a href="index.html">Browse by category instead</a>.</p></noscript>
  <div id="results"></div>
</main>
<script src="assets/js/fuse.min.js" defer></script>
<script src="assets/js/search.js" defer></script>
"""
        + footer(0)
    )


def render_about() -> str:
    return (
        head("About — Awesome Warez",
             "About this site, disclaimer, credits, and legal notes.",
             depth=0)
        + header(depth=0, current="about")
        + """
<main class="container prose">
  <h1>About</h1>
  <p>This site is an index of resources related to the warez scene, file-sharing, piracy research, freedom of information, and related tools. Links are categorized, deduplicated, and search-indexed for fast lookup.</p>

  <h2>Disclaimer</h2>
  <p><strong>The maintainers do not host, distribute, or endorse pirated content.</strong> This is a reference index for research, education, and freedom-of-information purposes. We are not responsible for the content of external sites. If you object to a link, contact the destination site's owner or file a DMCA request with their host.</p>

  <h2>Why this exists</h2>
  <ul>
    <li>Research and education on file-sharing ecosystems.</li>
    <li>Freedom of information &mdash; access to legal documents, academic papers, and out-of-print media.</li>
    <li>A reliable, curated alternative to scattered or malware-laden lists.</li>
  </ul>

  <h2>How it's built</h2>
  <p>Pure static HTML. No frameworks, no trackers, no ads. <a href="https://fusejs.io/">Fuse.js</a> is vendored for in-browser fuzzy search. Dark/light theme uses CSS custom properties and a small inline boot script to avoid flash-of-wrong-theme.</p>
  <p>Source data lives in <code>data/links.json</code>; pages are regenerated by <code>scripts/render.py</code>.</p>

  <h2>How often is it updated?</h2>
  <p>Monthly link health checks run via GitHub Actions. Dead links are removed automatically. Manual edits to the JSON are merged via pull request.</p>

  <h2>Credits</h2>
  <ul>
    <li>Forked from <a href="https://github.com/CHEF-KOCH/Warez">CHEF-KOCH/Warez</a>.</li>
    <li>All contributors and demoscene people who built the scene.</li>
    <li>Everyone who has reported broken links or new submissions.</li>
  </ul>

  <h2>Search tips</h2>
  <ul>
    <li>Press <kbd>/</kbd> from any page to focus the search box.</li>
    <li>Search matches title, description, sub-section, and URL fragments.</li>
    <li>The filter input on a category page narrows down only that category.</li>
  </ul>
</main>
"""
        + footer(0)
    )


def render_404() -> str:
    return (
        head("Not found — Awesome Warez",
             "The page you requested doesn't exist.",
             depth=0)
        + header(depth=0)
        + """
<main class="container prose">
  <h1>404 &mdash; Not found</h1>
  <p>This page doesn't exist. Try the <a href="index.html">home page</a> or use the search above.</p>
</main>
"""
        + footer(0)
    )


def render_sitemap(data: dict) -> str:
    today = date.today().isoformat()
    urls = [f"{SITE_BASE}/", f"{SITE_BASE}/search.html", f"{SITE_BASE}/about.html"]
    for c in data["categories"]:
        urls.append(f"{SITE_BASE}/categories/{c['slug']}.html")
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        parts.append(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>")
    parts.append("</urlset>")
    return "\n".join(parts) + "\n"


def render_robots() -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE}/sitemap.xml\n"


def main() -> None:
    data = json.loads(LINKS.read_text(encoding="utf-8"))
    (ROOT / "index.html").write_text(render_home(data), encoding="utf-8")
    (ROOT / "search.html").write_text(render_search(), encoding="utf-8")
    (ROOT / "about.html").write_text(render_about(), encoding="utf-8")
    (ROOT / "404.html").write_text(render_404(), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(render_sitemap(data), encoding="utf-8")
    (ROOT / "robots.txt").write_text(render_robots(), encoding="utf-8")
    cat_dir = ROOT / "categories"
    cat_dir.mkdir(parents=True, exist_ok=True)
    for c in data["categories"]:
        (cat_dir / f"{c['slug']}.html").write_text(render_category(data, c), encoding="utf-8")
    print(f"rendered home + {len(data['categories'])} category pages + search/about/404 + sitemap + robots")


if __name__ == "__main__":
    main()
