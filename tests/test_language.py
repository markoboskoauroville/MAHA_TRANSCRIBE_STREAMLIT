"""THE LANGUAGE THAT REACHES WHISPER.

AUTO returned nothing at all. The reason was not the setting: it was
that "auto" was being SENT to Whisper, which is a 400 — and the key
rotation then burned through every key and returned an empty string, so
the screen showed nothing and named no fault.

v118 fixed exactly this in ttt/providers/groq.py, and it changed
nothing, because the path a recording actually takes never goes near
that file. app.py has its OWN copy of the Groq call. One implementation
in the module, used from everywhere, is the rule; the cost of breaking
it was a fix that read as complete and did nothing.

Nothing tested the SHAPE of the call, which is why a wrong shape shipped
twice.

    python3 tests/test_language.py
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


HERE = os.path.dirname(__file__)
APP = open(os.path.join(HERE, "..", "app.py"), encoding="utf-8").read()
GROQ = open(os.path.join(HERE, "..", "ttt", "providers", "groq.py"),
            encoding="utf-8").read()

print("THE LANGUAGE THAT REACHES WHISPER\n")

# --- every place that calls Whisper must guard "auto" ------------------
#
# A SOURCE CHECK because there is no key here and the failure was in the
# request itself. What matters is that no call site can send "auto".
calls = []
for name, src in (("app.py", APP), ("ttt/providers/groq.py", GROQ)):
    for m in re.finditer(r"audio\.transcriptions\.create\(", src):
        # the 400 characters before the call carry its keyword building
        calls.append((name, src[max(0, m.start() - 700):m.start()]))

check("1 the Whisper call sites are found", len(calls) >= 2,
      [n for n, _ in calls])

for name, before in calls:
    check("2 %s guards against sending 'auto'" % name,
          'language != "auto"' in before, before[-200:])
    check("3 %s omits the parameter rather than sending an empty one"
          % name, 'if language and' in before, before[-200:])


# --- the shape itself, exercised ---------------------------------------
def build(language):
    """The same rule both call sites use, so the behaviour can be run
    rather than only read."""
    kw = {"file": ("t.flac", b""), "model": "m",
          "response_format": "text", "temperature": 0.0}
    if language and language != "auto":
        kw["language"] = language
    return kw


check("4 AUTO sends NO language — Whisper then detects it",
      "language" not in build("auto"))
check("5 an empty setting does the same", "language" not in build(""))
check("6 None does the same", "language" not in build(None))
check("7 HR sends hr", build("hr").get("language") == "hr")
check("8 ENG sends en", build("en").get("language") == "en")

# --- the setting the app stores ----------------------------------------
check("9 the app offers exactly three languages",
      all(('args=("%s",)' % c) in APP for c in ("auto", "hr", "en")))
check("10 and AUTO is one of them, stored as 'auto'",
      'args=("auto",)' in APP)

# --- AssemblyAI spells it its own way ----------------------------------
AAI = open(os.path.join(HERE, "..", "ttt", "providers", "assemblyai.py"),
           encoding="utf-8").read()
check("11 AssemblyAI turns 'auto' into its own language_detection flag, "
      "rather than the app knowing how each engine spells it",
      'language == "auto"' in AAI and "language_detection" in AAI)

print("\n{} passed, {} failed".format(passed, failed))

if __name__ == "__main__":
    sys.exit(1 if failed else 0)


def test_language():
    assert failed == 0, "%d of %d checks failed" % (failed, passed + failed)
