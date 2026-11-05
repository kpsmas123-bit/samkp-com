/* ---------------------------------------------------------------------------
   Drop-in replacement for the window.claude.use('db') block.

   Returns exactly the shape the page already consumes:
     [{ seq, label, rov_updated, first_choice:{"Laura Babitt":n,...},
        rounds:[{round, candidate, votes}, ...] }]

   Two call-sites to wire up (marked TODO) once d1-count-map.html is in hand:
     EMBEDDED_FALLBACK - the page's existing inline Nov 4 array
     render(updates)   - whatever the page already calls to draw itself
--------------------------------------------------------------------------- */

const UPDATES_URL  = '/d1/updates.json';
const POLL_MS      = 5 * 60 * 1000;          // 5 minutes, per spec
const EMBEDDED_FALLBACK = window.EMBEDDED_UPDATES || []; // TODO: point at the inline array

let lastGoodJSON = null;

function normalise(data) {
  if (!Array.isArray(data)) throw new Error('updates.json is not an array');
  // defensive: sort by seq so render order never depends on file order
  return data.slice().sort((a, b) => (a.seq || 0) - (b.seq || 0));
}

async function loadUpdates() {
  try {
    const res = await fetch(UPDATES_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = normalise(await res.json());
    if (!data.length) throw new Error('empty array');
    lastGoodJSON = data;
    return data;
  } catch (err) {
    // Never let a transient fetch failure blank the page.
    console.warn('[d1] updates.json unavailable (' + err.message + ') - using fallback');
    return lastGoodJSON || normalise(EMBEDDED_FALLBACK);
  }
}

async function refresh() {
  const updates = await loadUpdates();
  render(updates);   // TODO: existing render entry point
}

refresh();
setInterval(refresh, POLL_MS);
