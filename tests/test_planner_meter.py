"""THE PLANNER COLLISION — which planner, and why.

    python3 tests/test_planner_meter.py

v236 made the reader generate one file per sentence. Google's free tier
allows ten TTS requests per account per day. One paragraph would spend an
account. This suite is the proof that the reader now chooses by whether
the voice is metered by the call, and that it does so WITHOUT naming a
vendor.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from ttt import speech as S                    # noqa: E402
from ttt import engines as EN                  # noqa: E402
from ttt.providers import get                  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def strip_comments(src: str) -> str:
    """Code only. A check that greps raw source matches its own
    explanation and passes for ever — face 2, met seven times here."""
    out = []
    for line in src.splitlines():
        if line.lstrip().startswith("#"):
            continue
        out.append(re.sub(r'(?<!["\'])#.*$', "", line))
    body = "\n".join(out)
    return re.sub(r'"""(?:.|\n)*?"""', "", body)


APP = strip_comments(open(os.path.join(ROOT, "app.py")).read())
SPEECH_SRC = strip_comments(open(os.path.join(ROOT, "ttt", "speech.py")).read())

SENT = ["Sentence %d." % i for i in range(1, 11)]

# =====================================================================
print("1 THE MECHANISM, ALONE")
# =====================================================================

unmetered = S.plan_for(SENT, metered=False)
metered = S.plan_for(SENT, metered=True)

check("unmetered gives one sentence per request", len(unmetered) == 10,
      len(unmetered))
check("metered gives blocks instead", len(metered) == 3, len(metered))
check("metered costs FEWER requests than unmetered",
      len(metered) < len(unmetered), (len(metered), len(unmetered)))

check("unmetered is exactly plan_sentences",
      unmetered == S.plan_sentences(SENT))
check("metered is exactly plan_even", metered == S.plan_even(SENT))

check("both return the same SHAPE, so the deck does not branch",
      all(isinstance(p, tuple) and len(p) == 2 and isinstance(p[0], list)
          and isinstance(p[1], int) for p in unmetered + metered))

# NOT ONE SENTENCE IS LOST OR DUPLICATED BY EITHER PLANNER. This is the
# invariant that matters most: a planner that drops a sentence reads a
# document with a hole in it and nothing on screen says so.
for name, plan in (("unmetered", unmetered), ("metered", metered)):
    flat = [s for ss, _off in plan for s in ss]
    check("%s keeps every sentence, in order" % name, flat == SENT,
          flat[:3])

# THE OFFSET MUST POINT AT THE SENTENCE. The offset is what places the
# highlight; an offset that drifts lights the wrong text, which is the
# one failure Baba refused outright.
joined = " ".join(SENT)
for name, plan in (("unmetered", unmetered), ("metered", metered)):
    bad = [(off, ss[0]) for ss, off in plan
           if not joined.startswith(ss[0], off)]
    check("%s: every offset lands on its own first sentence" % name,
          not bad, bad[:2])

check("default is UNMETERED — the safe direction to be wrong in",
      S.plan_for(SENT) == unmetered)

check("requests_for agrees with plan_for, unmetered",
      S.requests_for(SENT, False) == len(unmetered))
check("requests_for agrees with plan_for, metered",
      S.requests_for(SENT, True) == len(metered))

# THE NUMBER THAT MADE THIS NECESSARY. A paragraph against an allowance
# of ten. This is the collision, stated as an assertion.
para = ["A sentence about %d." % i for i in range(1, 21)]
allowance = get("google").calls_per_day
check("a 20-sentence paragraph unmetered would cost MORE than a whole "
      "Google account's day",
      S.requests_for(para, False) > allowance,
      (S.requests_for(para, False), allowance))
check("...and metered it fits inside one account's day",
      S.requests_for(para, True) <= allowance,
      (S.requests_for(para, True), allowance))

# =====================================================================
print()
print("2 THE REAL THING — the app, not the function")
# =====================================================================
#
# No key and no network here: what is being proved is that the READER
# calls this, which is the gap between "the function works" and "the
# feature works".

check("the reader calls plan_for", "SPEECH.plan_for(" in APP)
check("the reader no longer calls plan_sentences directly",
      "SPEECH.plan_sentences(" not in APP)
check("it passes the metering answer, not a constant",
      re.search(r"SPEECH\.plan_for\(\s*sentences,\s*metered=talking_is_metered\(\)",
                APP) is not None)
check("talking_is_metered is defined", "def talking_is_metered(" in APP)
check("...and it asks the PROVIDER, through the route",
      re.search(r'def talking_is_metered.*?current_routes\(\)\.get\("tts"\)'
                r'.*?metered_by_call', APP, re.S) is not None)

# §0 RULE 2. The whole point of doing it this way.
#
# A SLICE IS A CLAIM ABOUT WHERE, AND IT DESERVES A CHECK OF ITS OWN.
# index() raises where find() reports, and in a test file with no harness
# that kills the process — so every check after it silently never runs
# and the sweep prints no number at all. Face 1, met four times here in
# one day. And a slice whose bounds are the wrong way round is the empty
# string, in which "google" not in "" is True: face 6, a check that
# passes on nothing.
def region(src, start, end, label, least=50, most=6000):
    a = src.find(start)
    b = src.find(end)
    check("%s: start marker found" % label, a > 0, a)
    check("%s: end marker found" % label, b > 0, b)
    check("%s: bounds are in order" % label, 0 < a < b, (a, b))
    cut = src[a:b] if 0 < a < b else ""
    # The floor is small on purpose: with comments stripped, the seam is
    # a docstring-free three-line function. What this guards against is
    # ZERO — a reversed slice, in which "google" not in "" is True.
    check("%s: region is neither empty nor enormous (%d chars)"
          % (label, len(cut)), least < len(cut) < most, len(cut))
    return cut


seam = region(APP, "def talking_is_metered", "def llm_bridge",
              "the metering seam")
for vendor in ("google", "gemini", "edge", "speechify", "hume",
               "assemblyai", "anthropic", "groq"):
    check("the metering seam does not name %r" % vendor,
          vendor not in seam.lower(), seam.strip()[:80])

planner = region(SPEECH_SRC, "def plan_for", "def plan_parts", "plan_for")
for vendor in ("google", "gemini", "edge", "speechify"):
    check("plan_for does not name %r either" % vendor,
          vendor not in planner.lower())

# =====================================================================
print()
print("3 THE UGLY CASES")
# =====================================================================

for bad in ([], (), None):
    check("empty input plans nothing rather than raising: %r" % (bad,),
          S.plan_for(bad or [], True) == [] and S.plan_for(bad or [], False) == [])

blank = ["", "   ", "\n"]
check("blank sentences do not become requests, unmetered",
      S.plan_for(blank, False) == [], S.plan_for(blank, False))

huge = ["word " * 2000]

# THE TWO PLANNERS DISAGREE HERE, ON PURPOSE, AND IT IS WRITTEN DOWN IN
# BOTH. My first version of this check asserted that both split an
# over-long sentence. plan_even went red, and the code was right:
#
#   plan_sentences  SPLITS, "because a request that comes back 413 is a
#                   sentence that never plays"
#   plan_even       DOES NOT, "because the only alternative is splitting
#                   it, and a voice cut mid-clause is the thing this
#                   module exists to avoid"
#
# Both are defensible and neither is an accident. Meta-rule 2: an
# expectation comes from the previous behaviour, not from my taste — had
# I "fixed" plan_even to agree with me, a silent behaviour change would
# have ridden in alongside an unrelated feature.
#
# IT IS RECORDED AS A LIVE QUESTION rather than settled here. Gemini's
# real ceiling is about eight minutes of audio per call, not 1500
# characters, so for Google the cap is a heuristic borrowed from another
# provider and the un-split block is very likely fine. That is a thing to
# MEASURE against the live API, not to decide in a test.
split_plan = S.plan_for(huge, False)
check("unmetered splits an over-long sentence, as it promises",
      len(split_plan) > 1, len(split_plan))
check("...at a space, never mid-word",
      all(not ss[0].endswith("wor") for ss, _o in split_plan))
whole_plan = S.plan_for(huge, True)
check("metered keeps it whole, as IT promises — one request, not zero",
      len(whole_plan) == 1 and whole_plan[0][0] == huge, len(whole_plan))
check("either way the text survives the planner",
      "".join(s for ss, _o in whole_plan for s in ss).replace(" ", "")
      == huge[0].replace(" ", ""))

one = ["Only one."]
check("a single sentence is one request either way",
      len(S.plan_for(one, True)) == 1 == len(S.plan_for(one, False)))

# TRUTHINESS, not identity. The value arrives from getattr and may be
# anything a provider set.
check("metered accepts any truthy value",
      S.plan_for(SENT, 1) == metered and S.plan_for(SENT, "yes") == metered)
check("and any falsy value", S.plan_for(SENT, 0) == unmetered
      and S.plan_for(SENT, None) == unmetered)

# IDEMPOTENT. Planning twice must give the same plan, or a resumed
# reading lights different text than the one that made the audio.
check("planning the same text twice gives the same plan",
      S.plan_for(SENT, True) == S.plan_for(SENT, True)
      and S.plan_for(SENT, False) == S.plan_for(SENT, False))

# =====================================================================
print()
print("4 THE UPGRADE — an existing install, mid-reading")
# =====================================================================

check("the free engine is unchanged: still Edge and Groq",
      EN.get("normal").routes == {"stt": "groq", "tts": "edge", "llm": "groq"},
      EN.get("normal").routes)
check("EDGE IS STILL NOT METERED, so every existing reader plans exactly "
      "as it did before this change",
      get("edge").metered_by_call is False)
check("...and an Edge reading still gets one sentence per file",
      S.plan_for(SENT, get("edge").metered_by_call) == S.plan_sentences(SENT))

# STUDIO STAYS AN ENGINE, and its three providers stay providers.
# Baba: "Hume can stay, AssemblyAI can stay, Speechify can stay."
studio = EN.get("studio")
check("studio is still an engine", studio is not None)
check("studio is unchanged",
      studio.routes == {"stt": "assemblyai", "tts": "speechify",
                        "llm": "anthropic"}, studio.routes)
for pid in ("speechify", "assemblyai", "hume"):
    check("%s is still a provider in the registry" % pid, get(pid) is not None)
check("none of the studio providers became an engine",
      not any(e.id in ("speechify", "assemblyai", "hume") for e in EN.ENGINES))

# THE CHANGE ITSELF.
g = EN.get("google")
check("google routes all three tasks to google",
      g.routes == {"stt": "google", "tts": "google", "llm": "google"},
      g.routes)
check("it is one vendor now, so it is a PAIR in Baba's sense",
      len(set(g.routes.values())) == 1)
check("and it is a Google reading that gets blocks",
      S.plan_for(SENT, get("google").metered_by_call) == S.plan_even(SENT))

check("three engines, no more and no fewer", len(EN.ENGINES) == 3,
      [e.id for e in EN.ENGINES])
check("the default engine did not move", EN.DEFAULT == "normal")
check("the old 'free' id still resolves — rows written before 22.8 say it",
      EN.get("free") is EN.get("normal"))

# ROUTE SETTINGS ARE WHAT ACTUALLY GET WRITTEN. An engine that produces
# the wrong route_* strings is an engine that does nothing.
rs = EN.route_settings(g)
check("choosing google writes all three routes",
      rs == {"route_stt": "google", "route_tts": "google",
             "route_llm": "google"}, rs)
check("and current() reads them back as google",
      EN.current(rs) is g, EN.current(rs))
check("a half-patched board reads as mixed, not as google",
      EN.current({"route_stt": "google", "route_tts": "edge",
                  "route_llm": "google"}) is None)

print()
print("%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
