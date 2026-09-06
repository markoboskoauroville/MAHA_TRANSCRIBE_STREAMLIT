#!/usr/bin/env python3
"""BUILD A CLEAN secrets.toml FROM A FOLDER OF KEY FILES.

    python3 tools/keys_to_toml.py ~/keys
    python3 tools/keys_to_toml.py ~/keys -o secrets.toml
    python3 tools/keys_to_toml.py ~/keys --dry-run
    python3 tools/keys_to_toml.py ~/keys --keep-empty

Reads every text file in the folder, finds the keys by shape and by
label, TESTS EVERY ONE against its provider, and writes a secrets.toml
containing only the ones that can actually do work.

Baba, 6.9.2026: "He needs to test all the keys in the folder and then
not to write in secrets one which is not working."

---------------------------------------------------------------------
WHAT COUNTS AS "NOT WORKING", AND THE THREE THAT ARE NOT WHAT THEY LOOK
---------------------------------------------------------------------

There are five verdicts, not two, and three of them are traps:

    working    it did the work                       -> WRITTEN
    busy       throttled this minute. HEALTHY.       -> WRITTEN
    no credit  the key is valid, the account is
               alive, the balance is empty           -> dropped, but say so
    refused    401/403: wrong, revoked, mistyped     -> NEVER WRITTEN
    unknown    5xx, 404, no network. Says NOTHING
               about the key                         -> RETRIED, then written

**BUSY IS WRITTEN.** A throttled key is a healthy key having a busy
minute. Dropping it because a test caught it mid-limit would throw away
a perfectly good account.

**UNKNOWN IS RETRIED, NOT DROPPED.** This is the one that matters most
and it is not theoretical: on 6.9.2026 three of Baba's twenty-one Google
keys answered 503 on the first pass -- kalabhumi, mind body and tribal
-- and ALL THREE answered working on the retry. Kalabhumi is the account
every live test that day ran through. A tool that dropped unknowns would
have deleted three live accounts because Google had a bad minute.

So unknown is retried (three times, with a growing pause), and if it is
STILL unknown the key is written anyway with a comment beside it,
because "I could not reach the service" is not evidence against a key.

**NO CREDIT IS DROPPED BUT NAMED.** The account is alive and needs
paying, not deleting -- so its name is printed and `--keep-empty` puts
it back. Never silently.

---------------------------------------------------------------------
WHAT THIS DOES NOT DO
---------------------------------------------------------------------

It does not print a key, ever -- not in the report, not in an error, not
on failure. Positions and account names only.

It does not touch the repository, any ring, or localStorage. It reads a
folder and writes one file where you tell it to.

It does not delete anything at a provider. "Dropped" means "left out of
the file".
"""
import argparse
import hashlib
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from ttt import keyparse as KP                              # noqa: E402
from ttt import providers as PROVIDERS                      # noqa: E402
from ttt.providers import google as G                       # noqa: E402

# Eight at a time. Every probe waits on a network rather than a
# processor, and these are separate ACCOUNTS, so no per-key limit is
# shared. Eight rather than all of them because a burst of twenty-one
# connections from one address is the shape that gets a client blocked.
WORKERS = 8

# Ten braille frames, eight dots inside ONE cell, so the animation
# happens within a single character and the text beside it cannot move.
SPIN = "\u280b\u2819\u2839\u2838\u283c\u2834\u2826\u2827\u2807\u280f"

RETRIES = 3          # for unknown only
BACKOFF = (2, 5, 10)

# Which TOML name each provider's keys go under, and what shape it takes.
# Taken from the app's own SECRET_NAMES; see docs/SECRETS_AUDIT.md.
NAMES = {
    "google": ("GOOGLE_API_KEYS", "list"),
    "groq": ("GROQ_API_KEYS", "list"),
    "assemblyai": ("ASSEMBLYAI_API_KEYS", "list"),
    "speechify": ("SPEECHIFY_API_KEYS", "list"),
    "anthropic": ("ANTHROPIC_API_KEY", "single"),
    "hume": ("HUME_ACCOUNTS", "pairs"),
}

NOTES = {
    "GOOGLE_API_KEYS": [
        "Google's free tier is TEN TTS REQUESTS PER ACCOUNT PER DAY, so",
        "this is a list because it has to be: one account is one",
        "afternoon. QUOTAS ARE PER PROJECT, NOT PER KEY -- two keys from",
        "one Cloud project share one budget. One key per account.",
    ],
    "HUME_ACCOUNTS": [
        "A Hume credential is a PAIR. Both halves are needed: the key",
        "alone does TTS, but only the pair proves the account.",
    ],
    "GROQ_API_KEYS": ["Whisper for speech in, Llama for the text work."],
    "SPEECHIFY_API_KEYS": ["Studio speech out."],
    "ASSEMBLYAI_API_KEYS": ["Studio speech in."],
    "ANTHROPIC_API_KEY": ["Studio text work."],
}

WRITE = ("working", "busy")


def verdict_of(provider_id, key, secret=""):
    """One of the five words, plus the provider's own explanation.

    Every probe asks for REAL WORK, never a listing: keyring.md 2c,
    measured across six providers -- a spent Gemini key answers 200 to
    GET /models and 429 to anything real, so a listing tests validity
    and nothing else.
    """
    prov = PROVIDERS.get(provider_id)
    if prov is None:
        return G.UNKNOWN, "no provider for %s" % provider_id
    try:
        if provider_id == "hume":
            err, kind = prov.test_key(key, secret)
        else:
            err, kind = prov.test_key(key)
    except Exception as e:                                   # noqa: BLE001
        return G.UNKNOWN, str(e)[:120]
    if not err:
        return G.WORKING, ""
    low = str(err).lower()
    # THE MONEY WORDS FIRST, and only unambiguous ones. Each provider
    # picks a different status for "out of credit" -- Hume 400,
    # Speechify 402, Google 429 -- so the WORDS are matched, not the code.
    if any(m in low for m in G.MONEY_MARKS):
        return G.NO_CREDIT, str(err)[:120]
    if kind == "cool":
        return G.BUSY, str(err)[:120]
    if kind == "dead":
        return G.REFUSED, str(err)[:120]
    return G.UNKNOWN, str(err)[:120]


def read_folder(folder):
    """Every key in every text file, de-duplicated, in first-seen order."""
    raw = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        if os.path.splitext(name)[1].lower() not in (
                "", ".txt", ".md", ".text", ".csv", ".toml", ".json"):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                raw.append(fh.read())
        except Exception as e:                               # noqa: BLE001
            print("  could not read %s: %s" % (name, e))
    return KP.extract("\n".join(raw))


def test_all(found, quiet=False):
    """Test every key, in parallel, drawing progress as answers land."""
    # AN ENTRY THE PARSER ALREADY CALLED UNUSABLE IS NOT TESTED.
    # Five of Baba's Hume accounts have no api key in the file at all;
    # sending an empty string to the provider gets a 401, which reads as
    # REFUSED and turns "your file is missing this key" into "this
    # account is dead". That is the exact mistake this parser change
    # exists to stop making.
    todo = [f for f in found
            if f.provider in KP.KNOWN_HERE and getattr(f, "usable", True)]
    results = {}
    done, total = 0, len(todo)
    if not total:
        return results
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(verdict_of, f.provider, f.key,
                               f.secret or ""): f for f in todo}
        # as_completed, not submission order: the name shown must be the
        # one that just finished, not one that answered ten seconds ago.
        for fut in as_completed(futures):
            f = futures[fut]
            try:
                results[f.key] = fut.result()
            except Exception as e:                           # noqa: BLE001
                results[f.key] = (G.UNKNOWN, str(e)[:120])
            done += 1
            if not quiet:
                sys.stdout.write("\r  %s  %-24s %d / %d   " % (
                    SPIN[done % len(SPIN)],
                    (f.label or f.provider)[:24], done, total))
                sys.stdout.flush()
    if not quiet:
        sys.stdout.write("\r  tested %d / %d%s\n" % (total, total, " " * 26))
    return results


def retry_unknown(found, results, quiet=False):
    """Unknown says nothing about the key, so ask again before judging.

    THIS IS NOT DEFENSIVE PROGRAMMING, IT IS A MEASUREMENT. Three of
    twenty-one Google keys answered 503 on the first pass on 6.9.2026 and
    all three answered working on the retry.
    """
    for attempt in range(RETRIES):
        again = [f for f in found
                 if results.get(f.key, (None,))[0] == G.UNKNOWN]
        if not again:
            break
        pause = BACKOFF[min(attempt, len(BACKOFF) - 1)]
        if not quiet:
            print("  %d did not answer -- waiting %ds and asking again "
                  "(try %d of %d)" % (len(again), pause, attempt + 1, RETRIES))
        time.sleep(pause)
        results.update(test_all(again, quiet=quiet))
    return results


def build(found, results, keep_empty=False):
    """The TOML text, and the report rows. Returns (text, rows)."""
    rows, keep = [], []
    for f in found:
        if not getattr(f, "usable", True):
            # NOT A VERDICT ABOUT THE ACCOUNT. The file is incomplete,
            # and saying so is more useful than any test result.
            rows.append((f, "incomplete", f.problem, False))
            continue
        if f.provider not in KP.KNOWN_HERE:
            rows.append((f, "not used here", "", False))
            continue
        v, detail = results.get(f.key, (G.UNKNOWN, "never tested"))
        if v in WRITE:
            written = True
        elif v == G.NO_CREDIT:
            written = bool(keep_empty)
        elif v == G.UNKNOWN:
            # STILL UNKNOWN AFTER THREE TRIES. Written anyway: "I could
            # not reach the service" is not evidence against a key, and
            # dropping on it is how a live account is lost to somebody
            # else's bad afternoon.
            written = True
        else:                                     # refused
            written = False
        rows.append((f, v, detail, written))
        if written:
            keep.append((f, v))

    groups = {}
    for f, v in keep:
        groups.setdefault(f.provider, []).append((f, v))

    out = ["# Generated by tools/keys_to_toml.py on %s."
           % time.strftime("%Y-%m-%d %H:%M"),
           "# Only keys that answered are here. Paste into Streamlit",
           "# Cloud -> Settings -> Secrets. Never commit this file.",
           "#",
           "# ADD YOUR OWN ACCESS LINES -- this tool does not invent them:",
           '#   ADMIN_USER1  = "..."',
           '#   FREE_USER1   = "..."',
           '#   APP_PASSWORDS = ["...", "..."]',
           "# See docs/SECRETS_AUDIT.md for every name this app reads.",
           ""]
    for pid, (name, shape) in NAMES.items():
        items = groups.get(pid) or []
        if not items:
            continue
        for line in NOTES.get(name, ()):
            out.append("# " + line)
        if shape == "pairs":
            for f, v in items:
                out.append("[[%s]]" % name)
                out.append('name = "%s"' % (f.label or "account"))
                out.append('key = "%s"' % f.key)
                out.append('secret = "%s"' % (f.secret or ""))
                out.append("")
            continue
        if shape == "single":
            f, v = items[0]
            out.append('%s = "%s"' % (name, f.key))
            if len(items) > 1:
                out.append("# %d more working key(s) found; this name "
                           "takes only one." % (len(items) - 1))
        else:
            out.append("%s = [" % name)
            for f, v in items:
                tail = "  # %s" % f.label if f.label else ""
                if v == G.BUSY:
                    tail += "  (was busy when tested -- healthy)"
                if v == G.UNKNOWN:
                    tail += "  (could not be reached -- kept, unproven)"
                out.append('    "%s",%s' % (f.key, tail))
            out.append("]")
        out.append("")
    return "\n".join(out).rstrip() + "\n", rows


def report(rows):
    print()
    print("  %-11s %-22s %-11s %s" % ("provider", "account", "verdict",
                                      "written"))
    print("  " + "-" * 60)
    for f, v, detail, written in rows:
        print("  %-11s %-22s %-11s %s" % (
            f.provider, (f.label or "-")[:22], v, "yes" if written else "NO"))
        if detail and not written:
            print("      %s" % detail[:70])
    counts = {}
    for _f, v, _d, _w in rows:
        counts[v] = counts.get(v, 0) + 1
    print()
    print("  " + "  ".join("%s: %d" % (k, counts[k]) for k in sorted(counts)))
    print("  written: %d of %d" % (sum(1 for r in rows if r[3]), len(rows)))
    incomplete = [(f.label or "(unnamed)", d) for f, v, d, _w in rows
                  if v == "incomplete"]
    if incomplete:
        print()
        print("  %d account(s) named in the file have NO USABLE KEY IN IT."
              % len(incomplete))
        print("  These are NOT failed tests — nothing was tested, because")
        print("  there was nothing to test. The account may be perfectly")
        print("  fine; go back to the provider's dashboard and copy the")
        print("  key again.")
        for name, why in incomplete:
            print("    %-24s %s" % (name, why))
    dropped = [f.label or f.provider for f, v, _d, w in rows
               if not w and v not in ("not used here", "incomplete")]
    if dropped:
        print("  LEFT OUT, by name: %s" % ", ".join(dropped))
        print("  Out-of-credit accounts are ALIVE -- topping one up makes")
        print("  the same key work again. --keep-empty puts them back.")


def write_report(path, rows, out_path, wrote_text, folder):
    """A report a person can paste to somebody else. NO KEY MATERIAL.

    Baba, 6.9.2026: the Claude Code session should report back, and that
    report gets assessed. So the FACTUAL half is generated here rather
    than written from memory — four-tests.md: "find a number the outside
    world will confirm." A session can misremember what it did; a digest
    and a set of counts cannot.

    WHAT IS DELIBERATELY ABSENT: every key, every secret, every masked
    fragment of one. Account NAMES are present, because "kalabhumi is
    unpaid" is actionable and "key 7 of 21" is not, and a name leaks
    nothing. The report is asserted key-free before it is written.
    """
    counts = {}
    for _f, v, _d, _w in rows:
        counts[v] = counts.get(v, 0) + 1
    written = [f for f, _v, _d, w in rows if w]
    per_provider = {}
    for f in written:
        per_provider[f.provider] = per_provider.get(f.provider, 0) + 1

    L = []
    L.append("# SECRETS BUILD REPORT")
    L.append("")
    L.append("Generated by `tools/keys_to_toml.py` on %s."
             % time.strftime("%Y-%m-%d %H:%M"))
    L.append("This file contains NO key material and is safe to paste.")
    L.append("")
    L.append("## What was read")
    L.append("")
    L.append("    folder            %s" % os.path.abspath(folder))
    L.append("    credentials found %d" % len(rows))
    for pid in sorted(per_provider):
        L.append("    written, %-9s %d" % (pid, per_provider[pid]))
    L.append("")
    L.append("## Verdicts")
    L.append("")
    for k in sorted(counts):
        L.append("    %-14s %d" % (k, counts[k]))
    L.append("")
    L.append("## Not written, by name")
    L.append("")
    any_out = False
    for f, v, d, w in rows:
        if w or v == "not used here":
            continue
        any_out = True
        L.append("    %-24s %-12s %s" % (f.label or "(unnamed)", v, d[:60]))
    if not any_out:
        L.append("    nothing — every credential found was written")
    L.append("")
    L.append("## The file")
    L.append("")
    if wrote_text is None:
        L.append("    --dry-run: no file was written")
    else:
        L.append("    path      %s" % os.path.abspath(out_path))
        L.append("    bytes     %d" % len(wrote_text))
        L.append("    sha256    %s"
                 % hashlib.sha256(wrote_text.encode("utf-8")).hexdigest())
        try:
            import tomllib
            d = tomllib.loads(wrote_text)
            for k, v in sorted(d.items()):
                L.append("    %-22s %s" % (
                    k, "%d entries" % len(v) if isinstance(v, list) else "set"))
            L.append("    parses as TOML: yes")
        except Exception as e:                               # noqa: BLE001
            L.append("    parses as TOML: NO — %s" % e)
    L.append("")
    L.append("## What the session must add below this line")
    L.append("")
    L.append("- which access lines were filled in, and from where")
    L.append("- anything in the folder that was NOT a key file")
    L.append("- any decision taken without asking, and why")
    L.append("- WHAT WAS NOT DONE, as plainly as what was")
    L.append("")
    text = "\n".join(L) + "\n"

    # PROVE IT BEFORE WRITING IT. A report that leaked a key would be
    # pasted into a chat by somebody trusting this line.
    for f, _v, _d, _w in rows:
        for material in (f.key, f.secret):
            if material and len(material) >= 8 and material in text:
                raise SystemExit(
                    "REFUSED to write the report: it contains key "
                    "material for %s" % (f.label or f.provider))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, 0o600)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", help="folder holding the key files")
    ap.add_argument("-o", "--out", default="secrets.toml")
    ap.add_argument("--dry-run", action="store_true",
                    help="test and report, write nothing")
    ap.add_argument("--keep-empty", action="store_true",
                    help="include out-of-credit accounts too")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--report", default="REPORT.md",
                    help="where to write the key-free build report")
    a = ap.parse_args(argv)

    if not os.path.isdir(a.folder):
        print("Not a folder: %s" % a.folder)
        return 2

    found = read_folder(a.folder)
    if not found:
        # A ZERO IS A FAILURE OF THE CHECK UNTIL PROVEN OTHERWISE. An
        # empty result almost always means an unrecognised format, not
        # an empty folder, so say what to look at -- WITHOUT printing
        # any of it.
        print("No keys found in %s." % a.folder)
        print("That usually means a format the parser does not know, not")
        print("an empty folder. Check lengths and prefixes, never content:")
        print("  awk '{print length($0), substr($0,1,4)}' <file> | sort -u")
        return 1

    by = KP.by_provider(found)
    print("  found: " + ",  ".join("%s %d" % (p, len(v))
                                   for p, v in sorted(by.items())))
    results = test_all(found, quiet=a.quiet)
    results = retry_unknown(found, results, quiet=a.quiet)
    text, rows = build(found, results, keep_empty=a.keep_empty)
    report(rows)

    if a.dry_run:
        write_report(a.report, rows, a.out, None, a.folder)
        print("\n  --dry-run: no secrets written.")
        print("  report: %s" % a.report)
        return 0
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(a.out, 0o600)
    print("\n  wrote %s (%d bytes, mode 600)" % (a.out, len(text)))
    # PROVE IT PARSES BEFORE HE PASTES IT. A block Streamlit rejects
    # fails at import with a message Cloud REDACTS, so he would see a
    # broken app and no reason.
    try:
        import tomllib
        with open(a.out, "rb") as fh:
            d = tomllib.load(fh)
        print("  it parses as TOML: %s" % ", ".join(
            "%s=%s" % (k, len(v) if isinstance(v, list) else "set")
            for k, v in d.items()))
    except Exception as e:                                   # noqa: BLE001
        print("  *** IT DOES NOT PARSE: %s" % e)
        print("  *** Do not paste this. Fix it first.")
        write_report(a.report, rows, a.out, text, a.folder)
        return 1
    write_report(a.report, rows, a.out, text, a.folder)
    print("  report: %s  (no key material — safe to paste)" % a.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
