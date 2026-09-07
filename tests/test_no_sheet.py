"""THE SPREADSHEET IS GONE, AND NOTHING PRETENDS OTHERWISE.

    python3 tests/test_no_sheet.py

Baba, 5.9.2026: "we are removing any connection with Google accounts
through Google Script or App Script and Sheet that doesn't exist anymore,
so any code relating to that we remove... everything is in secrets."

THE SHEET HELD SIX THINGS and each had to go somewhere:

    engine choice     -> Secrets, ENGINE = "google"
    tab switches      -> Secrets, TABS_OFF = ["vr"]
    provider keys     -> Secrets, where they already were
    store-audio flag  -> gone, because Drive went with the Apps Script
    prompts           -> the code, which was already the fallback
    timings ledger    -> gone. It learns within a session and forgets

THE ONE THAT CANNOT SIMPLY MOVE is the tab switches. The spreadsheet was
the only WRITABLE store this app had: Secrets is read-only from inside
and session_state dies when a phone sleeps. So the switch works now and
says plainly that permanence means a line in Secrets — a control that
looked permanent and was not would be worse than one that admits it.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

ROOT = os.path.join(os.path.dirname(__file__), "..")
src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))

print("1 NOTHING REACHES THE SHEET ANY MORE")
check("1a the module is deleted",
      not os.path.exists(os.path.join(ROOT, "ttt", "sheet.py")))
check("1b the Apps Script is deleted",
      not os.path.exists(os.path.join(ROOT, "apps_script")))
check("1c and the auth script", not os.path.exists(os.path.join(ROOT, "auth_script")))
check("1d app.py does not import it", "import sheet" not in code)
check("1e and calls nothing on it", "SHEET." not in code,
      [l for l in code.splitlines() if "SHEET." in l][:2])
check("1f no secret named for it is READ any more — a lookup that can "
      "only return nothing is a lookup that misleads whoever reads it",
      "SHEETS_URL" not in code and "SHEETS_TOKEN" not in code,
      [l for l in code.splitlines() if "SHEETS_" in l][:2])

print("\n2 WHAT MOVED TO SECRETS")
check("2a the engine comes from Secrets", "def engine_from_secrets" in code)
check("2b read once per session, not per rerun",
      '"_engine_from_secrets_done"' in code)
check("2c a name that is not an engine changes nothing — a typo in "
      "Secrets must not switch anything",
      "if engine is None:" in code)
check("2d and a person who has already pressed a pill is not overridden",
      '"_engine_chosen_here"' in code)
check("2e the tab switches read Secrets", 'st.secrets.get("TABS_OFF"' in code)
check("2f taking either a list or a comma string, because somebody will "
      "write it either way", 'isinstance(raw, str)' in code)
check("2g the lock-out guard still holds on the way OUT of Secrets — a "
      "line written by hand cannot take away the way back",
      "off - set(TABS_NEVER_OFF)" in code)

print("\n3 THE SWITCH THAT CANNOT PERSIST SAYS SO")
# The honest half. Secrets is read-only from inside the app, so a global
# switch pressed in the panel holds for this running app and no longer.
check("3a pressing it works immediately", '"_tabs_off_session"' in code)
check("3b the session override is consulted BEFORE Secrets, or pressing "
      "the switch would do nothing while a Secrets entry existed",
      code.find('"_tabs_off_session"') < code.find('st.secrets.get("TABS_OFF"')) 
check("3c and it does not claim to have saved anywhere",
      "SHEET.put_setting" not in code)

print("\n4 WHAT WAS LOST, LOST HONESTLY")
check("4a the timings ledger is gone", "put_timing" not in code
      and "get_timings" not in code)
check("4b but the estimate still learns within a session — the first "
      "take has none, the third has one",
      '"_eta_samples_"' in code and "ETA.estimate" in code)
check("4c Drive storage went with the Apps Script that carried it",
      "Drive storage went with the Apps Script" in src)
check("4d and it SAYS so rather than pointing at secrets that no longer "
      "exist — the silence is what once had Baba recording three times "
      "with nothing kept",
      "Copy anything you need out" in src)
check("4e sheet_prompt is kept as a name returning \"\", which every "
      "caller already treats as 'use the built-in wording' — so no text "
      "on screen changed", 'def sheet_prompt' in code and 'return ""' in code)

print("\n5 THE USAGE LOG POSTS NOWHERE")
check("5a it is built with no destination", 'UsageLog(url="", token="", ' in code)
check("5b which is the state it was always in when the secrets were "
      "absent, so nothing about it had to change",
      "UsageLog(" in code)

print("\n6 THE SUITES THAT TESTED THE SHEET ARE MARKED, NOT DELETED")
# RENAMED OUT OF test*.py ON 7.9.2026 and described in README_SUPERSEDED.md,
# where tools/sweep.py now points. The file itself must still exist — the
# suite is the only record of what the sheet did — and the README must
# say what replaced it and the version that removed it.
readme = open(os.path.join(ROOT, "tests", "README_SUPERSEDED.md"),
              encoding="utf-8").read()
for name in ("test_users.py", "test_engine_sheet.py", "test_accounts.py",
             "test_admin_users.py", "test_must_change.py"):
    kept = os.path.join(ROOT, "tests", "superseded_" + name)
    check("6a %s is kept as superseded_%s and described" % (name, name),
          os.path.exists(kept) and ("superseded_" + name) in readme
          and not os.path.exists(os.path.join(ROOT, "tests", name)), name)
check("6b with the version that removed it, so the record is not just "
      "'this is broken'", "v237" in readme and "bb035b2" in readme)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
