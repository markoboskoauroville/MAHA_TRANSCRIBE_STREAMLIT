# STEP: a third language — auto
STATUS: done, pushed as v118

WHAT HAPPENED
- HR · ENG · auto. Auto lets the engine work the language out, which is
  what somebody who switches between Croatian and English mid-thought
  actually wants. Offered rather than made the default: naming the
  language is more accurate than detecting it, and detection can hear
  one English sentence inside Croatian and change its mind.
- THE APP STORES "auto" AND EACH PROVIDER SAYS IT ITS OWN WAY.
  AssemblyAI already understood it — language_detection=True. Groq did
  not: it always sent `language=`, and sending "auto" or "" to Whisper
  is an error. It omits the parameter now, which is how Whisper is told
  to detect. Neither the app nor either provider has to know how the
  other spells it.
- Five pills do not fit one line below 412px, and Streamlit wrapped them
  4 + 1, leaving `multi` alone underneath looking orphaned rather than
  paired with `single`. Split deliberately into two rows, each a whole
  group: language on one, mode on the next. Verified at 320 and 360px —
  both groups intact, no clipping, no sideways scroll.

NUMBERS
- source 19 · box 16 · login 11 — green
- pyflakes clean across app.py, ttt/ and ttt/providers/

WHAT BROKE, AND WHAT I UNDID
- Nothing in the app. But I booted a server after my own cleanup had
  removed the stub secrets FOUR times in this session, each costing an
  attempt — including twice after writing "write the secrets after the
  cleanup, not before" into the previous handoff. Writing a lesson down
  is not the same as following it.

STILL UNSURE
- Auto has not been tested against a real recording — no key here. The
  wiring is right on both providers; whether Whisper detects Croatian
  reliably from a short take is Baba's ear, not mine.

FOR BABA
- Try auto with a Croatian sentence and an English one, and see whether
  it holds.
- Still waiting from v114: open a note, press the DECK's rec (the words
  should join the note), then the note's own red button — its error is
  on screen now if it fails.
