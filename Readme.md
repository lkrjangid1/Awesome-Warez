# Awesome Warez

Live site: <https://lkrjangid1.github.io/Awesome-Warez/>

A categorized, deduplicated, searchable index of warez and freedom-of-information resources. Pure static HTML — no Jekyll, no frameworks, no trackers, no ads.

## What's in here

| Path                       | Purpose                                                        |
|----------------------------|----------------------------------------------------------------|
| `index.html`               | Home page with category grid + global search box               |
| `categories/<slug>.html`   | One page per top-level category (14 total)                     |
| `search.html`              | Global fuzzy search powered by [Fuse.js](https://fusejs.io/)   |
| `about.html`               | Disclaimer, credits, and legal notes                           |
| `data/links.json`          | **Single source of truth** for all links                       |
| `assets/css/style.css`     | Theme variables, layout, components                            |
| `assets/js/*.js`           | Vanilla JS for theme toggle, search, and page filtering        |
| `scripts/extract.py`       | One-shot parser: legacy `index.md` → `data/links.json`         |
| `scripts/check_links.py`   | Probes every URL and removes 404/dead entries                  |
| `scripts/render.py`        | `data/links.json` → all HTML pages                             |
| `.github/workflows/`       | GitHub Pages deploy + weekly link-health PR                    |

## Categories

Trackers & Torrents · Usenet · Seedboxes · Streaming · Music & Audio · Games · Apps & Software · Books, Comics & Manga · Education & Learning · Cloud & File Hosting · Media Servers · Privacy & Security · Tools & Utilities · Communities & Info

## Contributing

1. **Add or fix a link** — edit `data/links.json` directly. Each entry has `category`, `subcategory`, `title`, `url`, and `description`. Categories must use a `slug` from `data/links.json#categories[]`.
2. Re-run the renderer:
   ```bash
   python3 scripts/render.py
   ```
3. Commit `data/links.json` and the regenerated HTML files. The Pages workflow will deploy on push.

## Local development

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

Press <kbd>/</kbd> on any page to focus the search box.

## Link health

A scheduled workflow (`.github/workflows/link-check.yml`) runs every Sunday, removes dead entries, and opens a PR for review. To run it locally:

```bash
python3 scripts/check_links.py --workers 48           # conservative (default)
python3 scripts/check_links.py --workers 48 --strict  # also drop timeouts
```

Results are written to `data/dead-links.txt` for inspection.

## Disclaimer

The maintainers do not host, distribute, or endorse pirated content. This is a research and freedom-of-information index of external resources. We are not responsible for the content of any linked site. For takedown requests, contact the destination site or file a DMCA with their host.
