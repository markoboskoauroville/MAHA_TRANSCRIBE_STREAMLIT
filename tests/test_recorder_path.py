"""THE RECORDER PATH — the check that was missing.

Nothing in this repo drove a take. v177 to v184 shipped through nine
gates with the transcript never reaching the box, because every test
that touches the box WRITES `_t1_text` itself (tests/test_box.py) and so
proves the container while proving nothing about what fills it.

This file starts where the deck stops: it puts a real webm/opus take
exactly where `cassette_recorder` puts one, at `_take_<rec_key>`, and
asks what ends up in the box.

The four, and each fails alone:

    1  MECHANISM   the take is recognised, converted, and reaches Whisper
    2  REAL        a transcript that comes back is IN THE BOX
    3  UGLY        a run interrupted mid-transcription recovers, and the
                   deck is acknowledged BEFORE the long work starts
    4  UPGRADE     a session carrying the previous version's leftovers
                   still transcribes

    python3 tests/test_recorder_path.py

WHY 3 IS THE ONE THAT MATTERS. The deck holds its blob until Python
echoes the stamp, and re-posts after 2, 4, 8, 15, 25 seconds. Every
re-post is a rerun. Streamlit's RerunException is a BaseException, so it
passes through `except Exception` untouched — and `_digest` is committed
BEFORE the work begins. Measured 24.8.2026: on a three-second
transcription the deck re-posts at t+2.6s and is acknowledged at t+4.0s.
The run dies in between, the digest says the take is done, and the box
stays empty for ever with nothing red on the screen.
"""

import base64
import io
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.runtime.scriptrunner_utils.exceptions import RerunException  # noqa: E402
from streamlit.runtime.scriptrunner_utils.script_requests import RerunData  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


# --- a real take, in the deck's own format ---------------------------
# webm/opus at 128k is what MediaRecorder produces and what the deck
# sends. Generated rather than committed: a binary fixture in the repo
# is a binary fixture nobody can read a diff of.
def make_take(seconds=3):
    path = os.path.join(tempfile.gettempdir(), "gate_take.webm")
    if not os.path.exists(path):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
             "-i", "sine=frequency=440:duration=%d" % seconds,
             "-c:a", "libopus", "-b:a", "128k", path], check=True)
    return open(path, "rb").read()


RAW = make_take()
STAMP = 1756000000000
WORDS = "ovo je test hrvatskog jezika jedan dva tri"


class Take(io.BytesIO):
    name = "take.webm"


# --- the stubs -------------------------------------------------------
# Groq is replaced at the SDK, which is the seam app.py actually uses
# (`from groq import Groq`, line 35). Not a mock of our own wrapper:
# mocking the wrapper would prove the wrapper agrees with itself.
state = {"calls": 0, "raise_on": 0, "acks": []}


class _Tx:
    def create(self, **kw):
        state["calls"] += 1
        if state["calls"] == state["raise_on"]:
            # Exactly what a deck re-post does to a running script.
            raise RerunException(RerunData())
        return WORDS


class FakeGroq:
    def __init__(self, *a, **k):
        self.audio = type("A", (), {"transcriptions": _Tx()})()


import groq  # noqa: E402
groq.Groq = FakeGroq


def fake_deck(*a, **kw):
    """Stands in for the cassette component and records the ack it is
    handed, so test 3 can ask WHEN the deck was told its take landed."""
    key = str(kw.get("key", ""))
    if key.startswith(("mic_", "sys_")):
        state["acks"].append((state["calls"], kw.get("ack")))
        if state.get("deck_posts"):
            return {"b64": base64.b64encode(RAW).decode(), "mime": "audio/webm",
                    "name": "take.webm", "seconds": 3, "bytes": len(RAW),
                    "at": STAMP}
    return None


import streamlit.components.v1 as c1  # noqa: E402
_real_declare = c1.declare_component


def _declare(name, *a, **kw):
    return fake_deck if "cassette" in str(name) else _real_declare(name, *a, **kw)


c1.declare_component = _declare

from streamlit.testing.v1 import AppTest  # noqa: E402


def sget(at, key, default=None):
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def app():
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=180)
    at.secrets["APP_PASSWORDS"] = ["stub"]
    at.secrets["ADMIN_USER"] = "stub"
    at.secrets["GROQ_API_KEYS"] = ["gsk_test"]
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    at.session_state["active_tab"] = "transcribe"
    return at


def box(at):
    areas = [a for a in at.text_area if a.key.startswith("tx_area_")]
    return areas[0].value if areas else None


def reset(**kw):
    state.update({"calls": 0, "raise_on": 0, "acks": [], "deck_posts": False})
    state.update(kw)


print("THE RECORDER PATH — a take, all the way to the box\n")

# --- TEST 1 — THE MECHANISM ------------------------------------------
# Closes "the logic is wrong". Does a take get RECOGNISED and converted,
# and does something actually ask Whisper for words?
print("1 MECHANISM — the take is recognised and reaches Whisper")
reset()
at = app()
at.run()
at.session_state["_take_mic_0"] = Take(RAW)
at.session_state["_take_mime"] = "audio/webm"
at.run()
at.run()                      # fix A costs one rerun; old code needs none
run = sget(at, "_last_run") or {}
check("1a the file was identified as WebM", run.get("in") == "WebM", run)
check("1b it was converted to 16 kHz mono FLAC",
      run.get("out") == "16 kHz mono FLAC", run)
check("1c Whisper was asked, exactly once", state["calls"] == 1, state["calls"])

# --- TEST 2 — THE REAL THING -----------------------------------------
# Closes "the logic is right but nothing calls it". test_box.py proves a
# value put in _t1_text is shown; this proves a TRANSCRIPT gets there.
print("\n2 REAL — the words are in the box, and they stay")
check("2a the transcript is in the box", box(at) == WORDS, box(at))
check("2b _last_run counted the characters",
      run.get("chars") == len(WORDS), run.get("chars"))
at.run()
at.run()
check("2c it survives two more reruns", box(at) == WORDS, box(at))

# --- TEST 3 — THE UGLY CASE ------------------------------------------
# Closes "it works when the world behaves". This is the live bug of
# 24.8.2026 and it fails on v184.
print("\n3 UGLY — a rerun lands mid-transcription")
reset(raise_on=1)
at = app()
at.run()
at.session_state["_take_mic_0"] = Take(RAW)
at.session_state["_take_mime"] = "audio/webm"
at.run()                                   # killed inside Whisper
check("3a the interruption is silent, as Streamlit intends",
      not at.error and not at.exception,
      [e.value[:80] for e in at.error])
# The person is now looking at an empty box. The page redraws — a
# keystroke, a pill, the deck posting again. It must recover.
for _ in range(4):
    at.run()
check("3b the take is transcribed after the interruption, not abandoned",
      state["calls"] >= 2, "whisper called %d time(s)" % state["calls"])
check("3c THE WORDS REACH THE BOX", box(at) == WORDS, box(at))
check("3d and no recording was silently dropped",
      sget(at, "_digest") is not None)

# --- TEST 3e — THE ACK, WHICH IS THE CAUSE ---------------------------
# The deck re-posts until acknowledged, and every re-post is a rerun.
# So the deck must hold its ack BEFORE the long work starts, not after.
print("\n3e ACK — the deck is acknowledged before the long work")
reset(deck_posts=True)
at = app()
at.run()                                   # the deck posts its take here
at.run()
at.run()
before = [ack for calls, ack in state["acks"] if calls == 0]
check("3e the deck was told its take landed BEFORE Whisper was asked",
      STAMP in before,
      "acks seen before the first whisper call: %s" % before)

# --- TEST 4 — THE UPGRADE --------------------------------------------
# Closes "it works on a machine that never ran the old version". A live
# session carries the previous version's keys in session_state; a new
# flag must not make an old session unable to transcribe.
print("\n4 UPGRADE — a session left over from the previous version")
reset()
at = app()
at.run()
at.session_state["_digest"] = "leftover-digest-from-v184"
at.session_state["flac_path"] = "/tmp/gone.flac"
at.session_state["_take_mic_0"] = Take(RAW)
at.session_state["_take_mime"] = "audio/webm"
at.run()
at.run()
check("4a an old session still transcribes a new take", state["calls"] == 1,
      state["calls"])
check("4b and the words reach the box", box(at) == WORDS, box(at))

print("\n{} passed, {} failed".format(passed, failed))


def test_recorder_path():
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
