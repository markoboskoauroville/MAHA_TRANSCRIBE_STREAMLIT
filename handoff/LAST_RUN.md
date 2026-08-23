# STEP: the panel gets out of its own way
STATUS: done, pushed as v128. No deploy needed.

THE CONFUSION BABA REPORTED, AND WHAT IT ACTUALLY WAS
- "I clicked Reset Password and I got the name AND password. This is
  confusing." Nothing was wrong — the ADD-A-PERSON form sits directly
  under the confirm strip, and two adjacent things read as one. The
  fix is not to explain it but to remove it: while anything is being
  confirmed, the add form does not render.
- A DELIBERATE EXCEPTION to "no new elements appearing on the screen,
  everything is already there, only greyed out." That rule protects
  somebody hunting for a control. This is the opposite case: the owner
  has already found one and is about to end an account. Fewer things on
  screen is the kindness here, and the exception is written at the line
  that makes it.

THE REST
- RED, AND ONLY FOR DELETE. A red frame and a red confirm. Not for
  reset: a reset is recoverable, a delete is not, and red that appears
  for both says nothing about either. Same reservation the recording
  dot lives under.
- THE PEOPLE LIST FOLDS. "If I have 300 people it will fill up my whole
  interface — just make it a folder." Three names fit; thirty do not.
  The count is on the fold's own line, so closed it still answers "how
  many".
- `test` moved onto the engine line. It acts on whichever engine is
  chosen, so it belongs beside them rather than hanging underneath.

NUMBERS
- admin users 50 · engine UI 18 — green
- browser-verified: red frame rgb(217,72,75), add form absent during a
  confirm, People folded, test on the engine row
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- Delete's confirm needed its own key for the red styling to hang off,
  and my blanket rename gave that key to RESET's confirm too — in two
  places. Reset keeps the plain key, and there is now a check asserting
  that the reset strip is NOT the red one.

STILL NOT DONE, from Baba's two messages
- Per-provider test buttons (test Edge, test Groq separately, and one
  each for the studio three).
- The People list and the engine test result as real tables.
- THE KEYS IN THE SHEET — Speechify, AssemblyAI and Claude stored in
  the Google Sheet, read-only there, managed from the app: list, test,
  delete, copying his Key Tester app. This REVERSES his earlier "I will
  never enter the keys table, delete those." It is a session of its own
  and starts by reading Key Tester and Password Keyring.
