"""RETRIES THAT DO NOT ARRIVE TOGETHER.

    python3 tests/test_retry_jitter.py

Found at the delivery gate, 25.8.2026, G5: "every retry is bounded, backs
off exponentially, and adds jitter. Without jitter, retries synchronise
and arrive together."

The schedule (5, 30, 125) was bounded and did back off. It had NO JITTER,
and nothing tested this path at all — the retry loop had no suite of its
own, so the gap had nothing watching it.

WHY IT MATTERS HERE SPECIFICALLY. A long recording is split into chunks
and several are in flight at once. When the provider refuses them — the
whole reason the schedule exists — every chunk starts the same countdown
at the same instant and they all come back at 5s, then all at 30s, then
all at 125s. The retry meant to let the provider recover delivers the
same burst that caused the refusal, three more times.
"""
import os, statistics, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import audio as A  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

print("1 THE JITTER ITSELF")
for base in (5, 30, 125):
    vals = [A.jittered(base) for _ in range(3000)]
    lo, hi, mean = min(vals), max(vals), statistics.mean(vals)
    print("       %3ds -> min %.1f  max %.1f  mean %.1f" % (base, lo, hi, mean))
    check("1a %ds spreads either side of itself" % base, lo < base < hi,
          (lo, base, hi))
    check("1b %ds keeps its MEANING — mean stays on the schedule" % base,
          abs(mean - base) < base * 0.05, mean)
    check("1c %ds stays inside +/-20%%, so 5s is still a blip and 125s "
          "still outlasts a full rest" % base,
          lo >= base * 0.79 and hi <= base * 1.21, (lo, hi))

print("\n1b THE UGLY CASES")
check("1d it never returns less than a second — a retry after 0.2s is a "
      "second burst, not a retry", A.jittered(0.5) >= 1.0, A.jittered(0.5))
check("1e zero does not become zero", A.jittered(0) >= 1.0)
check("1f rand is injectable, so this is checkable at all",
      A.jittered(100, rand=lambda: 0.5) == 100.0,
      A.jittered(100, rand=lambda: 0.5))
check("1g the low end of rand gives the low end of the window",
      abs(A.jittered(100, rand=lambda: 0.0) - 80.0) < 0.01)
check("1h and the high end the high end",
      abs(A.jittered(100, rand=lambda: 1.0) - 120.0) < 0.01)

print("\n2 CHUNKS NO LONGER ARRIVE TOGETHER")
# The point of the whole thing: twenty chunks failing at the same instant
# must not all come back at the same instant.
first = [A.jittered(A.WAIT_SCHEDULE[0]) for _ in range(20)]
print("       20 chunks retrying the first wait: %d distinct times"
      % len(set(round(x, 3) for x in first)))
check("2a twenty simultaneous failures produce twenty different waits",
      len(set(round(x, 3) for x in first)) > 15,
      len(set(round(x, 3) for x in first)))
check("2b spread across a window wide enough to matter",
      max(first) - min(first) > 1.0, max(first) - min(first))

print("\n3 THE RETRY LOOP USES IT, AND IS STILL BOUNDED")
waits_seen = []


def never_works(path):
    raise RuntimeError("503 service unavailable")


txt, err = A.transcribe_one_chunk(never_works, "x",
                                  sleep=lambda s: waits_seen.append(s))
print("       waits actually slept: %s"
      % [round(w, 1) for w in waits_seen])
check("3a it gives up rather than retrying for ever",
      txt is None and err, err)
check("3b exactly len(schedule) waits, no more",
      len(waits_seen) == len(A.WAIT_SCHEDULE), len(waits_seen))
check("3c every wait was jittered, none is the bare schedule value",
      all(w not in A.WAIT_SCHEDULE for w in waits_seen), waits_seen)
check("3d and they still back OFF, each longer than the last",
      all(waits_seen[i] < waits_seen[i + 1]
          for i in range(len(waits_seen) - 1)), waits_seen)

ok_waits = []


def works_second_time(path, box=[0]):
    box[0] += 1
    if box[0] == 1:
        raise RuntimeError("429 too many requests")
    return "the words"


txt2, err2 = A.transcribe_one_chunk(works_second_time, "x",
                                    sleep=lambda s: ok_waits.append(s))
check("3e a chunk that recovers stops waiting", txt2 == "the words" and not err2)
check("3f having waited exactly once", len(ok_waits) == 1, ok_waits)


def permanent(path):
    raise RuntimeError("model_not_found")


no_waits = []
txt3, err3 = A.transcribe_one_chunk(permanent, "x",
                                    sleep=lambda s: no_waits.append(s))
check("3g a PERMANENT error is not retried at all — waiting cannot help",
      no_waits == [] and txt3 is None, no_waits)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
