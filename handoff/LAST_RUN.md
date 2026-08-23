# STEP: the links match, measured
STATUS: done, pushed as v142. No deploy needed.

WHAT HAPPENED
- copy · clear · new · add to notes are now one size and one colour —
  14px, rgb(177,163,137), MEASURED on both sides in a browser.
- Baba named the cause himself: "styles are coming from different
  sources." `copy` is a COMPONENT and its neighbours are not. It has to
  be — nothing but a real button in a real document can reach the
  clipboard — so it lives in an iframe with its own stylesheet.

THE THREE TRAPS, NOW IN HOW_WE_WORK.md
1. `rem` INSIDE AN IFRAME resolves against the iframe's root, not the
   page's. Both files said 0.72rem and they rendered at different
   sizes: the same number in two files meaning two things.
2. CSS VARIABLES DO NOT CROSS. var(--dim) in the component resolves to
   nothing; colours must be literal hex, so a colour changed on the
   page does not follow.
3. THE PAGE'S COMPUTED VALUE IS NOT WHAT ITS STYLESHEET SAYS. `clear`
   computes to 14px, not the 11.5px its 0.72rem implies — other rules
   win. Deriving the component's numbers from the stylesheet gave the
   wrong answer TWICE.

WHAT I GOT WRONG ON THE WAY
- My first fix made the component scale with Baba's text-size setting.
  That would have made `copy` GROW while `clear` beside it stayed put,
  because the setting resizes text areas and reading surfaces, not the
  page root. Caught by measuring before shipping rather than after.
- My second used a colour this file had been guessing at. Also wrong,
  also only visible once measured.

NUMBERS
- box 16 · tier 15 — green
- browser-measured: clear ['14px','rgb(177,163,137)'], copy the same.
  MATCH: True
- pyflakes clean
