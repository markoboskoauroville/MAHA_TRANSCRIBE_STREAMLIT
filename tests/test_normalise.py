"""EVERY HUME VOICE AT THE SAME VOLUME.

    python3 tests/test_normalise.py

Baba, 25.8.2026: "There is an issue with Hume. Not all their voices are
on the same volume. Some are very loud, some are very quiet. We need to —
before playing any Hume audio, ffmpeg must normalise it. That's the
rule."

TEST 1 MEASURES. It builds two clips 29 dB apart, runs them through the
normaliser, and reads the loudness back with ffmpeg's own ebur128 —
which is an outside number, not our opinion of our own output.

TEST 2 reads the app and says what it searched for.

WHAT THIS CANNOT CATCH: how it sounds. Real Hume voices differ in more
than level, and loudness matching is not the same as sounding alike.
"""
import os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import audio as A  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

HAVE = bool(__import__("shutil").which("ffmpeg"))
TMP = tempfile.mkdtemp(prefix="norm_")


def tone(vol, name, seconds=3):
    path = os.path.join(TMP, name)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "sine=frequency=220:duration=%d" % seconds,
                    "-af", "volume=%s" % vol, "-ar", "48000", "-ac", "1",
                    path], check=True)
    return open(path, "rb").read()


def lufs(raw):
    """ffmpeg's own EBU R128 meter. An outside number — four-tests.md:
    the strongest check is one an independent party agrees with."""
    fh = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    fh.write(raw)
    fh.close()
    p = subprocess.run(["ffmpeg", "-v", "info", "-i", fh.name, "-af",
                        "ebur128=framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True)
    os.unlink(fh.name)
    m = re.findall(r"I:\s*(-?\d+\.\d+) LUFS", p.stderr)
    return float(m[-1]) if m else None


if not HAVE:
    print("  skip  ffmpeg is not on this machine — TEST 1 cannot run")
else:
    print("1 IT MEASURABLY LEVELS THEM")
    loud, quiet = tone("0.9", "loud.wav"), tone("0.03", "quiet.wav")
    bl, bq = lufs(loud), lufs(quiet)
    print("       before: loud %.1f LUFS, quiet %.1f LUFS, spread %.1f dB"
          % (bl, bq, abs(bl - bq)))
    check("1a the two really are far apart to begin with",
          abs(bl - bq) > 20, abs(bl - bq))
    al, aq = lufs(A.normalise_speech(loud)), lufs(A.normalise_speech(quiet))
    print("       after:  loud %.1f LUFS, quiet %.1f LUFS, spread %.1f dB"
          % (al, aq, abs(al - aq)))
    check("1b the loud one comes down to the target",
          abs(al + 16) < 2, al)
    check("1c the quiet one comes up to it", abs(aq + 16) < 2, aq)
    check("1d and they end within 2 dB of EACH OTHER — the whole point",
          abs(al - aq) < 2, abs(al - aq))

    print("\n1b IT DOES NOT DESTROY THE AUDIO")
    out = A.normalise_speech(loud)
    check("1e it is still a WAV", out[:4] == b"RIFF", out[:4])
    check("1f and not empty", len(out) > 1000, len(out))
    check("1g the length is preserved, not truncated",
          abs(len(out) - len(loud)) < len(loud) * 0.6,
          (len(loud), len(out)))
    twice = A.normalise_speech(out)
    check("1h normalising an already-level clip barely moves it",
          abs(lufs(twice) - lufs(out)) < 1.5,
          (lufs(out), lufs(twice)))

print("\n2 THE UGLY CASES — a convenience must never be a dependency")
check("2a empty bytes come back unchanged, not as a crash",
      A.normalise_speech(b"") == b"")
check("2b None comes back as None", A.normalise_speech(None) is None)
junk = b"this is not audio at all" * 40
check("2c rubbish comes back UNCHANGED rather than lost — uneven audio "
      "is a complaint, no audio is a broken feature",
      A.normalise_speech(junk) == junk)
png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 500
check("2d a picture is not turned into silence", A.normalise_speech(png) == png)

print("\n3 BOTH HUME PATHS USE IT")
app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
vr = app[app.index('elif active == "vr":'):app.index('elif active == "looks":')]
print("       searched the vr tab for normalise_speech on each path")
pick = vr[vr.index("def _vr_pick_voice"):vr.index("_cur_voice = ")]
go = vr[vr.index("def _vr_go"):vr.index("with st.container(key=\"nact_vr\")")]
check("3a the PREVIEW is levelled before it reaches the player",
      "normalise_speech(audio)" in pick, pick[-300:])
check("3b so is the REHEARSAL take", "normalise_speech(audio)" in go,
      go[-300:])
check("3c the take is levelled AFTER the segments are joined, not before "
      "— one pass over the finished file, not one per request",
      go.index("join_audio") < go.index("normalise_speech"))
check("3d it reuses the recorder's own loudnorm, not a second set of "
      "numbers to drift from the first",
      "LOUDNORM" in open(os.path.join(os.path.dirname(__file__), "..",
                                      "ttt", "audio.py"),
                         encoding="utf-8").read())

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
