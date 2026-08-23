# STEP: numbered notes, and an interface you can resize
STATUS: done, pushed as v148. No deploy needed.

SIX THINGS, AND TWO OF THEM WERE MY MESS
1. THE CONFIRM WAS STILL DARK — asked twice, wrong both times. v141 took
   the red away and I stopped there; the real cause was
   `type="primary"`, which gives Streamlit's own colour rules and they
   win over the link styling beside it. Measured now: `sure?` and
   `close` are the same rgb(177,163,137).
2. THE NOTICE GAP WENT FROM 2px TO 41px — Baba: "you create another
   mess." Correct in direction and absurd in size, because Streamlit's
   container margin added to mine. 0.15rem now, about one line.
3. Serial numbers on the note cards: 1. 2. 3. The POSITION in the list,
   not an id — it exists to point at, so it must match what somebody is
   counting on the screen.
4. The cards have a gold edge and prose-coloured words. The edge says a
   card is a thing you can open; the colour says what is inside is the
   same stuff as the transcript.
5. `add to notes` stood on the box's border when the box was EMPTY. The
   glue is right with text and wrong without it, so the key now carries
   the state — a Streamlit container cannot be given a class, but it
   can be given a different key.
6. INTERFACE SIZE, beside text size. It moves the ROOT font size, which
   every rem in the stylesheet is measured against, so pills, labels,
   links and padding move together. Text size multiplies on top of it.
   Two questions, two controls: "I cannot read the transcript" and "the
   whole thing is too small".

NUMBERS
- tier 15 · box 16 · notes 46 · notes UI 22 · must change 15 ·
  owner edge 5 — green
- browser-measured: card border rgb(245,158,11), text rgb(242,221,180);
  `sure?` identical to `close`; interface size 8px/16px/32px at
  50/100/200
- pyflakes clean

STILL OPEN
- The reset-password test.
- test_reader 8, red since v101.
- THE KEYS IN THE SHEET — its own session.
