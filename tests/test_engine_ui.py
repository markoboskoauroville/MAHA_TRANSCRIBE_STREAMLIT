"""THE ENGINE ROW in Settings, the marked engine at the foot, the top bar.

    python3 tests/test_engine_ui.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402

from ttt import engines as EN  # noqa: E402

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


def clean_stored_settings(user="stub"):
    """Forget the server-side settings file between apps.

    Settings persist to tempfile.gettempdir() per user, and that file
    OUTLIVES an AppTest — so clicking an engine in one test restored
    itself over session_state in the next, and a later test read the
    earlier one's choice. That is the app working exactly as designed
    (§3: settings survive), and it makes every test after the first
    dependent on the ones before unless it is cleared here.
    """
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "maha_settings",
                        "".join(c for c in user if c.isalnum()) + ".json")
    try:
        os.remove(path)
    except OSError:
        pass


def app(tab="settings"):
    clean_stored_settings()
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=90)
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    at.session_state["active_tab"] = tab
    return at


print("THE ENGINE ROW\n")

at = app()
at.run()
check("1 settings renders", not at.exception, at.exception)

keys = [b.key for b in at.get("button")]
check("2 both engine buttons exist",
      "eng_normal" in keys and "eng_studio" in keys, keys)
check("3 the check engine button exists", "eng_check" in keys, keys)
check("4 THE INTERFACE LANGUAGE PILLS ARE GONE",
      "ui_en" not in keys and "ui_hr" not in keys, keys)

labels = [b.label for b in at.get("button") if b.key.startswith("eng_")]
check("5 the first engine is named Edge / Groq",
      any("Edge" in x and "Groq" in x for x in labels), labels)
check("6 the second names Speechify, AssemblyAI and Claude",
      any("Speechify" in x and "AssemblyAI" in x and "Claude" in x
          for x in labels), labels)

# --- choosing an engine writes the ROUTES -----------------------------
at2 = app()
at2.run()
# Same as test_engine_sheet: `eng_studio` was removed from app.py and
# this reached for it, so the file crashed instead of reporting.
_es = [b for b in at2.get("button") if b.key == "eng_studio"]
check("the studio engine control still exists", bool(_es),
      "no button keyed eng_studio")
if _es:
    _es[0].click().run()
check("7 choosing studio patches every route",
      (sget(at2, "route_stt"), sget(at2, "route_tts"), sget(at2, "route_llm"))
      == ("assemblyai", "speechify", "anthropic"),
      (sget(at2, "route_stt"), sget(at2, "route_tts"), sget(at2, "route_llm")))

_en = [b for b in at2.get("button") if b.key == "eng_normal"]
check("the normal engine control still exists", bool(_en),
      "no button keyed eng_normal")
if _en:
    _en[0].click().run()
check("8 choosing free patches them back",
      (sget(at2, "route_stt"), sget(at2, "route_tts"), sget(at2, "route_llm"))
      == ("groq", "edge", "groq"),
      (sget(at2, "route_stt"), sget(at2, "route_tts"), sget(at2, "route_llm")))

# --- the foot says which engine ---------------------------------------
#
# THE FOOT AND THE TOP BAR AS ASKED (Marko, 7.9.2026, app.py _foot_line):
# the page name top left; the admin panel, the version and (behind the
# door) log out top right; at the foot the engine IN FORCE as a marked
# word and every other engine as an underlined button; NO tier word.
# "free" was removed by name, and the person's name went earlier (v258,
# 6.9.2026: "his own text is on the screen" answers who he is). The
# verdict tick went with the tier word it was attached to. These checks
# describe THAT design; the ones they replace asserted the corner of
# v133-v257 — the tier, the tick, "mixed", the name, "shared".


def marked(at):
    """The ONE marked word at the foot — the engine in force.

    Matched on the exact class attribute, never on the word "tabsig_on":
    the stylesheet defines .tabsig_on, and a helper that matched it
    returned the CSS and passed for ever."""
    return " ".join(m.value for m in at.markdown
                    if 'class="tabsig tabsig_on"' in m.value)


def picks(at):
    """The engines offered as buttons — the ones NOT in force."""
    return sorted(b.key for b in at.get("button")
                  if b.key and b.key.startswith("eng_pick_"))


def topbar(at):
    return " ".join(m.value for m in at.markdown
                    if 'class="mahatop"' in m.value)


at3 = app("transcribe")
at3.run()
sig = marked(at3)
check("9 the foot marks the engine IN FORCE by its short name, no tier word",
      "Edge" in sig and "free" not in sig.lower() and "Groq" not in sig,
      sig[:160])
check("9b and every OTHER engine of the family is a button, this one is not",
      picks(at3) == ["eng_pick_google", "eng_pick_marko"], picks(at3))
check("10 and carries NO tick before any check has run",
      "✓" not in sig and "✗" not in sig, sig[:160])

# THE VERDICT DOES NOT LIVE AT THE FOOT ANY MORE. It was a tick after the
# tier word, and the tier word is gone; the engine check reports in
# Settings, on its own rows. A tick that reappeared here would be the old
# corner coming back unasked.
at3.session_state["_engine_check"] = {
    "engine": "free", "state": EN.OK, "rows": [], "at": "12:00"}
at3.run()
check("11 a PASSED check does not change the marked word",
      marked(at3) == sig, marked(at3)[:160])
at3.session_state["_engine_check"] = {
    "engine": "free", "state": EN.FAIL, "rows": [], "at": "12:00"}
at3.run()
check("12 nor does a FAILED one — no cross at the foot",
      marked(at3) == sig and "✗" not in marked(at3), marked(at3)[:160])
at3.session_state["_engine_check"] = {
    "engine": "studio", "state": EN.OK, "rows": [], "at": "12:00"}
at3.run()
check("13 a verdict for a DIFFERENT engine is not worn by this one",
      "✓" not in marked(at3), marked(at3)[:160])

# --- a hand-patched crosspoint marks NOTHING -----------------------------
# The engine is DERIVED from the routes every render (EN.current), never
# read back from a stored name. Routes that match no engine are "mixed":
# no marked word, and every engine of the family offered as a button.
at4 = app("transcribe")
at4.session_state["route_stt"] = "groq"
at4.session_state["route_tts"] = "speechify"
at4.session_state["route_llm"] = "groq"
at4.run()
check("14 a mixed board marks no engine and offers them all",
      marked(at4) == "" and "eng_pick_normal" in picks(at4)
      and "eng_pick_google" in picks(at4),
      (marked(at4)[:80], picks(at4)))

# --- switching engines drops a stale verdict --------------------------
at5 = app()
at5.run()
at5.session_state["_engine_check"] = {
    "engine": "free", "state": EN.OK, "rows": [], "at": "12:00"}
at5.run()
# A CONTROL THAT NO LONGER EXISTS IS A FINDING, NOT AN EXCEPTION.
_ctl1 = [b for b in at5.get("button") if b.key == "eng_studio"]
check("control eng_studio exists", bool(_ctl1), "missing: eng_studio")
if _ctl1:
    _ctl1[0].click().run()
check("15 switching engine FORGETS the old verdict",
      sget(at5, "_engine_check") is None, sget(at5, "_engine_check"))

# --- THE TOP BAR: the page, not the person ----------------------------
#
# And the one thing this line must never say: the APP_PASSWORDS fallback
# stores the PASSWORD THAT MATCHED in the session key that once held an
# account name, so anything that printed _user would print his password
# on every page. Nothing prints it now; check 17 keeps it that way.

at6 = app("transcribe")
at6.session_state["_user"] = "marko"
at6.session_state["_via_accounts"] = True
at6.run()
check("16 the top bar names the PAGE at the left, not the person",
      'class="mahatop_l">transcribe<' in topbar(at6)
      and "marko" not in topbar(at6), topbar(at6)[:200])
check("16b and carries the version at the right",
      'class="mahatop_v">' in topbar(at6), topbar(at6)[:200])
check("16c without the door there is no admin link and log out stays a button",
      "/portal/admin" not in topbar(at6)
      and any(b.key == "foot_logout" for b in at6.get("button")),
      topbar(at6)[:200])

at7 = app("transcribe")
at7.session_state["_user"] = "correct-horse-staple"   # a PASSWORD, not a name
at7.run()
_page7 = topbar(at7) + " " + marked(at7) + " " + " ".join(
    m.value for m in at7.markdown if "<style>" not in m.value)
check("17 A PASSWORD LOGIN NEVER PRINTS THE PASSWORD — _user holds the "
      "matched password, not a name, when nobody logged in by name",
      "correct-horse-staple" not in _page7, _page7[:200])

at8 = app("transcribe")
at8.session_state["_user"] = ""       # nobody logged in by name
at8.run()
check("18 an unnamed session gets the same bar — the page and the version",
      topbar(at8) == topbar(at6), (topbar(at8)[:120], topbar(at6)[:120]))

print("\n{} passed, {} failed".format(passed, failed))


def test_engine_ui():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_engine_ui.py` is how it is meant to be read."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
