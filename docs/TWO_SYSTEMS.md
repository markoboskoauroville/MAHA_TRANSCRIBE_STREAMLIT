# TWO SYSTEMS, AND A FILE EXPLORER

Written from Baba's own description, 23.08.2026, so that any session can
pick this up cold.

---

## The two systems, and why they are two

> *"There are two kinds of notes. We need to distinguish between these
> two. One is together with transcription, so audio and transcription
> match. And then user can add this to the notes and start to edit
> notes. And there's the note, separate note. So there are two separate
> systems."*

**A RECORDING is audio and its transcript, married.** They are made
together, they are about each other, and neither is much use alone. The
transcript can be re-made from the audio; the audio cannot be re-made
from anything. §60 already enforces the pairing on the Drive side —
`putText_` refuses a transcript whose recording has no row, precisely so
that half a pair can never exist.

**A NOTE is a document.** It may have started as a transcript, but the
moment somebody edits it, it stops being a record of what was said and
becomes a thing they are writing. It has no audio, it has no partner,
and it can be empty on purpose (v149).

Treating them as one thing is what has made the notes confusing. A
recording is *evidence* and a note is *work*.

### What this means in Drive

Today everything lands in `USERS/<person>/`, mixed:

```
emina/
  20260823-143616-c5e36f0e/     <- a recording folder
    part_0000.flac
    text.txt                    <- the transcript, beside its audio
  notes.txt                     <- the whole notebook, one file (v143)
```

Baba's shape, and it is better:

```
emina/
  transcriptions/
    20260823-143616-c5e36f0e/
      part_0000.flac
      text.txt
  notes/
    <one file per note>
```

**Two changes, both in the MAIN script**, and both needing a deploy:

1. `recFolder_` puts recordings under `transcriptions/` rather than at
   the top of the person's folder.
2. Notes become one file EACH under `notes/`, rather than one
   `notes.txt` holding all of them.

**MIGRATION IS NOT OPTIONAL AND MUST BE PREVIEWED.** Recordings already
exist at the old path with rows in the sheet pointing at them. Moving
them means either moving the files and rewriting the index, or leaving
old ones where they are and reading both places. The second is uglier
and safer; the first is cleaner and can lose somebody's audio. Whichever
is chosen, it follows the pattern `migrateEnginesPreview` /
`migrateEnginesRun` already set: show what would move, then move it.

### One file per note, not one file for all

Today the whole notebook is one `notes.txt`, replaced whole on every
save. That was right when notes were invisible in Drive. It is wrong for
an explorer:

- a person deleting one note should delete one FILE, not cause a rewrite
  of every note they have;
- two devices editing different notes would each overwrite the other's
  whole notebook;
- and a folder that shows one file called `notes.txt` is not something
  anybody can navigate.

The names must be readable — the first words and a date, not an id, or
the explorer shows a column of `n1 n2 n3`.

---

## The explorer

> *"We're going to create new interface instead of this Google Keep note
> interface. There will be folders which can be collapsed, uncollapsed.
> Inside, for every day, there will be audio files and note files. And
> then user, if he clicks on the note, it opens in the text window. If he
> clicks on the audio, then it opens in the recorder... And there will be
> a square next to each file, and if square is selected, it can be
> deleted, multiple files."*

**Shape:** a folder per DAY, collapsed by default, holding that day's
recordings and notes. A checkbox on each row. Tapping the name opens it;
tapping the box selects it.

**Opening depends on what it is.** A note opens in the text editor that
already exists. A recording opens in the PLAYER — which means the deck
needs a play mode, and Baba said so: *"we need to add play to the
recorder... should be play tab also. So user can also press record and
record new note, audio note."*

**What the person may and may not do**, in his words: *"User cannot
create folder or files, everything is done automatically, but he can
delete and open."* That is the whole permission model and it is a good
one — every file in there was made by an act the app already
understands, so there is nothing to name and nothing to misfile.

**Delete is the only destructive act, and it is plural.** Multi-select
delete on a phone, in an app with no undo, needs the same two presses
the note delete has, and it must say HOW MANY and OF WHAT: "delete 3
recordings and 1 note?" — not "delete 4 items?".

### Why this is worth building

It is a shape everybody already knows. Baba: *"this is very familiar,
user are familiar with this, and they can easily navigate it."* Nobody
has to be taught a folder. And it answers the thing Google Keep's card
list cannot: *where did my recording from Tuesday go, and can I hear it
again.*

### Order of work

Nothing here can be built on top of a Drive that does not have the files
in it. So:

1. **FIRST: find out why `text.txt` and `notes.txt` are not landing.**
   Baba's Drive holds `part_0000.flac` and nothing else.

   The path reads correct: `start_keeping` uploads in the background
   while Whisper works, then `finish_keeping` waits for it, and
   `put_text` writes the transcript into the same folder. `text` is the
   right variable and holds the transcript.

   **THE STRONGEST CANDIDATE, and it fits the evidence exactly.**
   `finish_keeping` waits 90 seconds and then gives up, returning `""`.
   The upload thread is a DAEMON, so it does not stop — it carries on
   and finishes, and the folder appears in Drive. But `_rec_id` was
   empty, so the `if _rec_id:` around `put_text` never ran.

   That produces precisely what he photographed: audio present,
   transcript absent, no error on screen. On a phone over 4G, ninety
   seconds is not a lot.

   If that is it, the fix is not a longer deadline — it is that the
   PAIRING must not depend on a race. Either the text is written by the
   same worker that uploads the audio, or the rec_id is handed back the
   moment registration succeeds rather than when the whole upload does.

   **It needs the log to confirm.** The `log` tab will say one of:
   *"storing did not finish within 90s"* (this theory), *"transcript not
   stored beside the audio"* (the script refused), or nothing at all
   (something else entirely, and then the reading starts over).
2. Split the Drive layout into `transcriptions/` and `notes/`, with a
   preview-then-run migration.
3. One file per note, with readable names.
4. The explorer itself, read-only first: folders, files, open.
5. Then selection and delete.
6. Then play in the deck, and audio notes.

Steps 2 and 3 need a MAIN SCRIPT deploy. Steps 4-6 do not.
