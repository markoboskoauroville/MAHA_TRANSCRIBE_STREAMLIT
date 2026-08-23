# STEP: insert, without breaking the sentence
STATUS: done, pushed as v145. No deploy needed.

WHAT HAPPENED
- Baba: "I put my cursor, I talk and insert, but it presses Enter or New
  Line after. I do not want that. Just insert that sentence, no New
  Line, no Enter."
- v138 wrapped every insert in blank lines. That is RIGHT for appending
  — a take from the deck is a new pass and each burst of dictation is
  its own paragraph — and WRONG for what he is actually doing: putting
  the cursor inside a line and speaking a clause into it. The words
  arrived and the sentence they belonged to was broken in three.
- Two different acts had one rule. They have two now:
  * NO CURSOR -> append, with a blank line. A new sitting.
  * A CURSOR  -> insert exactly there, with no line break at all.

THE SPACING, WHICH IS THE PART THAT IS EASY TO GET WRONG
- ONE SPACE WHERE ONE IS NEEDED, NONE WHERE IT IS NOT. A caret sitting
  straight after a word needs a space or the two run together; a caret
  already after a space needs nothing, and adding one leaves a double
  space that has to be hunted down later. Both sides checked, both
  mutated.

NUMBERS
- notes 46 (was 43) · notes persist 18 · notes UI 22 — green
- three mutations, all caught: blank lines back (5 red), no space at
  all (2 red), always a space (2 red)
- pyflakes clean

STILL OPEN
- The reset-password test, oldest outstanding.
- test_reader 8, red since v101.
- The owner's tab bar wraps at 360px.
- THE KEYS IN THE SHEET — its own session.
