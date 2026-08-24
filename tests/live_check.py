"""LIVE — the whole app, with Baba's real Secrets and a real Groq call.

Nothing is stubbed. This is Test 2 as `four-tests.md` means it: the real
endpoint, the real key, driven the way a person drives it, with an
outside number that has to agree.

    python3 tests/live_check.py

NOT a pytest file. It spends real money — a few seconds of Whisper — so
it runs when somebody asks for it, never in the suite.
"""

import io
import urllib.parse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402

TAKE = "/home/claude/real_take.webm"
SPOKEN = "this is a test of the transcription app one two three"

# THE NAMES ARE READ FROM THE SECRETS FILE, NEVER WRITTEN HERE.
# With this door the username IS the whole credential — there is no
# password behind it — so a real name in a committed test file is a
# credential in the repository.
import tomllib as _toml  # noqa: E402
_SEC = _toml.load(open(os.path.join(os.path.dirname(__file__), "..",
                                    ".streamlit", "secrets.toml"), "rb"))
OWNER = str(_SEC.get("ADMIN_USER1") or _SEC.get("ADMIN_USER") or "")
FREE = str(_SEC.get("FREE_USER1") or "")

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


def app():
    """NO at.secrets AT ALL. It reads .streamlit/secrets.toml, which holds
    exactly what Baba pastes into Streamlit Cloud. Overriding any of it
    here would be testing a file nobody deploys."""
    return AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=300)


def box(at):
    a = [x for x in at.text_area if x.key.startswith("tx_area_")]
    return a[0].value if a else None


def enter(at, name):
    at.run()
    at.text_input[0].set_value(name)
    [b for b in at.get("button") if b.key == "login_L"][0].click().run()
    return at


class Take(io.BytesIO):
    name = "take.webm"


print("LIVE — real Secrets, real Groq, real audio\n")

# --- 1. THE DOOR, with the real names --------------------------------
print("1 THE DOOR")
at = app()
at.run()
check("1a the app starts on this secrets file", not at.exception,
      [e.value[:200] for e in at.exception])
check("1b one box, one L", len(at.text_input) == 1
      and [b.label for b in at.get("button")] == ["L"],
      [b.label for b in at.get("button")])

at = enter(app(), OWNER)
check("1c Baba gets in", sget(at, "_authed") is True)
check("1d as admin", sget(at, "_view_tier") == "admin", sget(at, "_view_tier"))

at_free = enter(app(), FREE)
check("1e emina gets in", sget(at_free, "_authed") is True)
check("1f as free", sget(at_free, "_view_tier") == "free",
      sget(at_free, "_view_tier"))

at_bad = enter(app(), OWNER + "-not-me")   # a name that is in no tier
check("1g a name in no tier does not open it",
      sget(at_bad, "_authed") is not True)

# --- 2. THE RADIO -----------------------------------------------------
print("\n2 THE RADIO")
r = [x for x in at.get("radio") if x.key == "_view_tier"]
check("2a Baba gets all three tiers",
      r and list(r[0].options) == ["free", "studio", "admin"],
      list(r[0].options) if r else None)
check("2b emina gets no radio",
      not [x for x in at_free.get("radio") if x.key == "_view_tier"])

# --- 3. A REAL RECORDING, ALL THE WAY ---------------------------------
# This is the bug of 24.8.2026, tested against the real endpoint.
print("\n3 A REAL TAKE THROUGH REAL WHISPER")
raw = open(TAKE, "rb").read()
at = enter(app(), OWNER)
at.session_state["speech_lang"] = "en"
at.session_state["_take_mic_0"] = Take(raw)
at.session_state["_take_mime"] = "audio/webm"

t0 = time.time()
at.run()          # fix A: this run stores the take and returns at once
at.run()          # the transcription happens here
took = time.time() - t0

run = sget(at, "_last_run") or {}
got = (box(at) or "").strip()
print("       _last_run: %s" % run)
print("       box: %r" % got[:120])
print("       %.1fs wall clock" % took)

check("3a no error on screen", not at.error and not at.exception,
      [e.value[:200] for e in at.error])
check("3b the file was recognised as WebM", run.get("in") == "WebM", run)
check("3c it was converted to 16 kHz mono FLAC",
      run.get("out") == "16 kHz mono FLAC", run)
check("3d WORDS CAME BACK FROM GROQ", bool(got), repr(got))

# THE OUTSIDE NUMBER. four-tests.md: the strongest Test 2 is one where an
# independent party agrees. Groq heard the audio and returned words; the
# words have to be the ones that were spoken, not merely non-empty.
spoken_words = set(SPOKEN.split())
heard = set("".join(c if c.isalnum() or c.isspace() else " "
                    for c in got.lower()).split())
overlap = len(spoken_words & heard)
print("       %d of %d spoken words came back: %s"
      % (overlap, len(spoken_words), sorted(spoken_words & heard)))
check("3e and they are THE WORDS THAT WERE SPOKEN",
      overlap >= len(spoken_words) * 0.6,
      "%d of %d" % (overlap, len(spoken_words)))
check("3f _last_run counted the characters",
      run.get("chars") == len(got), (run.get("chars"), len(got)))

# --- 4. IT STAYS ------------------------------------------------------
print("\n4 IT STAYS")
at.run()
at.run()
check("4a the transcript survives two reruns", (box(at) or "").strip() == got,
      box(at))
check("4b and Whisper was not asked again",
      (sget(at, "_last_run") or {}).get("chars") == run.get("chars"))

# --- 5. THE SHEET AND DRIVE -------------------------------------------
print("\n5 GOOGLE, AS STORAGE ONLY")
import urllib.request  # noqa: E402
sec = _SEC
try:
    req = urllib.request.Request(
        sec["SHEETS_URL"] + "?token=" + urllib.parse.quote(sec["SHEETS_TOKEN"])
        + "&action=config",
        headers={"User-Agent": "ttt-lll/gate"})
    with urllib.request.urlopen(req, timeout=45) as r:
        body = r.read(400).decode("utf-8", "replace")
    reachable = True
except Exception as e:
    body = "%s %s" % (getattr(e, "code", "?"), type(e).__name__)
    reachable = False
print("       sheet says: %s" % body[:200].replace("\n", " "))
check("5a the Apps Script answers", reachable, body[:200])
check("5b AUTH_URL is not needed by the app any more",
      "AUTH_URL" not in sec, "still in the file")

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
