"""THE DOOR — one box, one key marked L.

Baba, 24.8.2026: "First screen of an app doesn't have anything, only one
entry box. There is no title, no text, zero."

Checked against the exact secrets SHAPE: ADMIN_USER1, FREE_USER1,
FREE_USER2. What each tier GETS is tests/test_tiers.py; this file is only
about the door itself.

The names below are invented. With this door the username IS the whole
credential — there is no password behind it — so the real ones live in
Streamlit Cloud Settings and never in this repository.

    python3 tests/test_door.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402

OWNER = "owner-test-name"
FAMILY1 = "family-one"
FAMILY2 = "family-two"

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def sget(at, k, d=None):
    try:
        return at.session_state[k]
    except (KeyError, AttributeError):
        return d


def door():
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=120)
    at.secrets["ADMIN_USER1"] = OWNER
    at.secrets["FREE_USER1"] = FAMILY1
    at.secrets["FREE_USER2"] = FAMILY2
    at.secrets["GROQ_API_KEYS"] = ["gsk_stub_not_real"]
    return at


def enter(at, name):
    at.text_input[0].set_value(name)
    [b for b in at.get("button") if b.key == "login_L"][0].click().run()
    return at


print("THE DOOR — a name, and the letter L\n")

# --- 1. the screen itself --------------------------------------------
print("1 THE FIRST SCREEN")
at = door()
at.run()
check("1a exactly one text box", len(at.text_input) == 1,
      [i.label for i in at.text_input])
check("1b exactly one button", len(at.get("button")) == 1,
      [b.label for b in at.get("button")])
check("1c and it says only L", at.get("button")[0].label == "L",
      at.get("button")[0].label)
check("1d no heading of any kind", len(at.get("heading")) == 0,
      [h.value for h in at.get("heading")])
check("1e no title", len(at.title) == 0)
# The only markdown on this screen is the stylesheet, which is invisible.
# Anything that is NOT a <style> block is words on a screen Baba asked to
# be empty, so that is what is counted.
_words = [m.value for m in at.markdown
          if not m.value.lstrip().startswith("<style>")]
check("1f nothing is written on the screen — only the stylesheet",
      not _words and len(at.caption) == 0,
      [w[:60] for w in _words])
check("1g the box carries no visible label",
      "collapsed" in str(at.text_input[0].label_visibility).lower(),
      at.text_input[0].label_visibility)

# --- 2. who gets in --------------------------------------------------
print("\n2 WHO GETS IN")
at = enter(door().run(), OWNER)
check("2a the owner gets in", sget(at, "_authed") is True)
check("2b and is remembered by name", sget(at, "_user") == OWNER,
      sget(at, "_user"))

at = enter(door().run(), FAMILY1)
check("2c the first family name gets in", sget(at, "_authed") is True)

at = enter(door().run(), FAMILY2)
check("2d the second family name gets in", sget(at, "_authed") is True)

# --- 3. who does not -------------------------------------------------
print("\n3 WHO DOES NOT")
at = enter(door().run(), "someone-else")
check("3a a name that is not in Secrets does NOT get in",
      sget(at, "_authed") is not True, sget(at, "_authed"))
check("3b and the door is still standing, box and key",
      len(at.text_input) == 1 and len(at.get("button")) == 1)

at = enter(door().run(), "")
check("3c an empty box does not open it", sget(at, "_authed") is not True)

at = enter(door().run(), "   ")
check("3d nor does a box of spaces", sget(at, "_authed") is not True)

# --- 4. the ugly cases -----------------------------------------------
print("\n4 UGLY")
at = enter(door().run(), "  " + OWNER + "  ")
check("4a spaces round a real name are trimmed, not rejected",
      sget(at, "_authed") is True, sget(at, "_authed"))

at = enter(door().run(), OWNER.upper())
check("4b the name is not case-sensitive", sget(at, "_authed") is True)

at = enter(door().run(), FAMILY1)
at.run()
at.run()
check("4c staying in survives reruns", sget(at, "_authed") is True)

# A DEPLOYMENT WITH NO NAMES SET must refuse everybody rather than
# letting anybody in. Sabotage, and the one that would be worst.
at = AppTest.from_file(
    os.path.join(os.path.dirname(__file__), "..", "app.py"),
    default_timeout=120)
at.secrets["GROQ_API_KEYS"] = ["gsk_stub_not_real"]
at.run()
# With no names AND no APP_PASSWORDS there is no door at all — the app
# stops on a red line before drawing one, which is the right answer: a
# deployment nobody is named in should let nobody in, not everybody.
check("4d with no names in Secrets there is no door to try",
      len(at.text_input) == 0 and bool(at.error),
      "%d boxes, %d errors" % (len(at.text_input), len(at.error)))
check("4e and nobody is signed in", sget(at, "_authed") is not True,
      sget(at, "_authed"))

# --- 5. the owner is still the owner ---------------------------------
print("\n5 THE OWNER IS STILL THE OWNER")
at = enter(door().run(), OWNER)
def nav(a):
    """The tab strip. It is a segmented_control, which this Streamlit
    reports as a ButtonGroup."""
    for g in a.get("button_group"):
        opts = [str(o) for o in getattr(g, "options", [])]
        if opts:
            return opts
    return []

owner_tabs = nav(at)
at2 = enter(door().run(), FAMILY1)
family_tabs = nav(at2)
check("5a the owner sees more tabs than the family",
      len(owner_tabs) > len(family_tabs),
      "owner %s / family %s" % (owner_tabs, family_tabs))

print("\n{} passed, {} failed".format(passed, failed))


def test_door():
    assert failed == 0, "%d of %d failed" % (failed, passed + failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
