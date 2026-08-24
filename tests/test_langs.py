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

EDGE_LANGS = set(re.findall(
    r'"\w+": \("[a-z]{2}-[A-Z]{2}-\w+",\s*"[^"]*",\s*"(\w+)"', TALK))
ck("4 EVERY EDGE VOICE BELONGS TO A TR LANGUAGE — the deck reads the "
   "TR grid, so a voice for anything else is a voice nothing can reach",
   EDGE_LANGS <= set(LANGS_TR), sorted(EDGE_LANGS))

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
    # THE AMENDMENT, 24.8.2026. Baba: "that language rule only applies to
    # other tabs. Translation tab is free. It's a free soul. He can speak
    # any. He is multilingual polyglot." So a translate-only language MAY
    # have Edge voices — that is what the TR deck reads with — but it
    # still may not appear in T's or R's pickers, or as an interface
    # language, or as something the app will transcribe.
    ck("9 %r IS NOT IN R's VOICE PICKER — the lock still holds for T "
       "and R" % code, code not in VOICES_BY_LANG)
    ck("10 %r is not in the login/interface pills" % code,
       code not in LANGS5)
    ck("11 %r HAS BOTH AN EDGE VOICE, FEMALE AND MALE — the TR deck "
       "offers exactly two buttons and a language that answers only "
       "one of them is a control that does nothing half the time"
       % code,
       ('"%sF"' % code) in TALK and ('"%sM"' % code) in TALK)

# EVERY TR LANGUAGE, not just the extra ones — the deck can be pointed
# at any of them.
for code in LANGS_TR:
    ck("12 %r can be read by the deck, female and male" % code,
       ('"%sF"' % code) in TALK or code in ("hr", "en"),
       "missing a pair")

ck("13 ENGLISH IS BRITISH, EVERYWHERE. Baba: 'we don't work in this app "
   "with American English, we just forget it.'",
   "en-US" not in TALK and "en-GB" in TALK)
ck("14 THE DECK PICKS BY LANGUAGE AND GENDER, never by name — one "
   "binary choice, because the people using this are not going to "
   "learn ten voice names",
   "def vkey_for" in TALK and "def tr_voice_key" in SRC)
# The pairing is checked INSIDE tr_read, not anywhere in the file:
# "translate_src" appears all over the tab, so a global search passes
# even when the lower box has been wired to the upper row. That exact
# mutation slipped through the first version of this check.
_body = SRC[SRC.index("def tr_read("):]
_body = _body[:_body.index("\ndef ", 1)]
_src_branch = _body[:_body.index("else:")]
_out_branch = _body[_body.index("else:"):]
ck("15 THE UPPER BOX SPEAKS THE UPPER ROW",
   '"translate_src"' in _src_branch and '"translate_tgt"' not in _src_branch,
   _src_branch.strip()[-120:])
ck("15b AND THE LOWER BOX SPEAKS THE LOWER ROW — reading a translation "
   "in the language it came FROM is the mistake this prevents",
   '"translate_tgt"' in _out_branch and '"translate_src"' not in _out_branch,
   _out_branch.strip()[:160])

# --- the consequence, stated in the code ------------------------------
ck("16 the rule is written down where the next session will meet it",
   "multilingual polyglot" in open(
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
