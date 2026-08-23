# STEP: the note keeps only its transport
STATUS: done, pushed as v134. No deploy needed.

WHAT HAPPENED
- The five selection arrows are gone from the open note. Baba: "only
  the record, pause and stop are there — these things to select words
  and other things are going."
- They were built for a real problem: editing by thumb without a
  keyboard. But a note is a place to SPEAK into, and five arrows sat
  above the transport competing with it every time one opened.
- THE FUNCTIONS STAY IN THE FILE, unwired — extendWord, extendLine,
  cutSelection, cutLine. The problem they answered has not gone away,
  and deleting working code because its buttons were removed is how a
  solution has to be found twice.

NUMBERS
- notes UI 22 · components 25 (source) · 18 (executed) — green
- browser-checked: no selection row, three transport buttons, no page
  errors
- pyflakes clean

WHY THE COMPONENT HARNESS EARNED ITS KEEP AGAIN
- Removing buttons is exactly what broke the frame in v121: the ids
  were left in a forEach and the whole script died before ready(), so
  the editor simply was not there. The node harness ran this change and
  said the script still runs and a render still does not throw — which
  is the check that would have caught v121 the day it shipped.

STILL OPEN
- The note's red rec, never seen to work — now with nothing else on the
  row to distract from it.
- test_reader 8, red since v101.
- The owner's tab bar wraps at 360px with `log` orphaned underneath.
- THE KEYS IN THE SHEET — its own session.
