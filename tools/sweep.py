#!/usr/bin/env python3
"""THE SWEEP, RUN BY A MACHINE INSTEAD OF BY EYE.

    python3 tools/sweep.py            # everything under the slow line
    python3 tools/sweep.py --all      # including the slow ones
    python3 tools/sweep.py --baseline # record today's lint count

WHY THIS EXISTS, and it is not a tidying job.

On 25.8.2026 I pushed v224 with a BLANK LINE in the sweep — a suite that
had crashed rather than reported — with that blank line on the screen in
front of me. Four hours after writing the module that names that exact
failure twice:

    face 1  a crash and a pass look equally unlike a failure in a sweep
    §10     does EVERY LINE of the sweep end in a number?

The sweep was a shell loop I typed out each time and read with my eyes.
Twenty lines at midnight, one of them silently short. Eyes are the wrong
instrument for that and no amount of care fixes it, because care is
exactly what runs out at midnight.

WHAT IT REFUSES TO DO, and each refusal is a fault from that day:

    A SUITE WITH NO NUMBER IS A FAILURE, not a blank. Crashing is worse
    than failing, because a failure at least names itself.

    CACHES ARE CLEARED FIRST. A stale __pycache__ produced two fabricated
    blocking defects in a delivery record — a passing suite reporting
    faults that existed nowhere in the source.

    THE LINTER RUNS IN HERE, not beside it. tools/lint_checks.py was
    written, proven and committed, and then not run before the push it
    would have saved. A linter that only runs when you remember is a
    linter for the days you did not need it.

    NEW LINT DEBT BLOCKS; the recorded backlog does not. 163 findings
    exist and mass-editing 137 of them in one pass is how a real fault
    gets swept in with them. So the baseline is written down and any
    INCREASE stops the sweep.

EXIT CODE 0 MEANS EVERY LINE HAD A NUMBER AND EVERY NUMBER WAS ZERO
FAILURES. Nothing else means anything.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TESTS = os.path.join(ROOT, "tests")
BASELINE = os.path.join(HERE, "lint_baseline.json")

# Suites that take minutes. Excluded by default so the sweep is something
# somebody actually runs before every commit — a check nobody runs
# because it is slow is a check that does not exist.
SLOW = {"test_recorder_stress.py"}

PER_SUITE_TIMEOUT = 300

# THREE SUMMARY FORMATS ARE IN USE, and the first version of this only
# knew two. It then reported "NO NUMBER" for two suites that were
# perfectly green — the instrument blaming the thing it was measuring,
# which is exactly the fault this whole tool exists to catch, committed
# into the tool itself on its first run.
#
#     "17 passed, 0 failed"     most of them
#     "22 ok, 0 failed"         the older ones
#     "23 checks, 0 failed"     test_sp_voices
COUNT = re.compile(r"(\d+)\s+(?:passed|ok|checks)\s*,\s*(\d+)\s+failed")

# A SUITE THAT NEEDS SOMETHING THIS MACHINE DOES NOT HAVE is not a
# failure and must not be silently green either. It is reported as
# SKIPPED, with the reason, and it does not block — but it is counted, so
# a growing list of things nobody can run stays visible.
NEEDS = {
    "test_layout.py": "a live server on 8811 (streamlit run app.py "
                      "--server.port 8811)",
    "test_shake.py": "a browser — it measures pixel movement",
}

# SUITES WHOSE SUBJECT NO LONGER EXISTS.
#
# Not skipped because they are slow or need hardware — skipped because
# the FEATURE they test was removed and nobody told them. They reach for
# controls that are not there, and every one of them was dying on [0] of
# an empty list, printing nothing.
#
# NOT DELETED HERE. Deleting somebody's test suite is their decision, and
# delivery-gate §6.2 stages a deletion rather than folding it into
# unrelated work. Listed instead, with the version that removed the
# thing, so the debt is VISIBLE rather than either noisy or silent.
# I LABELLED THESE "STALE" AND I WAS WRONG.
#
# Baba, 25.8.2026, asked what to do with them and then said: "that should
# be kept for studio users." So they are not suites testing a feature
# that was deliberately retired. They are suites STILL DESCRIBING A
# FEATURE THAT IS MEANT TO EXIST — and the feature is what went missing,
# not the test.
#
# Calling them stale invited deleting them, which would have destroyed
# the only written record of what the engine board did: two presses that
# switch every route at once, Edge/Groq for normal and
# Speechify/AssemblyAI/Claude for studio, plus a check-engine button and
# a tier in the corner.
#
# MEASURED: route_stt and route_llm survive in exactly ONE place — the
# list of settings that get persisted. Nothing reads them to choose a
# provider. The board and the routing it drove were removed together, so
# restoring the buttons alone would give a studio user two controls that
# change a value nobody consults.
#
# They do not block, and they must not be deleted.
MISSING = {
    "test_engine_ui.py": "THE ENGINE BOARD, which Baba wants back for "
                         "studio users — eng_normal / eng_studio / "
                         "eng_check, and routing that reads route_*",
    "test_engine_sheet.py": "the same engine board, from the sheet side",
    "test_accounts.py": "the accounts screen — log_out_btn and the "
                        "password section. Ask before deleting: this may "
                        "be wanted for studio users too",
}
REMOVED = MISSING


def _clear_caches():
    n = 0
    for dirpath, dirs, _files in os.walk(ROOT):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
                dirs.remove(d)
                n += 1
    return n


def _run(path, timeout=PER_SUITE_TIMEOUT):
    """(passed, failed, note). `note` is set when there is NO NUMBER."""
    try:
        p = subprocess.run([sys.executable, path], cwd=ROOT,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, None, "TIMED OUT after %ds" % timeout
    out = (p.stdout or "") + "\n" + (p.stderr or "")
    hits = COUNT.findall(out)
    if not hits:
        tail = [l for l in out.strip().splitlines() if l.strip()]
        why = tail[-1].strip()[:70] if tail else "no output at all"
        if "Traceback" in out:
            why = "CRASHED — %s" % why
        return None, None, why
    passed, failed = hits[-1]
    return int(passed), int(failed), ""


def _lint():
    p = subprocess.run([sys.executable, os.path.join(HERE, "lint_checks.py")],
                       cwd=ROOT, capture_output=True, text=True)
    m = re.search(r"(\d+) findings", p.stdout or "")
    return int(m.group(1)) if m else -1


def main(argv):
    want_all = "--all" in argv
    set_baseline = "--baseline" in argv

    print("THE SWEEP — %s" % time.strftime("%Y-%m-%d %H:%M"))
    print("  caches cleared: %d" % _clear_caches())

    lint_now = _lint()
    base = 0
    if os.path.exists(BASELINE):
        try:
            base = json.load(open(BASELINE)).get("findings", 0)
        except Exception:                                    # noqa: BLE001
            base = 0
    if set_baseline:
        json.dump({"findings": lint_now, "when": time.strftime("%Y-%m-%d")},
                  open(BASELINE, "w"), indent=2)
        print("  lint baseline recorded: %d" % lint_now)
        return 0
    print("  lint findings : %d (baseline %d)" % (lint_now, base))

    names = sorted(f for f in os.listdir(TESTS)
                   if f.startswith("test") and f.endswith(".py"))
    if not want_all:
        names = [n for n in names if n not in SLOW]

    print()
    bad_number, bad_missing = [], []
    skipped, stale = [], []
    for n in names:
        if n in NEEDS:
            print("  %-26s SKIPPED — needs %s" % (n[:-3], NEEDS[n]))
            skipped.append(n)
            continue
        if n in REMOVED:
            print("  %-26s MISSING FEATURE — %s" % (n[:-3], REMOVED[n]))
            stale.append(n)
            continue
        passed, failed, note = _run(os.path.join(TESTS, n))
        if note:
            # THE WHOLE POINT. A suite with no number is a FAILURE.
            print("  %-26s NO NUMBER — %s" % (n[:-3], note))
            bad_missing.append(n)
        elif failed:
            print("  %-26s %d passed, %d FAILED" % (n[:-3], passed, failed))
            bad_number.append(n)
        else:
            print("  %-26s %d passed" % (n[:-3], passed))

    print()
    if stale:
        print()
        print("  %d suite(s) DESCRIBE A FEATURE THAT IS MISSING. They do "
              "not block," % len(stale))
        print("  and they are the only record of what it did — do not "
              "delete them:")
        for n in stale:
            print("    %-24s %s" % (n[:-3], REMOVED[n]))
    if skipped:
        print("  skipped, needing something this machine lacks: %d"
              % len(skipped))
    if want_all is False and SLOW:
        print("  not run (slow, use --all): %s"
              % ", ".join(sorted(s[:-3] for s in SLOW)))

    trouble = []
    if bad_missing:
        trouble.append("%d suite(s) produced NO NUMBER: %s"
                       % (len(bad_missing),
                          ", ".join(x[:-3] for x in bad_missing)))
    if bad_number:
        trouble.append("%d suite(s) with failures: %s"
                       % (len(bad_number),
                          ", ".join(x[:-3] for x in bad_number)))
    if lint_now > base:
        trouble.append("lint findings ROSE from %d to %d — new debt, not "
                       "the recorded backlog" % (base, lint_now))

    if not trouble:
        print("  every line had a number, and every number was zero "
              "failures.")
        return 0
    for line in trouble:
        print("  BLOCKED: %s" % line)
    print()
    print("  A suite with no number is worse than one with failures: a")
    print("  failure names itself, a crash does not.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
