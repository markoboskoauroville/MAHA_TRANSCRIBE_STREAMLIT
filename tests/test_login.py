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


def submit(at, password=None, username=None):
    """Fill the form and press its button — the only way in now.

    v115 made the login a FORM, because typing and then clicking did
    nothing without one: the click blurs the field, and Streamlit had not
    committed the value by the time the callback ran. A form commits
    every widget inside it and THEN runs the submit callback.

    The consequence for tests is that set_value().run() no longer submits
    anything. That is not a regression — it is the form working. Nothing
    is submitted until the button is pressed, which is exactly what a
    person does.
    """
    if username is not None:
        at.session_state["_user_input"] = username
    if password is not None:
        at.session_state["_pw_input"] = password
    # A form's submit button is an ordinary button whose key Streamlit
    # builds as "FormSubmitter:<form>-<label>". There is no
    # at.form_submit_button accessor.
    for b in at.get("button"):
        if str(b.key or "").startswith("FormSubmitter:login_form"):
            b.click().run()
            return
    raise AssertionError("no submit button on the login form")


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
submit(at2, password="stub")
check("3 PASSWORD-ONLY LOGIN STILL WORKS with no sheet configured — "
      "nobody is locked out by this change",
      sget(at2, "_authed") is True, sget(at2, "_authed"))

at3 = fresh()
at3.run()
submit(at3, password="nope")
check("4 a wrong password is still refused", sget(at3, "_authed") is False)

# --- typing a name is not an attempt ----------------------------------
at4 = fresh()
at4.run()
at4.session_state["_user_input"] = "baba"; at4.run()
check("5 TYPING A USERNAME IS NOT A FAILED ATTEMPT — otherwise someone "
      "throttles themselves by filling the form top to bottom",
      sget(at4, "_authed") in (None, False) and not sget(at4, "_gate_wait"),
      sget(at4, "_gate_wait"))

submit(at4, password="stub")
check("6 and the password then still gets them in even though the sheet "
      "is unreachable", sget(at4, "_authed") is True, sget(at4, "_authed"))

# --- the throttle still bites on real attempts ------------------------
at5 = fresh()
at5.run()
for _ in range(6):
    submit(at5, password="wrong")
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
      any(str(b.key or "").startswith("FormSubmitter:login_form")
          for b in at8.get("button")),
      [b.key for b in at8.get("button")])

# TESTING THE BUTTON SPECIFICALLY IS AWKWARD, and the awkwardness is
# worth understanding rather than working around blindly.
#
# set_value() alone never reaches the widget — the callback reads an
# empty box. set_value().run() DOES reach it, but the run fires
# on_change, which is Enter, and Enter logs you straight in — so the
# button is gone before it can be pressed.
#
# So the value is put into session_state directly, which is the one way
# to have a filled box that has NOT been submitted. Then the button is
# the only thing that can act.
submit(at8, password="stub")
check("9 PRESSING IT LOGS YOU IN — not just Enter",
      sget(at8, "_authed") is True, sget(at8, "_authed"))

at9 = fresh()
at9.run()
submit(at9, password="wrong")
check("10 and a wrong password through the button is still refused",
      sget(at9, "_authed") is not True, sget(at9, "_authed"))

at10 = fresh()
at10.run()
submit(at10)
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
