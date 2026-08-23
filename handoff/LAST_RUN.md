# STEP: any size means any size
STATUS: done, pushed as v146. No deploy needed.

WHAT HAPPENED
- Baba: "we said any size. I put 12, I can't. Just don't give 0, 1, 2 —
  something minimum which can make the app unclickable."
- The range was 80–250. That was chosen when the size was a row of eight
  pills and every step had to earn its place. It is a typed number now,
  and refusing 12 because a designer once picked 80 is the app arguing
  with the person using it.
- 5 to 400 now. Five is just above the "0, 1, 2" he said to keep out,
  and not zero, which would be a size that is not a size.

WHY A FLOOR THAT LOW IS SAFE, WHICH IS THE PART I CHECKED FIRST
- This scale resizes the READING SURFACES only — the transcript box,
  the reader, the subtitle. The buttons, the pills and the `default`
  link beside the box are untouched by it.
- Measured at 12: reading text 2.016px, and the `default` link still
  11.2px and tappable. A setting too small to read can always be undone
  in one press, on a control that did not shrink. That is what makes it
  safe, not my judgement about what size somebody should want.
- My first attempt set the floor at 20 and would still have refused the
  12 he actually named — a floor picked by me rather than by him.
  Caught by testing with his number instead of a round one.

NUMBERS
- box 16 · owner edge 5 — green; reader has only its pre-existing
  check 8 red
- browser-measured at 12: text 2px, default link 11.2px, tappable
- pyflakes clean
