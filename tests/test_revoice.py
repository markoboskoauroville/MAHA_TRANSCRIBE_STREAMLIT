"""CHANGING VOICE RESTARTS THE READING FROM THE TOP.

    python3 tests/test_revoice.py

Baba, 25.8.2026: "If I'm reading in Sonia and I change to Gabi, the app
should restart reading and start from the top of the text with the new
voice. It is not replacing the current sentences until the end. What it
does is completely restart, taking the original pasted text and reading
from the top."

A REVERSAL. _revoice used to KEEP the index on purpose, so a new voice
took over from the block being listened to. That reasoning answers a
different question: it is right for RESUMING and wrong for CHOOSING.
Nobody changes voice to carry on — they change it to hear how the other
one sounds, and the only fair comparison is the same words from the same
start.

TEST 1 drives _revoice's behaviour on a plain dict, so the state
transition can be checked with no Streamlit at all. TEST 2 reads the
reader and says what it searched for.

WHAT THIS CANNOT CATCH: whether the restart is AUDIBLE as a restart —
that the old voice stops and the new one begins at word one. A person
with a phone.
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
body = app[app.index("def _revoice():"):app.index("def _voice_row_synth_only")]


def revoice(state):
    """_revoice's body, on a plain dict. Kept in step with the real one
    by check 2a-2e below, which read the source rather than trusting
    this copy — a stand-in that drifts is worse than none."""
    job = state.get("_talk_job")
    if job:
        job["cache"] = {}
        job["index"] = 0
        state.pop("_talk_player_seen", None)
        state.pop("_talk_start_seen", None)
        state["_talk_revoice"] = True
    return state


print("1 THE STATE TRANSITION")
st = {"_talk_job": {"parts": [("a", 0), ("b", 5), ("c", 9), ("d", 14)],
                    "index": 3, "cache": {0: "x", 1: "y", 2: "z", 3: "w"},
                    "full_text": "the original pasted text"},
      "_talk_player_seen": 111, "_talk_start_seen": 222}
revoice(st)
job = st["_talk_job"]
check("1a it goes back to the TOP, not to where it was", job["index"] == 0,
      job["index"])
check("1b the cache is dropped, so nothing plays in the old voice",
      job["cache"] == {}, job["cache"])
check("1c the finish stamp is cleared, or the restart skips its first "
      "hand-off", "_talk_player_seen" not in st, st.get("_talk_player_seen"))
check("1d the start stamp too", "_talk_start_seen" not in st)
check("1e the synth is flagged for rebuilding — the closure still points "
      "at the OLD voice", st.get("_talk_revoice") is True)

print("\n1b THE TEXT IS NOT TOUCHED")
# "taking the original pasted text and read from the top" — the parts are
# the text. Rebuilding them would be a different bug.
check("1f the parts survive intact",
      job["parts"] == [("a", 0), ("b", 5), ("c", 9), ("d", 14)], job["parts"])
check("1g and so does the full text the highlighter aligns against",
      job["full_text"] == "the original pasted text")

print("\n1c WITH NO READING IN FLIGHT")
empty = {}
revoice(empty)
check("1h choosing a voice with nothing playing does nothing at all",
      empty == {}, empty)
check("1i and does not invent a job", "_talk_job" not in empty)

print("\n1d TWICE IN A ROW")
st2 = {"_talk_job": {"index": 2, "cache": {0: "x"}, "parts": [1, 2, 3]}}
revoice(st2); first = dict(st2["_talk_job"])
revoice(st2)
check("1j changing voice twice is the same as once",
      dict(st2["_talk_job"]) == first, st2["_talk_job"])

print("\n2 THE REAL _revoice DOES THE SAME")
print("       searched _revoice's body, %d chars" % len(body))
check("2a it puts the index back to zero", 'job["index"] = 0' in body, body)
check("2b it drops the cache", 'job["cache"] = {}' in body)
check("2c it clears the finish stamp", '"_talk_player_seen"' in body)
check("2d and the start stamp", '"_talk_start_seen"' in body)
check("2e it asks for the synth to be rebuilt", '"_talk_revoice"' in body)
check("2f it does nothing when there is no job", "if job:" in body)
check("2g it does not rebuild parts — the text is the text",
      '"parts"' not in body, body)

print("\n2b THE REVERSAL IS RECORDED, NOT ERASED")
# MAINTENANCE.md: write down that a rule was reversed, so nobody spends a
# day rediscovering the reasoning that was replaced.
check("2h the old behaviour and why it changed are written down",
      "A REVERSAL" in body and "RESUMING" in body, body[:200])
play = app[app.index("A VOICE WAS CHANGED WHILE PLAYING"):]
play = play[:play.index("idx = job[")]
check("2i and the comment in the playing branch no longer claims the "
      "index is untouched",
      "index is untouched" not in play, play[-200:])

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
