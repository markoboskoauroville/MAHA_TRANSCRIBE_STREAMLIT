# STEP: save a recording to this device
STATUS: done, pushed as v162. No deploy needed.

WHAT HAPPENED
- Baba: "add option to export recorded file to local hard disk. One or
  multiple? All works. If there are multiples, they should download one
  after the other."
- `save` sits with the other links. It works on MANY, like delete —
  copying a file to a disk is the same act repeated, unlike playing or
  transcribing, where several at once is not a thing.

"ONE AFTER THE OTHER" IS A STACK OF BUTTONS, AND THAT IS NOT A DODGE
- A browser will not let a page push files at somebody unasked. That is
  a download bomb, and every browser blocks it after the first. Pressing
  each in turn is the only honest way to do it — and it is also
  recoverable: somebody who changes their mind halfway simply stops
  pressing.
- Each button carries its NAME AND SIZE, so a person can see what they
  are about to put on their phone.

THE WAIT IS NARRATED, because it has to be
- st.download_button needs the bytes at render time, so saving ten
  recordings means ten fetches BEFORE anything appears. Same bar and
  same line as the delete and the second reading: "fetching 2 of 3 ·
  rec-1 · 1.1s".

AND `done` FREES THE MEMORY
- A dozen recordings held in session state is a dozen recordings this
  instance cannot spare — the same reason the deck lets a take go once
  the words are out. The buttons deliberately survive reruns until then,
  because a button that vanishes on the next render cannot be pressed.

NUMBERS
- box 16 · drive text 20 · notes UI 27 · tier 15 — green
- driven against a fake: two ticked, fetched in 1.1s, two buttons
  labelled "rec-0.flac · 120 KB"; they survive a rerun; `done` clears
  both the files and the selection
- pyflakes clean
