"""THE ENGINE ROW in Settings, and the corner badge.

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


def corner(at):
    """The signature DIV only.

    Matching on the word "tabsig" also matched the stylesheet, which
    defines .tabsig — so the helper returned CSS and the assertion
    failed against a page that was perfectly correct.
    """
    return " ".join(m.value for m in at.markdown
                    if 'class="tabsig"' in m.value)


print("THE ENGINE ROW\n")

at = app()
at.run()
check("1 settings renders", not at.exception, at.exception)

keys = [b.key for b in at.get("button")]
check("2 both engine buttons exist",
      "eng_free" in keys and "eng_studio" in keys, keys)
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
[b for b in at2.get("button") if b.key == "eng_studio"][0].click().run()
check("7 choosing studio patches every route",
      (sget(at2, "route_stt"), sget(at2, "route_tts"), sget(at2, "route_llm"))
      == ("assemblyai", "speechify", "anthropic"),
      (sget(at2, "route_stt"), sget(at2, "route_tts"), sget(at2, "route_llm")))

[b for b in at2.get("button") if b.key == "eng_free"][0].click().run()
check("8 choosing free patches them back",
      (sget(at2, "route_stt"), sget(at2, "route_tts"), sget(at2, "route_llm"))
      == ("groq", "edge", "groq"),
      (sget(at2, "route_stt"), sget(at2, "route_tts"), sget(at2, "route_llm")))

# --- the corner says which engine -------------------------------------
at3 = app("transcribe")
at3.run()
sig = corner(at3)
check("9 the corner names the running engine",
      "Edge" in sig and "Groq" in sig, sig[:160])
check("10 and carries NO tick before any check has run",
      "✓" not in sig and "✗" not in sig, sig[:160])

# a passing check adds the tick
at3.session_state["_engine_check"] = {
    "engine": "free", "state": EN.OK, "rows": [], "at": "12:00"}
at3.run()
check("11 a PASSED check adds the tick", "✓" in corner(at3), corner(at3)[:160])

at3.session_state["_engine_check"] = {
    "engine": "free", "state": EN.FAIL, "rows": [], "at": "12:00"}
at3.run()
check("12 a FAILED check shows a cross, not a tick",
      "✗" in corner(at3) and "✓" not in corner(at3), corner(at3)[:160])

# a verdict about the OTHER engine must not be worn by this one
at3.session_state["_engine_check"] = {
    "engine": "studio", "state": EN.OK, "rows": [], "at": "12:00"}
at3.run()
check("13 a verdict for a DIFFERENT engine is not worn by this one",
      "✓" not in corner(at3), corner(at3)[:160])

# --- a hand-patched crosspoint reads as mixed -------------------------
at4 = app("transcribe")
at4.session_state["route_stt"] = "groq"
at4.session_state["route_tts"] = "speechify"
at4.session_state["route_llm"] = "groq"
at4.run()
check("14 a mixed board says mixed, not a stale engine name",
      "mixed" in corner(at4).lower(), corner(at4)[:160])

# --- switching engines drops a stale verdict --------------------------
at5 = app()
at5.run()
at5.session_state["_engine_check"] = {
    "engine": "free", "state": EN.OK, "rows": [], "at": "12:00"}
at5.run()
[b for b in at5.get("button") if b.key == "eng_studio"][0].click().run()
check("15 switching engine FORGETS the old verdict",
      sget(at5, "_engine_check") is None, sget(at5, "_engine_check"))

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
