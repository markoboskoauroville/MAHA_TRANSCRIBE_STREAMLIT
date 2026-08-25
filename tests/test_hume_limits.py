"""THE CEILING, THE FALLBACK, AND NOTHING SILENTLY DROPPED.

    python3 tests/test_hume_limits.py

Baba: "Make sure you understand the ceiling of every API... never send
more than the cap. If 4 sentences has more than the cap, don't send it,
cap it and generate the next pass. And what happens when you hit the
limit? We also have a fallback, we have a few more Hume APIs, so we can
go to fallback when one is rejecting us."

WHAT WAS MEASURED, 25.8.2026, one real key, ascending:

    1000 chars -> 200,  54s of audio
    2000 chars -> 200, 111s
    3000 chars -> 200, 170s
    5000 chars -> 400 zero_credits — that account ran out during the
                  probe, so the true ceiling above 3000 is STILL UNKNOWN

TEXT_CAP is therefore a KINDNESS cap of ours, not Hume's documented
limit. I had told Baba it was Hume's; it was a constant in our own file
and I repeated it back as a fact.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import vr as V  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()

print("1 NOTHING IS EVER SENT OVER THE CAP")
long_one = ("word " * 1200).strip() + "."
plan = V.plan_directed(long_one)
sizes = [len(" ".join(b)) for _, b in plan]
print("       6000-char sentence -> blocks of %s" % sizes)
check("1a an over-long sentence is SPLIT, not truncated", len(plan) > 1, sizes)
check("1b every block is within the cap",
      all(n <= V.TEXT_CAP for n in sizes), sizes)
check("1c and the words are all still there",
      sum(sizes) >= len(long_one) - len(plan), (sum(sizes), len(long_one)))
check("1d it splits at spaces, so no word is cut in half",
      all(not b[0].startswith(" ") and "  " not in b[0]
          for _, b in plan), [b[0][:20] for _, b in plan])

print("\n1b THE UGLY CASES")
check("1e one unbroken token still gets said, hard-cut as a last resort",
      all(n <= V.TEXT_CAP for n in
          [len(" ".join(b)) for _, b in V.plan_directed("x" * 5000 + ".")]))
check("1f a short sentence is untouched", V.split_long("Short.") == ["Short."])
check("1g empty is nothing", V.split_long("") == [] and V.split_long(None) == [])
check("1h exactly at the cap is one piece",
      len(V.split_long("a" * V.TEXT_CAP)) == 1)
check("1i one past the cap is two",
      len(V.split_long("a" * (V.TEXT_CAP + 1))) == 2)
check("1j splitting keeps the tags working — a long sentence under a tag "
      "stays under it",
      all(w == ["calm"] for w, _ in V.plan_directed("<calm>" + long_one)))

print("\n2 THE CALL REFUSES RATHER THAN TRIMMING")
sp = app[app.index("def hume_speak"):app.index("def hume_test_one")]
# CODE ONLY, NOT COMMENTS. The string still appears in the comment that
# explains why it was removed — and a check that cannot tell the two
# apart would force us to delete the explanation to keep it green, which
# is the tail wagging the dog.
_code = "\n".join(l for l in sp.splitlines()
                  if not l.lstrip().startswith("#"))
check("2a hume_speak no longer slices the text",
      "text[:VR.TEXT_CAP]" not in _code,
      [l for l in _code.splitlines() if "TEXT_CAP]" in l])
check("2a2 and the reason it was removed is still written down",
      "text[:VR.TEXT_CAP]" in sp)
check("2b an over-cap block is reported, not quietly shortened",
      't("vr_too_long")' in sp)
check("2c and it returns TWO values, like everything else here",
      'return None, t("vr_too_long") % VR.TEXT_CAP' in sp)

print("\n3 THE FALLBACK, WHICH IS WHAT HE ASKED ABOUT")
ek_all = app[app.index("def hume_error_kind"):app.index("def hume_error_message")]
# CODE ONLY. The comment above the guard quotes Hume's own error body,
# so a check that reads comments passes with the guard deleted — proven
# by deleting it and watching 3a and 3b stay green. The same fault as 2a,
# four checks apart, in the same file I wrote in one sitting.
ek = "\n".join(l for l in ek_all.splitlines()
               if not l.lstrip().startswith("#"))
print("       searched hume_error_kind's CODE for the credit case")
check("3a an exhausted account is DEAD, so the ring moves on",
      "zero_credits" in ek and 'return "dead"' in ek)
check("3b it is matched on the body, not only the status — Hume answers "
      "400 for this, which used to fall through to soft",
      "e0300" in ek.lower() and "credit balance" in ek.lower(), ek[-200:])
check("3b2 and the measured error body is written down beside it",
      "zero_credits" in ek_all)
check("3c 401 and 402 are still dead", "status in (401, 402)" in ek)
check("3d 429 still RESTS a key rather than condemning it — valid and "
      "throttled is not the same as bad", 'return "cool"' in ek)
check("3e 403/1010 is still soft, because that is Cloudflare refusing "
      "the client and not Hume refusing the key",
      '"1010" in (body or "")' in ek)

loop = sp[sp.index("for _ in range(n):"):]
check("3f a dead key advances to the next account", 'if kind == "dead"' in loop
      and "idx = (i + 1) % n" in loop)
check("3g a rested key advances too", 'if kind == "cool"' in loop)
check("3h and the loop really walks the WHOLE ring before giving up",
      "for _ in range(n):" in sp)
check("3i condemned, not rested — credit does not come back in sixty "
      "seconds", "cool_until" in loop and "dead" in loop)

print("\n4 THE CAP IS HONEST ABOUT WHAT IT IS")
vr = open(os.path.join(os.path.dirname(__file__), "..", "ttt", "vr.py"),
          encoding="utf-8").read()
check("4a it says it is OURS, not Hume's documented limit",
      "kindness cap" in vr.lower())
check("4b the measurement is written down beside it",
      "3000 chars -> 200" in vr)
check("4c including that the real ceiling is still unknown",
      "unknown" in vr.lower())

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
