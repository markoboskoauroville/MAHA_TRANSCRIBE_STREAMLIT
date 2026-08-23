# STEP: your recordings, and what happens to them
STATUS: done, pushed as v156. **NO DEPLOY NEEDED.**

WHAT BABA ASKED FOR
- "A remote file manager for Google Drive so user can delete its
  recording from this interface... just a table of files, mark the check
  mark and press delete. Nothing fancy, most basic."
- "A radio button to keep audio files after transcription or delete them
  automatically."
- "An audio player for stored files and retranscribe option."

WHAT WAS ALREADY THERE, UNUSED
- `audio_list` and `audio_del` have been in the DEPLOYED script all
  along, and ttt/drive.py already had list(), delete() and fetch().
  The whole feature was sitting there waiting. No deploy, no script
  change, nothing to paste.

WHAT IT DOES
- A fold in the grey gear: one row per recording, date · minutes · a
  mark if it has a transcript. Tick what you want.
- The actions appear ONLY when something is ticked, because a delete
  link with nothing selected is a question with no answer.
- `play` and `transcribe again` act on the first ticked; `delete` acts
  on all of them, in two presses, and the second one SAYS HOW MANY —
  "delete 3?" is a number somebody can check against what they ticked,
  "are you sure?" is not.
- Delete reports each outcome separately: "2 deleted, 1 could not be".
  A single "done" over a batch that half-worked is a lie by omission.
- KEEP AUDIO / DELETE AFTER, with a sentence under it saying what the
  choice costs. "Delete automatically" sounds like tidiness and is
  actually a decision about whether these words can ever be recovered.
  It obeys in BOTH recorders — the deck and the note — or "delete after"
  would be true of one and not the other, which is exactly the split
  that hid the note storage gap for fifty versions.

THREE THINGS I GOT WRONG WRITING IT
- I called `ttt_audio.join(parts)`. THERE IS NO JOINER IN THIS CODEBASE.
  Inventing one would have meant an ffmpeg concat, a temp file and a new
  failure mode, for a long take that is stored as pieces on purpose. It
  plays the parts in order, numbered, which is honest and costs nothing.
- I named the setting `keep_audio` — there is already a FUNCTION called
  that in the same module. A settings key and a function sharing a name
  is a reader's trap and one would eventually be mistaken for the other.
  It is `keep_recordings`.
- The radio printed the panel's heading a second time:
  label_visibility="collapsed" hides a label from SIGHT but Streamlit
  still renders it, and here it showed.

NUMBERS
- box 16 · drive text 20 · owner edge 5 · notes UI 27 · must change 15
- driven end to end against a fake Drive in a real browser: two rows
  listed, one ticked, "delete 1?", then "1 deleted" and one row left
- pyflakes clean
