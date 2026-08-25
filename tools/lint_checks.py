#!/usr/bin/env python3
"""A CHECK ON THE CHECKS.

    python3 tools/lint_checks.py            # the tests/ directory
    python3 tools/lint_checks.py path ...   # anything else

Four of the eight faces in MANTRA_MANIFEST/modules/checking-the-checks.md
are SHAPES rather than judgement, so a script can find them. This is that
script.

WHY IT EXISTS. On 25.8.2026 all eight faces were met in one day, in one
codebase, by one author being careful. Careful was not enough: each was
met fresh because nothing had written it down, and two of them nearly put
fabricated blocking defects into a delivery record.

WHAT IT CANNOT DO. Faces 2, 4, 7 and 8 need judgement — whether a check
matches its own comment, whether a count is standing in for a claim,
whether the caches were clear, whether the rule being tested is the rule
that was wanted. Those stay in the checklist. A linter that pretended to
cover them would be the very fault it is looking for.

IT FAILS LOUDLY AND EXITS NON-ZERO, so it can sit in the same sweep as
the tests. A linter that only runs when you remember is a linter for the
days you did not need it.
"""
import os
import re
import sys

# ---------------------------------------------------------------------
# FACE 1 — index() crashes, find() reports
#
# str.index RAISES when the thing is missing. In a test with no harness
# that kills the process, so every check after it never runs and the
# sweep prints NO NUMBER AT ALL for that suite. A crash and a pass look
# equally unlike a failure.
# ---------------------------------------------------------------------
INDEX_CALL = re.compile(r"\.index\(")

# ---------------------------------------------------------------------
# FACE 5 — a mutation that did not change the file
#
# A sed whose pattern misses exits 0 and changes nothing; the tests then
# pass because the code is untouched, and that reads exactly like proof
# the check is useless.
# ---------------------------------------------------------------------
WRITE_CALL = re.compile(r"open\(\s*[^)]*?['\"]w['\"]")

# ---------------------------------------------------------------------
# FACE 6 — a slice that covers nothing
#
# `tab[tab.index(A):tab.index(B)]` is the empty string when B is defined
# ABOVE A, and `"x" not in ""` is True. The check then passes on nothing.
# ---------------------------------------------------------------------
SLICE_PAIR = re.compile(
    r"(\w+)\s*\[\s*\1\.(?:index|find)\(([^)]+)\)\s*:\s*\1\.(?:index|find)\(([^)]+)\)\s*\]")

# ---------------------------------------------------------------------
# FACE 3 — a marker that its own definition contains
#
# `def foo():` contains `foo()`, so "is it called?" silently becomes
# "is it defined?" and survives the call being deleted.
# ---------------------------------------------------------------------
BARE_CALL = re.compile(r"""["'](\w+)\(\)["']""")


def _lines(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().splitlines()


def _is_comment(line):
    t = line.strip()
    return t.startswith("#") or not t


def check_file(path):
    """Every finding in one file as (line_no, face, message, source)."""
    out = []
    lines = _lines(path)
    text = "\n".join(lines)

    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue

        # FACE 1
        if INDEX_CALL.search(line) and "# lint:ok" not in line:
            out.append((i, "1", "index() raises when missing — the file "
                        "dies instead of reporting. Use find() and assert "
                        "the result is > 0.", line.strip()))

        # FACE 3
        for m in BARE_CALL.finditer(line):
            name = m.group(1)
            if ("def %s(" % name) in text and "# lint:ok" not in line:
                out.append((i, "3", "the marker %r is contained in its own "
                            "'def %s(' — this asks whether it is DEFINED, "
                            "not whether it is CALLED. Anchor on a leading "
                            "newline or an indent." % (name + "()", name),
                            line.strip()))

        # FACE 6
        for m in SLICE_PAIR.finditer(line):
            out.append((i, "6", "a slice bounded by two searches: assert "
                        "the bounds are ORDERED and the region is neither "
                        "empty nor enormous, and print its length. %s "
                        "before %s?" % (m.group(2).strip(), m.group(3).strip()),
                        line.strip()))

    # FACE 5 — a file that WRITES source must assert its target first.
    # Scoped to whole files rather than lines: the assert is usually a few
    # lines above the write.
    if WRITE_CALL.search(text) and ".replace(" in text:
        if "assert " not in text and "# lint:ok" not in text:
            out.append((0, "5", "this file rewrites source with .replace() "
                        "and never asserts the target exists. A pattern "
                        "that misses changes nothing and the tests then "
                        "pass for the wrong reason.", "(whole file)"))
    return out


def main(argv):
    roots = argv[1:] or ["tests"]
    paths = []
    for root in roots:
        if os.path.isfile(root):
            paths.append(root)
            continue
        for dirpath, _dirs, files in os.walk(root):
            if "__pycache__" in dirpath:
                continue
            for f in sorted(files):
                if f.endswith(".py"):
                    paths.append(os.path.join(dirpath, f))

    findings = []
    for p in sorted(set(paths)):
        for f in check_file(p):
            findings.append((p,) + f)

    print("A CHECK ON THE CHECKS — %d files examined" % len(set(paths)))
    print("  faces looked for: 1 index() · 3 self-containing marker · "
          "5 unasserted mutation · 6 unbounded slice")
    print("  faces NOT lintable, see the checklist: 2 matches its own "
          "comment · 4 a count is not a check · 7 stale bytecode · "
          "8 tests the code not the rule")
    print()

    if not findings:
        print("  %d findings." % 0)
        print("  A zero here is a failure of THIS script until proven "
              "otherwise. Break a check on purpose and watch it appear.")
        return 0

    by_face = {}
    for f in findings:
        by_face.setdefault(f[2], []).append(f)
    for face in sorted(by_face):
        print("  FACE %s — %d" % (face, len(by_face[face])))
        for path, line, _face, msg, src in by_face[face]:
            where = "%s:%s" % (path, line) if line else path
            print("    %s" % where)
            print("      %s" % msg)
            if src != "(whole file)":
                print("      | %s" % src[:88])
        print()
    print("  %d findings. Each is a check that may pass while proving "
          "nothing." % len(findings))
    print("  If one is deliberate and correct, put  # lint:ok  on the line "
          "and say why.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
