"""A DEAD RING COSTS ONE CALL AND IS SAID OUT LOUD.

    python3 tests/test_dead_key_take.py

Both G6 blockers from the delivery gate of 25.8.2026, and both are
fault 7 from Baba's brief at 03:20 that morning:

  "with every key dead the app retried 6 times over 8 redraws and showed
   NOTHING"

TWO CAUSES, ONE PLACE. transcribe_any_size walks a ladder — direct, then
transcoded, then chunked — and swallowed the first two failures with
`except Exception: pass`. Each rung solves a SIZE problem. None of them
helps a revoked key, which refuses the chunks exactly as it refused the
file. 1 + 1 + 4 retries = the six.

And is_transient("401 Invalid API Key") returned True, because it ended
in `or True` and 401 was not on the permanent list. So waiting 5s, 30s
and 125s was tried against a key that will never come back.

THE DISTINCTION THAT MATTERS: by the time either function is asked
anything, the ring has ALREADY walked every key. So the question is not
"is this key bad" but "will the WHOLE RING be different in two minutes".
For a rate limit it will — that is what the 125s is for. For a bad or
unpaid key it will not.
"""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import audio as A  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

print("1 WHAT IS WORTH WAITING FOR")
for msg, want, why in (
        ("401 Invalid API Key", False, "revoked — waiting cannot revive it"),
        ("invalid_api_key", False, "the same, as Groq spells it"),
        ("Authentication error, API token missing/invalid", False,
         "the same, as AssemblyAI spells it"),
        ("Exhausted credit balance", False, "no credit"),
        ("zero_credits", False, "the same, as Hume's slug"),
        ("insufficient quota", False, "no credit, other words"),
        ("429 rate limit reached", True, "THROTTLED — waiting is the fix"),
        ("All 5 key(s) unavailable. Last: 429 too many requests", True,
         "the whole ring is resting, and rests end"),
        ("All 5 key(s) unavailable. Last: 401 Invalid API Key", False,
         "the whole ring is dead, and dead does not end"),
        ("503 service unavailable", True, "their outage"),
        ("timed out", True, "a blip"),
        ("model_not_found", False, "permanent, already known")):
    got = A.is_transient(RuntimeError(msg))
    check("1a %-52s -> %-5s (%s)" % (msg[:52], got, why), got == want,
          "expected %s" % want)

print("\n2 THE LADDER STOPS ON A PERMANENT FAILURE")
tmp = tempfile.mktemp(suffix=".wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                "-i", "sine=frequency=200:duration=2", "-ar", "16000",
                "-ac", "1", tmp], check=True)


def run(err):
    n = {"c": 0}

    def fn(p):
        n["c"] += 1
        raise RuntimeError(err)
    try:
        A.transcribe_any_size(tmp, fn, sleep=lambda s: None)
        return n["c"], None
    except Exception as ex:
        return n["c"], str(ex)


calls_dead, err_dead = run("401 Invalid API Key")
print("       every key dead   : %d provider call(s)" % calls_dead)
check("2a a dead ring costs ONE call, not six", calls_dead == 1, calls_dead)
check("2b and it RAISES, so the caller can put it on screen",
      err_dead is not None, err_dead)
check("2c the message says what actually happened",
      "401" in (err_dead or ""), err_dead)

calls_cool, err_cool = run("429 rate limit reached")
print("       every key resting: %d provider call(s)" % calls_cool)
check("2d a THROTTLED ring still gets the full ladder and its retries — "
      "that is what the waits are for", calls_cool > 3, calls_cool)
check("2e and it still ends by raising rather than returning silence",
      err_cool is not None, err_cool)

print("\n2b THE HAPPY PATH IS UNTOUCHED")
n = {"c": 0}


def works(p):
    n["c"] += 1
    return "the words"


txt, method, reusable, temps = A.transcribe_any_size(tmp, works,
                                                     sleep=lambda s: None)
check("2f a working provider is called exactly once",
      n["c"] == 1, n["c"])
check("2g and its words come back", txt == "the words", txt)
check("2h by the direct route, with no transcode", method == "direct", method)

print("\n2c A FAILURE THAT REALLY IS ABOUT SIZE STILL CLIMBS")
n2 = {"c": 0}


def too_big_once(p):
    n2["c"] += 1
    if n2["c"] == 1:
        raise RuntimeError("413 payload too large")
    return "the words"


txt2, method2, _r, _t = A.transcribe_any_size(tmp, too_big_once,
                                              sleep=lambda s: None)
check("2i a size failure falls through to the next rung",
      txt2 == "the words" and n2["c"] == 2, (n2["c"], method2))
check("2j and reports which rung worked", method2 == "transcoded", method2)

try:
    os.unlink(tmp)
except OSError:
    pass

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
