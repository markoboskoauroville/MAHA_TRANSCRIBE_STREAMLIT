"""THE ETA AND THE BRAILLE LINE — Test 1, the mechanism alone.

What could be true and these still pass: the sheet never receives a row
(needs the MAIN deploy and a phone); the spinner never appears on screen
(needs a browser). What THIS closes: the arithmetic being wrong, one bad
sample poisoning every later estimate, the estimate appearing before
there is enough history to justify it, and the line changing width as it
animates.

    python3 tests/test_eta.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ttt import eta as ETA          # noqa: E402

passed = failed = 0


def ck(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def S(audio, wall, engine="groq"):
    return {"engine": engine, "audio_s": audio, "wall_s": wall}


print("THE ETA\n")

# --- the case it is FOR ----------------------------------------------
# Three takes, each transcribed in a fifth of their own length.
easy = [S(60, 12), S(120, 24), S(30, 6)]
ck("1 the ratio is learned from the samples",
   ETA.ratio_for(easy, "groq") == 0.2, ETA.ratio_for(easy, "groq"))
ck("2 and a new take is estimated from it — 300s audio -> 60s",
   ETA.estimate(easy, 300, "groq") == 60.0, ETA.estimate(easy, 300, "groq"))

# --- SILENCE UNTIL IT KNOWS ------------------------------------------
ck("3 NO ESTIMATE FROM NOTHING", ETA.estimate([], 300, "groq") is None)
ck("4 NO ESTIMATE FROM ONE SAMPLE — one take is luck, not a rate",
   ETA.estimate([S(60, 12)], 300, "groq") is None)
ck("5 nor from two", ETA.estimate([S(60, 12), S(30, 6)], 300, "groq") is None)
ck("6 three is enough, which is what 'after a few' means",
   ETA.estimate(easy, 300, "groq") is not None)

# --- THE POINT OF THE MEDIAN -----------------------------------------
# One take hit a rate limit and crawled. The estimate must not limp.
limped = easy + [S(60, 600)]        # ratio 10 — real, and not typical
ck("7 ONE SLOW TAKE DOES NOT MOVE THE ESTIMATE — this is the whole "
   "reason it is a median and not a mean",
   ETA.estimate(limped, 300, "groq") == 60.0,
   ETA.estimate(limped, 300, "groq"))
mean = sum(s["wall_s"] / s["audio_s"] for s in limped) / len(limped)
ck("8 and a mean WOULD have moved it, which is why this matters",
   abs(mean * 300 - 60.0) > 30, mean * 300)

# --- THE UGLY CASES ---------------------------------------------------
ck("9 zero-length audio is not a sample (its ratio is infinity, and one "
   "would poison every later estimate)", not ETA.usable(S(0, 10)))
ck("10 negative is not a sample", not ETA.usable(S(-5, 10)))
ck("11 zero wall time is not a sample", not ETA.usable(S(60, 0)))
ck("12 a None is not a sample", not ETA.usable({"audio_s": None,
                                                "wall_s": None}))
ck("13 a string that is not a number is refused, not raised on",
   not ETA.usable({"audio_s": "abc", "wall_s": "x"}))
ck("14 a stall (60s audio, 40 min wall) is refused as a measurement "
   "of SPEED", not ETA.usable(S(60, 2400)))
ck("15 and refusing it keeps the estimate honest",
   ETA.estimate(easy + [S(60, 2400)], 300, "groq") == 60.0)
ck("16 estimating for zero-length audio returns None, not zero",
   ETA.estimate(easy, 0, "groq") is None)
ck("17 garbage in the audio length is refused",
   ETA.estimate(easy, "soon", "groq") is None)
ck("18 an empty median is None, not a crash", ETA.median([]) is None)

# --- PER ENGINE -------------------------------------------------------
mixed = [S(60, 12, "groq"), S(60, 12, "groq"), S(60, 12, "groq"),
         S(60, 120, "assemblyai"), S(60, 120, "assemblyai"),
         S(60, 120, "assemblyai")]
ck("19 groq is estimated from groq's samples",
   ETA.estimate(mixed, 100, "groq") == 20.0, ETA.estimate(mixed, 100, "groq"))
ck("20 ASSEMBLYAI IS ESTIMATED FROM ITS OWN — mixing them gives a "
   "number that is wrong for both",
   ETA.estimate(mixed, 100, "assemblyai") == 200.0,
   ETA.estimate(mixed, 100, "assemblyai"))
ck("21 an engine with too little history of its own stays silent even "
   "when other engines have plenty",
   ETA.estimate(mixed + [S(60, 6, "whisper-local")], 100,
                "whisper-local") is None)

# --- HOW IT READS -----------------------------------------------------
ck("22 seconds read as seconds", ETA.human(20).endswith("s"))
ck("23 minutes read as minutes", "m" in ETA.human(150))
ck("24 a tiny wait does not claim precision it lacks",
   ETA.human(2) == "a few seconds", ETA.human(2))
ck("25 None renders as nothing at all, never as '0s'", ETA.human(None) == "")
ck("26 no estimate is ever stated to the second — a method this rough "
   "must not print 143s",
   not re.search(r"\b\d*[1-46-9]s\b", ETA.human(143) + ETA.human(37)),
   ETA.human(143) + " / " + ETA.human(37))

# --- THE LINE ITSELF --------------------------------------------------
SRC = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
m = re.search(r'BRAILLE = "([^"]+)"', SRC)
ck("27 the Braille frames exist in app.py", m is not None)
if m:
    frames = m.group(1)
    ck("28 ten frames", len(frames) == 10, len(frames))
    ck("29 EVERY FRAME IS ONE CHARACTER, so the line cannot change "
       "width as it spins and drag the page under it",
       all(len(f) == 1 for f in frames))
    ck("30 and they are all Braille (U+28xx), not a mix",
       all(0x2800 <= ord(f) <= 0x28FF for f in frames))
ck("31 the line names the engine in parentheses, as asked",
   '"%s %s (%s)"' in SRC)
ck("32 the estimate is written AFTER the transcript is delivered, "
   "never before — storage must never stand in front of the words",
   SRC.index("remember_timing(_eng") > SRC.index('stage["transcribe_s"]'))

print("\n%d ok, %d failed" % (passed, failed))


def test_eta():
    """The verdict, in the one form pytest can report. The checks run
    above, at import, because this file is a script first."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT — at module level it
# fires during pytest's collection and aborts the whole run with
# INTERNALERROR before one test is reported. The repo learned this at
# test_login.py; this file did not, until it did the same thing.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
