# STEP: the note's red button never worked, and its bar was not a transport
STATUS: fixed and pushed as v121

THE ERROR BABA PHOTOGRAPHED
- `'model' is a required property` — a 400, every key tried, nothing
  returned. The note's own recorder passed model="" meaning "the
  engine's default", which ttt/providers/groq.py has always understood
  (`model or FAST_STT`). app.py's SECOND COPY of that call did not.
- Same two-implementations fault as v120's language bug, in the same
  function, one version later. That copy has now cost two bugs; it
  should be deleted and routed through the provider, and that is a real
  piece of work rather than a patch.

WHAT CHANGED IN THE NOTE
- The bar is a TRANSPORT: rec, pause, stop. Cut and line are gone — the
  arrows above already delete what they select, so those two were a
  second way to do the same thing sitting where the transport belongs.
- Pause keeps the clock honest: the paused seconds are added back to the
  start time, so it counts recorded time rather than elapsed time.
- "to the box" and "new note" removed. Baba: "I don't know what that
  means." He was right — "to the box" was the old ARCHIVE's habit
  surviving into a place where the note IS the document, and "new note"
  only closed this one, so it was `close` under a second name.
- delete and close now sit small in the upper right corner.
- REMOVED MY OWN DEBUG LOGGING from note_frontend — three console.log
  lines from the v101 investigation had been shipped and left there.

NUMBERS
- notes UI 22 · box 16 · notes 39 · language 13 — green
- measured: actions 15px from the panel's right edge, nothing clipped
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- Four attempts at the corner placement. Sharing a row with the title
  ran `close` past the panel edge (a text_input has a minimum width). An
  empty spacer column collapsed and left both buttons on the left at
  x=54. What worked was aligning the ROW — the same approach that
  finally worked for the notes link, which I had already learned once
  and did not apply.
- One check drove "to the box", the button this change removed. Rewritten
  to test what remains true: opening a note takes the module over, and
  closing it returns the box untouched.

STILL UNSURE
- The note's recorder has still never been seen to SUCCEED. The model
  fix is right and the error it threw is gone, but only Baba pressing it
  proves the whole path.

FOR BABA
- Open a note, press its red rec, speak, press stop. The words should
  appear in the note.
- If it fails, the error is on screen — send me that text.
