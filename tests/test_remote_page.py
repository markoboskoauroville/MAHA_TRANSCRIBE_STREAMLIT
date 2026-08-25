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
      "REMOTE.put(REMOTE_STORE, remote_code(), t1_text(), REMOTE.SAY)" in src)
check("2b the hear channel is read back",
      "REMOTE.get(REMOTE_STORE, _rem_code, REMOTE.HEAR)" in src)
check("2c arrival is decided by the sequence, not by comparing text",
      "REMOTE.arrived(_hear" in src)
# THE WRITE MOVED TO kept_set IN v218, when the boxes stopped living in
# widget keys. index() then raised and killed this file; my first repair
# left an unbalanced paren and killed it a second way. Both bounds are
# find() now and both are checked before being compared.
_seq_at = src.find('_rem_heard_seq"] = int')
_use_at = src.find('kept_set("talk_text", _hear')
check("2d0 both halves of the handover are present",
      _seq_at > 0 and _use_at > 0, (_seq_at, _use_at))
check("2d what arrives is marked taken BEFORE it is acted on",
      0 < _seq_at < _use_at, (_seq_at, _use_at))
check("2e and it starts reading by itself", '"_auto_read"] = True' in src)
check("2f the remote page pushes with force, so push always sends",
      "REMOTE.HEAR, force=True" in src)

# THE ORDERING BUG BABA FOUND WITH TWO TABS OPEN, 25.8.2026.
# The push read _t1_text ABOVE the tab bar — before the T body that
# produces it — so it published the previous render's text, and on the
# render where a take landed it published "". The window then showed a
# fresh "updated 1m ago" (its own creation time) over an empty box.
print("       checking WHERE the push happens, not just that it does")
i_tabs = src.index('key="active_tab"')
i_push = src.index("REMOTE.put(REMOTE_STORE, remote_code(), t1_text(), REMOTE.SAY)")
i_pull = src.index("REMOTE.arrived(_hear")
check("2g the PUSH happens after the tab bodies, not above the tab bar",
      i_push > i_tabs, (i_tabs, i_push))
check("2h the PULL still happens before them, so arriving text can act",
      i_pull < i_tabs, (i_pull, i_tabs))
check("2i the push is guarded — the last line of the script must not be "
      "what takes the page down",
      "except Exception:" in src[i_push:i_push + 400])

# THE §63 TRAP. value= and key= together means Streamlit reads
# session_state and ignores value, so the box never showed anything.
print("       checking the remote box does not pass value= AND key=")
box = src[src.index("def _remote_transcript"):]
box = box[:box.index("st.button(t(\"rem_refresh\")")]
check("2j the transcript box passes value and NO key",
      "value=slot.get" in box and 'key="rem_box' not in box, box[:200])

# THE ACTION ROW UNDER THE PULLED TRANSCRIPT. Baba, 25.8.2026: "we miss
# the action buttons. Refresh now, great. Then we need to have copy."
print("       checking the action row under the pulled transcript")
# SLICE PAST THE def LINE. "def _remote_transcript():" CONTAINS
# "_remote_transcript()" as a substring, so slicing to that marker gave
# an empty string and three checks read as failures on code that was
# right there. Caught twice in this file; anchoring on the call site
# after the body is what actually works.
_i = src.index("def _remote_transcript")
row = src[_i:src.index("\n    _remote_transcript()", _i)]
check("2k copy is there, and it is a real clipboard component",
      "copybtn.cp_html(slot.get" in row, row[-400:])
check("2l it copies what the box is SHOWING, not a stale capture",
      'cp_html(slot.get("text")' in row)
check("2m refresh is still there beside it",
      't("rem_refresh")' in row)
check("2n copy comes FIRST — box_links' rule, copy outranks the rest",
      row.index("cp_html(slot.get") < row.index('t("rem_refresh")'))

print("\n3 THE REMOTE PAGE — a code nobody opened")
at3 = boot(query="zzzzzzz"); at3.run()
check("3a a closed window is a sentence, not a crash", not at3.exception,
      [e.value[:200] for e in at3.exception])
check("3b and it says the window is closed",
      any("closed" in str(x.value).lower() for x in at3.info), texts(at3)[:200])
check("3bb the link row is a collapsed expander, one line until wanted",
      'with st.expander(t("rem_link")' in src)
check("3bc and it carries a real clipboard component, not a fake link",
      "copybtn.cp_html(_rem_url" in src)
check("3c it does NOT show the tab bar", not [r for r in at3.get("segmented_control")
                                              if r.key == "active_tab"])

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
