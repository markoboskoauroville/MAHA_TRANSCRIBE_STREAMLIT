# STEP: the top of the screen, on a phone
STATUS: done, pushed as v150. No deploy needed.

WHAT BABA SAW
- Streamlit's toolbar — Share, the star, the pencil, the GitHub mark,
  the three dots — printed ACROSS his tab row. "Share" sat on top of TR.
- It only shows on a phone: the header those icons live in is fixed and
  narrow enough there that the icons and the tabs occupy the same band.

THE FIX, AND WHY IT IS A REMOVAL
- The toolbar is gone. It is Streamlit's, not this app's: Share, fork,
  star and edit belong to a demo somebody might copy, not to his
  family's transcriber. Nobody here has ever pressed one.
- Removing it removes the collision ENTIRELY rather than negotiating
  with it — which is what padding-top had been doing since v138, and
  what it kept losing. The page top came back from 64px to 12px as a
  result, which is where Baba wanted it in the first place.
- THE RUNNING INDICATOR STAYS. It is the only thing up there that says
  the app is working, and on a slow phone that is the difference
  between waiting and pressing again.

AND THE ORPHAN I HAD LEFT
- The owner's seven tabs wrapped at 360px with `log` alone underneath —
  the same shape Baba objected to for `multi`, noted at v130 and not
  fixed. One row now, nothing clipped, no sideways scroll.
- My first attempt styled `stSegmentedControl`. The element that
  actually wraps is `.stButtonGroup`'s inner div; I found it by walking
  up from the `log` tab and printing each ancestor's computed display
  and flex-wrap. Same lesson as the add-to-notes link: when a rule does
  nothing, print the chain instead of guessing at a test-id.

NUMBERS
- box 16 · tier 15 · owner edge 5 — green
- measured on a 360px MOBILE viewport: toolbar hidden, 7 tabs, 1 row,
  0 clipped, 0 overflow
- pyflakes clean

STILL UNANSWERED FROM BABA
- "There is no note next to recording, only recording." I do not
  understand this one and have NOT guessed at it — see the reply.
