"""AN INTERRUPTED NOTE TAKE IS SKIPPED, NEVER DESTROYED.

    python3 tests/test_note_take.py

Fault 8 of Baba's brief, 03:20 on 25.8.2026, and the last of that brief
to be closed:

  "transcribe_note_take() POPS `_note_take` before doing the work, so an
   interrupted note take is GONE rather than skipped — the same fault
   v185 fixed for the deck, with a worse outcome."

WORSE BECAUSE THE DECK'S TAKE IS STILL IN THE RECORDER. A note's take
exists only in `_note_take`. Popping it and then being interrupted — a
rerun, a phone call, Android suspending the tab — destroyed the only copy
of something he had just said. Silently, because losing something nobody
promised to keep raises no error.

TEST 1 drives the state machine on a plain dict, so an interruption is
just "stop running", which is exactly what it is.
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
fn = app[app.index("def transcribe_note_take"):app.index("def keep_as_note")]
code = "\n".join(l for l in fn.splitlines() if not l.lstrip().startswith("#"))


def finished(st):
    st["_note_done"] = True
    st.pop("_note_take", None)


def run(st, outcome, digest="d1"):
    """One render. `outcome` is what happens to the transcription."""
    take = st.get("_note_take")
    if not take:
        return "nothing to do"
    if st.get("_note_digest") == digest and st.get("_note_done"):
        return "already done"
    st["_note_digest"] = digest
    st["_note_done"] = False
    if outcome == "interrupted":
        return "interrupted"          # the script stops here. No finish.
    if outcome == "refused":
        finished(st)
        return "refused"
    if outcome == "silence":
        finished(st)
        return "nothing heard"
    st.setdefault("note_body", []).append(take["words"])
    finished(st)
    return "written"


print("1 INTERRUPTED — the take must SURVIVE")
st = {"_note_take": {"words": "the thing I just said", "b64": "x"}}
r = run(st, "interrupted")
check("1a the run stops", r == "interrupted")
check("1b THE TAKE IS STILL THERE — this is the whole fault",
      st.get("_note_take") is not None, st.get("_note_take"))
check("1c and it is not marked done, so the next render tries again",
      st.get("_note_done") is False, st.get("_note_done"))
r2 = run(st, "ok")
check("1d the next render transcribes it", r2 == "written", r2)
check("1e the words reach the note", st["note_body"] == ["the thing I just said"])
check("1f and NOW the take is let go", st.get("_note_take") is None)

print("\n1b INTERRUPTED TWICE, THEN ALLOWED TO FINISH")
st2 = {"_note_take": {"words": "twice", "b64": "x"}}
run(st2, "interrupted")
run(st2, "interrupted")
check("1g still there after two interruptions",
      st2.get("_note_take") is not None)
run(st2, "ok")
check("1h and still arrives", st2.get("note_body") == ["twice"])

print("\n2 FINISHED — the take must NOT be done twice")
st3 = {"_note_take": {"words": "once", "b64": "x"}}
run(st3, "ok")
before = list(st3["note_body"])
for _ in range(5):
    run(st3, "ok")
check("2a five more renders add nothing", st3["note_body"] == before,
      st3["note_body"])
check("2b because the take is gone", st3.get("_note_take") is None)

print("\n2b A CONCLUSION IS NOT AN INTERRUPTION")
for outcome, why in (("refused", "the engine refused"),
                     ("silence", "nothing was heard")):
    st4 = {"_note_take": {"words": "w", "b64": "x"}}
    run(st4, outcome)
    check("2c %-20s lets the take go — the same bytes would fail again"
          % why, st4.get("_note_take") is None, st4.get("_note_take"))
    check("2d %-20s and does not retry on every render" % why,
          run(st4, outcome) == "nothing to do")

print("\n3 THE APP DOES THE SAME")
print("       searched transcribe_note_take, %d chars of code" % len(code))
check("3a it no longer POPS before the work",
      'pop("_note_take"' not in code, "pop is back in the function body")
check("3b it reads the take instead",
      'st.session_state.get("_note_take")' in code)
check("3c a digest says whether THIS take was already done",
      '"_note_digest"' in code and '"_note_done"' in code)
check("3d the digest covers the NOTE as well as the audio — the same "
      "words into two notes are two jobs",
      "note_id, take.get(" in code)
check("3e there is one place that concludes a take",
      "def _note_take_finished" in app)
check("3f and it is the only thing that pops",
      app[app.index("def _note_take_finished"):
          app.index("def transcribe_note_take")].count('pop("_note_take"') == 1)
_calls = code.count("_note_take_finished()")
print("       conclusions: %d" % _calls)
check("3g every conclusive path calls it — words written, engine "
      "refused, nothing heard, undecodable, note gone",
      _calls >= 5, _calls)
check("3h the words are written BEFORE the take is let go",
      code.index("NOTES.append") < code.rindex("_note_take_finished()"))
# THE CLAIM, STATED PROPERLY. My first 3i asserted something about the
# word "raise" that had nothing to do with the rule it was named for — a
# check whose text and whose test were about different things, which is
# worse than no check because it reads as cover.
#
# The real claim: the guard is set to False BEFORE any work begins, so a
# script that stops mid-work leaves it False and the take intact.
# find(), NOT index(). Third time today: index() RAISES when the thing is
# gone, so the mutation that removes it CRASHES the file instead of
# turning the check red — and in a sweep a crash and a pass look equally
# unlike a failure. -1 is an answer; an exception is not.
_i_false = code.find('"_note_done"] = False')
check("3i the take is marked NOT done before any work begins, so an "
      "interruption leaves it that way",
      _i_false > 0 and _i_false < code.index("base64.b64decode"), _i_false)
# 3i2 REMOVED RATHER THAN TUNED. It counted occurrences of a substring
# against a sum of other counts — arithmetic dressed as a claim, which
# could be made green by adjusting the number until it fit and would then
# mean nothing at all. 3f already says the only thing that matters: the
# helper is the only place that pops.

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
