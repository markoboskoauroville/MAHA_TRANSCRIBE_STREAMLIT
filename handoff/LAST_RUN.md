# STEP: AUTO first and in caps, and the link on the right
STATUS: done, pushed as v119

WHAT HAPPENED
- AUTO · HR · ENG, in that order, AUTO in caps like the other two.
- "add to notes" now sits at the right edge, 11px in — the button's own
  padding — lined up with the tab signature below it.

THE PART WORTH READING: SEVEN ROUNDS TO MOVE A LINK
- I changed the CSS six times and measured no improvement, or a small
  one, every time. The reason was not Streamlit being difficult. It was
  that I kept styling the thing I wanted to move instead of measuring
  what was holding it.
- The nesting is button > div > p, and each layer had its own answer:
  the ELEMENT CONTAINER was 128px inside a 390px parent; the BUTTON had
  `width: 100%` immediately followed by `width: auto` — a leftover from
  an earlier attempt, so the last one won and every rule after it argued
  with a line I had forgotten to delete; and the DIV inside the button
  is a flex with justify-content: center, so a full-width button still
  centred a 104px paragraph.
- What ended it was walking the ancestor chain and printing the computed
  width of every level. That took one command and should have been the
  FIRST thing, not the seventh.
- Two wrong turns worth recording: I blamed st.columns stacking (they do
  not stack here — the language pills prove it), and I blamed a column
  flex direction (it is a row). Both were guesses dressed as diagnoses.

NUMBERS
- inset from right: 11px, measured
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- Nothing in the app. But I booted a dead server SIX more times because
  my cleanup removes the stub secrets and I keep writing the boot before
  the secrets. Third handoff running that this appears in.

STILL UNSURE
- Nothing here.

FOR BABA
- Still waiting from v114: open a note, press the DECK's rec — the words
  should join the note. Then the note's own red button; if it fails its
  error is on screen now.
- And auto: try a Croatian sentence and an English one and see whether
  it holds.
