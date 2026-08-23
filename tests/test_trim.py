"""THE SECONDS YOU DO NOT SEND ARE FREE.

From Baba's cost document, which ranks this first of everything: async
speech-to-text is billed per second of AUDIO, dictation is roughly half
silence, and trimming the gaps costs nothing in quality because what is
deleted carried no words.

TWO THRESHOLDS, DELIBERATELY DIFFERENT, and that is the whole subtlety
here. Trimming asks "is this gap worth cutting" and being wrong leaves a
few seconds of silence in. The silence CHECK asks "is this worth
uploading at all" and being wrong costs somebody their words. So the
second question is asked far lower down.

    python3 tests/test_trim.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ttt import audio as A                        # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


HAVE_FFMPEG = bool(shutil.which("ffmpeg"))
D = tempfile.mkdtemp(prefix="trim_")


def tone(name, filt, secs):
    """Build a test clip with ffmpeg. Returns its path."""
    p = os.path.join(D, name)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=16000:cl=mono", "-filter_complex", filt,
                    "-map", "[out]", "-ar", "16000", "-ac", "1",
                    "-t", str(secs), p], capture_output=True)
    return p


print("TRIMMING THE SILENCE\n")

if not HAVE_FFMPEG:
    print("  ffmpeg is not here — nothing to measure. SKIP")
    print("\n0 passed, 0 failed")
    sys.exit(0)

# --- the saving, on something shaped like a real dictation -------------
#
# 3s speech, 5s thinking, 3s speech, 6s thinking, 2s speech: 8 seconds of
# words inside 19 seconds of recording. That ratio is the point — it is
# what dictation actually looks like.
dictation = tone(
    "dictation.flac",
    "sine=frequency=200:duration=3[a];"
    "anullsrc=r=16000:cl=mono,atrim=0:5[b];"
    "sine=frequency=250:duration=3[c];"
    "anullsrc=r=16000:cl=mono,atrim=0:6[d];"
    "sine=frequency=180:duration=2[e];"
    "[a][b][c][d][e]concat=n=5:v=0:a=1[out]", 19)

out, before, after = A.trim_silence(dictation)
check("1 a dictation with thinking pauses is measurably shorter",
      after < before, "%.1f -> %.1f" % (before, after))
check("2 AND THE SAVING IS REAL — a third at the very least, on audio "
      "that is half silence. This is billed per second, so this is money",
      after < before * 0.7, "%.0f%% saved" % (100 * (before - after) / before))
check("3 but the words are still there: it did not cut everything",
      after > 6.0, after)

# --- what must NOT happen ---------------------------------------------
continuous = tone("cont.flac", "sine=frequency=220:duration=10[out]", 10)
same, b2, a2 = A.trim_silence(continuous)
check("4 CONTINUOUS SPEECH IS LEFT ALONE, and no second file is made — "
      "under a tenth saved, a copy costs more in disk and confusion than "
      "it returns",
      same == continuous, "%.1f -> %.1f" % (b2, a2))

# --- the silence check, and its own lower threshold --------------------
silent = tone("silent.flac", "anullsrc=r=16000:cl=mono,atrim=0:8[out]", 8)
check("5 A SILENT TAKE IS CAUGHT BEFORE THE UPLOAD. Never pay for a clip "
      "that turned out to be nothing",
      A.is_silent(silent) is True)

for vol, label, db in (("0.3", "a normal voice", -31),
                       ("0.05", "a quiet voice", -47),
                       ("0.02", "a very quiet voice", -55)):
    clip = tone("v%s.flac" % vol.replace(".", "_"),
                "sine=frequency=200:duration=5,volume=%s[out]" % vol, 5)
    check("6 %s (about %ddB) is NOT thrown away" % (label, db),
          A.is_silent(clip) is False)

check("7 THE TWO THRESHOLDS ARE DIFFERENT ON PURPOSE. Trimming at -42dB "
      "risks leaving silence in; refusing to upload at -42dB would risk "
      "somebody's words, so that question is asked at -60dB",
      A.TRIM_THRESHOLD != A.SILENCE_THRESHOLD,
      (A.TRIM_THRESHOLD, A.SILENCE_THRESHOLD))

# --- and it never loses a recording ------------------------------------
check("8 a file that is not there is refused rather than crashing",
      A.is_silent("/nowhere/at/all.flac") is False)
gone, b3, a3 = A.trim_silence("/nowhere/at/all.flac")
check("9 and trimming one hands the original straight back — a saving is "
      "worth having and is never worth a lost dictation",
      gone == "/nowhere/at/all.flac")

print("\n{} passed, {} failed".format(passed, failed))

if __name__ == "__main__":
    sys.exit(1 if failed else 0)


def test_trim():
    assert failed == 0, "%d of %d checks failed" % (failed, passed + failed)
