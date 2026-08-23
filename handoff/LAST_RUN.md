# STEP: play means play
STATUS: done, pushed as v161. No deploy needed.

WHAT HAPPENED
- Baba: "when I select file and press play, very nice player appears
  below that. That works, but user needs to press play. Please make it
  autoplay."
- He is right and it is worth naming why: he had already ticked the file
  and pressed a link called `play`. Being asked to press play again is
  one press too many, and it makes the FIRST press feel as though it did
  not work.

WHAT IT TOOK
- `autoplay` is st.audio's own argument. Nothing to invent and nothing
  to wrap — the reader has been using it since v88 and the archive
  player simply never did.

ONLY THE FIRST PIECE
- A long take is stored as ten-minute pieces. Three players all starting
  at once would be three voices over each other, which is the opposite
  of what he asked for. Piece one starts; the rest wait to be pressed.
- Verified in a browser with a two-part recording: first player
  autoplay=True, second False.

WHAT MIGHT STILL ASK FOR A PRESS, AND WHY IT IS NOT A BUG TO CHASE
- Browsers block autoplay with sound until somebody has interacted with
  the page. By the time this renders, Baba has ticked a checkbox and
  pressed a link, so the gesture is there. Where a browser refuses
  anyway, the player is sitting in front of him with its own button —
  the honest fallback, rather than a fight with a policy that exists for
  good reasons.

NUMBERS
- box 16 · notes UI 27 — green
- browser-verified: [autoplay True, autoplay False]
- pyflakes clean
