# STEP: setting up the handoff loop
STATUS: done

WHAT HAPPENED
- handoff/ created, with README.md explaining the loop and its rules.
- docs/HOW_WE_WORK.md now tells Claude Code to write this file after
  every step, commit it, and push.
- This file is the template in use. Overwrite it; do not add new ones.

NUMBERS
- nothing run — documentation only.

WHAT BROKE, AND WHAT I UNDID
- nothing.

STILL UNSURE
- nothing.

FOR BABA
- Nothing here. The queue is unchanged: deploy the AUTH script (Reset
  asks for your password and the deployed script still ignores it), add
  AUTH_ADMIN_TOKEN to the Streamlit Cloud secrets, and check whether
  migrateRun() ever ran on the live sheet — if it did not, the family's
  rows are still plaintext.
