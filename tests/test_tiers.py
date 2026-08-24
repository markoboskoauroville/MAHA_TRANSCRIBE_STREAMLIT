"""THE THREE TIERS — free, studio, admin — and the radio that switches view.

Baba, 24.8.2026: "Any studio user is also free user, but it's not admin
user... Admin user is Marko, but he's also studio user 1 — even if he's
admin, he's automatically studio user 1. So software can merge the 2."

So a tier is a FLOOR, not a slot, and the same name appearing under two
headings is not an error to reject — it is two true statements, and the
answer is the larger one.

    python3 tests/test_tiers.py

The names below are invented. With this door the username IS the whole
credential, so the real ones live in Streamlit Cloud Settings and never
in this repository.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402

OWNER = "owner-name"
STUDIO = "studio-name"
FREE1 = "free-one"
FREE2 = "free-two"

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


def app(**extra):
    """THE EXACT SHAPE BABA SENT, repeated name and all.

    He listed the owner three times over — as ADMIN_USER1, as
    STUDIO_USER1 and as a FREE_USER. That is the case this file exists
    to pin down.
    """
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=120)
    at.secrets["ADMIN_USER1"] = OWNER
    at.secrets["STUDIO_USER1"] = OWNER          # the same person again
    at.secrets["STUDIO_USER2"] = STUDIO
    at.secrets["FREE_USER1"] = FREE1
    at.secrets["FREE_USER2"] = FREE2
    at.secrets["FREE_USER3"] = OWNER            # and a third time
    at.secrets["GROQ_API_KEYS"] = ["gsk_stub_not_real"]
    for k, v in extra.items():
        at.secrets[k] = v
    return at


def enter(at, name):
    at.run()
    at.text_input[0].set_value(name)
    [b for b in at.get("button") if b.key == "login_L"][0].click().run()
    return at


def radio(at):
    for r in at.get("radio"):
        if r.key == "_view_tier":
            return r
    return None


def tabs(at):
    for g in at.get("button_group"):
        opts = [str(o) for o in getattr(g, "options", [])]
        if opts:
            return opts
    return []


print("THE THREE TIERS\n")

# --- 1. the merge -----------------------------------------------------
print("1 A REPEATED NAME MERGES TO THE HIGHEST TIER")
at = enter(app(), OWNER)
check("1a the owner gets in", sget(at, "_authed") is True)
check("1b named three times, he is admin — not free, not studio",
      sget(at, "_view_tier") == "admin", sget(at, "_view_tier"))

at = enter(app(), STUDIO)
check("1c a studio-only name is studio", sget(at, "_view_tier") == "studio",
      sget(at, "_view_tier"))

at = enter(app(), FREE1)
check("1d a free name is free", sget(at, "_view_tier") == "free",
      sget(at, "_view_tier"))
at2 = enter(app(), FREE2)
check("1e the second free name works too", sget(at2, "_authed") is True)

# ORDER MUST NOT MATTER. The same facts listed the other way round have
# to give the same answer, or the merge is really "whichever was last".
at = AppTest.from_file(
    os.path.join(os.path.dirname(__file__), "..", "app.py"),
    default_timeout=120)
at.secrets["FREE_USER1"] = OWNER          # free FIRST this time
at.secrets["STUDIO_USER1"] = OWNER
at.secrets["ADMIN_USER1"] = OWNER
at.secrets["GROQ_API_KEYS"] = ["gsk_stub_not_real"]
at = enter(at, OWNER)
check("1f the answer does not depend on the order they are listed in",
      sget(at, "_view_tier") == "admin", sget(at, "_view_tier"))

# --- 2. who is refused ------------------------------------------------
print("\n2 WHO IS REFUSED")
at = enter(app(), "nobody-at-all")
check("2a a name in no tier does not get in", sget(at, "_authed") is not True)
check("2b and the door is still standing", len(at.text_input) == 1)

# --- 3. the radio -----------------------------------------------------
print("\n3 THE RADIO AT THE TOP")
at = enter(app(), OWNER)
r = radio(at)
check("3a the owner gets a radio", r is not None)
check("3b with all three tiers, lowest first",
      r is not None and list(r.options) == ["free", "studio", "admin"],
      list(r.options) if r else None)

at = enter(app(), STUDIO)
r = radio(at)
check("3c a studio user gets two, not three",
      r is not None and list(r.options) == ["free", "studio"],
      list(r.options) if r else None)

at = enter(app(), FREE1)
check("3d a free user gets NO radio — there is nothing to choose",
      radio(at) is None,
      list(radio(at).options) if radio(at) else None)

# --- 4. switching view actually changes the app -----------------------
print("\n4 SWITCHING THE VIEW CHANGES WHAT IS THERE")
at = enter(app(), OWNER)
admin_tabs = tabs(at)
radio(at).set_value("free").run()
free_tabs = tabs(at)
check("4a as admin he sees more tabs than as free",
      len(admin_tabs) > len(free_tabs),
      "admin %s / free %s" % (admin_tabs, free_tabs))
check("4b dropping to free really lowers the view",
      sget(at, "_view_tier") == "free", sget(at, "_view_tier"))

# THE WAY BACK. This is the trap: a radio drawn from the VIEW would
# vanish the moment he chose free, and the only way out would be to log
# in again.
back = radio(at)
check("4c the radio is STILL there in the free view, so he can come back",
      back is not None and list(back.options) == ["free", "studio", "admin"],
      list(back.options) if back else None)
back.set_value("admin").run()
check("4d and he can come back", tabs(at) == admin_tabs, tabs(at))

# --- 5. the view cannot grant what the account does not hold ----------
print("\n5 A VIEW CANNOT GRANT WHAT THE ACCOUNT DOES NOT HOLD")
at = enter(app(), FREE1)
at.session_state["_view_tier"] = "admin"      # forged by hand
at.run()
check("5a a free user with 'admin' forced into state stays free",
      tabs(at) and len(tabs(at)) == len(free_tabs),
      "%s vs free %s" % (tabs(at), free_tabs))
check("5b and still gets no radio", radio(at) is None)

# THE REAL VERSION OF THAT SCENARIO: a session is carrying "admin" from
# before, and the Secrets no longer grant it — Baba removes a name, or a
# session outlives a Settings change. The stored value must be clamped
# BEFORE the radio is built, or st.radio raises on a value that is not
# one of its options and takes the whole page down.
#
# Set before the first run, because poking session_state at a radio that
# already exists is something only the harness can do; a browser cannot.
at = AppTest.from_file(
    os.path.join(os.path.dirname(__file__), "..", "app.py"),
    default_timeout=120)
at.secrets["STUDIO_USER1"] = STUDIO
at.secrets["FREE_USER1"] = FREE1
at.secrets["GROQ_API_KEYS"] = ["gsk_stub_not_real"]
at.session_state["_authed"] = True
at.session_state["_user"] = STUDIO
at.session_state["_view_tier"] = "admin"       # left over, no longer granted
at.run()
check("5c a stale 'admin' does not crash the page",
      not at.exception, [e.value[:120] for e in at.exception])
check("5d and it is clamped back to what the account holds",
      sget(at, "_view_tier") == "studio", sget(at, "_view_tier"))
check("5e so the admin tabs are not there",
      len(tabs(at)) < len(admin_tabs),
      "%s vs admin %s" % (tabs(at), admin_tabs))

# --- 6. nothing named at all -----------------------------------------
print("\n6 A DEPLOYMENT WITH NOBODY NAMED")
at = AppTest.from_file(
    os.path.join(os.path.dirname(__file__), "..", "app.py"),
    default_timeout=120)
at.secrets["GROQ_API_KEYS"] = ["gsk_stub_not_real"]
at.run()
check("6a there is no door at all, and it says why",
      len(at.text_input) == 0 and bool(at.error),
      "%d boxes, %d errors" % (len(at.text_input), len(at.error)))

# --- 7. the old ADMIN_USER still works -------------------------------
print("\n7 THE NAME FROM BEFORE v186")
at = AppTest.from_file(
    os.path.join(os.path.dirname(__file__), "..", "app.py"),
    default_timeout=120)
at.secrets["ADMIN_USER"] = OWNER               # no digit, the v185 spelling
at.secrets["GROQ_API_KEYS"] = ["gsk_stub_not_real"]
at = enter(at, OWNER)
check("7a ADMIN_USER without a digit still admits the owner as admin",
      sget(at, "_view_tier") == "admin", sget(at, "_view_tier"))

print("\n{} passed, {} failed".format(passed, failed))


def test_tiers():
    assert failed == 0, "%d of %d failed" % (failed, passed + failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
