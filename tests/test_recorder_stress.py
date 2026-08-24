"""G6 — STRESS. The world misbehaving on purpose, on the take path.

The specific risk this release introduces: `_digest_done` makes an
unfinished take eligible to run again. If a REAL error left it unfinished
too, the app would retry on every redraw and spend a key each time. That
must not happen, and it is checked here.
"""

import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.runtime.scriptrunner_utils.exceptions import RerunException  # noqa: E402
from streamlit.runtime.scriptrunner_utils.script_requests import RerunData  # noqa: E402

import subprocess
import tempfile

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def make(seconds, path):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=%d" % seconds,
                    "-c:a", "libopus", "-b:a", "128k", path], check=True)
    return open(path, "rb").read()


TMP = tempfile.gettempdir()
SHORT = make(3, os.path.join(TMP, "s.webm"))
LONG = make(120, os.path.join(TMP, "l.webm"))
WORDS = "ovo je test"

mode = {"do": "ok", "calls": 0}


class _Tx:
    def create(self, **kw):
        mode["calls"] += 1
        if mode["do"] == "rerun":
            raise RerunException(RerunData())
        if mode["do"] == "dead":
            raise RuntimeError("401 Invalid API Key")
        return WORDS


class FakeGroq:
    def __init__(self, *a, **k):
        self.audio = type("A", (), {"transcriptions": _Tx()})()


import groq  # noqa: E402
groq.Groq = FakeGroq

from streamlit.testing.v1 import AppTest  # noqa: E402


class Take(io.BytesIO):
    name = "take.webm"


def sget(at, k, d=None):
    try:
        return at.session_state[k]
    except (KeyError, AttributeError):
        return d


def app():
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=300)
    at.secrets["APP_PASSWORDS"] = ["stub"]
    at.secrets["ADMIN_USER"] = "stub"
    at.secrets["GROQ_API_KEYS"] = ["gsk_test"]
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    at.session_state["active_tab"] = "transcribe"
    return at


def box(at):
    a = [x for x in at.text_area if x.key.startswith("tx_area_")]
    return a[0].value if a else None


def feed(at, raw):
    at.session_state["_take_mic_0"] = Take(raw)
    at.session_state["_take_mime"] = "audio/webm"


print("G6 STRESS — the take path under sabotage\n")

# --- SABOTAGE 1: a dead key must NOT become an endless retry ---------
print("SABOTAGE — every key is dead")
mode.update(do="dead", calls=0)
at = app()
at.run()
feed(at, SHORT)
for _ in range(8):
    at.run()
check("the failure is shown to the person", bool(at.error), "no error rendered")
check("it is NOT retried on every redraw (a key would be spent each time)",
      mode["calls"] <= 3, "whisper called %d times over 8 redraws" % mode["calls"])
print("       whisper calls over 8 redraws: %d" % mode["calls"])

# --- SABOTAGE 2: interrupted, then interrupted again -----------------
print("\nSABOTAGE — interrupted twice in a row, then allowed to finish")
mode.update(do="rerun", calls=0)
at = app()
at.run()
feed(at, SHORT)
at.run()
at.run()
mode["do"] = "ok"
for _ in range(4):
    at.run()
check("it still recovers after two interruptions", box(at) == WORDS, box(at))
print("       whisper calls: %d" % mode["calls"])

# --- SOAK: fifty redraws after a finished take -----------------------
print("\nSOAK — fifty redraws after the words have landed")
mode.update(do="ok", calls=0)
at = app()
at.run()
feed(at, SHORT)
at.run()
at.run()
first = mode["calls"]
for _ in range(50):
    at.run()
check("the transcript is untouched after 50 redraws", box(at) == WORDS, box(at))
check("no take was re-transcribed while idling",
      mode["calls"] == first, "%d -> %d" % (first, mode["calls"]))
print("       whisper calls: %d before, %d after 50 redraws" % (first, mode["calls"]))

# --- ENORMOUS: a two-minute take, chunked ----------------------------
print("\nENORMOUS — a two-minute take")
mode.update(do="ok", calls=0)
at = app()
at.run()
feed(at, LONG)
at.run()
at.run()
check("a long take still reaches the box", bool((box(at) or "").strip()),
      box(at))
print("       whisper calls: %d, _last_run: %s"
      % (mode["calls"], sget(at, "_last_run")))

# --- EMPTY and MALFORMED ---------------------------------------------
print("\nEMPTY and MALFORMED")
for name, blob in (("a zero-byte take", b""),
                   ("a truncated webm", SHORT[:200]),
                   ("a picture, not sound", b"\x89PNG\r\n\x1a\n" + b"\x00" * 400)):
    mode.update(do="ok", calls=0)
    at = app()
    at.run()
    feed(at, blob)
    at.run()
    at.run()
    at.run()
    standing = box(at) is not None or bool(at.error)
    check("%s leaves the page standing" % name, standing,
          [e.value[:80] for e in at.exception])

print("\n{} passed, {} failed".format(passed, failed))


def test_stress():
    assert failed == 0, "%d of %d failed" % (failed, passed + failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
