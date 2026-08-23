# STEP: three words, not four
STATUS: done, pushed as v147. No deploy needed.

WHAT HAPPENED
- `new` is gone. Baba: "we do not need new — copy copies, clear clears
  for new transcription, add to notes if it is empty creates a new
  note." Two words for one act.
- ADD TO NOTES ON AN EMPTY BOX MAKES A BLANK NOTE, which is the useful
  half of what `new` did: a note to open and speak into, rather than a
  blank box. It used to return and do nothing, which reads as a broken
  button.
- The links row now appears even with an empty box, showing only
  `add to notes` — copy and clear stay away, because there is nothing
  to copy or clear.

THE TWO ALIGNMENT FAULTS, AND WHY I KEPT MISSING ONE
- "It is sitting on the buttons. Still did not fix. I asked 2-3 times."
  He was right, and three times I widened the gap BELOW the card. The
  gap he meant was INSIDE it — between his sentence and the buttons
  under it. Read what somebody is pointing AT, not what is nearby.
- And even then my margin did nothing: Streamlit wraps every markdown
  in its own element container, so MY margin sat inside that wrapper
  where the next element could not see it. The wrapper is the thing
  with a neighbour, so the wrapper needed the space. 2px, then 41.
- The links were "dancing" because the row had no align-items: each
  cell stretched to equal height and each link sat wherever its own box
  put it — and `copy` is an IFRAME while the others are buttons, so
  their boxes are different heights. Aligned to flex-end, all on one
  baseline.

AND A GUARD THAT UNDID THE WHOLE CHANGE
- An `if _body:` from v114 still wrapped the T links, from when the row
  held only "add to notes" and an empty box had nothing to keep. It was
  invisible from inside box_links and quietly cancelled the new
  behaviour — the row simply never appeared on an empty box. Found by
  testing the empty case rather than the full one.

NUMBERS
- tier 15 · box 16 · notes UI 22 · must change 15 — green
- browser-measured: notice gap 2px -> 41px; links share one baseline;
  empty box shows only `add to notes` and pressing it says `kept`
- pyflakes clean
