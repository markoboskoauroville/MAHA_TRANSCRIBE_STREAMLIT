# STEP: the note editor would not load, and the frame got tighter
STATUS: fixed and pushed as v122

THE CRASH, AND IT WAS MINE FROM v121
- "Your app is having trouble loading the app.ttt_note component."
- v121 removed the cut and line BUTTONS and left their ids in a
  forEach. getElementById returned null, addEventListener threw, the
  script died before ready() was ever sent — so Streamlit waited, gave
  up, and said only that it could not load. The editor was absent and
  pressing rec did nothing, because nothing was listening.
- Two more dead lookups were waiting in the render handler for the day
  Python sent those labels again. Gone, and setLabel() now skips a
  missing element rather than throwing.

THE TEST THAT WOULD HAVE CAUGHT IT — AND MY FIRST ONE THAT WOULD NOT
- I wrote a source-reading test first. Its mutation SURVIVED: it looked
  for getElementById('bCut'), and the real bug used getElementById(id)
  with the id coming from an array. Invisible to a regex, fatal at
  runtime.
- So tests/gastest/test_components.js EXECUTES every component against a
  fake DOM that knows only the ids really in its markup. Both bugs that
  have shipped are now caught: v121's dead ids, and v101's label
  constant declared in the wrong file.
- Emulating the browser mattered as much as being strict: a browser
  exposes every id as a global, and cassette_frontend uses `bFile` bare.
  Without that the deck failed here while working perfectly for Baba —
  the wrong kind of red.

THE DESIGN, ALL FOUR THINGS HE ASKED FOR
- Tabs at the top: Streamlit reserves room for a header this app does
  not use, which was most of the band. Panel padding trimmed too.
- Each section a shade darker inside its frame — barely a shade, since
  the frames already divide them and colour still means STATE here.
- delete and close are LINKS, not pills, glued to the note's top edge.
- The date is `7:46/23/08/26` — hour without a leading zero, no century,
  no word "made" in front of it explaining what a date already says.
  One date, not two: the later of made and edited.

NUMBERS
- notes 39 · notes UI 22 · box 16 · login 11 · language 13
- components 25 (source) · 18 (executed in node)
- both shipped component bugs mutated and caught
- pyflakes clean

FOR BABA
- Open a note and press its red rec. The editor is back, so this is the
  first time that button has had a chance to work.
- If it fails, the error is on screen — send me that text.
