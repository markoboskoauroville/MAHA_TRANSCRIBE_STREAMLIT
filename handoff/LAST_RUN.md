# STEP: the reading tab, corrected
STATUS: done, pushed as v125

WHAT HAPPENED
- The voices are grouped by language again: HR · Gabi · Srećko · ENG ·
  Sonia · Ryan, all on one row. A REVERSAL, and a deliberate one — the
  headings were removed once on Baba's own reasoning ("we know Gabrijela
  and Srećko are Croats"). Both readings are right about different
  people: he knows which voice speaks what, somebody meeting the app
  does not. So the tags return as TAGS — dim, small, in the row — not as
  headings on lines of their own. The row still costs one line, which is
  what the removal was protecting.
- "Gabby" is "Gabi". An English shortening of a Croatian name, sitting
  next to Srećko who kept his diacritic.
- The tags say HR and ENG, the same words as the pills in T.
  lang.upper() gave "EN", which is correct and is not what the rest of
  the app says — two names for one language on two screens is how
  somebody starts wondering whether they mean the same thing.
- The voices moved ABOVE the player. Choosing who reads comes before
  pressing play, so the screen reads in that order.
- "New text" is gone. The box is always there and typing in it is how a
  new text begins; the button was a second way to say "finished with
  this one", which the next press of play says by itself.
- A grey line under the box: "press play to read". The read button was
  removed on purpose in §64 and nothing on the screen said where play
  had gone.

NUMBERS
- tier 12 — green; R renders with no exception
- pyflakes clean

STILL RED, AND NOT FROM TODAY
- test_reader check 8, "changing voice DROPS the cache". It fails on
  v101 as pushed, so it is mine but older than this round. The detail
  says synth_rebuilt: True and cache_keys: [] — the closure IS rebuilt
  and the cache is never refilled, which is either a real gap in the
  rebuild path or a check that cannot be reached from AppTest at all.
  I did not chase it here rather than half-chase it; it deserves its
  own pass.

FOR BABA
- The note's red rec has still never been seen to work. Oldest open
  thing in the app.
- And the four items from v124's list are still waiting, one of them on
  a question: usage as totals only, or totals plus one shared events
  tab keeping the detail.
