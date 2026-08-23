#!/usr/bin/env python3
"""FILL apps_script/Code.gs FROM YOUR SECRETS FILE, AND CHECK IT.

Baba: "I am lost in this, too many codes, too much lines for me."

This exists because a deploy went wrong in exactly the way that is
hardest to see: `git stash` said "No local changes to save", which
meant the working copy already matched the repo — so `assume-unchanged`
had been hiding a CLEAN file, not a filled-in one. The three secrets
were placeholders and nothing said so. Pasting that into the live
editor would have taken down the sheet, Drive and every recording.

    python3 tools/fill_gs.py            # fill and report
    python3 tools/fill_gs.py --check    # report only, change nothing

IT WRITES TO A COPY, never to the tracked file. `apps_script/Code.filled.gs`
is what you paste; `apps_script/Code.gs` stays as it is in git, with its
placeholders, so it can never be committed with real secrets in it.
That is the opposite of the assume-unchanged trick, which tried to keep
a secret-bearing file invisible and failed silently.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SRC = os.path.join(ROOT, "apps_script", "Code.gs")
OUT = os.path.join(ROOT, "apps_script", "Code.filled.gs")

# Where to look for the values, in order. The first file that exists
# wins. All are gitignored.
CANDIDATES = [
    os.path.join(ROOT, "secrets_streamlit.txt"),
    os.path.join(ROOT, ".streamlit", "secrets.toml"),
    os.path.expanduser("~/Desktop/TTT-BACKUP/AUTH_SECRETS.txt"),
]

# The three the main script needs, and the placeholder each still has.
WANTED = ["SHEETS_TOKEN", "DRIVE_SECRET", "DRIVE_ROOT_ID"]

PLACEHOLDERS = ("CHANGE_ME", "PUT_YOUR", "PASTE_", "REPLACE_", "")


def read_values(path):
    """Pull KEY = "value" or KEY: value out of a text or toml file."""
    found = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r'^([A-Z_][A-Z0-9_]*)\s*[:=]\s*(.+)$', line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            val = val.rstrip(",")
            if val[:1] in "\"'" and val[-1:] == val[:1]:
                val = val[1:-1]
            if val:
                found[key] = val
    return found


def looks_real(value):
    if not value:
        return False
    up = value.upper()
    return not any(p and up.startswith(p) for p in PLACEHOLDERS)


def main():
    check_only = "--check" in sys.argv

    src = open(SRC, encoding="utf-8").read()

    # WHAT THE TRACKED FILE CURRENTLY HOLDS. Reported first, because
    # this is the thing that was invisible: a file full of placeholders
    # looks exactly like a file full of secrets from the outside.
    print("apps_script/Code.gs as tracked:")
    current = {}
    for key in WANTED:
        m = re.search(r"^var %s = '([^']*)';" % key, src, re.M)
        current[key] = m.group(1) if m else None
        state = ("MISSING" if current[key] is None
                 else "real" if looks_real(current[key]) else "PLACEHOLDER")
        print("  %-14s %s" % (key, state))

    source = next((p for p in CANDIDATES if os.path.exists(p)), None)
    if not source:
        print("\nNo secrets file found. Looked in:")
        for p in CANDIDATES:
            print("  " + p)
        return 1

    print("\nreading values from: %s" % source)
    vals = read_values(source)

    missing = [k for k in WANTED if not looks_real(vals.get(k, ""))]
    for key in WANTED:
        got = vals.get(key, "")
        print("  %-14s %s" % (key, "found" if looks_real(got) else "NOT FOUND"))

    if missing:
        print("\nCannot fill: %s not in that file." % ", ".join(missing))
        print("Add them as  NAME = value  (one per line) and run again.")
        return 1

    if check_only:
        print("\n--check: nothing written.")
        return 0

    out = src
    for key in WANTED:
        out = re.sub(r"^var %s = '[^']*';" % key,
                     "var %s = '%s';" % (key, vals[key]), out, count=1, flags=re.M)

    # VERIFY WHAT WAS WRITTEN, rather than trusting the substitution.
    # A regex that misses leaves the placeholder in place and reports
    # success — which is precisely how the last deploy went wrong.
    bad = []
    for key in WANTED:
        m = re.search(r"^var %s = '([^']*)';" % key, out, re.M)
        if not m or m.group(1) != vals[key]:
            bad.append(key)
    if bad:
        print("\nSubstitution did not land for: %s" % ", ".join(bad))
        print("Nothing written.")
        return 1

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(out)

    print("\nwrote apps_script/Code.filled.gs  —  all three verified in it")
    print("PASTE THAT FILE, not Code.gs.")
    print("\n  open %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
