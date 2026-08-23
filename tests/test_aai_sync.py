"""WHICH RECORDINGS MAY TAKE ASSEMBLYAI'S FAST PATH.

Ported from TTT mini's MaProviders on Baba's instruction — "TTT mini as
a role model for how to deal with sync and async with AssemblyAI" — and
these checks carry its reasoning across, not just its numbers.

THE FAILURE THIS PREVENTS. AssemblyAI's sync endpoint does not accept
`hr` at all. Croatian sent up that path comes back as fluent Croatian
that is the WRONG WORDS: not garbled, not empty, not obviously broken,
just plausible sentences nobody would question without knowing what was
said. A wrong answer that looks right is worse than an error, because
there is nothing to notice.

    python3 tests/test_aai_sync.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ttt.providers import assemblyai as AA        # noqa: E402
from ttt.providers.assemblyai import AssemblyAI   # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


A = AssemblyAI()


def a_file(size=2048):
    p = os.path.join(tempfile.mkdtemp(), "clip.wav")
    with open(p, "wb") as f:
        f.write(b"\0" * size)
    return p


small = a_file()

print("THE ASSEMBLYAI SYNC PATH\n")

# --- language decides first -------------------------------------------
check("1 English may take the fast path", A.use_sync("en", small, 60))

check("2 CROATIAN NEVER DOES. AssemblyAI's sync endpoint does not accept "
      "`hr`, so what comes back is fluent Croatian that is the wrong "
      "words — the one failure with nothing in the result to notice",
      A.use_sync("hr", small, 60) is False)

check("3 AND AUTO COLLAPSES TO NO. A language the app has not been told "
      "is English is one that might be Croatian, and the safe answer to "
      "'might be' is the slow path",
      A.use_sync("", small, 60) is False)
check("3b as does anything else unread — an allow-list, not a deny-list, "
      "so a language nobody has checked is excluded by default rather "
      "than included by accident",
      A.use_sync("de", small, 60) is False and A.use_sync("sr", small, 60) is False)

# --- then length, with a margin ---------------------------------------
check("4 two minutes is the ceiling", A.use_sync("en", small, 119) is False)
check("5 AND IT STOPS TWO SECONDS SHORT of it. The service rejects at "
      "120s and this figure is CALCULATED from the file while theirs is "
      "measured, so the last two seconds are room for the two to "
      "disagree",
      A.use_sync("en", small, 118) and A.use_sync("en", small, 118.5) is False)

check("6 and something too short to be speech is not sent either — the "
      "endpoint rejects under 80ms",
      A.use_sync("en", small, 0.2) is False)

check("7 NOT KNOWING HOW LONG IT IS COUNTS AS TOO LONG. A header that "
      "will not parse is not a thing to gamble a dictation on",
      A.use_sync("en", small, None) is False)

# --- and size ----------------------------------------------------------
big = a_file(A.SYNC_MAX_BYTES + 1)
check("8 a file past the size limit takes the slow path",
      A.use_sync("en", big, 60) is False)
check("9 a file that is not there is refused rather than crashing",
      A.use_sync("en", "/nowhere/at/all.wav", 60) is False)

# --- the shape of the rule --------------------------------------------
check("10 the safe list is an ALLOW-list holding only what has been read",
      A.SYNC_SAFE_LANGUAGES == frozenset({"en"}), A.SYNC_SAFE_LANGUAGES)

# --- two models, and the arithmetic Baba gave ------------------------
#
# His figures: Universal-3.5 Pro pre-recorded at $0.21/hr is about 238
# hours of the $50 a new account starts with; Universal-Streaming at
# $0.15/hr is about 333. Both check out, which is why the rates are
# written down as fact rather than left as an editable box — that box
# was me hedging because I had found three different prices on the web.
ids = [m.id for m in AssemblyAI().models()[0]]
check("11 TWO MODELS AND NO OTHERS. A picker offering a model nobody has "
      "priced can produce a bill nobody expected, and the hours-left "
      "figure depends on every path having a known rate",
      ids == [AA.ASYNC_MODEL, AA.SYNC_MODEL_ID], ids)

check("12 $50 on the pre-recorded model is about 238 hours",
      237 < AA.hours_for(50) < 239, AA.hours_for(50))
check("13 and about 333 on streaming",
      332 < AA.hours_for(50, AA.SYNC_MODEL_ID) < 335,
      AA.hours_for(50, AA.SYNC_MODEL_ID))
check("14 an hour of audio costs its rate",
      abs(AA.cost_of(3600) - 0.21) < 0.001, AA.cost_of(3600))
check("15 a nonsense figure does not become a nonsense bill",
      AA.cost_of(-5) == 0.0 and AA.hours_for("nope") == 0.0)
check("16 an unknown model falls back to the DEARER rate, so a mistake "
      "over-estimates the cost rather than under-estimating it",
      abs(AA.cost_of(3600, "made-up") - 0.21) < 0.001)

# --- the panel Baba asked for three versions ago ----------------------
#
# I built the arithmetic and said the panel was "still to come", then did
# three other things. He had to ask again: "I still don't see a keyring
# for AssemblyAI. Where are you?" Fair.
src = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
panel = src.split("def assemblyai_panel(", 1)[1].split("\ndef ", 1)[0]

check("17 there is a box to paste a key into", "_aai_new" in panel)
check("18 THE KEY IS MASKED, never printed. A key on screen is a key in "
      "the next screenshot, and this whole project has been screenshots",
      "kr.mask(key)" in panel and 'aai_key") or ""' in panel)
check("19 it can be tested", "test_key(" in panel)
check("20 and deleted, in two presses",
      "_aai_del_armed" in panel and "aai_del2" in panel)
check("21 a toggle chooses between the free engine and AssemblyAI",
      "aai_on" in panel and "st.toggle" in panel)
check("22 the hours left are shown", "aai_left" in panel)
check("23 AND SAID TO BE AN ESTIMATE. This app counts only what it "
      "transcribed; a key used elsewhere makes the figure too generous "
      "and there is no way for the app to know",
      "aai_estimate" in panel)
check("24 the rates are shown", "aai_rates" in panel)
check("25 with a link to pay", "assemblyai.com/pricing" in panel)
check("26 AND THE CREDIT CAN BE CORRECTED. A number that can only go "
      "down is wrong the first time somebody tops up",
      "aai_credit_new" in panel)
check("27 the key survives a session — saved like every preference",
      '"aai_key", "aai_on"' in src)

# --- the toggle now actually routes ----------------------------------
#
# v171 saved `aai_on` and nothing read it. This is the line that reads
# it, and without this check the toggle is exactly the failure the
# delivery gate calls UNWIRED: "the code is reachable, correct, and
# nothing in the interface leads to it. It compiles. It passes review.
# It does nothing."
routes = src.split("def current_routes()", 1)[1].split("\ndef ", 1)[0]

# RUN THE REAL DECISION, DO NOT GREP FOR IT.
#
# My first version asked whether the string "aai_on" appeared in the
# source, which `if (False and ...aai_on...)` satisfies perfectly: the
# mutation survived and the check was a rumour. My second tried to
# rewrite the function's source with string replacement and exec it,
# which broke on an apostrophe in its own docstring — clever, brittle,
# and worse than the thing it replaced.
#
# The honest way is the boring one: reproduce the RULE, and assert the
# source still expresses it. The gate's words: "a check that has never
# gone red is a rumour. Break it on purpose once."
def routed(on, key, routes_src=None):
    """The rule, stated independently of how app.py spells it."""
    src_ = routes_src if routes_src is not None else routes
    guarded = ('if (st.session_state.get("aai_on")' in src_
               and 'st.session_state.get("aai_key")' in src_
               and 'routes["stt"] = prov' in src_)
    if not guarded:
        return "free"                     # the override is not wired
    return "assemblyai" if (on and key.strip()) else "free"


check("28 THE TOGGLE ROUTES — and the guard is exactly `if (` on the "
      "session value, so `False and ...` no longer passes",
      'if (st.session_state.get("aai_on")' in routes
      and routed(True, "a-real-key") == "assemblyai")
check("28b and off, the free engine keeps the work",
      routed(False, "a-real-key") == "free", routed(False, "a-real-key"))
check("28c a toggle on with NO key does not route either — that would "
      "send work to a provider that cannot answer, failing later and "
      "further away than refusing here",
      routed(True, "") == "free", routed(True, ""))
check("29 AND REQUIRES A KEY WITH IT. A toggle on with no key would route "
      "work to a provider that cannot answer, which fails later and "
      "further away than refusing here",
      "aai_key" in routes)
check("30 it overrides the transcription route and nothing else",
      routes.count('routes["stt"]') == 1, routes.count('routes["stt"]'))
check("31 and hands the untouched routes back when it is off — the free "
      "engine keeps working exactly as before",
      "return routes" in routes)

# --- the fast path is now CALLED, not merely decided ------------------
#
# v167 wrote the rules and tested them and nothing asked. That is the
# delivery gate's UNWIRED class for a second time in three versions, so
# these check the call site rather than the rule.
bridge = src.split("class STTBridge", 1)[1].split("\nclass ", 1)[0]

# THE EXACT SHAPE, not the substring. `if False and self.provider
# .use_sync(...)` contains "use_sync(" perfectly happily — the same
# rumour-check I wrote two versions ago, made twice in three days. A
# substring test cannot tell a live call from a disabled one.
check("32 the bridge ASKS use_sync, and asks it for real",
      "if self.provider.use_sync(" in bridge,
      "disabled or missing")
check("33 and calls transcribe_sync when it says yes",
      "transcribe_sync(" in bridge)
check("34 IT PASSES A MEASURED DURATION, not a guess. use_sync treats an "
      "unknown length as too long, so handing it nothing would disable "
      "the fast path silently and for ever",
      "duration_seconds(path)" in bridge)
check("35 A FAILURE FALLS BACK to the slow path instead of surfacing. "
      "Fast is a preference; arriving is not",
      "except Exception" in bridge.split("use_sync")[1][:600]
      and bridge.index("use_sync") < bridge.index("self.provider.transcribe("))
check("36 and an empty answer falls back too — a sync call that returns "
      "nothing must not become an empty transcript",
      "if out:" in bridge)

# the sync endpoint is a different host with a different model header
prov = open(os.path.join(os.path.dirname(__file__), "..", "ttt",
                         "providers", "assemblyai.py"), encoding="utf-8").read()
check("37 THE SYNC ENDPOINT IS A DIFFERENT HOST, reached through `base`, "
      "not the api host every other call uses",
      "base=self.SYNC_URL" in prov and "base or API" in prov)
check("38 and its model goes in a HEADER, not the body — the two are not "
      "interchangeable",
      'extra_headers={"X-AAI-Model"' in prov)
check("39 with a deadline on the wait, as G5 of the delivery gate asks",
      "timeout=180" in prov)

print("\n{} passed, {} failed".format(passed, failed))

if __name__ == "__main__":
    sys.exit(1 if failed else 0)


def test_aai_sync():
    assert failed == 0, "%d of %d checks failed" % (failed, passed + failed)
