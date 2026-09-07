# Superseded tests — v185

`superseded_test_login.py` and `superseded_test_calm_login.py` are the
checks for the login screen that v185 replaced. They are kept, renamed
out of pytest's `test*.py` pattern rather than deleted, because the door
they describe may come back.

**What replaced them:** `tests/test_door.py` — one box, one key marked L,
names from Secrets.

**What those files still describe, which v185 does NOT do:**

- a password, and a username box above it
- the `APP_PASSWORDS` emergency door
- the brute-force throttle in `ttt/gate.py`
- Remember me, and the token minted for it
- login through the Google accounts script

If any of that is wanted again, these files say what it has to do.
