"""THE LOCKED LANGUAGES — the rule in HOW_WE_WORK.md, as a check.

Two languages for transcription and reading: hr and en. Locked.
Translation may be any language on this planet.

This exists because the rule was broken within one session of being
needed: a Spanish translate pill reached for a Spanish voice, an entry in
TRANSLATE_VKEY, and an Edge voice table row before anybody noticed that
"translate into Spanish" and "speak Spanish" are different offers. A rule
that lives only in a document gets re-broken by whoever did not read it.

    python3 tests/test_langs.py
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

SRC = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
TALK = open(os.path.join(ROOT, "talk_engine.py"), encoding="utf-8").read()

passed = failed = 0


def ck(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def literal(pattern):
    m = re.search(pattern, SRC, re.S)
    assert m, "not found in app.py: " + pattern
    return eval(m.group(1))          # noqa: S307 — our own source


print("THE LOCKED LANGUAGES\n")

LANGS5 = literal(r"LANGS5 = (\[[^\]]*\])")
LANGS_TR = literal(r"LANGS_TR = (\[[^\]]*\])")
TRANSLATE_VKEY = literal(r"TRANSLATE_VKEY = (\{[^}]*\})")
VOICES_BY_LANG = literal(r"VOICES_BY_LANG = (\{[^}]*\})")
LANG_PILL = literal(r"LANG_PILL = (\{[^}]*\})")

SPOKEN = {"hr", "en"}

# --- the lock ---------------------------------------------------------
ck("1 READING ALOUD IS hr AND en ONLY",
   set(VOICES_BY_LANG) == SPOKEN, set(VOICES_BY_LANG))

sp = re.search(r"SP_VOICES_BY_LANG = \{(.*?)\n\}", SRC, re.S)
ck("2 and the Speechify voices are the same two languages",
   sp is not None and set(eval("{" + sp.group(1) + "}")) == SPOKEN)

ck("3 THE LOGIN/INTERFACE PILLS GAIN NOTHING — the app itself is "
   "written in two languages and a third pill would promise a "
   "translation of the app that does not exist",
   set(LANGS5) <= SPOKEN | {"it", "de", "fr"}, LANGS5)

ck("4 EVERY VOICE IN THE EDGE TABLE IS hr OR en OR A TRANSLATE-TAB "
   "LANGUAGE — never a language added only for translation",
   set(re.findall(r'"\w+": \("[a-z]{2}-[A-Z]{2}-\w+",\s*"[^"]*",\s*"(\w+)"',
                  TALK)) <= set(LANGS5), sorted(set(re.findall(
                      r'"\w+": \("[a-z]{2}-[A-Z]{2}-\w+",\s*"[^"]*",\s*"(\w+)"',
                      TALK))))

# --- the exception ----------------------------------------------------
ck("5 TRANSLATION MAY BE ANY LANGUAGE — the grid is free to grow",
   len(LANGS_TR) >= len(LANGS5), (LANGS_TR, LANGS5))
ck("6 Spanish is in the translate grid, which is what Baba asked for",
   "es" in LANGS_TR, LANGS_TR)
ck("7 and its pill says SPA, three letters, as asked",
   LANG_PILL.get("es") == "SPA", LANG_PILL.get("es"))

# --- and the exception STAYS an exception -----------------------------
extra = [c for c in LANGS_TR if c not in LANGS5]
ck("8 there is at least one translate-only language to test the rule "
   "against", bool(extra), extra)
for code in extra:
    ck("9 %r HAS NO VOICE — a translate-only language must never "
       "acquire one" % code, code not in TRANSLATE_VKEY,
       TRANSLATE_VKEY)
    ck("10 %r is not in VOICES_BY_LANG" % code, code not in VOICES_BY_LANG)
    ck("11 %r is not in the login/interface pills" % code,
       code not in LANGS5)
    ck("12 %r HAS NO EDGE VOICE — no '%s-' locale in the voice table"
       % (code, code), ('"%s-' % code) not in TALK)

# --- the consequence, stated in the code ------------------------------
ck("13 the rule is written down where the next session will meet it",
   "TWO LANGUAGES, LOCKED" in open(
       os.path.join(ROOT, "docs", "HOW_WE_WORK.md"), encoding="utf-8").read())

print("\n%d ok, %d failed" % (passed, failed))


def test_langs():
    """The verdict, in the one form pytest can report. The checks run
    above, at import, because this file is a script first."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT — at module level it
# fires during pytest's collection and aborts the whole run with
# INTERNALERROR before one test is reported. The repo learned this at
# test_login.py; this file did not, until it did the same thing.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
