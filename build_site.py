#!/usr/bin/env python3
"""
build_site.py — render index.html from content.json + hotspots.json + assets/.

The page is the Canva art shown as responsive PNG panels, with REAL text layered
on for SEO and accessibility:
  - a real <h1>Sam Kaplan Pettus</h1>,
  - honest per-panel alt text,
  - .sr-only transcriptions that mirror the art (screen-reader parity, not
    keyword-stuffed hidden text),
  - <a> hotspot overlays positioned as PERCENTAGES so they scale with the image.

Run:  python3 build_site.py   ->   writes ./index.html
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


def render_hotspots(zones):
    out = []
    for z in zones:
        url = z.get("url", "")
        # Skip un-calibrated (zero-size) or unset zones so we never ship dead boxes.
        if not url or url == "TODO" or not (z.get("w") and z.get("h")):
            print(f"  ! skipping hotspot '{z.get('label','?')}' "
                  f"(url={url!r}, size={z.get('w')}x{z.get('h')}) — not ready")
            continue
        style = (f"left:{z['x']}%;top:{z['y']}%;"
                 f"width:{z['w']}%;height:{z['h']}%")
        label = esc(z.get("label", url))
        external = url.startswith("http")
        rel = ' rel="noopener"' if external else ""
        tgt = ' target="_blank"' if external else ""
        out.append(f'      <a class="hotspot" style="{style}" href="{esc(url)}" '
                   f'aria-label="{label}"{tgt}{rel}></a>')
    return "\n".join(out)


def render_sr_only(sr):
    if not sr:
        return ""
    parts = []
    nav = sr.get("nav")
    for line in sr.get("body", []):
        parts.append(f"      <p>{esc(line)}</p>")
    return "\n".join(parts)


def render_panel(page):
    idx = page["index"]
    asset = page["asset"]
    if not os.path.exists(os.path.join(ROOT, asset)):
        print(f"  ! WARNING: missing asset {asset} (panel {idx}) — "
              "run the export before building for a complete page.")
    hotspots = render_hotspots(page.get("hotspots", []))
    sr = page.get("sr_only") or {}
    heading = sr.get("heading")
    # Page 1's heading is the real site <h1>; later panels get an <h2>.
    htag = "h1" if idx == 1 else "h2"
    head_html = f'      <{htag} class="sr-only">{esc(heading)}</{htag}>\n' if heading else ""
    body_html = render_sr_only(sr)
    body_block = f'    <div class="sr-only">\n{body_html}\n    </div>\n' if body_html else ""
    return f"""  <section class="panel" id="{esc(page.get('id', 'panel-'+str(idx)))}" aria-labelledby="panel-{idx}-h">
{head_html}    <img src="{esc(asset)}" alt="{esc(page.get('alt',''))}" loading="{'eager' if idx==1 else 'lazy'}" decoding="async">
{hotspots}
{body_block}  </section>"""


def main():
    content = load("content.json")
    hotspots = load("hotspots.json")
    site = content["site"]

    # attach hotspot lists to their pages by id
    for page in content["pages"]:
        page["hotspots"] = hotspots.get(page.get("id"), [])

    panels = "\n".join(render_panel(p) for p in content["pages"])

    title = esc(site["title"])
    desc = esc(site["meta_description"])
    url = esc(site.get("url", ""))
    og_image = esc(site.get("og_image", ""))
    og_image_abs = f"{site.get('url','').rstrip('/')}/{site.get('og_image','')}" if url else og_image
    lang = esc(site.get("lang", "en"))
    name = esc(site["name"])

    doc = f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{esc(og_image_abs)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{json.dumps({
    "@context": "https://schema.org",
    "@type": "Person",
    "name": site["name"],
    "url": site.get("url", ""),
    "jobTitle": "Political organizer, communicator & strategist",
    "description": site["meta_description"],
}, indent=0)}
</script>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #f4efe6; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 900px; margin: 0 auto; }}
  .panel {{ position: relative; }}
  .panel img {{ display: block; width: 100%; height: auto; }}
  .hotspot {{ position: absolute; display: block; z-index: 2;
             /* transparent by default; uncomment to debug placement:
             background: rgba(255,0,0,.25); outline: 1px solid red; */ }}
  .hotspot:focus-visible {{ outline: 3px solid #1a73e8; outline-offset: 2px; }}
  .skip {{ position: absolute; left: -9999px; top: 0; }}
  .skip:focus {{ left: 8px; top: 8px; z-index: 10; background: #fff; padding: 8px 12px; }}
  .sr-only {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
             overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }}
</style>
</head>
<body>
<a class="skip" href="#consulting">Skip to content</a>
<main>
{panels}
</main>
</body>
</html>
"""

    out_path = os.path.join(ROOT, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"Wrote {out_path} ({len(doc)} bytes, {len(content['pages'])} panels).")


if __name__ == "__main__":
    sys.exit(main())
