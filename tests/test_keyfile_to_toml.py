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

many = [F("anthropic", "sk-ant-" + c * 40, "acct" + c) for c in "xy"]
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
print("%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
