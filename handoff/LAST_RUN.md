# STEP: the delete reports in its own row
STATUS: done, pushed as v164. No deploy needed.

WHAT HAPPENED
- Baba: "progress bar for delete should appear under the file itself,
  same as player, same as download. Everything is same logic."
- HE IS RIGHT THAT IT IS ONE RULE, and this is the third time he has had
  to say it: whatever an action produces belongs to the row that caused
  it. The player (v158), the save link (v163), and now the delete.
- The panel used to hand itself over — the whole list replaced by one
  bar — so the rows somebody was looking at disappeared while they were
  being removed.

THE CHANGE THAT MADE IT POSSIBLE: ONE DELETE PER RENDER
- The old version looped through every recording inside a single run,
  which is why it could only draw one bar for the batch. Now the queue
  is in session state and each render deletes the head of it and comes
  back.
- The row and its bar are drawn BEFORE the delete runs — Streamlit
  streams elements as the script makes them — so the wait happens in
  front of somebody rather than behind a blank panel.
- Still one at a time on purpose: a failure names the recording it
  happened to and everything after it still gets its chance.

WHAT COST ME THREE ATTEMPTS
- My first scripted edit asserted against text containing an em-dash and
  the heredoc mangled it, so the whole script aborted and nothing
  applied — which at least failed loudly.
- My second sliced from `_run_deletion` to `note_number`, and
  note_number is EARLIER in the file. The slice ran backwards and
  duplicated three functions. Reverted and done by line number.
- LESSON, and it is the same one as v157: a scripted edit that computes
  its own boundaries is a guess unless both boundaries are checked. This
  one printed "runner replaced" while breaking the file.

NUMBERS
- box 16 · notes UI 27 · tier 15 — green
- three deleted end to end: "3 deleted in 0.0s", every tick cleared
- with st.rerun held so the frame could be captured: ONE bar, at 66%,
  inside the row — recording 2 of 3
- pyflakes clean
