"""NO COMPONENT MAY LOOK UP AN ELEMENT THAT IS NOT THERE.

This has killed a frame twice.

v101: a label constant was declared in the WRONG component, so
setRecording() threw "L_STOP is not defined" on the first press and took
the meter, the clock and the message line with it — while the button
still toggled, which is why it looked like it worked.

v121: the cut and line BUTTONS were removed and their ids left in a
forEach, so getElementById returned null, addEventListener threw, the
script died before ready() was ever sent, and Streamlit showed "trouble
loading the app.ttt_note component". The editor was simply absent and
pressing rec did nothing, because nothing was listening.

Both are the same shape: markup and script drifting apart, with no test
between them. A JavaScript exception fails nothing on its own — it just
quietly removes half the feature.

    python3 tests/test_components.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


ROOT = os.path.join(os.path.dirname(__file__), "..")
FRONTENDS = [d for d in sorted(os.listdir(ROOT))
             if d.endswith("_frontend")
             and os.path.isfile(os.path.join(ROOT, d, "index.html"))]

print("EVERY COMPONENT'S SCRIPT AGAINST ITS OWN MARKUP\n")

check("1 the components are found", len(FRONTENDS) >= 3, FRONTENDS)

for name in FRONTENDS:
    src = open(os.path.join(ROOT, name, "index.html"), encoding="utf-8").read()

    ids = set(re.findall(r'id="([A-Za-z0-9_-]+)"', src))
    looked = set(re.findall(r"getElementById\(['\"]([A-Za-z0-9_-]+)['\"]\)", src))
    missing = sorted(looked - ids)
    check("2 %s looks up nothing that is missing from its markup" % name,
          not missing, missing)

    # A stray console.log is debug scaffolding that got shipped. v121
    # found three of them still in note_frontend from the v101 hunt.
    logs = len(re.findall(r"console\.log\(", src))
    check("3 %s ships no debug logging" % name, logs == 0, logs)

    # Every frame must announce itself, or Streamlit waits forever and
    # then reports that it cannot load the component.
    check("4 %s tells Streamlit it is ready" % name,
          "componentReady" in src, "no componentReady")

    # The script must at least parse. A syntax error is the same class of
    # failure: nothing renders and the app says only that it cannot load.
    script = src.split("<script>", 1)[-1].split("</script>", 1)[0]
    check("5 %s has balanced braces in its script" % name,
          script.count("{") == script.count("}"),
          "%d open, %d close" % (script.count("{"), script.count("}")))

print("\n{} passed, {} failed".format(passed, failed))

if __name__ == "__main__":
    sys.exit(1 if failed else 0)


def test_components():
    assert failed == 0, "%d of %d checks failed" % (failed, passed + failed)
