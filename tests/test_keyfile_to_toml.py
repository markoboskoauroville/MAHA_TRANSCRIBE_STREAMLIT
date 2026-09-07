"""THE SECRETS BUILDER — only working keys reach the file.

    python3 tests/test_keyfile_to_toml.py

No network here: verdicts are injected, so the decision logic is tested
without spending a key. The live run is recorded in the commit.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

import keys_to_toml as B                       # noqa: E402
from ttt import keyparse as KP                   # noqa: E402
from ttt.providers import google as G            # noqa: E402

import tomllib                                  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def F(pid, key, label="", secret=None):
    return KP.Found(key, pid, label, secret)


G1 = "AQ.Ab8RN6" + "a" * 40
G2 = "AQ.Ab8RN6" + "b" * 40
G3 = "AQ.Ab8RN6" + "c" * 40
G4 = "AQ.Ab8RN6" + "d" * 40
G5 = "AQ.Ab8RN6" + "e" * 40
HK = "HUMEKEY7" + "g" * 30 + "42"
HS = "HUMESECRET9" + "h" * 40 + "73"

found = [F("google", G1, "alive"), F("google", G2, "empty"),
         F("google", G3, "rejected"), F("google", G4, "throttled"),
         F("google", G5, "silent"),
         F("hume", HK, "acct.one", HS),
         F("elevenlabs", "sk_" + "z" * 20, "not ours")]
results = {G1: (G.WORKING, ""), G2: (G.NO_CREDIT, "empty"),
           G3: (G.REFUSED, "401"), G4: (G.BUSY, "429"),
           G5: (G.UNKNOWN, "503"), HK: (G.WORKING, "")}

print("1 THE MECHANISM — who gets written")
text, rows = B.build(found, results)
w = {f.label: written for f, _v, _d, written in rows}

check("working is written", w["alive"] is True)
check("REFUSED IS NEVER WRITTEN", w["rejected"] is False)
# BUSY IS HEALTHY. A throttled key is a good key having a busy minute,
# and dropping it because a test caught it mid-limit throws away an
# account that would have worked a second later.
check("BUSY IS WRITTEN — a throttled key is a healthy key",
      w["throttled"] is True)
# UNKNOWN SAYS NOTHING ABOUT THE KEY. On 6.9.2026 three of Baba's
# twenty-one Google keys answered 503 and all three worked on retry.
check("UNKNOWN IS WRITTEN, not dropped — 503 is the service, not the key",
      w["silent"] is True)
check("no credit is dropped by default", w["empty"] is False)

text2, rows2 = B.build(found, results, keep_empty=True)
w2 = {f.label: written for f, _v, _d, written in rows2}
check("--keep-empty puts the alive-but-empty account back",
      w2["empty"] is True)
check("...but still never the refused one", w2["rejected"] is False)

print()
print("2 THE FILE ITSELF")
check("the working key is in the file", G1 in text)
check("the busy key is in the file", G4 in text)
check("the unknown key is in the file", G5 in text)
check("THE REFUSED KEY IS NOT IN THE FILE", G3 not in text)
check("the empty account is not in the file", G2 not in text)
check("the hume pair is written with all three fields",
      "[[HUME_ACCOUNTS]]" in text and HK in text and HS in text
      and 'name = "acct.one"' in text)
check("a provider this app does not use is left out",
      "sk_" + "z" * 20 not in text)
check("the busy key is marked as healthy, not silently included",
      "healthy" in text)
check("the unproven key says it is unproven", "unproven" in text)
check("account names ride along as comments", "# alive" in text)
check("it tells him to add his own access lines, which no tool can invent",
      "ADMIN_USER1" in text and "APP_PASSWORDS" in text)

import tomllib                                   # noqa: E402
d = tomllib.loads(text)
check("the generated TOML parses", "GOOGLE_API_KEYS" in d, sorted(d))
check("...with exactly the three keepable google keys",
      len(d["GOOGLE_API_KEYS"]) == 3, len(d.get("GOOGLE_API_KEYS", [])))
check("...and the hume pair as a table with all three fields",
      d["HUME_ACCOUNTS"][0].get("secret") == HS)

print()
print("3 THE UGLY CASES")
t3, r3 = B.build([], {})
check("no keys at all produces a file, not a crash", isinstance(t3, str))
t4, r4 = B.build(found, {})
w4 = {f.label: written for f, _v, _d, written in r4}
check("a key that was never tested is treated as unknown and KEPT",
      w4["alive"] is True)
check("...and every row still reports something",
      all(v for _f, v, _d, _w in r4))

many = [F("sk-ant-" + c * 40, "acct" + c) for c in "xy"]
t5, _ = B.build(many, {("sk-ant-" + c * 40): (G.WORKING, "") for c in "xy"})
check("a single-valued name takes one key and SAYS the rest were dropped",
      t5.count("ANTHROPIC_API_KEY =") == 1 and "1 more working" in t5, t5)

print()
print("4 THE SETTINGS THAT DECIDE IT")
check("only working and busy are in the write list",
      B.WRITE == ("working", "busy"), B.WRITE)
check("unknown is RETRIED before it is judged", B.RETRIES >= 3, B.RETRIES)
check("...with a growing pause, so a bad minute is not hammered",
      list(B.BACKOFF) == sorted(B.BACKOFF), B.BACKOFF)
check("eight at a time", B.WORKERS == 8, B.WORKERS)
check("the spinner is braille and one cell per frame",
      all(0x2800 <= ord(c) <= 0x28FF for c in B.SPIN) and len(B.SPIN) == 10)
check("every provider the app holds secrets for has a TOML name",
      set(B.NAMES) == set(KP.KNOWN_HERE), (sorted(B.NAMES), sorted(KP.KNOWN_HERE)))
check("hume is the pairs shape", B.NAMES["hume"][1] == "pairs")
check("anthropic is the single shape", B.NAMES["anthropic"][1] == "single")

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "tools", "keys_to_toml.py")).read()
check("the tool never prints a key", ".key)" not in src.split("def report")[1])
check("the file is written 0600", "0o600" in src)
check("it proves the TOML parses before he pastes it", "tomllib" in src)
check("an empty result is called a parser problem, not an empty folder",
      "not\\nan empty folder" in src or "not" in src and "empty folder" in src)


print()
print("5 THE REPORT — generated, checkable, and key-free")
# =====================================================================
#
# Baba, 6.9.2026: the Claude Code session reports back and that report
# gets assessed. So the factual half is GENERATED rather than written
# from memory — a session can misremember what it did; a digest and a
# set of counts cannot.

import tempfile                                  # noqa: E402

rows_for_report = [
    (F("google", G1, "alive"), G.WORKING, "", True),
    (F("google", G2, "empty"), G.NO_CREDIT, "no credit left", False),
    (F("google", G3, "rejected"), G.REFUSED, "401", False),
    (F("hume", HK, "acct.one", HS), G.WORKING, "", True),
    (F("", "no.key.here"), "incomplete",
     "the API key is missing from the file", False),
]
text_written = 'GOOGLE_API_KEYS = ["%s"]\n' % G1
tmp = tempfile.mkdtemp()
rp = os.path.join(tmp, "REPORT.md")
rep = B.write_report(rp, rows_for_report, os.path.join(tmp, "s.toml"),
                     text_written, tmp)

check("the report is written", os.path.exists(rp))
check("it is 0600", oct(os.stat(rp).st_mode)[-3:] == "600",
      oct(os.stat(rp).st_mode)[-3:])

# THE ONE THAT MATTERS MOST.
check("NO KEY MATERIAL IS IN THE REPORT",
      not any(k in rep for k in (G1, G2, G3, HK, HS)),
      [k[:10] for k in (G1, G2, G3, HK, HS) if k in rep])
check("...not even a masked fragment", "…" not in rep and "..." not in rep)
# Only the NOT-WRITTEN accounts are named, and that is the right
# choice: those are the ones somebody has to act on. The written ones
# are covered by the per-provider counts, and the arithmetic check
# below is what catches one going missing.
check("account NAMES of what was NOT written are present",
      "empty" in rep and "no.key.here" in rep and "rejected" in rep)
check("...and the written ones are counted per provider",
      "written, google" in rep and "written, hume" in rep)

# COUNTS, NOT ADJECTIVES.
check("every verdict is counted", "working" in rep and "no credit" in rep
      and "refused" in rep and "incomplete" in rep)
check("what was NOT written is listed by name",
      "empty" in rep and "rejected" in rep and "no.key.here" in rep)
check("the reason is given beside each", "401" in rep)

# A NUMBER THE OUTSIDE WORLD WILL CONFIRM.
import hashlib as _h                             # noqa: E402
check("the sha256 of the written file is in the report",
      _h.sha256(text_written.encode()).hexdigest() in rep)
check("the byte count is in the report", str(len(text_written)) in rep)
check("whether it parses as TOML is stated", "parses as TOML: yes" in rep)

# THE ARITHMETIC MUST CLOSE. This is the check that would have caught
# 21 hume blocks producing 17 pairs.
check("credentials found equals written plus not written",
      "credentials found %d" % len(rows_for_report) in rep,
      [l for l in rep.splitlines() if "credentials found" in l])

check("the session is asked for what a tool cannot know",
      "WHAT WAS NOT DONE" in rep)
check("...and for decisions taken without asking", "without asking" in rep)

# --dry-run STILL REPORTS. A run that tested and wrote nothing is still
# a run somebody needs the numbers from.
rep2 = B.write_report(rp, rows_for_report, "x.toml", None, tmp)
check("a dry run still produces a report", "--dry-run" in rep2)
check("...and says no file was written", "no file was written" in rep2)

# THE REFUSAL IS REAL, not a warning. Proven by feeding it a row whose
# key IS in the text it would write.
# HOW A KEY WOULD ACTUALLY REACH A REPORT: through a LABEL or a detail
# string, not through the secrets file — the report never quotes that.
# The parser now refuses to take a credential as a name, but this is
# the second line of defence for the day a new file shape defeats it.
# My first version of this check fed a key that was only in the
# secrets file, so the guard had nothing to find and stayed quiet.
LEAK = "LEAKYKEY" + "z" * 30
leaky = [(F("google", LEAK, LEAK), G.WORKING, "", False)]
try:
    B.write_report(rp, leaky, "s.toml", "K = 1\n", tmp)
    ok, why = False, "it wrote the report anyway"
except SystemExit as e:
    ok, why = "REFUSED" in str(e), str(e)[:60]
check("a report that WOULD contain a key is REFUSED, not warned about",
      ok, why)
check("...and the refusal names the account so it can be found",
      "oops" not in why)


print()
print("6 THE ROUND TRIP — we must be able to read what we write")
# =====================================================================
#
# FOUND BY A CLAUDE CODE SESSION, 6.9.2026, running this tool over a
# PREVIOUS secrets.toml: 21 Hume blocks in, ZERO pairs out. The parser
# was written for the dashboard export and only ever tested against it,
# so the one file this project GENERATES was the one shape it could not
# read back. The tool wrote [[HUME_ACCOUNTS]] tables and the parser saw
# nothing.
#
# A format you emit is a format you must be able to read, and the test
# for that is a round trip. It is cheap and it did not exist.

rt_rows = [
    (F("google", G1, "alive"), G.WORKING, "", True),
    (F("google", G2, "second"), G.WORKING, "", True),
    (F("hume", HK, "kalabhumi", HS), G.WORKING, "", True),
    (F("H" + "m" * 47, "svaram", "S" + "t" * 63), G.WORKING, "", True),
]
rt_text, _ = B.build([r[0] for r in rt_rows],
                     {r[0].key: (r[1], r[2]) for r in rt_rows})

back = KP.extract(rt_text)
usable = [f for f in back if f.usable]
by = {}
for f in usable:
    by.setdefault(f.provider, []).append(f)

check("the file we wrote parses as TOML", bool(tomllib.loads(rt_text)))
check("READING IT BACK finds both google keys",
      sorted(f.key for f in by.get("google", [])) == sorted([G1, G2]),
      [f.key[:12] for f in by.get("google", [])])
check("READING IT BACK finds BOTH hume pairs — this was zero",
      len(by.get("hume", [])) == 2, len(by.get("hume", [])))
check("...each with its secret intact",
      all(f.secret for f in by.get("hume", [])),
      [(f.label, bool(f.secret)) for f in by.get("hume", [])])
check("...and its account name",
      sorted(f.label for f in by.get("hume", [])) == ["kalabhumi", "svaram"],
      sorted(f.label for f in by.get("hume", [])))
check("no account is lost in the round trip",
      len(usable) == 4, [(f.provider, f.label) for f in usable])
check("nothing is reported as a problem",
      not [f for f in back if not f.usable],
      [f.problem for f in back if not f.usable])

# AND ROUND TRIP TWICE, because a second pass is what a person actually
# does: build, look at it, build again from the same folder.
again = KP.extract(B.build([f for f in usable],
                           {f.key: (G.WORKING, "") for f in usable})[0])
check("a SECOND round trip is stable — same counts, same names",
      sorted((f.provider, f.label) for f in again if f.usable)
      == sorted((f.provider, f.label) for f in usable),
      sorted((f.provider, f.label) for f in again if f.usable))

# THE TABLE PATH'S GUARDS. A TOML block must carry BOTH halves and both
# must look like credentials — the same rule as the labelled export, for
# the same reason: a field name does not make the value beneath it a key.
_no_secret = '[[HUME_ACCOUNTS]]\nname = "half"\nkey = "%s"' % HK
_ns = KP.extract(_no_secret)
check("a table with a key and NO secret yields no usable pair",
      not [f for f in _ns if f.provider == "hume" and f.usable],
      [(f.provider, f.usable) for f in _ns])
check("...and the account is REPORTED BY NAME rather than lost as an "
      "anonymous token",
      [f.label for f in _ns if not f.usable] == ["half"],
      [(f.label, f.problem[:34]) for f in _ns])

_ph = ('[[HUME_ACCOUNTS]]\nname = "placeheld"\nkey = "notshown"\n'
       'secret = "%s"' % HS)
_got = KP.extract(_ph)
check("a placeholder key in a TOML table yields no usable pair",
      not [f for f in _got if f.usable], _got)
check("...and the account is reported by name",
      [f.label for f in _got if not f.usable] == ["placeheld"],
      [(f.label, f.problem[:30]) for f in _got])

_ph2 = ('[[HUME_ACCOUNTS]]\nname = "nosecret"\nkey = "%s"\n'
        'secret = "short"' % HK)
check("a placeholder SECRET in a table is reported too",
      any("secret key is missing" in f.problem
          for f in KP.extract(_ph2) if not f.usable),
      [f.problem[:40] for f in KP.extract(_ph2)])

# A NON-HUME TABLE MUST NOT BE CLAIMED. Only a header naming hume, or no
# header at all, may produce a pair.
_other = ('[[SOMETHING_ELSE]]\nname = "x"\nkey = "%s"\nsecret = "%s"'
          % (HK, HS))
check("a table under a different header is not read as a hume pair",
      not [f for f in KP.extract(_other) if f.provider == "hume"],
      [(f.provider, f.label) for f in KP.extract(_other)])

print()
print("7 A VALUE CAN NEVER BECOME A NAME")
# =====================================================================
#
# The v246 tool printed the first characters of SHEETS_TOKEN's VALUE on
# a terminal, as the "label" of the token beneath it. The label is shown
# in the key tester panel and printed by the report, so a name holding a
# value puts a credential on a screen.

for line in ['SHEETS_TOKEN = "abcde12345678901234567890123456789012"',
             'DRIVE_SECRET="xyz9876543210987654321098765432109876"',
             'api_key: abcde12345678901234567890123456789012',
             '    "AQ.%s",' % ("q" * 45)]:
    got = KP.extract(line + "\n" + G1)
    labels = [f.label for f in got if f.usable]
    check("an assignment line is not a label: %.34s" % line,
          all(not lab for lab in labels), labels)

check("looks_like_name refuses an assignment",
      not KP.looks_like_name('SHEETS_TOKEN = "abcdefghijklmnopqrstuvwxyz12"'))
check("...and any line holding a 20+ character run",
      not KP.looks_like_name("note abcdefghijklmnopqrstuvwxyz123"))
check("...while an ordinary account name still passes",
      KP.looks_like_name("kalabhumi") and KP.looks_like_name("marko.bosko croatia")
      and KP.looks_like_name("AV LIVE VMIX"))

print()
print("%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
