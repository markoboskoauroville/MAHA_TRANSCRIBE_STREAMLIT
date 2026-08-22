# STEP: install the dev requirements, run the browser tests
STATUS: done, pushed as v106 `97db018`

WHAT HAPPENED
- Installed `requirements-dev.txt` and Chromium. Both browser tests ran
  on your Mac for the first time.
- `test_shake` was right: the shipped colour-only highlight moves NO
  word, while the old padding+background style shoved 195 of 812 words
  by up to 307px.
- `test_layout` failed two checks and the app was innocent. Its frame
  list had no `langrow`, so it measured deck→cmdrow ACROSS the whole
  HR / ENG / single / multi row and called that 61.6px gap a chasm. The
  real rhythm is even. With your yes, `langrow` was added to the list,
  and check 3's count now comes from the list instead of a hardcoded 3.
- Re-verified today on the current tree: everything below is a fresh run.

NUMBERS
- pytest tests/  ->  18 passed in 84s (app served) · 17 + 1 skipped without
- gaps measured  ->  8.8 · 8.8 · 9.8 px, spread 1.0px
- test_shake     ->  shipped style 0 of 812 words moved; old style 195
- pyflakes       ->  clean across app.py, ttt/ and tests/
- no app code changed by this step

WHAT BROKE, AND WHAT I UNDID
- Two deliberate sabotages, to prove test_layout can still go red. The
  first, in `app.py`, did NOTHING and taught the useful part: `ttt/theme.py`
  resets those frames' margins to `0 !important` and is emitted after
  app.py's own stylesheet, so frame spacing is `--frame-gap` in theme.py
  and nowhere else. The second, in theme.py, worked: gaps became
  34.8 / 34.8 / 9.8 and the test failed at once. Both reverted with
  `git checkout --`.
- I ran a Streamlit server on port 8811 for the test, then stopped it.

STILL UNSURE
- The install upgraded Streamlit 1.58.0 -> 1.62.0 in your SHARED pyenv,
  where another project (videolingo) pins 1.38.0. Already mismatched at
  1.58; wider now. Every suite here passes on 1.62. If that project
  misbehaves, a virtualenv for this repo is the fix — say the word.
- `test_layout` needs the app running or it skips. Nobody is served by a
  suite that quietly reports 17 + 1 on a machine where the app is down.

FOR BABA
- Queue unchanged, and all three are things only you can do: deploy the
  AUTH script (Reset asks for your password and the deployed script still
  ignores it), add `AUTH_ADMIN_TOKEN` to the Streamlit Cloud secrets, and
  check whether `migrateRun()` ever ran on the live sheet.
