"""THE PLAYER AND THE DOWNLOADER SHARE ONE CACHE.

    python3 tests/test_stitch_share.py

Baba, 25.8.2026: "What happens if all audio blocks are not generated and
I press download? I paste, I say read, then I say download, and the
downloader generates what is missing and the player uses the credits of
the downloader to play. They help each other, they are good friends
living in the same app."

They already do, and this file is the proof rather than my word for it.
Every block goes into job["cache"], both sides read it, and neither
renders anything the other has already paid for. That matters in money,
not just in speed: Hume bills per character.

TEST 1 drives stitch_reading's contract with a COUNTING builder, so
"nothing was rendered twice" is a number rather than an opinion.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()


class Deck:
    """A job and its block builder, counting every real render."""

    def __init__(self, n):
        self.parts = list(range(n))
        self.cache = {}
        self.rendered = []          # every i that cost a real request

    def block(self, i):
        if i in self.cache:
            return self.cache[i]    # already paid for: free
        if i >= len(self.parts):
            return None
        self.rendered.append(i)
        self.cache[i] = {"audio": b"RIFF" + bytes([i])}
        return self.cache[i]


def stitch(deck):
    """stitch_reading's contract: build every block, in order."""
    out = []
    for i in range(len(deck.parts)):
        got = deck.block(i)
        if not got or got.get("err"):
            return None
        out.append(got["audio"])
    return b"".join(out)


print("1 DOWNLOAD FIRST, NOTHING PLAYED YET")
d = Deck(5)
whole = stitch(d)
check("1a it builds every block rather than saving a hole",
      len(d.rendered) == 5, d.rendered)
check("1b and the file has all five", whole is not None and len(whole) == 25,
      len(whole or b""))
check("1c and they are now in the cache the PLAYER reads",
      sorted(d.cache) == [0, 1, 2, 3, 4], sorted(d.cache))

print("\n1b AND THE PLAYER PAYS NOTHING FOR THEM")
before = list(d.rendered)
for i in range(5):
    d.block(i)                      # the player walking through the reading
check("1d playing the whole reading after a download costs ZERO new "
      "renders", d.rendered == before, d.rendered)

print("\n2 PLAY FIRST, DOWNLOAD AFTER — the case Baba described")
d2 = Deck(9)
for i in (0, 1, 2):                 # three blocks played
    d2.block(i)
played = list(d2.rendered)
whole2 = stitch(d2)
check("2a the three already heard are NOT rendered again",
      d2.rendered[:3] == played, d2.rendered)
check("2b only the missing six are built",
      d2.rendered[3:] == [3, 4, 5, 6, 7, 8], d2.rendered[3:])
check("2c nine blocks, nine renders, never ten",
      len(d2.rendered) == 9, len(d2.rendered))
check("2d the file is the whole reading", len(whole2) == 45, len(whole2))

print("\n2b AND THE PLAYER CARRIES ON FROM WHERE IT WAS, free")
before2 = list(d2.rendered)
for i in range(3, 9):
    d2.block(i)
check("2e the rest of the reading is already paid for",
      d2.rendered == before2, d2.rendered)

print("\n3 A REFUSING BLOCK STOPS IT")
class Bad(Deck):
    def block(self, i):
        if i == 2:
            return {"err": "no key"}
        return super().block(i)

b = Bad(5)
check("3a a failure returns nothing rather than a file with a gap",
      stitch(b) is None)
check("3b and it stops there rather than paying for the rest",
      b.rendered == [0, 1], b.rendered)

print("\n4 THE APP WIRES IT THAT WAY")
print("       searched app.py for the shared cache and the stale guard")
blk = app[app.index("def _vr_block"):app.index("if _vr_job and _vr_job.get")]
check("4a VR's builder returns the cached block without re-rendering",
      'if i in job.get("cache", {})' in blk)
check("4b and writes into the job the player reads",
      'job["cache"][i] =' in blk)
mk = app[app.index("        def _make(i):"):app.index("        if cached is None:")]
check("4c R's builder does the same",
      'if i in job["cache"]' in mk and 'job["cache"][i] =' in mk)
check("4d the stitcher uses those very builders, not a private path",
      "stitch_reading(len(job.get" in app
      and "stitch_reading(len(parts), _make)" in app)

print("\n4b THE SAVED FILE BELONGS TO THE READING THAT MADE IT")
# Paste a new line, press rehearse, press download: without this you get
# the PREVIOUS reading. A file that plays perfectly and is the wrong
# words is the worst kind of wrong.
go = app[app.index("def _vr_go"):app.index('with st.container(key="nact_vr")')]
check("4e a new VR reading drops the old stitched file",
      'pop("_vr_whole", None)' in go, go[-200:])
rj = app[app.index('st.session_state.pop("_rd_whole", None)'):]
check("4f a new R reading drops it too",
      'pop("_rd_whole", None)' in app)
rev = app[app.index("def _revoice"):app.index("def _voice_row_synth_only")]
check("4g and changing voice drops it, because the file was made in the "
      "OLD voice", 'pop("_rd_whole", None)' in rev, rev[-200:])
check("4h it is dropped in exactly the places a reading is replaced",
      app.count('pop("_rd_whole", None)') == 2,
      app.count('pop("_rd_whole", None)'))

print("\n5 THE CACHE HAS A CEILING")
# Streamlit Community Cloud gives 1 GB for the WHOLE app, shared by every
# session, and session_state lives in it. An audio cache that only grows
# is not a slow leak — it is a reboot for whoever else is mid-sentence.
check("5a there is a cap at all", "VR_CACHE_BYTES" in app)
blk2 = app[app.index("def _vr_block"):app.index("if _vr_job and _vr_job.get")]
check("5b the builder enforces it", "VR_CACHE_BYTES" in blk2)
check("5c it drops the OLDEST ALREADY-HEARD block, never the one being "
      "listened to or the ones ahead",
      "if k < i" in blk2, blk2[-400:])
check("5d and it stops rather than looping when there is nothing old "
      "left to drop", "if not _old:" in blk2)
check("5e the cap is a real number, not a guess left as TODO",
      "20 * 1024 * 1024" in app)

# The eviction rule, driven rather than read.
def evict(cache, i, cap):
    while sum(len(v) for v in cache.values()) > cap:
        old = [k for k in sorted(cache) if k < i]
        if not old:
            break
        cache.pop(old[0], None)
    return cache

c = {0: b"x" * 10, 1: b"x" * 10, 2: b"x" * 10, 3: b"x" * 10}
evict(c, 3, 25)
check("5f it evicts down to the cap", sum(len(v) for v in c.values()) <= 25, c)
check("5g the block being played survives", 3 in c, sorted(c))
c2 = {5: b"x" * 100}
evict(c2, 5, 10)
check("5h it never evicts the block being played, even over the cap",
      c2 == {5: b"x" * 100}, c2)
c3 = {0: b"x" * 10, 5: b"x" * 10, 6: b"x" * 10}
evict(c3, 5, 25)
check("5i blocks AHEAD are kept — they are the prefetch",
      6 in c3 and 5 in c3, sorted(c3))

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
