"""THE LOGIN SCREEN — the one path where a failure is total.

§1: a failure here locks EVERYONE out, because nobody can get past it to
reach anything else. So the sheet is tried first and the built-in
passwords always still work.

    python3 tests/test_login.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def sget(at, key, default=None):
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def fresh():
    return AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=90)


def box(at, key):
    return [x for x in at.text_input if x.key == key][0]


print("THE LOGIN SCREEN\n")

at = fresh()
at.run()
check("1 it renders", not at.exception, at.exception)
keys = [x.key for x in at.text_input]
check("2 a username box above the password box",
      "_user_input" in keys and "_pw_input" in keys, keys)

# --- the old way must keep working, with no sheet at all --------------
at2 = fresh()
at2.run()
box(at2, "_pw_input").set_value("stub").run()
check("3 PASSWORD-ONLY LOGIN STILL WORKS with no sheet configured — "
      "nobody is locked out by this change",
      sget(at2, "_authed") is True, sget(at2, "_authed"))

at3 = fresh()
at3.run()
box(at3, "_pw_input").set_value("nope").run()
check("4 a wrong password is still refused", sget(at3, "_authed") is False)

# --- typing a name is not an attempt ----------------------------------
at4 = fresh()
at4.run()
box(at4, "_user_input").set_value("baba").run()
check("5 TYPING A USERNAME IS NOT A FAILED ATTEMPT — otherwise someone "
      "throttles themselves by filling the form top to bottom",
      sget(at4, "_authed") in (None, False) and not sget(at4, "_gate_wait"),
      sget(at4, "_gate_wait"))

box(at4, "_pw_input").set_value("stub").run()
check("6 and the password then still gets them in even though the sheet "
      "is unreachable", sget(at4, "_authed") is True, sget(at4, "_authed"))

# --- the throttle still bites on real attempts ------------------------
at5 = fresh()
at5.run()
for _ in range(6):
    box(at5, "_pw_input").set_value("wrong").run()
check("7 repeated WRONG PASSWORDS still trigger the throttle",
      bool(sget(at5, "_gate_wait")), sget(at5, "_gate_wait"))

# --- THE VISIBLE WAY IN ------------------------------------------------
#
# Enter always worked and always was invisible. Baba's mother has to be
# TOLD about an invisible control, and this screen is the first thing she
# meets. The button is the one that must not break.
at8 = fresh()
at8.run()
check("8 there is a visible Log in button",
      "login_now" in [b.key for b in at8.get("button")],
      [b.key for b in at8.get("button")])

box(at8, "_pw_input").set_value("stub")
[b for b in at8.get("button") if b.key == "login_now"][0].click().run()
check("9 PRESSING IT LOGS YOU IN — not just Enter",
      sget(at8, "_authed") is True, sget(at8, "_authed"))

at9 = fresh()
at9.run()
box(at9, "_pw_input").set_value("wrong")
[b for b in at9.get("button") if b.key == "login_now"][0].click().run()
check("10 and a wrong password through the button is still refused",
      sget(at9, "_authed") is not True, sget(at9, "_authed"))

at10 = fresh()
at10.run()
[b for b in at10.get("button") if b.key == "login_now"][0].click().run()
check("11 pressing it with an EMPTY password does nothing, and does not "
      "spend a throttle attempt",
      sget(at10, "_authed") is not True and not sget(at10, "_gate_wait"),
      sget(at10, "_gate_wait"))

print("\n{} passed, {} failed".format(passed, failed))


def test_login():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_login.py` is how it is meant to be read."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
