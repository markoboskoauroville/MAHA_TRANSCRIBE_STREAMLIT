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

# Superseded tests — v186 / v237, renamed 7.9.2026

Five more suites describe the spreadsheet and the accounts script. The
design went in v186 ("authentication through Google in Google Sheets is
gone forever" — app.py, the Looks tab, beside the password form that is
left standing dark) and the code went in v237, commit `bb035b2` ("the
spreadsheet is gone": `ttt/sheet.py`, `ttt/accounts.py`, `apps_script/`,
`auth_script/` and every call site removed). Three of them died at import
on `from ttt import sheet` / `accounts`; two rendered a panel that no
longer exists. Renamed out of `test*.py`, not deleted — Baba, 25.8.2026:
"that should be kept for studio users."

- `superseded_test_accounts.py` — the accounts script over HTTP, and
  APP_PASSWORDS as the door when it does not answer. **Replaced by**
  `test_door.py` (names and passwords from Secrets; nothing over HTTP).
- `superseded_test_users.py` — login against the sheet's user list, an
  engine per person. **Replaced by** `test_door.py` and `test_tier.py`;
  the engine is one Secrets entry (`ENGINE`) since v237, not a column.
- `superseded_test_engine_sheet.py` — the engine board reading its
  choice from the sheet. **Replaced by** `test_engine_ui.py` (the board
  and the foot) and `engine_from_secrets()` in app.py.
- `superseded_test_admin_users.py` — the owner's PEOPLE screen (list,
  add, reset, delete, rename by writing spreadsheet rows). **Replaced
  by** nothing on screen: "who can get in is a Secrets question now"
  (app.py, above `engine_from_secrets`). Adding somebody is a line and
  a redeploy.
- `superseded_test_must_change.py` — the forced password change through
  the accounts script. **Replaced by** nothing: `change_own_password()`
  in app.py says passwords live in Secrets, and `_must_change` is never
  set because nothing sets `kind == "accounts"` any more. Its checks 1-5
  (the nudge renders and does not block) still passed; 6-7 (the change
  is SENT) cannot, by design.

`tools/sweep.py` listed these five under MISSING with the same reasons;
that list now points here.
