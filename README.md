# samkp.com

Personal site for Sam Kaplan Pettus. Designed in Canva; published to GitHub Pages
at **samkp.com**. You edit in Canva, run one GitHub Action, and the site rebuilds:
the Action exports each Canva page as a PNG, renders `index.html` with real text
(SEO + accessibility) and clickable link-hotspots over the tape-label buttons.

## Layout

```
assets/            exported page PNGs (page-1.png … page-N.png, stable names)
content.json       all real copy: name, title, meta description, per-page alt + transcriptions
hotspots.json      clickable zones as PERCENTAGE coords {x,y,w,h,url} so they scale
build_site.py      renders index.html from the three inputs above
canva_export.py    CI engine: refresh token → rotate+persist → export pages → download
.github/workflows/publish.yml   manual (workflow_dispatch) publish pipeline
CNAME              samkp.com (custom domain)
```

## The token rotation gotcha (read this)

Canva rotates the refresh token on **every** refresh. If the new one isn't saved,
the next run dies with `invalid_grant`. `canva_export.py` persists the rotated
token **first, before exporting**:
- locally → `canva_tokens.json`
- in CI → writes it back to the `CANVA_REFRESH_TOKEN` repo secret via `gh secret set`,
  which needs a **`GH_PAT`** secret (a PAT allowed to write Actions secrets).

## Local run

```bash
cp .env.example .env      # fill in real values (gitignored)
set -a; . ./.env; set +a
python3 canva_export.py   # exports assets/page-*.png, rotates token into canva_tokens.json
python3 build_site.py     # writes index.html
open index.html
```

## GitHub setup (one time)

1. Create the repo and push this directory.
2. Add repo secrets: `CANVA_CLIENT_ID`, `CANVA_CLIENT_SECRET`, `CANVA_REFRESH_TOKEN`,
   `CANVA_DESIGN_ID` (`DAHO2N3OqNg`), and `GH_PAT`.
3. Settings → Pages → Source = **GitHub Actions**.
4. Settings → Pages → Custom domain = `samkp.com`; add the DNS records GitHub shows
   (A/AAAA to GitHub Pages IPs for the apex, or ALIAS/ANAME); keep the `CNAME` file.
5. Actions tab → **Publish samkp.com** → Run workflow.

## Editing content

- Change words/photos → edit in Canva, re-run the Action.
- Change link targets or hotspot boxes → edit `hotspots.json` (percentages of the
  page image; uncomment the `.hotspot` background in `build_site.py` to see the boxes).
- Change SEO copy / transcriptions → edit `content.json`.
