# STEP: pull, install the dev requirements, run the browser tests
STATUS: done

WHAT HAPPENED
- Pulled. `docs/HOW_WE_WORK.md` arrived and was read; `handoff/` landed
  while this step was already running, so this is the first real report.
- Installed `requirements-dev.txt` and Chromium. Both browser tests ran
  on this Mac for the first time.
- `test_shake` was right. `test_layout` failed two checks and the app was
  innocent: its frame list had no `langrow`, so it measured deck→cmdrow
  ACROSS the HR / ENG / single / multi row. The real gaps are even.
- With your yes, `langrow` was added to that list. Committed as v106.

NUMBERS
- pytest tests/  ->  18 passed in 83s (app served) · 17 + 1 skipped without
- pyflakes       ->  clean across app.py, ttt/ and tests/
- gaps measured  ->  8.8 · 8.8 · 9.8 px, spread 1.0px
- test_shake     ->  shipped style moves 0 of 812 words; the old one, 195

WHAT BROKE, AND WHAT I UNDID
- Two deliberate sabotages, to prove test_layout can still go red. The
  first, in app.py, did nothing — ttt/theme.py resets those margins with
  `!important` and wins. The second, in theme.py, worked: gaps 34.8 /
  34.8 / 9.8 and the test failed at once. Both reverted with
  `git checkout --`; only the test file and HANDOVER.md changed.
- I ran a Streamlit server on port 8811 for the test, and stopped it.

STILL UNSURE
- The install upgraded Streamlit 1.58.0 -> 1.62.0 in your SHARED pyenv,
  where another project (videolingo) pins 1.38.0. It was already
  mismatched at 1.58; this widened it. If that project misbehaves, the
  fix is a virtualenv for this repo. Every suite here passes on 1.62.

FOR BABA
- Queue unchanged: deploy the AUTH script (Reset asks for your password
  and the deployed script still ignores it), add `AUTH_ADMIN_TOKEN` to
  the Streamlit Cloud secrets, and check whether `migrateRun()` ever ran
  on the live sheet.
