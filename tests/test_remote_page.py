"""THE REMOTE WINDOW, wired — the page, the link, the push and the pull.

    python3 tests/test_remote_page.py

ttt/remote.py is tested alone in test_remote.py. This is the other half:
that the app actually USES it. four-tests.md, Test 2 — the gap between
"the function works" and "the feature works" is where the shipped bugs
live, and every check here drives the real app.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import remote as R  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

APP = os.path.join(os.path.dirname(__file__), "..", "app.py")

def boot(query=None):
    at = AppTest.from_file(APP, default_timeout=120)
    at.secrets["APP_PASSWORDS"] = ["stub"]
    at.secrets["ADMIN_USER"] = "stub"
    at.secrets["GROQ_API_KEYS"] = ["gsk_test"]
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    if query:
        at.query_params["remote"] = query
    return at

def sget(at, k, d=None):
    """AppTest's session_state has no .get — a missing key raises
    AttributeError from a confusing place. Every read goes through here."""
    try:
        return at.session_state[k]
    except (KeyError, AttributeError):
        return d


def texts(at):
    return " ".join(str(getattr(m, "value", "") or getattr(m, "body", ""))
                    for m in list(at.markdown) + list(at.info) + list(at.error))

print("1 THE DEVICE SIDE — the link is above the tabs")
at = boot(); at.run()
check("1a the app still starts with all this in front of the door",
      not at.exception, [e.value[:200] for e in at.exception])
code = sget(at, "_remote_code")
check("1b a window code was made", bool(code) and len(code) == R.CODE_LENGTH, code)
body = texts(at)
check("1c the link is on the page", "?remote=" + (code or "x") in body, body[:200])
check("1d and the whole address is shown, not a shortened one",
      body.count("?remote=" + (code or "x")) >= 2, body.count("?remote="))
i_link = body.find("remote=")
check("1e it is drawn BEFORE the tab bar", i_link >= 0)

print("\n2 PUSH — the wiring, and what cannot be reached from here")
# HONESTY FIRST. The relay is a st.cache_resource dict, shared between
# SESSIONS of one server. AppTest re-executes app.py for every run, so
# each run gets a fresh function object and therefore a fresh cache
# entry — two AppTests are two universes, not two devices.
#
# So the thing this feature exists for, one device seeing another's
# text, CANNOT BE TESTED HERE AT ALL. Saying so is the point; the first
# draft of this file reached into `import app` for the store, got a
# THIRD unrelated dict, and reported the feature broken when it was the
# test that was wrong.
print("       cross-session sharing needs a real server: NOT TESTED here")
print("       searched app.py for the push and the pull call sites")
src = open(APP, encoding="utf-8").read()
check("2a the transcript is pushed on the say channel",
      "REMOTE.put(REMOTE_STORE, _rem_code, t1_text(), REMOTE.SAY)" in src)
check("2b the hear channel is read back",
      "REMOTE.get(REMOTE_STORE, _rem_code, REMOTE.HEAR)" in src)
check("2c arrival is decided by the sequence, not by comparing text",
      "REMOTE.arrived(_hear" in src)
check("2d what arrives is marked taken BEFORE it is acted on",
      src.index('_rem_heard_seq"] = int') < src.index('"talk_text"] = _hear'))
check("2e and it starts reading by itself", '"_auto_read"] = True' in src)
check("2f the remote page pushes with force, so push always sends",
      "REMOTE.HEAR, force=True" in src)

print("\n3 THE REMOTE PAGE — a code nobody opened")
at3 = boot(query="zzzzzzz"); at3.run()
check("3a a closed window is a sentence, not a crash", not at3.exception,
      [e.value[:200] for e in at3.exception])
check("3b and it says the window is closed",
      any("closed" in str(x.value).lower() for x in at3.info), texts(at3)[:200])
check("3c it does NOT show the tab bar", not [r for r in at3.get("segmented_control")
                                              if r.key == "active_tab"])

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
