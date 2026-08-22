# STEP: plan SELF UPGRADE — a second Streamlit app on a `beta` branch
STATUS: done — plan only, no code written

WHAT HAPPENED
- Wrote `docs/SELF_UPGRADE.md`: the shape, the three decisions you asked
  for, the flow screen by screen, and what already exists in the repo.
- Read the current Claude API reference before naming anything:
  `claude-opus-5`, $5 / $25 per million tokens, 1M context. A file-sized
  request is a few cents.

THE THREE ANSWERS, SHORT
- Own sheet AND own Drive folder: YES, both, and it is the one
  non-optional part — beta writes real rows and real audio otherwise.
  Accounts stay SHARED but with the login token only, never the admin
  token, so a broken beta cannot create, delete or reset anybody.
- The second deployment needs 8 things from you, all outside this repo:
  a beta branch, a new Streamlit app on it, a copy of the sheet, a new
  Drive folder, a second Apps Script project, beta's secrets, a
  fine-grained GitHub token, and two decisions (colour — I recommend
  cyan; and whether Push to main may push straight to main).
- Six ways main can still die are listed with their guards. Recovery
  from a phone, first thing to try: GitHub in the browser → Commits →
  the bad one → Revert. Redeploys in about two minutes.

NUMBERS
- nothing run — planning only. No test, no commit to app code.

WHAT BROKE, AND WHAT I UNDID
- Nothing was changed or undone. One thing found already broken:
  `ttt/providers/anthropic.py` `complete()` always sends `temperature`,
  and every current Claude model rejects sampling parameters with a 400.
  Its `max_tokens` default (2048) is also too small to return an edited
  file. This must be fixed before the Claude step can work at all — it
  is in the plan, not fixed, because you said plan only.

STILL UNSURE
- Whether one file per request is enough. A real change often touches
  `app.py` and a `ttt/` module together, and the plan currently sends
  one file. Better decided once the first version exists than guessed
  now.
- Whether you want the diff to be readable on a phone. It changes how
  step 5 is drawn, and you are on a phone half the time.

FOR BABA
- Read `docs/SELF_UPGRADE.md` §1.2 — the eight things only you can do.
- Two decisions before any code: the beta colour, and whether "Push to
  main" pushes straight to `main` or stops at a branch you merge.
- Older queue, unchanged: deploy the AUTH script, add
  `AUTH_ADMIN_TOKEN` to the Streamlit Cloud secrets, and check whether
  `migrateRun()` ever ran on the live sheet.
