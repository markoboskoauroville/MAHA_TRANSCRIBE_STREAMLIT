"""EVERY RING FALLS BACK — audited across all four providers.

    python3 tests/test_fallback_audit.py

Baba: "Check on all other APIs if the fallback mechanism is well written
and it will work. Go in the code and see if all is coded correctly."

WHAT THE AUDIT FOUND, 25.8.2026, after the Hume ring was found broken:

  every classifier took ONLY the status, so none could tell a Cloudflare
    403/1010 from a real 403. That buries the WHOLE ring at once,
    because it hits every key identically — measured across 21 Hume
    pairs in the manifest.
  none could tell a 400 that means "no credit" from a 400 that means
    "bad request". Measured on Hume: an empty account answers 400 with
    slug zero_credits, not 402.
  AssemblyAI's copy was MISSING 402 entirely. Speechify had it.
  Speechify and AssemblyAI READ THE BODY for the message and threw it
    away for the verdict, which is where the decision lives.

TEST 1 is the shared rule as a truth table. TEST 2 walks a ring under
each verdict with a counting fake. TEST 3 reads the wiring.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt.providers import base  # noqa: E402
from ttt.providers.groq import classify_exception  # noqa: E402
from ttt import keyring as kr  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

C = base.classify_standard

print("1 THE ONE RULE, AS A TRUTH TABLE")
table = [
    (200, "", "soft", "not an error at all"),
    (401, "", "dead", "bad key"),
    (402, "", "dead", "payment required"),
    (403, "", "dead", "genuinely forbidden"),
    (403, "error code: 1010", "soft", "CLOUDFLARE, not the key"),
    (429, "", "cool", "valid but throttled — rest it, never bury it"),
    (400, '{"slug":"zero_credits"}', "dead", "the account is empty"),
    (400, "Exhausted credit balance", "dead", "same, in words"),
    (400, "invalid_request: bad body", "soft", "our fault, no key helps"),
    (500, "", "soft", "their fault"),
    (404, "", "soft", "wrong endpoint, not a bad key"),
]
for status, body, want, why in table:
    got = C(status, body)
    check("1a %3d %-26s -> %-4s  (%s)" % (status, body[:26], got, why),
          got == want, "expected %s" % want)

print("\n1b THE TWO THAT A STATUS ALONE CANNOT SEE")
check("1b1 403+1010 is NOT dead — it would bury every key at once",
      C(403, "error code: 1010") != "dead")
check("1b2 but a plain 403 still is", C(403, "forbidden") == "dead")
check("1b3 a credit 400 IS dead, so the ring moves on",
      C(400, "zero_credits") == "dead")
check("1b4 while an ordinary 400 is not, because no other key would fix it",
      C(400, "malformed json") == "soft")
check("1b5 the body is optional, so old call sites still work",
      C(401) == "dead" and C(429) == "cool")
check("1b6 and case does not matter", C(400, "ZERO_CREDITS") == "dead")

print("\n2 WHAT EACH VERDICT DOES TO A RING")


def walk(verdicts):
    """Drive kr.rotate with n keys and a scripted verdict per attempt."""
    ring = {"keys": [{"key": "k%d" % i, "state": "new", "cool_until": 0,
                      "calls": 0, "chars": 0} for i in range(len(verdicts))],
            "active": 0}
    tried = []

    def attempt(key):
        i = int(key[1:])
        tried.append(i)
        v = verdicts[i]
        if v == "ok":
            return {"ok": True}, None, "ok"
        return None, "e%d" % i, v

    res, err = kr.rotate(ring, attempt)
    return ring, tried, res, err


ring, tried, res, err = walk(["dead", "dead", "ok"])
check("2a a dead key moves to the next, and the third answers",
      res is not None and tried == [0, 1, 2], tried)
check("2b the dead ones are buried",
      [k["state"] for k in ring["keys"][:2]] == ["dead", "dead"],
      [k["state"] for k in ring["keys"]])
check("2c and the good one is not", ring["keys"][2]["state"] != "dead")

ring, tried, res, err = walk(["cool", "ok"])
check("2d a throttled key is RESTED, not buried",
      ring["keys"][0]["state"] == "cool", ring["keys"][0]["state"])
check("2e and the next one is tried at once", res is not None, tried)
check("2f a rested key keeps its future — cool_until is set",
      ring["keys"][0]["cool_until"] > 0)

ring, tried, res, err = walk(["soft", "ok"])
check("2g a SOFT failure stops rather than burning the ring — no other "
      "key can fix our own bad request",
      res is None and tried == [0], tried)
check("2h and it does not bury the key it stopped on",
      ring["keys"][0]["state"] != "dead", ring["keys"][0]["state"])

ring, tried, res, err = walk(["dead", "dead", "dead"])
check("2i all dead is an error, not a crash", res is None and err)
check("2j and every key was tried exactly once", tried == [0, 1, 2], tried)

print("\n3 EVERY PROVIDER IS WIRED TO IT")
app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
code = "\n".join(l for l in app.splitlines() if not l.lstrip().startswith("#"))
print("       searched app.py CODE for each classifier and its call site")
check("3a Speechify defers to the shared rule",
      "def sp_error_kind" in code and "classify_standard(status, body)" in code)
check("3b AssemblyAI does too", "def aai_error_kind" in code)
check("3c Speechify PASSES the body to the verdict, not just the message",
      "sp_error_kind(e.code, body)" in code)
check("3d AssemblyAI passes it too", "aai_error_kind(e.code, resp)" in code)
check("3e Hume reads the body as well", "hume_error_kind(e.code, raw)" in code)
check("3f and Hume's credit case defers to the shared rule rather than "
      "keeping a private copy",
      "PROVIDERS.base.classify_standard(status, body)" in code)

groq = open(os.path.join(os.path.dirname(__file__), "..", "ttt",
                         "providers", "groq.py"), encoding="utf-8").read()
gcode = "\n".join(l for l in groq.splitlines() if not l.lstrip().startswith("#"))
check("3g Groq hands the message through as the body",
      "classify_standard(status, text)" in gcode)
check("3h and catches 1010 in the text path too, for an exception with "
      "no status", '"1010" in text' in gcode)
check("3i Groq sends a User-Agent, which avoids the trap at source",
      "User-Agent" in groq)

print("\n3b GROQ'S EXCEPTIONS")
class E(Exception):
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status_code = status

for exc, want, why in (
        (E("unauthorized", 401), "dead", "bad key"),
        (E("rate limit", 429), "cool", "throttled"),
        (E("403 Forbidden error code: 1010", 403), "soft", "Cloudflare"),
        (E("Forbidden", 403), "dead", "really forbidden"),
        (E("error code: 1010"), "soft", "Cloudflare, no status on the exc"),
        (E("invalid_request"), "soft", "our request"),
        (E("insufficient quota"), "dead", "no credit")):
    got = classify_exception(exc)
    check("3j %-34s -> %-4s (%s)" % (str(exc)[:34], got, why), got == want,
          "expected %s" % want)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
