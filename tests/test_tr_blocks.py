"""THE TR CRASH — the check that was missing on 25.8.2026.

Three versions shipped through nine gates and the Translate tab came up
as a red Python wall the first time a person pressed read on it. The
suite caught none of it, because nothing in the suite ever asked what
shape `plan_blocks` returns or what TR did with it.

    python3 tests/test_tr_blocks.py

TEST 1 territory: no Streamlit, no network, no key. If this file needs
the app to be running, it is the wrong file.

WHAT THIS CANNOT CATCH: that the TR deck's play button reaches
tr_make_audio at all, and that the joined MP3 actually sounds like
speech. Both live in a browser. Check 4 below is the nearest thing —
it reads app.py as text and asserts the wiring — and it is honest about
being a grep, not a press.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ttt import speech as SPEECH  # noqa: E402

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

print("TR BLOCKS — the shape a caller may rely on\n")

# --- 1. THE SHAPE plan_blocks ACTUALLY HAS ---------------------------
# The fault was a caller believing this returned strings. Assert what it
# returns, so anyone who reads only the tests learns the true contract.
print("1 WHAT plan_blocks RETURNS")
blocks = SPEECH.plan_blocks(["One.", "Two.", "Three."])
check("1a every block is a (sentences, char_offset) pair",
      all(isinstance(b, tuple) and len(b) == 2 for b in blocks), blocks)
check("1b the first half is a LIST of str, never a str",
      all(isinstance(b[0], list) and all(isinstance(s, str) for s in b[0])
          for b in blocks), blocks)
check("1c the second half is an int offset",
      all(isinstance(b[1], int) for b in blocks), blocks)
# The exact line that crashed, kept as a test so it can never come back
# quietly: joining a block whole must still be an error.
try:
    " ".join(blocks[0])
    joined = True
except TypeError:
    joined = False
check("1d joining a block WHOLE is still a TypeError — the 03:20 crash",
      not joined, "a block became joinable; the contract moved")

# --- 2. block_texts, THE THING TR ASKS FOR ---------------------------
print("\n2 block_texts GIVES TEXT AND ONLY TEXT")
texts = SPEECH.block_texts(["One.", "Two.", "Three.", "Four."])
check("2a every item is a str", all(isinstance(x, str) for x in texts), texts)
check("2b nothing is lost — every sentence survives the grouping",
      all(isinstance(x, str) for x in texts)
      and " ".join(texts) == "One. Two. Three. Four.", texts)
check("2c the doubling shape is kept: 1 then 2 then the rest",
      all(isinstance(x, str) for x in texts)
      and [len(x.split()) for x in texts][:2] == [1, 2], texts)

# --- 3. THE UGLY CASES ------------------------------------------------
# Empty, one, and a sentence far past the character budget — the last
# one is plan_blocks' "one sentence longer than the budget" branch,
# which returns a block nobody else exercises.
print("\n3 EMPTY, ONE, AND ENORMOUS")
check("3a no sentences is no blocks, not a crash",
      SPEECH.block_texts([]) == [], SPEECH.block_texts([]))
check("3b one sentence is one block", SPEECH.block_texts(["Only."]) == ["Only."],
      SPEECH.block_texts(["Only."]))
huge = "x" * 4000 + "."
big = SPEECH.block_texts([huge, "After."])
check("3c a sentence past the budget is never split mid-sentence",
      big[0] == huge, len(big[0]))
check("3d and every item is STILL a str", all(isinstance(x, str) for x in big))
# Croatian, because the app is written in two languages and a
# non-ASCII sentence has broken a join before.
hr = SPEECH.block_texts(["Ovo je test.", "Čujem li se dobro?", "Da."])
check("3e Croatian survives the join",
      all(isinstance(x, str) for x in hr)
      and " ".join(hr) == "Ovo je test. Čujem li se dobro? Da.", hr)

# --- 4. IS IT WIRED IN? -----------------------------------------------
# The grep half. G5's lesson, from the gate: a pattern check must SAY
# what it searched for, because a check that finds nothing and a check
# that runs nothing look identical from outside.
print("\n4 TR ACTUALLY CALLS IT")
src = open(APP, encoding="utf-8").read()
fn = re.search(r"def tr_make_audio\(.*?\n(?=\S)", src, re.S)
body = fn.group(0) if fn else ""
print("       searched tr_make_audio's body, %d chars, for "
      "'SPEECH.block_texts' and for 'isinstance(block'" % len(body))
check("4a tr_make_audio was found in app.py", bool(body))
check("4b it asks SPEECH.block_texts for its pieces",
      "SPEECH.block_texts" in body, body[:200])
check("4c and it no longer GUESSES the shape with isinstance",
      "isinstance(block" not in body,
      "the isinstance guess is back in tr_make_audio")
check("4d R still unpacks plan_blocks itself, for the char offset",
      "ss, char_off = parts[i]" in src,
      "R's reader stopped unpacking; word timings would silently move")

print("\n{} passed, {} failed".format(passed, failed))


def test_tr_blocks():
    assert failed == 0, "%d of %d failed" % (failed, passed + failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
