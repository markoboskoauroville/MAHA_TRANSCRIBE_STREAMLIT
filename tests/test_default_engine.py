"""THE MACHINE'S DEFAULT ENGINE IS THE DEFAULT FOR EVERY TASK (7.9.2026).

    python3 tests/test_default_engine.py

The Oracle machine names TTT_DEFAULT_ENGINE=offline and every new person still
read "Edge" at the foot and sent recordings to Groq: the tasks' fallbacks in
routing.TASKS were written once (groq, edge, groq) and nothing rewrote them.
Now engines.py rewrites them from the default engine's routes.

1  the mechanism: with TTT_DEFAULT_ENGINE=google (an engine every machine has)
   the tts fallback is google's provider and current({}) is google; with
   nothing named, the fallbacks are the normal engine's and current({}) is normal
2  the whole board: routing.all_routes on an empty session follows the default
3  ugly: an unknown name falls back to normal, quietly
4  upgrade: a person with a stored route keeps it, whatever the default
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def fresh(default):
    if default is None:
        os.environ.pop("TTT_DEFAULT_ENGINE", None)
    else:
        os.environ["TTT_DEFAULT_ENGINE"] = default
    from ttt import routing, engines
    importlib.reload(routing)
    return importlib.reload(engines), routing


print("1 THE MECHANISM, ALONE")
EN, RO = fresh("google")
g = EN.get("google")
check("google is the default", EN.DEFAULT == "google")
check("the tts fallback is google's provider", EN.TASK_DEFAULTS["tts"] == g.routes["tts"], EN.TASK_DEFAULTS)
check("and routing.TASKS says the same", {t.id: t.default for t in RO.TASKS}["tts"] == g.routes["tts"])
check("an empty session amounts to google", EN.current({}) is g, EN.current({}))
EN, RO = fresh(None)
check("nothing named: normal is the default", EN.DEFAULT == "normal")
check("and the fallbacks are normal's", all(EN.TASK_DEFAULTS[k] == v for k, v in EN.get("normal").routes.items()), EN.TASK_DEFAULTS)
check("an empty session amounts to normal", EN.current({}) is EN.get("normal"))

print("2 THE WHOLE BOARD")
EN, RO = fresh("google")


class _P:
    def __init__(self, pid):
        self.id = pid


class _Registry:
    """The shape routing needs: every provider answers every capability here."""
    def __init__(self, ids):
        self.all = [_P(pid) for pid in ids]

    def with_capability(self, cap):
        return list(self.all)


providers = _Registry({v for e in EN.ENGINES for v in e.routes.values()})
routes = RO.all_routes(providers, lambda p: True, {})
check("all_routes on an empty session gives google's tts", routes["tts"].id == g.routes["tts"], {k: v.id for k, v in routes.items()})

print("3 THE UGLY CASES")
EN, RO = fresh("nonsense")
check("an unknown name falls back to normal", EN.DEFAULT == "normal" and EN.current({}) is EN.get("normal"))
EN, RO = fresh("")
check("an empty name falls back to normal", EN.DEFAULT == "normal")

print("4 UPGRADE")
EN, RO = fresh("google")
kept = dict(EN.get("normal").routes)
stored = {"route_%s" % k: v for k, v in kept.items()}
check("a person with stored routes keeps their engine", EN.current(stored) is EN.get("normal"))
fresh(None)

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
