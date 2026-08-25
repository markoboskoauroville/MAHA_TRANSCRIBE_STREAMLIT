"""FOUR BY FOUR — the reading algorithm.

    python3 tests/test_four_by_four.py

Baba, 25.8.2026: "You generate audio up to 4 sentences and play that,
and while this is playing you generate the next block. We are not
waiting any more long time, we are going 4 by 4."

TEST 1 is the block planner alone — no Streamlit, no voice, no network.
TEST 2 greps the reader to prove it is the planner actually being used,
and says what it searched for.

WHAT THIS CANNOT CATCH: whether a hand-off is AUDIBLE. That is a person
listening to a long text on a phone, and nothing here replaces it.
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import speech as S  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

def sizes(blocks): return [len(b) for b, _ in blocks]

print("1 FOUR SENTENCES A BLOCK, HOWEVER LONG THE TEXT")
for n, want in ((1, [1]), (4, [4]), (5, [4, 1]), (8, [4, 4]),
                (14, [4, 4, 4, 2]), (40, [4] * 10)):
    ss = ["S%d." % i for i in range(n)]
    check("1a %d sentences -> %s" % (n, want), sizes(S.plan_even(ss)) == want,
          sizes(S.plan_even(ss)))
# WHAT THE READER ACTUALLY ASKS FOR, which is 1,4,4 since Baba chose it.
_plan = S.plan_even(["S."] * 25, first=1)
print("       the reader's own plan for 25 sentences: %s"
      % [len(b) for b, _ in _plan])
check("1a2 the reader's first block is ONE sentence", len(_plan[0][0]) == 1)
check("1a3 and the rest are fours",
      set(len(b) for b, _ in _plan[1:-1]) == {4},
      [len(b) for b, _ in _plan])

check("1b it never grows, however long — the doubling shape is gone",
      set(sizes(S.plan_even(["x."] * 200))[:-1]) == {4},
      set(sizes(S.plan_even(["x."] * 200))))

print("\n1b NOTHING IS LOST AND NOTHING IS SPLIT")
ss = ["One.", "Two.", "Three.", "Four.", "Five.", "Six.", "Seven."]
flat = [x for b, _ in S.plan_even(ss) for x in b]
check("1c every sentence appears exactly once, in order", flat == ss, flat)
check("1d a sentence is never cut in half",
      all(x in ss for x in flat))

print("\n1c THE OFFSETS THE HIGHLIGHTER NEEDS")
# The offset counts characters from the start of the joined text. Get it
# wrong and the word highlight drifts, which is the fault word-timing.md
# exists for.
blocks = S.plan_even(ss)
joined = " ".join(ss)
ok = True
for sents, off in blocks:
    if joined[off:off + len(sents[0])] != sents[0]:
        ok = False
check("1e every block's offset lands on its own first sentence", ok,
      [(o, joined[o:o + 6]) for _, o in blocks])
check("1f the first offset is zero", blocks[0][1] == 0)

print("\n1d THE UGLY CASES")
check("1g no sentences is no blocks, not a crash", S.plan_even([]) == [])
check("1h one sentence is one block", sizes(S.plan_even(["Only."])) == [1])
huge = "x" * 4000 + "."
big = S.plan_even([huge, "After.", "More.", "Yet.", "Again."])
check("1i a sentence past the whole budget is still taken, alone",
      big[0][0] == [huge], len(big[0][0]))
check("1j and the ones after it still group by four",
      sizes(big)[1:] == [4], sizes(big))
mid = S.plan_even(["a." * 300, "b." * 300, "c." * 300, "d." * 300, "e."])
check("1k the character budget stops a block early rather than sending "
      "a request that comes back 413",
      all(sum(len(x) + 1 for x in b) <= 1500 or len(b) == 1
          for b, _ in mid), sizes(mid))
check("1l Croatian and its diacritics survive",
      [x for b, _ in S.plan_even(["Čuo sam.", "Đavo.", "Šuma."]) for x in b]
      == ["Čuo sam.", "Đavo.", "Šuma."])

print("\n1e THE FAST START IS ONE NUMBER, NOT A SECOND ALGORITHM")
check("1m first=1 gives 1 then fours", sizes(S.plan_even(["x."] * 10, first=1))
      == [1, 4, 4, 1], sizes(S.plan_even(["x."] * 10, first=1)))
check("1n first=0 means the same as the rest",
      sizes(S.plan_even(["x."] * 10, first=0)) == [4, 4, 2])
check("1o per_block is honoured too",
      sizes(S.plan_even(["x."] * 9, per_block=3)) == [3, 3, 3])
check("1p a nonsense per_block cannot make an empty block",
      sizes(S.plan_even(["x."] * 3, per_block=0)) == [1, 1, 1])

print("\n2 THE READER ACTUALLY USES IT")
app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
print("       searched app.py for plan_even, plan_blocks and PREFETCH_AHEAD")
# NOT PINNED TO THE EXACT CALL. The first version asserted
# "SPEECH.plan_even(sentences)" character for character and went red the
# moment `first=1` was added — a test failing for a reason unconnected to
# the feature, which four-tests.md names under "test the test". It asks
# whether the reader plans with plan_even, not how it spells the call.
check("2a the reader plans with plan_even",
      re.search(r"SPEECH\.plan_even\(sentences[,)]", app) is not None)
check("2b and no longer with the doubling planner",
      "SPEECH.plan_blocks(sentences)" not in app)
m = re.search(r"^PREFETCH_AHEAD = (\d+)", app, re.M)
check("2c it builds ahead while playing", m is not None)
check("2d two ahead — one is heard as silence when a request is slow",
      m and int(m.group(1)) >= 2, m.group(1) if m else None)
check("2e the prefetch runs AFTER the player is on the page, so building "
      "costs the listener nothing",
      app.index("wanted = [i for i in range(idx + 1")
      > app.index('key="talk_player"'))
check("2f block 0 is played, not waited past — the player renders "
      "before the prefetch",
      app.index('key="talk_player"') < app.index("PREFETCH_AHEAD, len(parts)"))

print("\n2b PLAN_BLOCKS IS KEPT, NOT DELETED")
# MAINTENANCE.md: record a reversal rather than erase it. TR still uses
# block_texts, which is built on plan_blocks, and the doubling shape is
# the thing four-by-four was chosen over — a reader needs to see both.
sp = open(os.path.join(os.path.dirname(__file__), "..", "ttt", "speech.py"),
          encoding="utf-8").read()
check("2g plan_blocks still exists for TR and for the record",
      "def plan_blocks(" in sp)
check("2h and the trade is written down where the code is",
      "plan_blocks` DOUBLED" in sp or "DOUBLED" in sp)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
