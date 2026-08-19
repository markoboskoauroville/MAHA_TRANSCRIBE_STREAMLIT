"""ONE T, WITH A SOURCE DROPDOWN.

    python3 tests/test_source.py
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


def clean():
    import tempfile
    for who in ("stub",):
        p = os.path.join(tempfile.gettempdir(), "maha_settings", who + ".json")
        try:
            os.remove(p)
        except OSError:
            pass


def app():
    clean()
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=90)
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    at.session_state["active_tab"] = "transcribe"
    return at


print("ONE T, SOURCE DROPDOWN\n")

at = app()
at.run()
check("1 T renders", not at.exception, at.exception)

# --- T2 is gone -------------------------------------------------------
src = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
check("2 tabaudio is not in the tab list", '"tabaudio"' not in
      src.split("tabs = [")[1].split("]")[0])
check("3 the tab is called T, not T1",
      '"tab_transcribe":     {"en": "T",' in src)
check("4 there is no tab_tabaudio label left", '"tab_tabaudio"' not in src)

# --- the dropdown -----------------------------------------------------
sel = [x for x in at.selectbox if x.key == "rec_source"]
check("5 there is a source dropdown", len(sel) == 1,
      [x.key for x in at.selectbox])
# AppTest reports the FORMATTED labels, not the raw values — format_func
# has already run by the time .options is read. Asserting the raw values
# here failed against a dropdown that was perfectly correct.
check("6 it offers microphone and computer audio",
      sel and list(sel[0].options) == ["microphone", "computer audio"],
      sel[0].options if sel else None)
check("7 it starts on the microphone", sget(at, "rec_source") == "mic",
      sget(at, "rec_source"))

# --- switching --------------------------------------------------------
at2 = app()
at2.run()
[x for x in at2.selectbox if x.key == "rec_source"][0].select("system").run()
check("8 it can be switched to computer audio",
      sget(at2, "rec_source") == "system", sget(at2, "rec_source"))
check("9 and the app still runs", not at2.exception, at2.exception)

caps = " ".join(c.value for c in at2.caption)
check("10 computer audio shows the one line about ticking the audio box",
      "AUDIO BOX" in caps.upper(), caps[:120])

at3 = app()
at3.run()
caps3 = " ".join(c.value for c in at3.caption)
check("11 the microphone shows no such line — it is not different",
      "AUDIO BOX" not in caps3.upper(), caps3[:120])

# --- it survives a reload --------------------------------------------
check("12 rec_source is a persisted setting",
      '"rec_source"' in src.split("SETTINGS_KEYS = (")[1].split(")")[0])

# --- the component is told -------------------------------------------
wf = open(os.path.join(os.path.dirname(__file__), "..",
                       "cassette_frontend", "index.html"),
          encoding="utf-8").read()
check("13 the deck reads a source argument", "SOURCE=" in wf.replace(" ", ""))
check("14 system audio uses getDisplayMedia", "getDisplayMedia" in wf)
check("15 video is requested, because Chrome will not offer the audio "
      "checkbox otherwise", "video: true" in wf)
check("16 and the video track is stopped, not kept",
      "getVideoTracks().forEach" in wf)
check("17 SHARING WITHOUT AUDIO IS REFUSED, not recorded as silence",
      "noaudio" in wf and "tracks.length" in wf)
check("18 stopping the share from the browser bar ends the take",
      "'ended'" in wf)
check("19 ONE component, not two — there is no second deck file",
      not os.path.exists(os.path.join(os.path.dirname(__file__), "..",
                                      "system_frontend")))

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
