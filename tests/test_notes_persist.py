"""NOTES MUST SURVIVE A RELOAD.

Baba: "notes are not surviving between sessions — I create a note, I
log in as Emina again, and the note is gone."

They lived in session_state alone, which dies with the tab. Everything
a person typed was kept exactly as long as they kept the page open,
which makes a notebook a scratchpad.

WHAT THIS DOES NOT TEST, and cannot: whether the browser really wrote
the value. ls_sync is a component, and a component returns its default
under AppTest (§73). What is testable is the two halves either side of
it — that a change QUEUES a write, and that a value coming back from
storage is read into the notebook — plus the guard that stops a stale
copy overwriting live notes.

    python3 tests/test_notes_persist.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402
from ttt import notes as N                # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


APP = os.path.join(os.path.dirname(__file__), "..", "app.py")


def app(**state):
    at = AppTest.from_file(APP, default_timeout=90)
    at.secrets["APP_PASSWORDS"] = ["stub"]
    at.secrets["ADMIN_USER"] = "stub"
    at.secrets["GROQ_API_KEYS"] = ["gsk_test"]
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    at.session_state["active_tab"] = "transcribe"
    at.session_state["_notes_adopted"] = True
    for k, v in state.items():
        at.session_state[k] = v
    return at


def sget(at, key, default=None):
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


print("NOTES THAT SURVIVE A RELOAD\n")

# --- a change queues a write ------------------------------------------
seed = {}
N.add(seed, "prva biljeska")
at = app(**{N.KEY: seed[N.KEY]})
at.run()
check("1 the app renders", not at.exception, at.exception)

# Something changes the notebook, exactly as speaking into it would.
at.session_state[N.KEY] = seed[N.KEY] + [
    dict(seed[N.KEY][0], id="second", text="druga biljeska")]
at.run()
# WHAT IS OBSERVABLE IS THE FINGERPRINT, not the queue.
#
# persist_notes() queues the write and then calls st.rerun(), because
# the bridge sends what was queued BEFORE it — a write left in the queue
# at the end of a run waits for a run that may never come. The rerun
# means the queue is consumed within this same test run, so `_pending_ls`
# is empty by the time a check could look at it.
#
# `_notes_saved` is the record of what was written, and it is the thing
# that decides whether anything is written next time.
saved = sget(at, "_notes_saved")
check("2 A CHANGE IS WRITTEN — the fingerprint records it",
      bool(saved), saved)
try:
    body = json.loads(saved) if saved else None
except Exception:
    body = None
check("3 and what is written is the WHOLE notebook, not one note",
      isinstance(body, list) and len(body) == 2,
      len(body) if isinstance(body, list) else body)
check("4 with the words in it",
      any("druga" in (n.get("text") or "") for n in (body or [])), body)

# --- an unchanged notebook writes nothing ------------------------------
#
# Otherwise every render queues a write, the bridge runs every render,
# and a component round trip costs a rerun — the app would never settle.
at2 = app(**{N.KEY: seed[N.KEY]})
at2.run()
# AppTest's session_state has no .pop() — it is not a dict. Setting the
# key to an empty queue says the same thing.
first = sget(at2, "_notes_saved")
at2.run()
check("5 AN UNCHANGED NOTEBOOK WRITES NOTHING AGAIN — otherwise every "
      "render writes, every write forces a rerun, and the app never "
      "settles",
      sget(at2, "_notes_saved") == first, (first, sget(at2, "_notes_saved")))

# --- reading it back ---------------------------------------------------
#
# THE SOURCE IS CHECKED HERE, not the behaviour. LS_DATA is filled from
# ls_sync, which is a component and returns its default under AppTest —
# so a value cannot be pushed in from a test. Same limit as §73, named
# rather than worked around.
src = open(APP, encoding="utf-8").read()
body = src.split("def restore_notes(", 1)[1].split("\ndef ", 1)[0]
check("6 restore reads the browser's copy", "LS_DATA.get(NOTES_LS_KEY)" in body,
      body[:200])
check("7 IT RUNS ONCE per session", "_notes_restored" in body, body[:200])
check("8 AND IT WILL NOT OVERWRITE LIVE NOTES. Restoring over a "
      "notebook that already has something in it would undo whatever "
      "was said in the seconds before the write landed",
      "st.session_state.get(NOTES.KEY)" in body, body[:300])
check("9 a corrupt value is ignored rather than crashing the app",
      "except Exception" in body, body[:300])
check("10 and only a list is accepted — a string or a dict from an "
      "older shape must not become the notebook",
      "isinstance(got, list)" in body, body[:300])

# --- the key is per person ---------------------------------------------
check("11 THE KEY NAMES THE PERSON, so two people on one phone do not "
      "read each other's notebooks",
      'NOTES_LS_KEY = f"maha_notes_{USER}"' in src,
      [l for l in src.splitlines() if "NOTES_LS_KEY =" in l])

# --- the two faults a browser found, and AppTest cannot ---------------
#
# BOTH OF THESE SHIPPED AND BOTH WERE INVISIBLE HERE. Their mutations
# survive every behavioural check above, because both live on the far
# side of a COMPONENT and a component returns its default under AppTest.
# Source checks, labelled as such, are worth more than the false comfort
# of eleven green checks that cannot see them.
psrc = src.split("def persist_notes(", 1)[1].split("\ndef ", 1)[0]

check("12 A WRITE ASKS FOR ONE MORE RUN. The bridge sends what was "
      "queued BEFORE it, so a write queued at the end of a run waits "
      "for a run that may never come — measured: localStorage held [] "
      "while notes sat on the screen",
      "st.rerun()" in psrc, psrc[-200:])
check("13 and the fingerprint is set BEFORE that rerun, so it cannot "
      "loop", psrc.index('_notes_saved"] = now') < psrc.index("st.rerun()"),
      "order wrong")

rsrc = src.split("def restore_notes(", 1)[1].split("\ndef ", 1)[0]
check("14 RESTORE WAITS FOR THE BRIDGE. On the first render after a "
      "reload LS_DATA is empty because the component has not reported "
      "yet — giving up there marks the notebook restored and it is "
      "never read back",
      "if not LS_DATA:" in rsrc, rsrc[:300])

# --- and Drive, beside the recordings ----------------------------------
#
# Baba: "notes should be saved in the same location where audio files
# are saved, and a simple text file as a backup in Google Drive."
#
# SOURCE CHECKS. The Drive store is off without secrets and its calls go
# over the network, so the behaviour cannot be reached here. What the
# GAS side does is tested for real in tests/gastest/test_notes_drive.js,
# against the actual Code.gs in a fake Drive.
check("15 THE BROWSER IS THE FAST COPY AND DRIVE IS THE TRUE ONE — a "
      "save goes to both", "put_notes" in psrc, psrc[-400:])
check("16 and Drive never blocks the browser copy: it is wrapped, so a "
      "notebook that cannot reach Drive still saves locally and the "
      "person can still type",
      "try:" in psrc.split("put_notes")[0][-200:], psrc[-400:])
check("17 RESTORE FALLS BACK TO DRIVE when the browser has nothing — a "
      "new device, or a cleared browser, which is the one case the "
      "browser copy cannot cover",
      "get_notes" in rsrc, rsrc[-400:])
check("18 and only when the browser is EMPTY, never as a merge: two "
      "copies edited in two places cannot be merged without deciding "
      "which edit loses",
      rsrc.index("if not raw:") < rsrc.index("get_notes"), "order wrong")

print("\n{} passed, {} failed".format(passed, failed))

if __name__ == "__main__":
    sys.exit(1 if failed else 0)


def test_notes_persist():
    assert failed == 0, "%d of %d checks failed" % (failed, passed + failed)
