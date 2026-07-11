#!/usr/bin/env python3
"""
build_site.py — render a multi-page static site from content.json + hotspots.json + assets/.

Each page in content.json becomes its own HTML document (its own URL) sharing a top
nav bar. The Canva art shows as a full-bleed responsive PNG with real text layered on
for SEO/accessibility:
  - a real <h1> per page,
  - honest per-panel alt text,
  - .sr-only transcriptions that mirror the art (screen-reader parity, not
    keyword-stuffed hidden text),
  - <a> hotspot overlays positioned as PERCENTAGES so they scale with the image.

Asset/nav links are root-relative ("/assets/...", "/consulting/") so they resolve
from any page directory on the custom domain (site root = samkp.com/).

Run:  python3 build_site.py   ->   writes index.html, consulting/index.html, ...
"""

import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def esc(s):
    return html.escape(str(s), quote=True)


def asset_url(path):
    return "/" + path.lstrip("/")


def render_hotspots(zones):
    out = []
    for z in zones:
        url = z.get("url", "")
        if not url or url == "TODO" or not (z.get("w") and z.get("h")):
            print(f"  ! skipping hotspot '{z.get('label','?')}' (url={url!r}) — not ready")
            continue
        style = f"left:{z['x']}%;top:{z['y']}%;width:{z['w']}%;height:{z['h']}%"
        external = url.startswith("http")
        extra = ' target="_blank" rel="noopener"' if external else ""
        out.append(f'      <a class="hotspot" style="{style}" href="{esc(url)}" '
                   f'aria-label="{esc(z.get("label", url))}"{extra}></a>')
    return "\n".join(out)


def render_nav(nav, current_id):
    items = []
    for n in nav:
        href = n.get("href", "")
        if not href or href == "TODO":
            continue
        external = href.startswith("http")
        extra = ' target="_blank" rel="noopener"' if external else ""
        cur = ' aria-current="page"' if n.get("id") == current_id else ""
        items.append(f'    <a href="{esc(href)}"{cur}{extra}>{esc(n["label"])}</a>')
    return "\n".join(items)


def render_sr_body(sr):
    return "\n".join(f"      <p>{esc(line)}</p>" for line in (sr.get("body") or []))


def render_page(page, site, nav, hotspots_map):
    pid = page["id"]
    sr = page.get("sr_only") or {}
    heading = sr.get("heading") or site["name"]
    asset = page["asset"]
    if not os.path.exists(os.path.join(ROOT, asset)):
        print(f"  ! WARNING: missing asset {asset}")
    hotspots = render_hotspots(hotspots_map.get(pid, []))
    sr_body = render_sr_body(sr)
    sr_block = f'    <div class="sr-only">\n{sr_body}\n    </div>\n' if sr_body else ""

    base = site.get("url", "").rstrip("/")
    title = esc(page.get("title") or site["title"])
    desc = esc(page.get("meta_description") or site["meta_description"])
    canonical = base + page.get("route", "/")
    og_image = base + asset_url(site.get("og_image", asset))
    navbar = render_nav(nav, pid)
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "Person",
        "name": site["name"], "url": site.get("url", ""),
        "jobTitle": "Political organizer, communicator & strategist",
        "description": site["meta_description"],
    }, indent=0)

    return f"""<!doctype html>
<html lang="{esc(site.get('lang','en'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(og_image)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{ld}
</script>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #e8823a; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  .topbar {{ position: sticky; top: 0; z-index: 10; display: flex; align-items: center; justify-content: space-between;
             gap: 10px 24px; flex-wrap: wrap; padding: 12px 22px; background: #14503a; color: #f4efe6; }}
  .topbar .brand {{ font-weight: 700; font-size: 18px; letter-spacing: .02em; color: #f4efe6; text-decoration: none; }}
  .topbar nav {{ display: flex; gap: 20px; flex-wrap: wrap; }}
  .topbar nav a {{ color: #f4efe6; text-decoration: none; opacity: .88; font-size: 16px; }}
  .topbar nav a:hover {{ opacity: 1; text-decoration: underline; }}
  .topbar nav a[aria-current="page"] {{ opacity: 1; font-weight: 700; text-decoration: underline; }}
  main {{ width: 100%; }}
  .panel {{ position: relative; font-size: 0; }}          /* font-size:0 removes the gap under the image */
  .panel img {{ display: block; width: 100%; height: auto; }}   /* full-bleed art, no side whitespace */
  .hotspot {{ position: absolute; display: block; z-index: 2;
             /* debug: uncomment to see the clickable boxes
             background: rgba(255,0,0,.25); outline: 1px solid red; */ }}
  .hotspot:focus-visible {{ outline: 3px solid #1a73e8; outline-offset: 2px; }}
  .skip {{ position: absolute; left: -9999px; top: 0; }}
  .skip:focus {{ left: 8px; top: 8px; z-index: 20; background: #fff; padding: 8px 12px; }}
  .sr-only {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
             overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <a class="brand" href="/">{esc(site['name'])}</a>
  <nav aria-label="Primary">
{navbar}
  </nav>
</header>
<main id="main">
  <section class="panel" id="{esc(pid)}">
    <h1 class="sr-only">{esc(heading)}</h1>
    <img src="{esc(asset_url(asset))}" alt="{esc(page.get('alt',''))}" loading="eager" decoding="async">
{hotspots}
{sr_block}  </section>
</main>
</body>
</html>
"""


def main():
    content = load("content.json")
    hotspots = load("hotspots.json")
    site = content["site"]
    nav = content.get("nav", [])
    hotspots_map = {k: v for k, v in hotspots.items() if not k.startswith("_")}

    for page in content["pages"]:
        doc = render_page(page, site, nav, hotspots_map)
        out_path = os.path.join(ROOT, page["output"])
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(doc)
        print(f"Wrote {page['output']} ({len(doc)} bytes) [{page['id']} -> {page['route']}]")


if __name__ == "__main__":
    sys.exit(main())
