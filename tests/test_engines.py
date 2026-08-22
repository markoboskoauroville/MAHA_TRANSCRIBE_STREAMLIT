"""ENGINES — the mechanism alone. No Streamlit, no network, no keys.

    python3 tests/test_engines.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ttt import engines as EN  # noqa: E402
from ttt import routing as RO  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


print("ENGINES — mechanism alone\n")

free = EN.get("free")
studio = EN.get("studio")

# --- the presets --------------------------------------------------
check("1 two engines", len(EN.ENGINES) == 2, [e.id for e in EN.ENGINES])
check("2 Edge/Groq is the free one",
      free.routes == {"stt": "groq", "tts": "edge", "llm": "groq"}, free.routes)
check("3 Speechify/AssemblyAI/Claude is the other",
      studio.routes == {"stt": "assemblyai", "tts": "speechify",
                        "llm": "anthropic"}, studio.routes)

# EVERY TASK IN routing.TASKS MUST BE COVERED, or choosing an engine
# would leave one job patched to whatever it was before — a silent
# half-switch, which is the worst kind.
for eng in EN.ENGINES:
    missing = [t.id for t in RO.TASKS if t.id not in eng.routes]
    check("4 %s covers every routing task" % eng.id, not missing, missing)

# --- the settings it writes ---------------------------------------
rs = EN.route_settings(studio)
check("5 it writes the SAME route_* keys the patch bay uses",
      rs == {"route_stt": "assemblyai", "route_tts": "speechify",
             "route_llm": "anthropic"}, rs)
for t_ in RO.TASKS:
    check("6 route_%s matches routing's own setting_key name" % t_.id,
          t_.setting_key in rs, t_.setting_key)

# --- which engine is running --------------------------------------
check("7 current() recognises a full free board",
      EN.current(EN.route_settings(free)) is free)
check("8 current() recognises a full studio board",
      EN.current(EN.route_settings(studio)) is studio)

mixed = EN.route_settings(studio)
mixed["route_tts"] = "edge"
check("9 ONE hand-patched crosspoint reports mixed, not a stale name",
      EN.current(mixed) is None, EN.current(mixed))
# An EMPTY board is not mixed — nothing has been patched, so every task
# is running its own default, and for a new person that really is the
# free engine. Reading "mixed" there was the label being wrong in the one
# case where it matters most: the first time anybody looks at it.
check("10 an empty board is the DEFAULT engine, not mixed",
      EN.current({}) is free, EN.current({}))
check("10b and the defaults it falls back to are routing's own",
      EN.TASK_DEFAULTS == {t.id: t.default for t in RO.TASKS},
      EN.TASK_DEFAULTS)

# --- provider list, in task order ---------------------------------
check("11 free lists each provider once, in task order",
      free.provider_ids == ["groq", "edge"], free.provider_ids)
check("12 studio lists all three",
      studio.provider_ids == ["assemblyai", "speechify", "anthropic"],
      studio.provider_ids)

check("13 tasks_for says WHAT stops working, not just who refused",
      EN.tasks_for(free, "groq") == ["stt", "llm"], EN.tasks_for(free, "groq"))

# --- the check ----------------------------------------------------
def fake(results):
    return lambda pid: results.get(pid, (EN.FAIL, "not asked"))


state, rows = EN.check(studio, fake({"assemblyai": (EN.OK, ""),
                                     "speechify": (EN.OK, ""),
                                     "anthropic": (EN.OK, "")}))
check("14 all three good -> ok", state == EN.OK, state)
check("15 one row per provider", len(rows) == 3, rows)

state, rows = EN.check(studio, fake({"assemblyai": (EN.OK, ""),
                                     "speechify": (EN.FAIL, "401"),
                                     "anthropic": (EN.OK, "")}))
check("16 ONE failure fails the whole engine — the verdict is the worst "
      "part, not an average", state == EN.FAIL, state)
check("17 and the failing part is named",
      [r for r in rows if r["state"] == EN.FAIL][0]["provider"] == "speechify")
check("18 with its reason kept",
      [r for r in rows if r["state"] == EN.FAIL][0]["detail"] == "401")

state, rows = EN.check(free, fake({"groq": (EN.OK, ""),
                                   "edge": (EN.SKIP, "no key needed")}))
check("19 a keyless part does NOT fail the engine", state == EN.OK, state)
check("20 and it is reported as skipped, not as proven",
      [r for r in rows if r["provider"] == "edge"][0]["state"] == EN.SKIP)

state, rows = EN.check(free, fake({"groq": (EN.FAIL, "no working key"),
                                   "edge": (EN.SKIP, "")}))
check("21 the free engine CAN fail — Groq keys can be exhausted",
      state == EN.FAIL, state)

# --- ugly cases ---------------------------------------------------
check("22 an unknown engine id is None, not a crash", EN.get("nope") is None)
check("23 and an empty one too", EN.get("") is None)

calls = []


def counting(pid):
    calls.append(pid)
    return EN.OK, ""


EN.check(free, counting)
check("24 a provider used for two jobs is tested ONCE, not twice",
      calls.count("groq") == 1, calls)

print("\n{} passed, {} failed".format(passed, failed))


def test_engines():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_engines.py` is how it is meant to be read."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
