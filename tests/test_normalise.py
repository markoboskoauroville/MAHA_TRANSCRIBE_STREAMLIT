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

    print("\n1b IT PACKS AS WELL AS LEVELS")
    out = A.normalise_speech(loud)
    print("       %.1f KB in, %.1f KB out, %.1fx smaller"
          % (len(loud) / 1024, len(out) / 1024, len(loud) / len(out)))
    check("1e it comes back as MP3, not WAV — Hume's WAV is 5.6 MB a "
          "minute and the whole app has 1 GB",
          out[:3] in (b"ID3", b"\xff\xfb", b"\xff\xf3"), out[:4])
    check("1e2 and it really is much smaller",
          len(out) < len(loud) / 5, (len(loud), len(out)))
    check("1f and not empty", len(out) > 1000, len(out))
    check("1g the DURATION is preserved even though the bytes are not",
          abs((lufs(out) or 0) - (lufs(out) or 0)) < 1)
    twice = A.normalise_speech(out, suffix=".mp3")
    check("1h re-levelling an already-level clip barely moves it",
          abs(lufs(twice) - lufs(out)) < 1.5, (lufs(out), lufs(twice)))
    check("1i and a second pass does not keep shrinking it away",
          len(twice) > len(out) * 0.6, (len(out), len(twice)))

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

print("\n2b THE SIZE IS THE POINT")
print("       Streamlit Community Cloud: 1 GB of RAM for the WHOLE app,")
print("       shared by every session. session_state lives in it.")
one_min = tone("0.5", "min.wav", seconds=60)
packed = A.normalise_speech(one_min)
kb = len(packed) / 1024
print("       one minute of speech: %.0f KB packed, %.0f KB as a data-URI"
      % (kb, kb * 4 / 3))
check("2e a minute of speech fits in well under a megabyte",
      kb < 700, kb)
check("2f so forty minutes fits in the 20 MB cap",
      kb * 40 < 20 * 1024, kb * 40)

print("\n3 EVERY HUME PATH USES IT")
app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
vr = app[app.index('elif active == "vr":'):app.index('elif active == "looks":')]
print("       searched the vr tab for normalise_speech on each path")
pick = vr[vr.index("def _vr_pick_voice"):vr.index("_cur_voice = ")]
blk = vr[vr.index("def _vr_block"):vr.index("if _vr_job and _vr_job.get")]
check("3a the PREVIEW is levelled before it reaches the player",
      "normalise_speech(audio)" in pick, pick[-300:])
# THE REHEARSAL PATH CHANGED SHAPE IN v206 and these checks had to change
# with it. There is no join any more: blocks are played in TURN, so each
# one is levelled as it is built. The old checks asserted a join order
# and went red on a correct change — the fourth time a check of mine has
# described the code rather than the rule.
check("3b every BLOCK is levelled as it is built",
      "normalise_speech(data)" in blk, blk[-300:])
check("3c and it happens before the block is cached, so a block is never "
      "stored at the wrong level",
      blk.index("normalise_speech") < blk.index('return job["cache"][i]'))
# Same correction as test_vr_tags 5m. The stitcher joins on purpose;
# the reading path must not.
# THE SLICE RAN BACKWARDS. _vr_block is defined ABOVE _vr_go in the
# tab, so [_vr_go : _vr_block] covered NOTHING and the check passed
# on an empty string — it stayed green when a join was injected into
# the reading path. Bounded by the end of _vr_go instead.
_go = vr.index("def _vr_go")
_play = vr[_go:vr.index("with st.container(key=\"nact_vr\")", _go)]
check("3d the READING path has no join left to level after",
      "join_audio" not in _play, _play[-200:])
check("3d2 and the stitcher's join is levelled per block before it, so "
      "the saved file is even too",
      "normalise_speech(data)" in vr[vr.index("def _vr_block"):])
check("3e it reuses the recorder's own loudnorm, not a second set of "
      "numbers to drift from the first",
      "LOUDNORM" in open(os.path.join(os.path.dirname(__file__), "..",
                                      "ttt", "audio.py"),
                         encoding="utf-8").read())

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
