# STEP: the armed delete stays readable
STATUS: done, pushed as v141. No deploy needed.

WHAT HAPPENED
- Baba: "it has changed the colour and it is not visible — please do
  not change the colour, keep it the same."
- The armed delete was red on a dark panel. That red was chosen for a
  FILLED button, where the text sits on it in dark ink and reads
  perfectly; as link text on the panel's own background it is nearly
  invisible. One colour, two jobs, and it only worked in one of them.
- It keeps the link's own colour now, identical to `close` — measured,
  same computed value. THE WORDS ARE THE SIGNAL, which is enough: a
  person who has just pressed delete does not need telling in red that
  they pressed delete.
- The admin panel's confirm is untouched. That one IS a filled red
  button with dark text on it, which is the shape this colour is for.

AND A SECOND FAULT, FOUND BY LOOKING
- "delete — sure?" was WIDER than the "delete user" it replaces, so it
  was cut at the panel edge — §27 forbids a cut word outright. It says
  `sure?` now: shorter than what it replaces rather than longer, and
  the question mark carries the whole message.

NUMBERS
- notes UI 22 · notes persist 14 — green
- browser-measured: armed colour rgb(177,163,137), identical to close;
  not clipped
- pyflakes clean

STILL OPEN
- The reset-password test, oldest thing outstanding.
- test_reader 8, red since v101.
- The owner's tab bar wraps at 360px.
- Notes are per-DEVICE until Drive is wired (v140).
- THE KEYS IN THE SHEET — its own session.
