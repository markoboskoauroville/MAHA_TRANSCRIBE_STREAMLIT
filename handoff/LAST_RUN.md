# STEP: five pills, one line
STATUS: done, pushed as v130. No deploy needed.

WHAT HAPPENED
- AUTO · HR · ENG · single · multi, all on one row.
- A REVERSAL of v118, which split them precisely because five pills
  clipped below 412px. §27 is the rule that decides it, and it allows
  this: the CELLS may shrink and the TYPE may shrink; what may never
  happen is a word being cut. So the type came down to 0.72rem, nowrap
  holds the row, and the column shares follow the word lengths.
- Measured at 320, 360 and 412px: one line, nothing clipped, no
  sideways scroll at any of them.

NUMBERS
- source 19 · box 16 · tier 12 — green
- pyflakes clean

SEEN WHILE MEASURING, NOT FIXED
- THE TAB BAR WRAPS FOR THE OWNER at 360px: seven tabs go to two lines,
  with `log` alone underneath. A family member has five and stays on one
  line, so this is the owner's screen only — but it is the same orphan
  shape Baba objected to for `multi`, and it will look wrong to him the
  moment he notices. Not touched today because he asked for one thing.

STILL OPEN
- The note's red rec, never seen to work.
- test_reader 8, red since v101.
- Per-provider test buttons; People and the test result as real tables.
- THE KEYS IN THE SHEET — a session of its own, starting by reading Key
  Tester and Password Keyring.
