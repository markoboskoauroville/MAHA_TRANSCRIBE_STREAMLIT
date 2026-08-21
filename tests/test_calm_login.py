"""THE CALM LOGIN, the language switch, and the editor's readable floor.

    python3 tests/test_calm_login.py
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


def fresh(remembered=None):
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=90)
    if remembered:
        at.session_state["_remembered"] = remembered
    return at


def box(at, key):
    got = [x for x in at.text_input if x.key == key]
    return got[0] if got else None


print("THE CALM LOGIN\n")

# --- nobody remembered: the old screen, unchanged ---------------------
at = fresh()
at.run()
check("1 the login screen renders", not at.exception, at.exception)
check("2 with a username and a password box",
      box(at, "_user_input") and box(at, "_pw_input"))
keys = [b.key for b in at.get("button")]
check("3 and NO continue button when nobody is remembered",
      "login_go" not in keys, keys)

# --- somebody remembered: prepared, NOT entered -----------------------
rem = {"user": "baba", "token": "TOK", "kind": "password"}
at2 = fresh(rem)
at2.run()
check("4 A REMEMBERED LOGIN DOES NOT ENTER BY ITSELF — this is the whole "
      "point: you must be able to see who you are about to be",
      sget(at2, "_authed") is not True, sget(at2, "_authed"))
check("5 the username is filled in for them",
      sget(at2, "_user_input") == "baba", sget(at2, "_user_input"))
keys2 = [b.key for b in at2.get("button")]
check("6 a continue button appears", "login_go" in keys2, keys2)
check("7 and a way to say it is not you", "login_notme" in keys2, keys2)
check("8 the button names WHO it will let in",
      any("baba" in (b.label or "") for b in at2.get("button")
          if b.key == "login_go"),
      [b.label for b in at2.get("button") if b.key == "login_go"])

# --- pressing it lets them in -----------------------------------------
[b for b in at2.get("button") if b.key == "login_go"][0].click().run()
check("9 pressing continue logs them in", sget(at2, "_authed") is True)
check("10 as the right person", sget(at2, "_user") == "baba",
      sget(at2, "_user"))
check("11 and the remembered state is spent, not left lying around",
      sget(at2, "_remembered") is None)

# --- what Enter can and cannot do, stated honestly --------------------
#
# Baba asked to press Enter and be let in. Streamlit does NOT fire
# on_change when a value has not changed, so Enter in an EMPTY password
# box fires nothing — in a real browser as much as here. Making it work
# would mean wrapping the login in st.form, which changes how every
# callback on that screen behaves, and the login screen is the one place
# where a mistake locks out everybody (§1).
#
# So the button is the press. It is one press, it says his name, and it
# works everywhere. This test records the limit rather than pretending
# past it.
at3 = fresh(dict(rem))
at3.run()
box(at3, "_pw_input").set_value("").run()
check("12 Enter on an EMPTY password does nothing — Streamlit fires no "
      "event when a value has not changed, so the button is the press",
      sget(at3, "_authed") is not True, sget(at3, "_authed"))

# AND THE PATH IS DRIVEN FOR REAL, because the check above cannot fail.
#
# 12 sets the password box to the value it already has, so Streamlit
# fires no event and the branch is never reached — a green that proves
# nothing, which is exactly the false-green §71 and §73 describe. The
# old 12b was worse: it assigned session_state by hand and asserted on a
# key nothing had written.
#
# THE USERNAME BOX FIRES THE SAME HANDLER. That is the real trigger, it
# changes value, and it is what a person actually does: type their name,
# press Enter, password box still empty. Under the code this replaces,
# that logged them straight in as the remembered user — without a
# password, without the button, and WITHOUT EVEN READING THE NAME THEY
# TYPED. Driven through the widget, not by poking at state.
at3b = fresh(dict(rem))
at3b.run()
box(at3b, "_user_input").set_value("somebody-else").run()
check("12b typing a USERNAME and pressing Enter does not log anybody in "
      "— an empty password is not a press",
      sget(at3b, "_authed") is not True, sget(at3b, "_authed"))
check("12c and the remembered login is still waiting to be confirmed",
      (sget(at3b, "_remembered") or {}).get("user") == "baba",
      sget(at3b, "_remembered"))
check("12d and nobody has been signed in under a name they did not type",
      not sget(at3b, "_user"), sget(at3b, "_user"))
check("12e and it does not burn a throttle attempt",
      not sget(at3b, "_gate_wait"), sget(at3b, "_gate_wait"))

# --- "not me" clears it ------------------------------------------------
at4 = fresh(dict(rem))
at4.run()
[b for b in at4.get("button") if b.key == "login_notme"][0].click().run()
check("13 'not me' forgets them", sget(at4, "_remembered") is None)
check("14 and does NOT log anybody in", sget(at4, "_authed") is not True)
check("15 and empties the name box", not sget(at4, "_user_input"),
      sget(at4, "_user_input"))

# --- a real password still works while somebody is remembered ---------
at5 = fresh(dict(rem))
at5.run()
box(at5, "_pw_input").set_value("stub").run()
check("16 typing a real password still works, and wins over the "
      "remembered name", sget(at5, "_authed") is True, sget(at5, "_authed"))

# --- a wrong password is still wrong ----------------------------------
at6 = fresh(dict(rem))
at6.run()
box(at6, "_pw_input").set_value("nonsense").run()
check("17 a WRONG password is still refused, even with someone "
      "remembered", sget(at6, "_authed") is not True, sget(at6, "_authed"))

# --- the language switch ----------------------------------------------
print()
at7 = AppTest.from_file(
    os.path.join(os.path.dirname(__file__), "..", "app.py"),
    default_timeout=90)
at7.session_state["_authed"] = True
at7.session_state["_user"] = "stub"
at7.session_state["active_tab"] = "looks"
at7.run()
lkeys = [b.key for b in at7.get("button")]
check("18 THE LANGUAGE SWITCH IS IN THE USER GEAR — the people this app "
      "is for do not speak English",
      "ui_hr" in lkeys and "ui_en" in lkeys, lkeys)

[b for b in at7.get("button") if b.key == "ui_hr"][0].click().run()
check("19 choosing Croatian sets it", sget(at7, "ui_lang") == "hr",
      sget(at7, "ui_lang"))
check("20 and the interface actually changes language",
      any("Odjavi" in (b.label or "") for b in at7.get("button")),
      [b.label for b in at7.get("button")][:6])

# --- _try_remembered must PREPARE, never enter ------------------------
#
# A SOURCE CHECK, and here is why rather than a better one: the value it
# reads comes from the ls_bridge COMPONENT, and components return their
# `default` under AppTest — so LS_DATA is always empty and the path
# cannot be reached at all from a test.
#
# Seeding `_remembered` by hand, which the checks above do, exercises
# what happens AFTER that function. It does not exercise the function,
# and a mutation putting the auto-login back survived every one of them.
# That is the §71 lesson again: a check that cannot fail is not a check.
print()
src = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
body = src.split("def _try_remembered():", 1)[1]
body = body.split("\ndef ", 1)[0]

check("21 _try_remembered does NOT log anybody in — it only prepares",
      '_authed"] = True' not in body,
      [ln.strip() for ln in body.splitlines() if "_authed" in ln])
check("22 it records who is remembered instead",
      '_remembered"] = {' in body)
check("23 and only enter_remembered() sets _authed",
      '_authed"] = True' in src.split("def enter_remembered():", 1)[1]
      .split("\ndef ", 1)[0])

# --- the editor's readable floor --------------------------------------
print()
ed = open(os.path.join(os.path.dirname(__file__), "..",
                       "note_frontend", "index.html"), encoding="utf-8").read()
check("24 the editor no longer reads the scale as a PERCENTAGE — it is a "
      "multiplier, and 1.0 became 1% of 16px",
      "a.scale + '%'" not in ed)
check("25 it multiplies by a11y's own BASE_REM floor",
      "* 1.05" in ed and "rem'" in ed)
check("26 and the CSS carries a readable floor of its own, so a missing "
      "scale can never leave someone squinting",
      "font-size: 1.05rem" in ed)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
