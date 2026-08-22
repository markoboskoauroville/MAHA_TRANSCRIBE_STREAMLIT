"""THE PATCH BAY IS GONE, AND THE ENGINE COMES FROM THE SHEET.

    python3 tests/test_engine_sheet.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402

from ttt import routing as RO  # noqa: E402
from ttt import sheet as SHEET  # noqa: E402

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


def clean_stored(user="stub"):
    import tempfile
    p = os.path.join(tempfile.gettempdir(), "maha_settings",
                     "".join(c for c in user if c.isalnum()) + ".json")
    try:
        os.remove(p)
    except OSError:
        pass


print("PATCH BAY GONE, ENGINE FROM THE SHEET\n")

# --- the patch bay is really gone -------------------------------------
check("1 routing has no matrix()", not hasattr(RO, "matrix"))
check("2 routing has no crosspoint()", not hasattr(RO, "crosspoint"))
check("3 the crosspoint states are gone too",
      not any(hasattr(RO, n) for n in ("PATCHED", "OPEN", "NOKEY", "BLANK")))

src = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
check("4 no patchbay CSS left in app.py", "st-key-patchbay" not in src)

check("5 allow_patch_bay is out of the sheet defaults",
      "allow_patch_bay" not in SHEET.DEFAULTS, list(SHEET.DEFAULTS))

gs = open(os.path.join(os.path.dirname(__file__), "..", "apps_script",
                       "Code.gs"), encoding="utf-8").read()
check("6 and out of the Apps Script seed rows", "allow_patch_bay" not in gs)

# --- what routing KEPT, because engines are built on it ---------------
check("7 resolve() is still there — engines are built on it",
      callable(getattr(RO, "resolve", None)))
check("8 all_routes() is still there", callable(getattr(RO, "all_routes", None)))
check("9 TASKS still names all three jobs",
      [t.id for t in RO.TASKS] == ["stt", "tts", "llm"],
      [t.id for t in RO.TASKS])

# --- the sheet now carries the engine ---------------------------------
check("10 engine is a sheet setting with a default",
      SHEET.DEFAULTS.get("engine") == "free", SHEET.DEFAULTS.get("engine"))
check("11 and the Apps Script seeds it", "'engine'" in gs)

cfg = {"ok": True, "settings": [["global", "engine", "studio"]]}
check("12 a global row is read",
      SHEET.setting(cfg, "engine") == "studio", SHEET.setting(cfg, "engine"))
cfg2 = {"ok": True, "settings": [["global", "engine", "studio"],
                                 ["stub", "engine", "free"]]}
check("13 a user row beats the global row",
      SHEET.setting(cfg2, "engine", "stub") == "free",
      SHEET.setting(cfg2, "engine", "stub"))
check("14 an absent sheet falls back to the built-in default",
      SHEET.setting({}, "engine") == "free", SHEET.setting({}, "engine"))


# --- the app applies it -----------------------------------------------
def app(sheet_cfg=None, tab="transcribe"):
    clean_stored()
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=90)
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    at.session_state["active_tab"] = tab
    if sheet_cfg is not None:
        # Pre-seed the cache so no network call is made — the fetch is
        # cached per session, which is exactly the seam to test through.
        at.session_state["_sheet_config"] = sheet_cfg
    return at


at = app({"ok": True, "settings": [["global", "engine", "studio"]]})
at.run()
check("15 THE SHEET'S ENGINE IS APPLIED at startup",
      (sget(at, "route_stt"), sget(at, "route_tts"), sget(at, "route_llm"))
      == ("assemblyai", "speechify", "anthropic"),
      (sget(at, "route_stt"), sget(at, "route_tts"), sget(at, "route_llm")))

at2 = app({"ok": True, "settings": [["global", "engine", "free"]]})
at2.run()
check("16 and the other way round",
      sget(at2, "route_tts") == "edge", sget(at2, "route_tts"))

# --- a press must not be undone by the sheet on the next rerun --------
at3 = app({"ok": True, "settings": [["global", "engine", "free"]]},
          tab="settings")
at3.run()
[b for b in at3.get("button") if b.key == "eng_studio"][0].click().run()
at3.run()
at3.run()
check("17 A PRESS OUTRANKS THE SHEET for the rest of the session — "
      "otherwise the button reads as dead",
      sget(at3, "route_tts") == "speechify", sget(at3, "route_tts"))

# --- nonsense in the sheet changes nothing ----------------------------
at4 = app({"ok": True, "settings": [["global", "engine", "banana"]]})
at4.run()
check("18 an engine name that does not exist switches nothing",
      sget(at4, "route_tts") in (None, "edge"), sget(at4, "route_tts"))
check("19 and the app still runs", not at4.exception, at4.exception)

at5 = app({})
at5.run()
check("20 an unreachable sheet is not an error", not at5.exception,
      at5.exception)

# --- writing the engine BACK to the sheet -----------------------------
import json as _json  # noqa: E402
import threading  # noqa: E402
from http.server import BaseHTTPRequestHandler, HTTPServer  # noqa: E402

SEEN = []
MODE = {"old_deployment": False}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = _json.loads(self.rfile.read(n).decode())
        SEEN.append(body)
        if body.get("token") != "TOK":
            out = {"ok": False, "error": "bad token"}
        elif MODE["old_deployment"]:
            # A deployment WITHOUT the set_put branch falls through to the
            # usage-logging appendRow and answers ok — the §47 trap.
            out = {"ok": True}
        elif body.get("what") != "set_put":
            out = {"ok": False, "error": "unknown"}
        elif body.get("key") not in ("engine",):
            out = {"ok": False, "error": "not writable"}
        else:
            out = {"ok": True, "updated": True,
                   "scope": body.get("scope"), "key": body.get("key")}
        raw = _json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:{}/".format(srv.server_port)

check("21 put_setting writes the engine",
      SHEET.put_setting(URL, "TOK", "engine", "studio") is True)
check("22 it sends what=set_put with scope global",
      SEEN[-1]["what"] == "set_put" and SEEN[-1]["scope"] == "global",
      SEEN[-1])

check("23 a bad token cannot write",
      SHEET.put_setting(URL, "WRONG", "engine", "studio") is False)
check("24 a setting the script will not write is refused",
      SHEET.put_setting(URL, "TOK", "prompt_grammar", "x") is False)

MODE["old_deployment"] = True
check("25 AN OLD DEPLOYMENT ANSWERING ok IS NOT BELIEVED — success is "
      "only accepted when the reply names the key back (the §47 trap)",
      SHEET.put_setting(URL, "TOK", "engine", "studio") is False)
MODE["old_deployment"] = False

check("26 an unreachable script is False, not a crash",
      SHEET.put_setting("http://127.0.0.1:1/", "TOK", "engine", "free") is False)
check("27 no url is False", SHEET.put_setting("", "TOK", "engine", "free") is False)

srv.shutdown()

print("\n{} passed, {} failed".format(passed, failed))


def test_engine_sheet():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_engine_sheet.py` is how it is meant to be read."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
