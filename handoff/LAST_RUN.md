# STEP: an id that cannot collide
STATUS: done, pushed as v152. No deploy needed. **THIS WAS CRASHING THE
LIVE APP.**

WHAT HAPPENED
- StreamlitDuplicateElementKey, in notes_panel, on Baba's phone: a red
  wall of Python where his notes should be.
- `_seq` is a MODULE-LEVEL counter that restarts at 1 with the process.
  Before v140 that was harmless — notes died with the session, so
  nothing older was around to clash with.
- Notes come back from the browser and from Drive now, KEEPING their
  ids. So the first new note of a session asked for `n1` while a
  restored `n1` was already on screen. Two buttons, one key, dead app.
- The id is derived from WHAT IS IN THE NOTEBOOK now, not from how many
  times this process has been asked.
- AND THE CARD KEY CARRIES THE POSITION as well as the id. That is the
  second line of defence: the notebook can arrive from the browser or
  from Drive, and data that came from somewhere else must never be able
  to take the app down.

THE MUTATION SURVIVED THE FIRST TIME, AND THAT MATTERED
- Putting the counter back did not fail the new checks, because earlier
  checks in the same file had already advanced `_seq` past n1 — so the
  collision never happened and the test passed by luck.
- It resets `N._seq` to where a fresh process starts before testing.
  Then the mutation fails 2. A test that cannot reproduce the crash is
  not a test of the crash.

NUMBERS
- notes 53 (was 50) · notes UI 22 · notes persist 18 · box 16 · tier 15
- mutation caught after the reset was added
- pyflakes clean

STILL OPEN
- STORAGE IS STILL OFF for Baba — v151 makes the log say which piece is
  missing, and he has not read it yet. Nothing reaches Drive until then.
- A language pill in the open note. Asked, not started.
- The two-system split and the explorer — docs/TWO_SYSTEMS.md.
