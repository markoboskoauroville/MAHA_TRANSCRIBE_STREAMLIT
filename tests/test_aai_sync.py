"""WHICH RECORDINGS MAY TAKE ASSEMBLYAI'S FAST PATH.

Ported from TTT mini's MaProviders on Baba's instruction — "TTT mini as
a role model for how to deal with sync and async with AssemblyAI" — and
these checks carry its reasoning across, not just its numbers.

THE FAILURE THIS PREVENTS. AssemblyAI's sync endpoint does not accept
`hr` at all. Croatian sent up that path comes back as fluent Croatian
that is the WRONG WORDS: not garbled, not empty, not obviously broken,
just plausible sentences nobody would question without knowing what was
said. A wrong answer that looks right is worse than an error, because
there is nothing to notice.

    python3 tests/test_aai_sync.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ttt.providers import assemblyai as AA        # noqa: E402
from ttt.providers.assemblyai import AssemblyAI   # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


A = AssemblyAI()


def a_file(size=2048):
    p = os.path.join(tempfile.mkdtemp(), "clip.wav")
    with open(p, "wb") as f:
        f.write(b"\0" * size)
    return p


small = a_file()

print("THE ASSEMBLYAI SYNC PATH\n")

# --- language decides first -------------------------------------------
check("1 English may take the fast path", A.use_sync("en", small, 60))

check("2 CROATIAN NEVER DOES. AssemblyAI's sync endpoint does not accept "
      "`hr`, so what comes back is fluent Croatian that is the wrong "
      "words — the one failure with nothing in the result to notice",
      A.use_sync("hr", small, 60) is False)

check("3 AND AUTO COLLAPSES TO NO. A language the app has not been told "
      "is English is one that might be Croatian, and the safe answer to "
      "'might be' is the slow path",
      A.use_sync("", small, 60) is False)
check("3b as does anything else unread — an allow-list, not a deny-list, "
      "so a language nobody has checked is excluded by default rather "
      "than included by accident",
      A.use_sync("de", small, 60) is False and A.use_sync("sr", small, 60) is False)

# --- then length, with a margin ---------------------------------------
check("4 two minutes is the ceiling", A.use_sync("en", small, 119) is False)
check("5 AND IT STOPS TWO SECONDS SHORT of it. The service rejects at "
      "120s and this figure is CALCULATED from the file while theirs is "
      "measured, so the last two seconds are room for the two to "
      "disagree",
      A.use_sync("en", small, 118) and A.use_sync("en", small, 118.5) is False)

check("6 and something too short to be speech is not sent either — the "
      "endpoint rejects under 80ms",
      A.use_sync("en", small, 0.2) is False)

check("7 NOT KNOWING HOW LONG IT IS COUNTS AS TOO LONG. A header that "
      "will not parse is not a thing to gamble a dictation on",
      A.use_sync("en", small, None) is False)

# --- and size ----------------------------------------------------------
big = a_file(A.SYNC_MAX_BYTES + 1)
check("8 a file past the size limit takes the slow path",
      A.use_sync("en", big, 60) is False)
check("9 a file that is not there is refused rather than crashing",
      A.use_sync("en", "/nowhere/at/all.wav", 60) is False)

# --- the shape of the rule --------------------------------------------
check("10 the safe list is an ALLOW-list holding only what has been read",
      A.SYNC_SAFE_LANGUAGES == frozenset({"en"}), A.SYNC_SAFE_LANGUAGES)

# --- two models, and the arithmetic Baba gave ------------------------
#
# His figures: Universal-3.5 Pro pre-recorded at $0.21/hr is about 238
# hours of the $50 a new account starts with; Universal-Streaming at
# $0.15/hr is about 333. Both check out, which is why the rates are
# written down as fact rather than left as an editable box — that box
# was me hedging because I had found three different prices on the web.
ids = [m.id for m in AssemblyAI().models()[0]]
check("11 TWO MODELS AND NO OTHERS. A picker offering a model nobody has "
      "priced can produce a bill nobody expected, and the hours-left "
      "figure depends on every path having a known rate",
      ids == [AA.ASYNC_MODEL, AA.SYNC_MODEL_ID], ids)

check("12 $50 on the pre-recorded model is about 238 hours",
      237 < AA.hours_for(50) < 239, AA.hours_for(50))
check("13 and about 333 on streaming",
      332 < AA.hours_for(50, AA.SYNC_MODEL_ID) < 335,
      AA.hours_for(50, AA.SYNC_MODEL_ID))
check("14 an hour of audio costs its rate",
      abs(AA.cost_of(3600) - 0.21) < 0.001, AA.cost_of(3600))
check("15 a nonsense figure does not become a nonsense bill",
      AA.cost_of(-5) == 0.0 and AA.hours_for("nope") == 0.0)
check("16 an unknown model falls back to the DEARER rate, so a mistake "
      "over-estimates the cost rather than under-estimating it",
      abs(AA.cost_of(3600, "made-up") - 0.21) < 0.001)

print("\n{} passed, {} failed".format(passed, failed))

if __name__ == "__main__":
    sys.exit(1 if failed else 0)


def test_aai_sync():
    assert failed == 0, "%d of %d checks failed" % (failed, passed + failed)
