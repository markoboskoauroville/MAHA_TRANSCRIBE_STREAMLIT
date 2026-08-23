# STEP: an empty note, and actions at the foot
STATUS: done, pushed as v149. No deploy needed.

WHAT HAPPENED
- AN EMPTY NOTE CAN BE MADE ON PURPOSE. `add to notes` with an empty box
  now creates one and OPENS it — there is nothing to see on the card and
  nothing to read in the list, so the only reason to make one is to put
  something in it. A note WITH text stays closed: it is finished.
- The empty guard in NOTES.add is still there, because it exists to stop
  a RERUN turning a silent take into a blank note. `allow_empty`
  separates the two cases, and THE DUPLICATE GUARD is what keeps it
  safe: a second empty note while the first is still empty returns the
  first, so pressing twice cannot fill the list with blanks.
- THE ACTIONS MOVED BELOW THE RECORDER. Baba: "our visual language is
  that actions are written below the text boxes; in the notes they are
  above." He is right and it was the last place that disagreed — every
  other module puts what you can DO under what you are looking at,
  because you read first and act second.

WHAT I BROKE ON THE WAY, AND IT WAS BAD
- Removing a stale comment took the `with st.container(key="noteopen"):`
  line with it. The dedent that followed put the ENTIRE note view inside
  `_del_do()` — so an open note rendered nothing at all, and its body
  would only have run when somebody pressed delete.
- pyflakes was clean throughout. Valid Python, completely wrong
  program. Only opening a note in a browser showed it, and the
  screenshot was a panel with a deck and nothing under it.
- THE LESSON: a scripted deletion that swallows a line of CODE along
  with the comment above it cannot be caught by a syntax check. When a
  comment is removed, read back what sits where it was.

NUMBERS
- notes 50 (was 46) · notes UI 22 · tier 15 — green
- mutation: refusing empty again fails 2
- browser-verified: actions below the recorder, empty note opens itself
- pyflakes clean
