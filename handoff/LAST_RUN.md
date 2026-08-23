# STEP: everything T does is under the box
STATUS: done, pushed as v139. No deploy needed.

WHAT HAPPENED
- `new` moved under the text box and became a link. Baba: "it should
  appear under the text box, not above, and it is not a button, it is
  an action link."
- THE COMMAND ROW IS GONE FROM T ENTIRELY. `new` was the last thing in
  it, and a bordered row holding one word was the widest, emptiest
  thing on the screen.
- The studio tools went with it — grammar, reshape, custom act on the
  same text, so they belong in the same place. The row that held them
  was a second home for one idea.
- T now reads: deck, pills, box, then copy · clear · new · grammar ·
  reshape · custom · add to notes. In the order they are reached: read
  what came back, then act on it.

NUMBERS
- tier 15 (was 13) · box 16 · notes UI 22 — green
- browser-verified: no command row, links under the box, and v138's
  header clearance still holding
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- Four checks looked for the studio tools and `new` in the command row.
  They live under the box now, which means they need TEXT to appear —
  the same rule as copy and clear, and the right one: a new take with
  an empty box is a no-op and there is nothing to fix or reshape.
- Added a check that the free tier still gets none of the studio tools
  once its box HAS text, so seeding cannot hide a tier leak.

STILL OPEN
- The reset-password test.
- test_reader 8, red since v101.
- The owner's tab bar wraps at 360px.
- THE KEYS IN THE SHEET — its own session.
