# STEP: add-to-notes link, and the deck that fed the wrong surface
STATUS: done, pushed as v114

WHAT HAPPENED
- An orange "add to notes" LINE under the box, not a button. The box
  already carries five command keys; a sixth full-width button would
  compete with them for what is an afterthought — you read what came
  back, then you decide to keep it. It takes what is IN THE BOX, so a
  grammar pass or a hand edit is what gets kept.
- Notes are no longer made AUTOMATICALLY from every take. They were,
  which filled the list with false starts and would have made the new
  link produce a second copy of something already there. Nothing is lost
  by waiting: the audio and its text.txt are in Drive either way (§60).

THE REAL BUG HE REPORTED, AND IT WAS MINE
- "It does not insert what I say to note." With a note open, the DECK
  still wrote to the text box — and the box is not drawn while a note is
  open, because that is the takeover working. So the words landed on a
  surface nobody could see. Not lost. INVISIBLE, which is worse: the app
  looked broken rather than wrong.
- v98's comment says the deck is "the note's own record button". The
  code never made that true. It does now: deliver_text asks whether a
  note is open and appends there.
- AND `_note_error` was written in two places and displayed in NONE, so
  a failed take inside a note was completely silent. The §47 shape
  again — a failure that looks exactly like nothing happening.

NUMBERS
- notes 39 · notes UI 22 (was 18) · box 16 · login 11 — green
- both fixes mutated: the deck ignoring the open note fails 3 checks,
  silent note errors fails 1
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- Removing the automatic note left `if keep:` with an empty body — a
  syntax error. The whole block is gone now; `keep` stays in the
  signature because three callers pass it and the distinction it names
  is still real.
- My first three checks for the open-note fix never called deliver_text
  and so tested nothing. Rewritten as source checks, labelled with the
  reason: deliver_text is reached only through components, and
  components return their default under AppTest. Same limit as §73.

STILL UNSURE
- The note editor's OWN red button (inside the note, not the deck) posts
  its take through a different path — transcribe_note_take. That path
  reads correct and is unchanged, but I have never seen it succeed, and
  its errors were the ones being swallowed. Now they will be shown.
  If it still does nothing, the error on screen is the next clue.

FOR BABA
1. Log in with Remember me and tell me whether it still needs a refresh
   (v113's fix is reasoned, not proven).
2. Open a note and press the DECK's rec — the words should join the
   note now.
3. Then the note's own red button, and tell me what error appears if it
   fails.
