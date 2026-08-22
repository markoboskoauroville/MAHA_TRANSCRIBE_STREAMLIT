# STEP: v105 — fix the test harness (the four problems, worst first)
STATUS: done, pushed as v105 `4531b7d`

WHAT HAPPENED
- 17 test files ended in a module-level `sys.exit()`. pytest EXECUTES a
  file to collect it, so that fired during collection and killed the
  whole run with INTERNALERROR — the same crash whether checks passed or
  failed. Each now has a `test_<name>()` holding the tally, with the exit
  under `if __name__ == "__main__"`. Both ways of running still work.
- `tests/test1_wordtimes.py` began with a hardcoded sandbox path,
  `/home/claude/repo`, so it had NEVER run on your Mac or anywhere else.
  Fixed to find the repo from its own location: 65 checks ran for the
  first time and all 65 pass.
- Cleared the 3 pyflakes findings in `tests/`.
- Added `requirements-dev.txt` (playwright, pytest, pyflakes, and the
  Streamlit floor) and a two-line `pytest.ini`.
- The two browser tests now SKIP with a reason instead of erroring.

NUMBERS
- pytest tests/  ->  16 passed, 2 skipped in 33s  (436 checks inside)
- before this    ->  INTERNALERROR, "no tests ran"
- pyflakes       ->  clean across app.py, ttt/ and tests/
- no app code changed

WHAT BROKE, AND WHAT I UNDID
- My own mistake: while proving the runner can go red, I ran
  `git checkout -- tests/test_box.py` to undo a bad edit, and it silently
  reverted that file's real fixes too. I caught it, re-applied both, and
  checked its tail is now identical in shape to the other files. The
  green number was measured after that repair, not before it.

STILL UNSURE
- These numbers were measured on Streamlit 1.58.0 while
  `requirements.txt` asks for >=1.61 — so they were measured against a
  Streamlit production does not run. The next step closes that.

FOR BABA
- To run the browser tests yourself, one paste:
  `cd ~/Developer/MAHA_TRANSCRIBE_STREAMLIT && pip install -r requirements-dev.txt && python3 -m playwright install chromium`
