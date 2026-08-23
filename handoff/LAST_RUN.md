# STEP: the save link under its own file
STATUS: done, pushed as v163. No deploy needed.

WHAT HAPPENED
- Baba: "download link should appear under the file, the same as the
  player does."
- He had to say it twice, in effect: I had already learned this for the
  player in v158 and then built the save flow with a stack of buttons at
  the FOOT of the panel. With ten recordings ticked that is ten names to
  match against ten rows by reading — while under each row there is
  nothing to match, because it is already there.
- `done` belongs to its file now too. Dropping the bytes one recording
  at a time means somebody saving ten does not hold all ten in memory
  until the last is pressed.

THE BUG INSIDE THE MOVE, AND IT WAS THE WORST KIND
- The fetch ran in `_rec_after_actions`, which happens once the whole
  list has already rendered. So the bytes arrived a render too late and
  the buttons appeared only on the NEXT interaction.
- NOTHING FAILED. No error, no traceback — the save link simply did not
  show up. A row can only draw a button for bytes that already exist, so
  the fetching now happens before the rows are drawn.

AND A DEAD STRING REMOVED
- `rec_save_ready` said "press each one to save it to this device" above
  the old stack. The buttons sit under their own rows now, where the
  instruction IS the button — a line of prose explaining a control that
  is already obvious is a line nobody reads twice.

NUMBERS
- box 16 · notes UI 27 — green
- driven against a fake: two ticked, two buttons in two different rows,
  a `done` per file, and clearing one leaves the other
- pyflakes clean
