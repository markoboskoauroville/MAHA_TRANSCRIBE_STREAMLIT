# STEP: a second reading that says what it is doing
STATUS: done, pushed as v159. No deploy needed.

WHAT BABA ASKED
- "When audio is selected in archive it takes a long time until it
  actually gets transcribed, so user is confused what's going on... show
  what you can fetch from the transferring information."
- He asked the right question — WHAT CAN BE FETCHED — rather than
  assuming a percentage exists.

THE ANSWER: THREE REAL SOURCES, NONE INVENTED
1. THE DOWNLOAD. drive.fetch now takes an `on_part` callback and reports
   which part is coming, of how many, and how many KB have arrived.
2. THE TRANSCRIPTION. ttt/audio.py has had `progress_cb(done, total)`
   all along, firing once per ten-minute chunk. It was never wired to
   anything here. Now it is.
3. THE RETRIES. `on_wait(attempt, pause, err)` was also already there.
   A retry is the moment somebody most needs telling, because a patient
   app and a dead one look identical.

None of it is guessed. A bar that lies is a bar nobody believes twice,
and the honest half of a number is worth more than an invented whole.

THE BAR IS TWO HALVES, download then transcription — not because they
take equal time, they do not, but because a bar that jumps to 90% and
sits there is worse than one moving steadily through two honest halves.

WHAT THE FIRST VERSION GOT WRONG
- fetch announced the part with `i` and size 0, which read on screen as
  "part 0 of 3 · 0 KB" — a number nobody counts from and a size that
  looks like a failure. It is 1-based now, and the size is None while a
  part is still coming: "part 1/3 · waiting", then "part 1/3 · 300 KB".
  Verified against a deliberately slow fake.
- `rec_retry` collided with the deck's existing retry BUTTON. Two
  meanings on one key is how a button ends up labelled with a sentence
  about waiting.

NUMBERS
- drive text 20 · box 16 · tier 15 · notes UI 27 · source 19 — green
- driven against a fake serving 300 KB parts at 0.6s each: three parts,
  six narration events, 3.0s end to end
- pyflakes clean
