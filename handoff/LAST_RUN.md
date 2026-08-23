# STEP: recordings in T, and a delete that narrates
STATUS: done, pushed as v157. No deploy needed.

WHAT MOVED, AND WHAT DID NOT
- The RECORDINGS moved from Settings to T. Baba: "move recording tab
  from settings screen to transcription screen." A recording is made on
  that screen and belongs on it.
- The KEEP-OR-DELETE SETTING STAYED in Settings. That is the line
  between the two screens: a standing choice about how the app behaves
  is made once and lives in Settings; the recordings are things you go
  through. Moving the panel was right; moving this with it would not
  have been.

THE ACTIONS APPEAR TWICE, top and bottom
- Baba asked for it, and the reason shows itself at twenty rows: a
  person who ticks something at the bottom should not scroll up to act
  on it. The keys carry `top`/`bottom`, because two Streamlit widgets
  cannot share a key even when they are one idea.

THE DELETE NARRATES
- Baba: "when there is a deletion in process, show exactly what's going
  on. Verbose status with progress indicator and time."
- IT HAD TO MOVE OUT OF THE CALLBACK. A Streamlit callback cannot draw,
  so a delete started from on_click could not show a bar, a name or a
  clock. The press only records what was asked; the render body does it
  and narrates it.
- A progress bar, and under it the recording being worked on right now:
  "2 of 5 · 20260823-143616-c5e36f0e · 1.4s".
- ONE AT A TIME ON PURPOSE. A batch call would be quicker and would fail
  as one lump; this way a failure names the recording it happened to and
  everything after it still gets its chance.
- WHY IT NARRATES AT ALL: each delete is a round trip to Apps Script,
  which is not fast. Ten recordings is ten waits, and a screen that sits
  still looks broken — which is the moment somebody presses again, and a
  second delete of something already gone reads as a failure.
- The report carries the time and counts each outcome: "2 deleted in
  1.4s", or "2 deleted, 1 could not be — 3.1s".

WHAT BROKE, AND WHAT I UNDID
- My first attempt lifted the panel with a scripted re-indent. It
  mangled an unrelated docstring three hundred lines away and left the
  file unparseable. Reverted to the pushed state and done with precise
  edits instead. A scripted re-indent across a block is not a refactor,
  it is a guess with a wide blast radius.

NUMBERS
- box 16 · tier 15 · owner edge 5 · notes UI 27 · notes 53 ·
  must change 15 — green
- driven against a deliberately SLOW fake Drive (0.7s per delete): four
  listed, two ticked, both action rows present, "2 deleted in 1.4s"
- pyflakes clean
