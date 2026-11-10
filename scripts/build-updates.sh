#!/usr/bin/env bash
# Appends a new entry to d1/updates.json when the county posts a new report.
# Exit 0 = nothing to do (no change / rejected). Exit 1 = hard failure.
set -uo pipefail

RACE="Member, City Council, District 1 - Berkeley (RCV)"
OUT="${OUT:-d1/updates.json}"
RESULTS="${RESULTS:-https://alamedacountyca.gov/rovresults/260/index.htm}"
RCVXML="${RCVXML:-https://alamedacountyca.gov/rovresults/rcv/260/Berkeley/001-CityCouncil_District_1/RcvDetailedReport.xml}"
CANDS=("Laura Babitt" "Ross Bernet" "Daria Wrubel" "Moni Gangopadhyay" "Steve Kromer")

log(){ printf '%s %s\n' "[$(date -u +%H:%M:%SZ)]" "$*" >&2; }
nc(){ date +%H%M%S%N | cut -c1-9; }   # always-fresh cache buster
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

# ---------- fetch results page ----------
code=$(curl -sS --max-time 60 --retry 3 --retry-delay 5 \
        -o "$tmp/results.htm" -w '%{http_code}' "$RESULTS?nocache=$(nc)") || { log "FATAL: results fetch failed"; exit 1; }
[ "$code" = 200 ] || { log "FATAL: results page HTTP $code"; exit 1; }

ROV=$(grep -o -i -m1 'Last Updated:[^<]*' "$tmp/results.htm" | sed -e 's/^[Ll]ast [Uu]pdated:[[:space:]]*//' -e 's/[[:space:]]*$//')
[ -n "$ROV" ] || { log "FATAL: could not read Last Updated"; exit 1; }
log "county Last Updated: $ROV"

# ---------- dedupe before doing any more work ----------
PREV_ROV=$(jq -r 'if length==0 then "" else (max_by(.seq).rov_updated // "") end' "$OUT")
if [ "$ROV" = "$PREV_ROV" ]; then log "no change (matches latest stored entry) - nothing to do"; exit 0; fi

# ---------- first-choice votes, scoped to the D1 race block ----------
awk '/<!-- Start Race: Member, City Council, District 1 - Berkeley \(RCV\)-->/,/<!-- End panelDtl Member, City Council, District 1 - Berkeley \(RCV\) -->/' \
    "$tmp/results.htm" > "$tmp/d1.htm"
[ -s "$tmp/d1.htm" ] || { log "FATAL: D1 race block not found (page structure changed?)"; exit 1; }

tr -d '\n' < "$tmp/d1.htm" \
  | grep -oE 'scope="row">[^<]+</TH>[[:space:]]*<TD[^>]*>[0-9,]+' \
  | sed -E 's|scope="row">||; s|</TH>[[:space:]]*<TD[^>]*>|\t|' \
  | awk -F'\t' '{gsub(/,/,"",$2); gsub(/^[ \t]+|[ \t]+$/,"",$1); print $1"\t"$2}' > "$tmp/fc.tsv"

log "parsed $(wc -l < "$tmp/fc.tsv" | tr -d ' ') first-choice rows"

# ---------- validate: exactly the 5 known candidates ----------
printf '%s\n' "${CANDS[@]}" | sort > "$tmp/want"
cut -f1 "$tmp/fc.tsv" | sort > "$tmp/got"
if ! diff -q "$tmp/want" "$tmp/got" >/dev/null; then
  log "REJECT: candidate names do not match the expected 5. Parsed:"; sed 's/^/  /' "$tmp/got" >&2; exit 0
fi

# ---------- validate: not a zero report ----------
TOTAL=$(awk -F'\t' '{s+=$2} END{print s+0}' "$tmp/fc.tsv")
if [ "$TOTAL" -eq 0 ]; then log "REJECT: zero report (all first-choice totals are 0)"; exit 0; fi

# ---------- validate: no candidate's first-choice total went down ----------
# Only the 5 candidate rows live in fc.tsv, so this guard never touches
# Blanks / Exhausted / Overvotes - by design: those may legitimately fall.
if [ -n "$PREV_ROV" ]; then
  bad=0
  while IFS=$'\t' read -r name votes; do
    prev=$(jq -r --arg n "$name" 'max_by(.seq).first_choice[$n] // 0' "$OUT")
    if [ "$votes" -lt "$prev" ]; then log "REJECT: $name went DOWN $prev -> $votes"; bad=1; fi
  done < "$tmp/fc.tsv"
  [ "$bad" -eq 0 ] || { log "not writing - monotonicity violated"; exit 0; }
fi

# ---------- RCV rounds (404 = no rounds published yet) ----------
rcode=$(curl -sS --max-time 60 --retry 2 --retry-delay 5 \
         -o "$tmp/rcv.xml" -w '%{http_code}' "$RCVXML?nocache=$(nc)") || rcode=000
: > "$tmp/rounds.tsv"
if [ "$rcode" = 200 ]; then
  tr '<' '\n' < "$tmp/rcv.xml" \
    | grep -E 'Tablix5 Textbox86="Round |choiceGroup choiceName2=' \
    | sed -E 's/.*Textbox86="Round ([0-9]+)".*/@\1/; s/.*choiceName2="([^"]*)" votes="([0-9]+)\..*/\1\t\2/' \
    | awk -F'\t' '/^@/{r=substr($0,2); next} NF==2{print r"\t"$1"\t"$2}' > "$tmp/raw.tsv"

  # XML uses UPPERCASE candidate names in report order; normalise to canonical name + canonical order
  awk -F'\t' -v unmapped="$tmp/unmapped" 'BEGIN{
      m["LAURA BABITT"]="Laura Babitt";           o["Laura Babitt"]=1
      m["ROSS BERNET"]="Ross Bernet";             o["Ross Bernet"]=2
      m["DARIA WRUBEL"]="Daria Wrubel";           o["Daria Wrubel"]=3
      m["MONI GANGOPADHYAY"]="Moni Gangopadhyay"; o["Moni Gangopadhyay"]=4
      m["STEVE KROMER"]="Steve Kromer";           o["Steve Kromer"]=5
      m["Blanks"]="Blanks";                       o["Blanks"]=6
      m["Exhausted"]="Exhausted";                 o["Exhausted"]=7
      m["Overvotes"]="Overvotes";                 o["Overvotes"]=8
    }
    { n=m[$2]; if(n==""){ print $2 >> unmapped; next }
      printf "%s\t%d\t%s\t%s\n", $1, o[n], n, $3 }' "$tmp/raw.tsv" \
    | sort -t"$(printf '\t')" -k1,1n -k2,2n | cut -f1,3,4 > "$tmp/rounds.tsv"

  if [ -s "$tmp/unmapped" ]; then
    log "REJECT: unrecognised name(s) in RCV XML - report structure may have changed:"
    sort -u "$tmp/unmapped" | sed 's/^/  /' >&2
    exit 0
  fi
  log "rounds: $(wc -l < "$tmp/rounds.tsv" | tr -d ' ') rows across $(cut -f1 "$tmp/rounds.tsv" | sort -u | wc -l | tr -d ' ') round(s)"
else
  log "no RCV rounds (HTTP $rcode) - omitting"
fi

# ---------- validate: no candidate's round total went down ----------
# Blanks / Exhausted / Overvotes can legitimately FALL when the county adjudicates
# ballots (round-1 Overvotes went 53 -> 45 between Nov 06 and Nov 09), so those three
# rows are exempt from the decrease check. Candidate rows may only fall to 0, which
# means that candidate was eliminated a round earlier than in the previous report.
if [ -s "$tmp/rounds.tsv" ] && [ -n "$PREV_ROV" ]; then
  jq -r 'max_by(.seq).rounds[]? | [(.round|tostring), .candidate, (.votes|tostring)] | @tsv' \
     "$OUT" > "$tmp/prev_rounds.tsv"
  if [ -s "$tmp/prev_rounds.tsv" ]; then
    bad=0
    while IFS=$'\t' read -r rnd name votes; do
      case "$name" in Blanks|Exhausted|Overvotes) continue ;; esac
      prev=$(awk -F'\t' -v r="$rnd" -v n="$name" '$1==r && $2==n {print $3; exit}' "$tmp/prev_rounds.tsv")
      [ -n "$prev" ] || continue          # round not present last time - nothing to compare
      [ "$votes" -eq 0 ] && continue      # eliminated in this report, not a real decrease
      if [ "$votes" -lt "$prev" ]; then
        log "REJECT: round $rnd $name went DOWN $prev -> $votes"; bad=1
      fi
    done < "$tmp/rounds.tsv"
    [ "$bad" -eq 0 ] || { log "not writing - round monotonicity violated"; exit 0; }
  fi
fi

# ---------- label: "Nov 06, 5:30 PM" from the county timestamp ----------
LABEL=$(printf '%s' "$ROV" | sed -E 's/^[A-Za-z]+, ([A-Za-z]+) ([0-9]+), [0-9]{4}; (.*)$/\1 \2, \3/')
[ -n "$LABEL" ] && [ "$LABEL" != "$ROV" ] || LABEL="$ROV"

# ---------- append ----------
jq  --arg rov "$ROV" --arg label "$LABEL" \
    --rawfile fc "$tmp/fc.tsv" --rawfile rd "$tmp/rounds.tsv" '
  def rows($s): ($s|rtrimstr("\n")) as $t | if ($t|length)==0 then [] else ($t|split("\n")|map(split("\t"))) end;
  . as $all
  | ([ (if length==0 then 0 else (max_by(.seq).seq) end), 4 ] | max) as $last   # floor at 4: seq 4 is the baked-in snapshot, never reuse <= 4
  | $all + [{
      seq: ($last + 1),
      label: $label,
      rov_updated: $rov,
      first_choice: (rows($fc) | map({key:.[0], value:(.[1]|tonumber)}) | from_entries),
      rounds: (rows($rd) | map({round:(.[0]|tonumber), candidate:.[1], votes:(.[2]|tonumber)}))
    }]' "$OUT" > "$tmp/new.json" || { log "FATAL: jq build failed"; exit 1; }

jq -e 'type=="array" and length>0' "$tmp/new.json" >/dev/null || { log "FATAL: output invalid"; exit 1; }
mv "$tmp/new.json" "$OUT"
log "APPENDED seq $(jq -r 'max_by(.seq).seq' "$OUT") \"$LABEL\" ($ROV)"
echo "changed=true"
