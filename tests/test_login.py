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

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
