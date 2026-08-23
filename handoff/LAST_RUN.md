# STEP: the note keeps its audio too
STATUS: done, pushed as v154. No deploy needed.

WHAT BABA ASKED
- "Storage should work for both systems, recording and note."

WHAT I FOUND, AND IT IS THE ANSWER TO DAYS OF CONFUSION
- transcribe_note_take made a FLAC, transcribed it, and LET IT GO. No
  start_keeping, no put_text, nothing. Every word spoken into a note has
  had its audio thrown away since notes gained a recorder in v101.
- Nothing ever said so, because failing to keep something you never
  promised to keep raises no error. The deck's takes were kept and the
  note's were not, and the two look identical from the outside.
- This is very likely why Baba's Drive holds one folder from 14:36 and
  nothing since: he moved to recording INSIDE notes, and that path
  stored nothing at all. It may not be a broken configuration — it may
  be a feature that was never written.

WHAT IT DOES NOW
- Starts the upload alongside Whisper, exactly as the deck does, so
  keeping costs no waiting.
- Writes the transcript beside the audio afterwards — the same pair, so
  a note's recording is as findable as any other and neither half can
  exist alone.
- AND A FAILED TAKE DOES NOT LEAVE AN ORPHAN. If transcription fails
  after the upload has started, the recording is finished rather than
  abandoned half-written, and the log says the audio is there without
  its words.

FOUR THINGS I GOT WRONG WRITING THE TEST, ALL THE SAME MISTAKE
- I asserted `stt.transcribe` came before `finish_keeping` — it appears
  in BOTH engine branches, so the index found the wrong one.
- Then that `finish_keeping` appears twice — it appears three times,
  because the failure path sits above the success path in the source.
- Both times the test said "wrong order" about code that was right.
  Text position is not execution order, and counting occurrences of
  something I had just written was guessing at my own shape.
- What it asserts now: the LAST finish_keeping comes after the upload
  starts. Mutating start_keeping away fails it.

NUMBERS
- notes UI 27 (was 22) · notes 53 — green
- mutation caught
- pyflakes clean
