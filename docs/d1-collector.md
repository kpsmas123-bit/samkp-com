# samkp.com/d1 - live D1 ranked-choice count

Static page on **GitHub Pages**, data refreshed by a **GitHub Actions cron**.
(samkp.com is GitHub Pages behind Porkbun DNS - there is no Cloudflare in the path.)

## Layout

| path | role |
|---|---|
| `d1/index.html` | the page (**not yet added** - needs `d1-count-map.html`) |
| `d1/updates.json` | data the page polls; same-origin at `/d1/updates.json` |
| `d1/updates-loader.js` | drop-in replacement for the `claude.use('db')` block |
| `scripts/build-updates.sh` | polls the county, appends a new entry when one posts |
| `.github/workflows/d1-updates.yml` | cron + manual trigger |

## Data sources

- First choice: `https://alamedacountyca.gov/rovresults/260/index.htm?nocache=<n>`
  scoped to the `Member, City Council, District 1 - Berkeley (RCV)` race block.
  Vote cells carry thousands separators (`1,021`) - stripped on parse.
- Rounds: `.../rcv/260/Berkeley/001-CityCouncil_District_1/RcvDetailedReport.xml?nocache=<n>`
  Read from `choiceGroup/@votes` **only** - the sibling `nonTransferableGroup/@votes1`
  happens to be identical in the Nov 4 snapshot but is a different quantity.
  Candidate names are UPPERCASE there and in report order, so they are mapped to
  canonical names and canonical order. A 404 means no rounds yet -> `rounds: []`.

## Write rules

An entry is appended only when `Last Updated` differs from the newest stored entry.
An update is **rejected** (logged, not written) when:
- a candidate's first-choice total decreases versus the previous entry
- the parsed names are not exactly the five known candidates
- every first-choice total is 0 (zero report)
- an unrecognised name appears in the RCV XML

## Schedule

Mon, Thu & Fri, 4:00-9:00 PM Pacific, every 30 min (11 runs/day), through Dec 3 2026.
Pacific is PST all window (DST ended Nov 1), so 4 PM PT = 00:00 UTC *next day* -
hence cron weekdays are Tue(2)/Fri(5)/Sat(6), i.e. Mon/Thu/Fri PT. Verified:

| cron dow | UTC | Pacific |
|---|---|---|
| 2 | Tue 00:00 | Mon 4:00 PM PST |
| 5 | Fri 00:00 | Thu 4:00 PM PST |
| 6 | Sat 00:00 | Fri 4:00 PM PST |

Thursday is included so **certification on Thu Dec 3 is polled**. The date guard
uses the *Pacific* date, so the Dec 3 runs (which fire Dec 4 UTC) are allowed,
while the next Friday PT run (Dec 4) is blocked. Verified both ways.

County update days Nov 6, 9, 13, 16 and certification Dec 3 are all covered.

Manual run: Actions -> "D1 count updates" -> Run workflow (needs repo write access,
which is why no URL secret is needed).
## Local test

```bash
OUT=/tmp/t.json cp d1/updates.json /tmp/t.json
OUT=/tmp/t.json bash scripts/build-updates.sh    # expect "no change"
```
Override `RESULTS` / `RCVXML` to point at fixtures.


## Page contract (confirmed against the page code)

- `seq` need not be contiguous; the page takes the highest `seq` and sorts by it.
  **New entries must be `seq > 4`** - seq 4 is the baked-in snapshot with ballot-level
  dots. The builder floors at 4 so it can never emit <= 4, even if `updates.json`
  is emptied or truncated.
- `rov_updated` is not date-parsed - the page strips the weekday and ", 2026" and
  shows the remainder as text, so seq 1's "before 9:04 PM" renders fine.
- `label` is displayed as-is (escaped) in the history table; any string works.
- The page matches candidates by **last name, case-insensitive**, and treats
  Blanks/Exhausted/Overvotes as one column. The builder still normalises the
  XML's uppercase names to canonical form so stored entries are byte-comparable
  with the seed - that is what lets the seq4 reproduction test be an exact match.
