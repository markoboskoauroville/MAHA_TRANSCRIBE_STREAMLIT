"""THE SOAK (delivery-gate.md G6/G7): the app run again and again, every tab, and
the numbers written down — time per run and memory growth. Not a test of a
change: a test of duration. Counts printed, not adjectives.

    python3 tests/test_soak.py [runs]        default 40

What it catches: a render that gets slower with every run, a cache that grows
without bound, a tab that raises after the tenth visit. What it cannot catch:
a browser (AppTest has none), the network, a real voice.
"""
import os
import resource
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from streamlit.testing.v1 import AppTest        # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
TABS = ["transcribe", "talk", "translate", "vr", "looks", "help"]
passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def rss_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024.0 * 1024.0) if sys.platform == "darwin" else r / 1024.0


def one(i):
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=90)
    at.session_state["_authed"] = True
    at.session_state["_user"] = "soak"
    at.session_state["active_tab"] = TABS[i % len(TABS)]
    if i % 7 == 3:
        at.session_state["_via_portal"] = True
        at.session_state["_view_tier"] = "admin"
    t0 = time.time()
    at.run()
    dt = time.time() - t0
    exc = [str(e.value)[:120] for e in at.exception]
    return dt, exc, len(at.button), len(at.markdown)


times, errors, widgets = [], [], []
rss0 = rss_mb()
print("soak: %d runs over %d tabs, rss at start %.0f MB" % (RUNS, len(TABS), rss0))
for i in range(RUNS):
    dt, exc, nb, nm = one(i)
    times.append(dt)
    widgets.append((nb, nm))
    if exc:
        errors.append((i, TABS[i % len(TABS)], exc))
    if i % 10 == 9:
        print("  run %2d  tab %-10s  %.2fs  rss %.0f MB  buttons %d  markdown %d" % (i + 1, TABS[i % len(TABS)], dt, rss_mb(), nb, nm))
rss1 = rss_mb()

first, last = times[: len(times) // 4] or times, times[-(len(times) // 4):] or times
print("time per run: first quarter median %.2fs, last quarter median %.2fs, max %.2fs" % (
    sorted(first)[len(first) // 2], sorted(last)[len(last) // 2], max(times)))
print("rss: %.0f MB -> %.0f MB (%.0f MB growth over %d runs)" % (rss0, rss1, rss1 - rss0, RUNS))
check("no run raised (%d runs)" % RUNS, not errors, errors[:3])
check("the last quarter is not slower than twice the first",
      sorted(last)[len(last) // 2] <= 2 * sorted(first)[len(first) // 2] + 0.5)
check("memory growth under 300 MB over the soak", rss1 - rss0 < 300, rss1 - rss0)
check("every tab drew something (buttons on every run)", all(nb > 0 for nb, _nm in widgets), widgets[:6])
check("the same tab draws the same number of widgets every time",
      all(len({widgets[j] for j in range(len(widgets)) if j % len(TABS) == k and (j % 7 != 3)}) == 1 for k in range(len(TABS))),
      [sorted({widgets[j] for j in range(len(widgets)) if j % len(TABS) == k and (j % 7 != 3)}) for k in range(len(TABS))])

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
