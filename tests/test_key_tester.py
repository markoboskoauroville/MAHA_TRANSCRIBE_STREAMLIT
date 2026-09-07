"""THE KEY TESTER, AND THE BLOCK IT WRITES.

    python3 tests/test_key_tester.py

Ported from Key_Tester's KeyParser.kt. No network anywhere in here: the
parser is a pure function and the panel is driven through AppTest, so
this suite never spends a key.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from streamlit.testing.v1 import AppTest        # noqa: E402

from ttt import keyparse as KP                  # noqa: E402
from ttt import keyring as kr                   # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RAW = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()


def code_only(src):
    body = "\n".join(l for l in src.splitlines()
                     if not l.lstrip().startswith("#"))
    body = re.sub(r'(?<!["\'])#.*$', "", body, flags=re.M)
    return re.sub(r'"""(?:.|\n)*?"""', "", body)


CODE = code_only(RAW)

_m = re.search(r'"stale_modules":\s*\{"en": "(.*?)",\n\s*"hr": "(.*?)"\}',
               RAW, re.S)
STRINGS_EN = {"stale_modules": _m.group(1) if _m else ""}
STRINGS_HR = {"stale_modules": _m.group(2) if _m else ""}

# Shapes only. Not one of these is a real credential.
G1 = "AQ.Ab8RN6" + "a" * 40
G2 = "AQ.Ab8RN6" + "b" * 40
GROQ = "gsk_" + "c" * 40
ANT = "sk-ant-api03-" + "d" * 40
SPEE = "sk_" + "e" * 45
ELEV = "sk_" + "f" * 20
AAI = "0123456789abcdef0123456789abcdef"
# REAL HUME HALVES ARE ALPHANUMERIC, and that matters to the test as
# much as to the truth: the first version used pure letters, which the
# loose shape rejects for having no digit — so "the secret is not also
# reported as a loose key" was true no matter what the pairing did, and
# the mutation that stopped consuming it stayed GREEN.
HK = "HUMEKEY7" + "g" * 30 + "42"
HS = "HUMESECRET9" + "h" * 40 + "73"

NOTE = "\n".join([
    "AV LIVE VMIX", G1, "",
    "kalabhumi", G2, "",
    "my groq", GROQ, "",
    "claude", ANT, "",
    "speechify one", SPEE, "",
    "eleven", ELEV, "",
    "assembly", AAI, "",
    "account.one", "API key", HK, "Secret key", HS, "",
    "https://console.groq.com/keys?srsltid=AfmBOoqQaaaaaaaaaaaaaaaaaaaa",
    "cafeteria", "DELETED", "",
])

# =====================================================================
print("1 THE MECHANISM, ALONE — the parser")
# =====================================================================

found = KP.extract(NOTE)
byp = KP.by_provider(found)


def keys(pid):
    return [f.key for f in byp.get(pid, [])]


check("both Google keys are found", keys("google") == [G1, G2], keys("google"))
check("groq", keys("groq") == [GROQ])
check("anthropic", keys("anthropic") == [ANT])
check("assemblyai", keys("assemblyai") == [AAI])

# THE LENGTH SPLIT, which is the one rule here that will age.
check("a long sk_ is speechify", keys("speechify") == [SPEE])
check("a short sk_ is elevenlabs", keys("elevenlabs") == [ELEV])
check("the split is at 44 and nothing else",
      KP.classify("sk_" + "x" * 41) == "speechify"
      and KP.classify("sk_" + "x" * 40) == "elevenlabs",
      (len("sk_" + "x" * 41), KP.SK_SPEECHIFY_MIN))

# HUME IS A PAIR, READ FROM LABELS. Shape cannot tag either half.
hume = byp.get("hume") or []
check("hume comes back as ONE entry, not two", len(hume) == 1, len(hume))
check("...with the api key as the key", hume and hume[0].key == HK)
check("...the secret kept beside it", hume and hume[0].secret == HS)
check("...and the account name above it",
      hume and hume[0].label == "account.one",
      hume[0].label if hume else "")
check("neither half is ALSO reported as a loose key",
      HS not in [f.key for f in found], [f.key[:12] for f in found])
check("...and the fixture COULD have gone wrong — both halves are the "
      "shape the generic pass takes",
      KP.classify(HK) == "unknown" and KP.classify(HS) == "unknown",
      (KP.classify(HK), KP.classify(HS)))
# SHAPE CANNOT TAG EITHER HALF, which is the whole reason pass 1 reads
# LABELS. Neither is recognised as hume by shape — and in this fixture
# neither is recognised at all, because both are pure letters and the
# loose shape requires a digit as well. That is the point: whatever the
# generic pass would have said, it could never have said "hume".
check("shape alone could never tag either half as hume",
      KP.classify(HK) != "hume" and KP.classify(HS) != "hume",
      (KP.classify(HK), KP.classify(HS)))
check("...and the pair was found anyway, from the labels",
      bool(hume) and hume[0].secret == HS)

# THE LABELS, which are what make a verdict actionable.
check("each google key keeps its account name",
      [f.label for f in byp["google"]] == ["AV LIVE VMIX", "kalabhumi"],
      [f.label for f in byp["google"]])

# WHAT MUST NOT BE TAKEN.
allk = [f.key for f in found]
check("a tracking token in a URL is not a key",
      not any("AfmBOoqQ" in k for k in allk), allk)
check("the word cafeteria is not a key", "cafeteria" not in allk)
check("DELETED is not a key", "DELETED" not in allk)

# WHOLE-TOKEN, NEVER SEARCHED INSIDE.
check("a key-shaped run inside a longer token is not a key",
      KP.classify("prefix" + GROQ) != "groq",
      KP.classify("prefix" + GROQ))
check("an empty token classifies as nothing", KP.classify("") is None)
check("a short token classifies as nothing", KP.classify("abc") is None)

# ORDER INSIDE classify() — sk-ant- also matches the generic sk- shape.
check("anthropic is tested before the generic openai shape",
      KP.classify(ANT) == "anthropic")
check("a plain sk- key is still openai",
      KP.classify("sk-" + "z" * 40) == "openai")

# THE DIVERGENCE, ASSERTED SO IT CANNOT DRIFT BACK IN SILENTLY.
_retired = "AI" + "za"
check("the retired google prefix is NOT accepted",
      KP.classify(_retired + "x" * 35) != "google",
      KP.classify(_retired + "x" * 35))
check("...and is not written anywhere in the parser, comments included",
      _retired not in open(os.path.join(ROOT, "ttt", "keyparse.py")).read())
check("google's id here is 'google', not the android app's 'gemini'",
      "gemini" not in {f.provider for f in found})

check("providers this app does not hold are still RECOGNISED",
      "elevenlabs" in byp)
check("...but marked as not ours",
      not byp["elevenlabs"][0].known_here
      and byp["google"][0].known_here)

# =====================================================================
print()
print("2 THE REAL THING — the panel, driven")
# =====================================================================


ADMIN = ""
try:
    try:
        import tomllib
    except ModuleNotFoundError:                 # Python < 3.11: same parser, other name
        import tomli as tomllib
    with open(os.path.join(ROOT, ".streamlit", "secrets.toml"), "rb") as _f:
        _sec = tomllib.load(_f)
    ADMIN = str(_sec.get("ADMIN_USER")
                or (_sec.get("APP_PASSWORDS") or [""])[0])
except Exception:                                            # noqa: BLE001
    pass


def sget(at, key, default=None):
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def app():
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=90)
    at.session_state["_authed"] = True
    # THE OWNER NAMED IN THIS CLONE'S SECRETS. account_tier() is derived
    # from the name that matched at the door, so a stub name is a free
    # user — and a free user asking for the settings tab is redirected,
    # which is correct behaviour and made the first version of this
    # suite look for the panel on the translate tab.
    at.session_state["_user"] = ADMIN
    at.session_state["active_tab"] = "settings"
    return at


at = app()
at.run()
check("settings renders", not at.exception, at.exception)

btns = [b.key for b in at.button]
check("the tester has a Read keys button", "kt_go" in btns, btns)
check("...a Test all is not shown before anything is parsed",
      "kt_test" not in btns, btns)
check("...and a Forget button", "kt_forget" in btns, btns)

areas = [a.key for a in at.text_area]
check("there is a paste box", "kt_text" in areas, areas)

# PARSE, FOR REAL, THROUGH THE BUTTON. Not by calling the parser again:
# the gap between "the function works" and "the feature works" is where
# an enormous number of shipped bugs live.
at.text_area(key="kt_text").set_value(NOTE).run()
at.button(key="kt_go").click().run()
rows = sget(at, "_kt_found") or []
check("pressing Read keys fills the panel", len(rows) == len(found),
      len(rows))
check("...and it found the hume pair through the button too",
      any(r["provider"] == "hume" and r["secret"] for r in rows))

btns = [b.key for b in at.button]
check("Test all appears once there is something to test",
      "kt_test" in btns, btns)

# NOTHING WAS WRITTEN. This is the line between this panel and the paste
# box that was removed in v240.
rings = sget(at, "_rings") or {}
in_rings = [k.get("key") for r in rings.values() for k in r.get("keys", [])]
check("NOT ONE parsed key reached a ring",
      not any(k in in_rings for k in allk), in_rings[:3])
check("the panel keeps them in session_state and nowhere else",
      "KT_STATE" in CODE and 'st.session_state[KT_STATE]' in CODE)

# MASKED UNTIL ASKED.
code_blocks = [c.value for c in at.code]
shown = "\n".join(code_blocks)
check("the block is rendered", bool(shown.strip()), shown[:60])
check("NO REAL KEY IS ON SCREEN BEFORE THE TICK-BOX IS PRESSED",
      not any(k in shown for k in (G1, G2, GROQ, ANT, SPEE, HK, HS)),
      [k for k in (G1, GROQ, HK) if k in shown])
check("...but the masked form is",
      kr.mask(G1) in shown, shown[:120])

at.checkbox(key="kt_reveal").check().run()
shown2 = "\n".join(c.value for c in at.code)
check("ticking it shows the real keys, which is what he asked for",
      G1 in shown2 and GROQ in shown2 and HK in shown2)
check("...including the hume secret, which auth needs",
      HS in shown2)

# =====================================================================
print()
print("3 THE UGLY CASES")
# =====================================================================

for junk in ("", None, "   ", "\n\n\n", "no keys here at all",
             "=" * 500, "\x00\xff binary", "{}", "[[[["):
    try:
        got = KP.extract(junk)
        ok = isinstance(got, list)
    except Exception as e:                                   # noqa: BLE001
        ok, got = False, "RAISED %s" % e
    check("extract survives %.22r" % (junk,), ok, got)

check("a key appearing twice is returned once",
      len(KP.extract(GROQ + "\n" + GROQ)) == 1)

# A HUME BLOCK WITH ITS SECOND HALF MISSING must not half-pair.
half = "acct\nAPI key\n" + HK + "\n"
got = KP.extract(half)
check("an API key with no Secret key is not stored as a pair",
      not any(f.provider == "hume" for f in got),
      [(f.provider, f.key[:8]) for f in got])

# THE LABEL RULE: a run of keys must not label each with the one before.
run = GROQ + "\n" + "gsk_" + "z" * 40
labels = [f.label for f in KP.extract(run)]
check("a key is never used as the label of the next key",
      labels == ["", ""], labels)

# THE BLOCK ITSELF.
import importlib.util                            # noqa: E402
check("kt_secrets_block is built from SECRET_NAMES",
      "SECRET_NAMES.get(pid)" in CODE)
check("...and honours the three shapes",
      "SECRET_PAIRS" in CODE and "SECRET_SINGLE" in CODE)
check("the write button only appears where a write is possible",
      "kt_can_write_locally()" in CODE)
check("...and the Cloud sentence is shown where it is not",
      't("kt_cloud")' in CODE)
check("a key is never put in a log line or an error",
      "print(" not in CODE.split("def kt_verdict")[1].split("def kt_secrets")[0])

# THE VERDICTS ARE FIVE WORDS, not ok/not-ok.
check("kt_verdict reports no credit as its own word",
      "GOOGLE_P.NO_CREDIT" in CODE)
check("...and busy separately from refused",
      "GOOGLE_P.BUSY" in CODE and "GOOGLE_P.REFUSED" in CODE)
# find(), NOT index(). index() raises when the marker moves, and in a
# test file with no harness that kills the process — so every check
# after it never runs and the sweep prints NO NUMBER for the suite. A
# crash and a pass look equally unlike a failure. -1 is an answer.
_money_at = CODE.find("MONEY_MARKS")
_cool_at = CODE.find('if kind == "cool"')
check("both markers are present", _money_at > 0 and _cool_at > 0,
      (_money_at, _cool_at))
check("money words are matched before the status kind, per keyring.md",
      0 < _money_at < _cool_at, (_money_at, _cool_at))
# kt_verdict's LIVE PATH CANNOT BE REACHED WITHOUT SPENDING A KEY, so
# this is a source check and is labelled as one. It is made precise by
# reading the parse tree rather than grepping: the hume branch must call
# hume_test_one with BOTH halves, because the api key alone cannot prove
# the secret is right and the secret is half of what the ring stores.
import ast as _ast                               # noqa: E402
_fn = next(n for n in _ast.walk(_ast.parse(RAW))
           if isinstance(n, _ast.FunctionDef) and n.name == "kt_verdict")
_calls = [c for c in _ast.walk(_fn) if isinstance(c, _ast.Call)
          and getattr(c.func, "id", "") == "hume_test_one"]
check("kt_verdict calls hume_test_one", len(_calls) == 1, len(_calls))
check("...with two arguments, the key AND the secret",
      _calls and len(_calls[0].args) == 2,
      len(_calls[0].args) if _calls else 0)
_tests = [c for c in _ast.walk(_fn) if isinstance(c, _ast.Compare)
          and getattr(c.left, "id", "") == "provider_id"]
check("...behind a live branch on provider_id, not a dead one",
      len(_tests) == 1, len(_tests))

check("an exception from a provider is unknown, never dead",
      "except Exception as e:" in CODE
      and "GOOGLE_P.UNKNOWN, str(e)" in CODE)

# =====================================================================
print()
print("4 THE UPGRADE — nothing else moved")
# =====================================================================

check("the per-person key list still exists", "render_key_list(ring" in CODE)
check("keys still load from Secrets", "all_keys_from_secrets()" in CODE)
check("the tester did not reintroduce the removed paste box",
      "_key_paste" not in CODE and "_key_file" not in CODE)
check("the tester's own box has its own key, not the old one",
      '"kt_text"' in CODE)

_admin_at = CODE.find("def is_admin")
_title_at = CODE.find('t("kt_title")')
check("both markers are present", _admin_at > 0 and _title_at > 0,
      (_admin_at, _title_at))
check("the tester is inside the admin branch only",
      0 < _admin_at < _title_at, (_admin_at, _title_at))
at2 = app()
at2.session_state["_view_tier"] = "free"
at2.run()
free_btns = [b.key for b in at2.button]
check("a free view never sees the tester", "kt_go" not in free_btns,
      free_btns[:8])

check("the parser is importable on its own, with no Streamlit",
      importlib.util.find_spec("ttt.keyparse") is not None)
src = open(os.path.join(ROOT, "ttt", "keyparse.py")).read()
check("...and imports no Streamlit, so the next app can lift it",
      "streamlit" not in src)

# =====================================================================
print()
print("2b MEASURED AGAINST THE LIVE API, 6.9.2026 — recorded, not re-run")
# =====================================================================
#
# These cost real calls and one account's Hume pair is genuinely dead.
# The numbers are written down here so the next session does not spend
# them again — four-tests.md: expectations come from what was MEASURED.
#
#   parser, on Baba's two real key files
#     21 Google keys, every one AQ. and 53 characters, names preserved
#     17 Hume pairs, every one with its secret, read from the labels
#     0 false positives from either file
#
#   Google, key 12 of 21 (kalabhumi)
#     test_key            200, working
#     synth "Dobar dan."  96,570 bytes, 2.011s of audio, marks None
#                         raw PCM with NO header, exactly as measured
#                         24 kHz mono 16-bit; the 44 bytes we write make
#                         it a file Python's own wave module opens and
#                         agrees with, frame count matching the duration
#     generation speed    22.9s wall for 2.0s of audio on this call
#
#   Hume, 5 of 17 pairs probed two ways
#     kalabhumi, mantra.ishvara, auroville.community, Remini
#                         token 200, work 200
#     av.live.vmix        token 401, work 401 — Invalid ApiKey. DEAD.
#
# THE DIVERGENCE keyring.md §2c RECORDS — a pair that passes the token
# and refuses synthesis — WAS NOT REPRODUCED in that sample. That is a
# sample of five, not a refutation, and the code assumes §2c is right.

check("the hume test proves the ACCOUNT, not just the pair",
      "hume_work_probe(key)" in CODE)
check("...and the work probe sends no voice id, so a renamed voice "
      "cannot read as a dead account",
      '"utterances": [{"text": "Hi"}]' in CODE and "voice" not in
      CODE.split("def hume_work_probe")[1].split("def hume_error_kind")[0])
# SCOPED TO THE PROBE, NOT THE WHOLE FILE. The first version greped for
# "Could not reach Hume" anywhere in app.py — and the OLD hume_test_one
# has that line too, so flipping the new probe's verdict to "dead" left
# the check green. Face 4: it asserted that a string exists somewhere,
# not that this function does the right thing.
_probe = CODE.split("def hume_work_probe")[1].split("def hume_error_kind")[0]
check("the probe region was found and is a sensible size (%d chars)"
      % len(_probe), 200 < len(_probe) < 2000, len(_probe))
check("a transport failure is soft IN THIS PROBE, never dead — the "
      "network being down is not the account's fault",
      'return "Could not reach Hume: %s" % e, "soft"' in _probe,
      _probe[-140:])
_wp = CODE.split("def hume_work_probe")[1].split("def hume_error_kind")[0]
check("the work probe is a POST, because a GET would be a listing",
      'method="POST"' in _wp)
check("Google's measured facts are unchanged in the provider",
      "gemini-2.5-flash-preview-tts" in
      open(os.path.join(ROOT, "ttt", "providers", "google.py")).read())

# =====================================================================
print()
print("4b THE SPINNER, THE SPEED, AND WHAT MAY BE DELETED")
# =====================================================================

_run = CODE.split("def _kt_run_tests")[1].split("\ndef ")[0]
check("the runner region was found (%d chars)" % len(_run),
      300 < len(_run) < 3000, len(_run))

# PARALLEL, because every one of these waits on a network.
check("keys are tested in parallel", "ThreadPoolExecutor" in _run)
check("...eight at a time, not all twenty-one at once",
      "KT_WORKERS" in _run and "KT_WORKERS = 8" in CODE)
check("results are taken as they LAND, not in submission order — the "
      "name shown must be the one that just finished",
      "as_completed(futures)" in _run)

# THE MAIN THREAD DRAWS. A worker calling st.* writes into nothing.
check("no st.* call happens inside a worker",
      "kt_verdict" in _run and "pool.submit(kt_verdict" in _run)
check("the drawing is done in the loop on the main thread",
      "slot.text(" in _run)

# NOT on_click: a callback cannot draw, so the spinner would appear only
# after the last key answered — which is the wait being complained about.
check("Test all runs inline, not through on_click",
      'st.button(t("kt_test_all"), key="kt_test")' in CODE
      and 'key="kt_test",\n                          on_click' not in CODE)

# THE SPINNER.
check("the spinner is braille", all(0x2800 <= ord(c) <= 0x28FF
                                    for c in eval('"' + CODE.split('KT_SPIN = "')[1].split('"')[0] + '"')))
_frames = eval('"' + CODE.split('KT_SPIN = "')[1].split('"')[0] + '"')
check("it has ten frames", len(_frames) == 10, len(_frames))
check("every frame is ONE cell, so the text beside it cannot jitter",
      len(set(len(f) for f in _frames)) == 1)
check("the status shows the NAME being tested", '(row["label"] or' in _run)
check("...and a count, so 'how far through' is answerable",
      '%d / %d' in _run)
check("...and the counter cannot run past the total",
      "done, total" in _run)

# WHAT MAY BE DELETED, AND WHAT MAY NOT. This is the one that protects
# live accounts, so it is asserted on the RULE and not on the button.
_drop = CODE.split("def _kt_drop_where")[1].split("if _bad:")[0]
check("the drop region was found (%d chars)" % len(_drop),
      40 < len(_drop) < 600, len(_drop))

from ttt.providers import google as _G           # noqa: E402
check("refused is the only deletable verdict", _G.deletable(_G.REFUSED))
for keep in (_G.WORKING, _G.BUSY, _G.NO_CREDIT, _G.UNKNOWN):
    check("%r is NOT deletable" % keep, not _G.deletable(keep))
# SCOPED TO THE DROP FUNCTION. The first version greped the whole file,
# and deletable() also appears in the list that COUNTS the refused keys
# just above — so rewriting the drop filter to "everything not working"
# left this green while the button deleted live no-credit accounts. The
# most dangerous mutation in this set was the one my check could not see.
# THE FILTER MOVED WHEN THE SECOND BIN ARRIVED. It used to live in
# _kt_drop; it is now the predicate passed at each call site, and the
# helper itself is generic. So the assertion follows it to the call
# site rather than staying pointed at a function that no longer decides
# anything — which is how a check ends up green and meaningless.
_refused_btn = CODE.split("if _bad:")[1].split("_poor =")[0]
check("the refused button's block was found (%d chars)" % len(_refused_btn),
      60 < len(_refused_btn) < 800, len(_refused_btn))
check("the refused bin asks deletable(), not its own opinion",
      "GOOGLE_P.deletable(" in _refused_btn, _refused_btn)
check("the refused bin never compares against WORKING, which would bin "
      "no-credit and unknown accounts alike",
      "WORKING" not in _refused_btn, _refused_btn)
_poor_btn = CODE.split("_poor = [r for r in found")[1].split("st.markdown")[0]
check("the out-of-credit bin was found (%d chars)" % len(_poor_btn),
      60 < len(_poor_btn) < 1200, len(_poor_btn))
check("...and it removes ONLY no-credit, never refused or unknown",
      "GOOGLE_P.NO_CREDIT" in _poor_btn
      and "UNKNOWN" not in _poor_btn
      and "deletable" not in _poor_btn, _poor_btn)
check("UNKNOWN is offered a RETRY before any bin",
      't("kt_retry")' in CODE and 'GOOGLE_P.UNKNOWN' in CODE)
check("...and the note says a 503 is the service, not the key",
      "503" in RAW.split('"kt_unknown_note"')[1][:400])
check("the remove help says out-of-credit accounts are alive",
      "alive" in RAW.split('"kt_drop_help"')[1][:400])

# DELETING TOUCHES ONLY THE LIST THAT BUILDS THE BLOCK. Nothing is
# revoked at the provider and no ring is written.
check("dropping only rewrites the parsed list",
      "st.session_state[KT_STATE] = [" in _drop, _drop[:120])
check("...and calls nothing that could revoke anything",
      "delete" not in _drop.lower() and "revoke" not in _drop.lower())

# =====================================================================
print()
print("4c TWO BINS, AND THE AUDIT THAT FEEDS THE HANDOFF")
# =====================================================================

check("there is a bin for refused", 'key="kt_drop"' in CODE)
check("...and a SEPARATE bin for out-of-credit",
      'key="kt_drop_poor"' in CODE)
# The helper is DEFINED once and CALLED twice. Counting all three
# occurrences would have passed with one button and a stray mention.
check("they are two buttons, not one",
      CODE.count("on_click=lambda: _kt_drop_where(") == 2,
      CODE.count("on_click=lambda: _kt_drop_where("))
# THE WHOLE REASON THEY ARE TWO. One press for both would make "the key
# is wrong" and "the account is alive and empty" the same decision.
check("the out-of-credit bin filters on NO_CREDIT and nothing else",
      'r["verdict"] == GOOGLE_P.NO_CREDIT' in CODE)
check("the refused bin still asks deletable()",
      "GOOGLE_P.deletable(" in CODE)
_ph = RAW.split('"kt_drop_poor_help"')[1][:500]
check("the out-of-credit help says the accounts are ALIVE",
      "ALIVE" in _ph, _ph[:80])
check("...and that topping up makes the same key work again",
      "topping the account up" in _ph, _ph[:80])
check("...and that removing here closes nothing",
      "does not close anything" in _ph, _ph[:80])

# THE AUDIT MUST NOT ROT. It is the specification the local Claude Code
# session works from, so a name that changes in the code and not in the
# table sends that session to write a secrets file the app cannot read.
_audit = open(os.path.join(ROOT, "docs", "SECRETS_AUDIT.md")).read()
_appsrc = RAW + open(os.path.join(ROOT, "ttt", "keyring.py")).read()
_live = re.findall(r"^\| `([A-Z_0-9]+)[^`]*` \| \w+ \| \*\*LIVE",
                   _audit, re.M)
check("the audit lists live names", len(_live) >= 14, len(_live))
# SOME LIVE NAMES ARE MATCHED BY A PATTERN, NOT BY A LITERAL.
# STUDIO_USER1 and FREE_USER7 are never written out in the source: the
# tier scanner compiles ^(ADMIN|STUDIO|FREE)_USER\d*$ and walks the
# secrets. My first version of this check called both DEAD, which would
# have sent the local Claude Code session to delete the two names that
# decide who can log in at all. A check that is confidently wrong about
# a live name is worse than no check.
_PATTERNED = {"STUDIO_USER": "STUDIO", "FREE_USER": "FREE",
              "ADMIN_USER": "ADMIN"}
_missing = []
for n in _live:
    if '"%s"' % n in _appsrc:
        continue
    stem = _PATTERNED.get(n)
    if stem and "(ADMIN|STUDIO|FREE)_USER" in _appsrc:
        continue
    _missing.append(n)
check("EVERY name the audit calls LIVE is read by the code, as a "
      "literal or through the tier pattern",
      not _missing, _missing)
check("...and the tier pattern really is in the source",
      "(ADMIN|STUDIO|FREE)_USER" in _appsrc)
_dead = re.findall(r"^\| `([A-Z_0-9]+)` \| dead \| \*\*DEAD", _audit, re.M)
check("the audit lists the dead ones", len(_dead) == 2, _dead)
_alive = [n for n in _dead if '"%s"' % n in _appsrc]
check("EVERY name the audit calls DEAD has no reader at all",
      not _alive, _alive)

# THE HANDOFF MUST POINT SOMEWHERE REAL.
_hand = open(os.path.join(ROOT, "handoff", "CLAUDE_CODE_SECRETS.md")).read()
for ref in ("ttt/keyparse.py", "docs/SECRETS_AUDIT.md"):
    check("the handoff points at %s, and it exists" % ref,
          ref in _hand and os.path.exists(os.path.join(ROOT, ref)))
check("the handoff names the AQ. prefix and not the retired one",
      "AQ." in _hand and ("AI" + "za") in _hand)
check("...where the retired one appears ONLY as the thing to avoid",
      _hand.count("AI" + "za") == 1)
check("the handoff tells it never to print the key file",
      "Do not print it" in _hand)
check("...and to verify the TOML parses before he pastes it",
      "tomllib" in _hand)
check("...and names the dead secrets to drop",
      "SHEETS_URL" in _hand and "SHEETS_TOKEN" in _hand)
check("...and carries the measured verdicts, so it does not re-spend them",
      "eighteen working" in _hand and "av.live.vmix" in _hand)

# =====================================================================
print()
print("5 THE STALE-MODULE GUARD — the outage of 6.9.2026")
# =====================================================================
#
# The live app died at import with a REDACTED AttributeError on
# set_google_keys, on a commit where the function was provably present:
# the remote file matched local byte for byte, and a clean clone of that
# exact commit imported it fine. Streamlit re-reads app.py every run and
# keeps packages in sys.modules, so a rerun without a process restart
# runs a NEW app.py against the OLD ttt package.
#
# The code was right and the person was told nothing. That is the part
# this guard fixes.

from ttt import providers as _P                   # noqa: E402
check("the providers module states an API level",
      isinstance(getattr(_P, "API_LEVEL", None), int), 
      getattr(_P, "API_LEVEL", None))
check("...and it is at least the level app.py asks for",
      _P.API_LEVEL >= 2, _P.API_LEVEL)
check("app.py checks it BEFORE it uses anything from that level",
      CODE.find("API_LEVEL") < CODE.find("PROVIDERS.set_google_keys"),
      (CODE.find("API_LEVEL"), CODE.find("PROVIDERS.set_google_keys")))
check("it stops rather than carrying on into the crash",
      "st.stop()" in CODE.split("API_LEVEL")[1][:400])
check("getattr with a default, so an OLD module without the name is "
      "caught rather than raising the same AttributeError again",
      'getattr(PROVIDERS, "API_LEVEL", 0)' in CODE)

_msg = STRINGS_EN.get("stale_modules", "")
check("the message names the button to press", "Reboot app" in _msg, _msg[:70])
check("...and says the code is not broken, because it is not",
      "Nothing is broken" in _msg, _msg[:70])
check("...and exists in Croatian too", bool(STRINGS_HR.get("stale_modules")))


# =====================================================================
print()
print("6 THE NAME RULE — robust against a file that changes shape")
# =====================================================================
#
# Baba, 6.9.2026: "he must understand to attach the name to the account
# which has like banner or title before it, and the one which doesn't
# just doesn't... The structure of the file can change any time."

GK = "AQ." + "a" * 45
GK2 = "AQ." + "b" * 45
HKEY = "H" + "k" * 47
HSEC = "S" + "s" * 63


def names(text):
    return [(f.provider, f.label) for f in KP.extract(text) if f.usable]


# A NAME IS ATTACHED ONLY WHEN THERE REALLY IS ONE.
check("a name above the key is attached",
      names("kalabhumi\n" + GK) == [("google", "kalabhumi")])
check("a key alone gets NO name, not the line before it",
      names(GK) == [("google", "")])
check("a name below the key is still found, inside the block",
      names(GK + "\nkalabhumi") == [("google", "kalabhumi")])

# WHAT IS NOT A NAME, one case per rule. Each of these has appeared in a
# real key file at some point, and each would have become an account
# name under the old "take the line above" rule.
for junk, why in [
        ("https://aistudio.google.com/apikey", "a URL"),
        ("www.hume.ai", "a bare domain"),
        ("someone@example.com", "an email"),
        ("6.9.2026.", "a date"),
        ("API key", "a label word"),
        ("Secret key", "the other label word"),
        ("DELETED", "a status word"),
        ("CANCELLED", "another status word"),
        ("# gemini keys", "a heading"),
        ("---", "a separator"),
        ("12345", "a bare number"),
]:
    check("%s is not taken as a name" % why,
          names(junk + "\n" + GK) == [("google", "")],
          names(junk + "\n" + GK))

# TWO KEYS IN ONE BLOCK EACH KEEP THEIR OWN NAME. Searching upward and
# stopping at the previous key is what makes this work; taking "the
# block's first line" would name both the same.
check("two named keys in one block get their own names",
      names("acct one\n" + GK + "\nacct two\n" + GK2)
      == [("google", "acct one"), ("google", "acct two")])
check("one name and two keys: only the first is named — the second is "
      "NOT given its neighbour's name",
      names("only name\n" + GK + "\n" + GK2)
      == [("google", "only name"), ("google", "")])
check("a name in a DIFFERENT block does not reach across the blank line",
      names("acct one\n\n" + GK) == [("google", "")])

# SEVERAL KEYS ON ONE LINE GET NO NAME. Nothing in the file says which
# of them a title would belong to, and guessing puts a real account's
# name on a stranger.
check("a TOML list on one line yields keys with no names",
      names('KEYS = ["%s", "%s"]' % (GK, GK2))
      == [("google", ""), ("google", "")])

# HUME.
check("a hume pair keeps its account name",
      names("acct\nAPI key\n" + HKEY + "\nSecret key\n" + HSEC)
      == [("hume", "acct")])
check("A HUME PAIR WITH NO NAME DOES NOT TAKE ITS OWN KEY AS ONE",
      names("API key\n" + HKEY + "\nSecret key\n" + HSEC)
      == [("hume", "")],
      names("API key\n" + HKEY + "\nSecret key\n" + HSEC))
check("a URL inside a hume block does not become the name",
      names("acct\nhttps://x.y\nAPI key\n" + HKEY + "\nSecret key\n" + HSEC)
      == [("hume", "acct")])
# BOTH LABELS OR IT IS NOT A HUME BLOCK. A google key under the words
# "API key" was swallowed whole: the hume path claimed the block and
# the generic pass never ran.
check("a google key labelled 'API key' is still found as google",
      names("API key\n" + GK) == [("google", "")],
      names("API key\n" + GK))

print()
print("7 A PLACEHOLDER IS NOT A KEY — the five lost accounts")
# =====================================================================
#
# MEASURED on the real export, 6.9.2026: a Hume api key is 48 characters
# and a secret is 64. FIVE of twenty-one accounts carry the SAME
# nine-character placeholder where the api key should be.
#
# The old parser took whatever followed the label. So av.live.vmix was
# paired with a placeholder, answered 401 "Invalid ApiKey", and WAS
# REPORTED TO BABA AS A DEAD ACCOUNT. It is not known to be dead; its
# key was simply not in the file. The other four shared that placeholder
# and the de-duplication collapsed them into one — FOUR ACCOUNTS
# VANISHED WITHOUT A WORD.

short = "acct\nAPI key\nnotshown\nSecret key\n" + HSEC
got = KP.extract(short)
check("a placeholder api key yields NO usable key",
      not [f for f in got if f.usable], got)
check("...and the account is REPORTED, by name, not dropped",
      [f.label for f in got if not f.usable] == ["acct"],
      [(f.label, f.problem) for f in got])
check("...and the problem says what was wrong",
      "API key is missing" in got[0].problem, got[0].problem)
check("a missing secret is reported too",
      any("secret key is missing" in f.problem
          for f in KP.extract("acct\nAPI key\n" + HKEY + "\nSecret key\n")),
      [f.problem for f in KP.extract("acct\nAPI key\n" + HKEY + "\nSecret key\n")])

# FIVE ACCOUNTS SHARING ONE PLACEHOLDER MUST BE FIVE REPORTS, NOT ONE.
five = "\n\n".join("acct%d\nAPI key\nnotshown\nSecret key\n%s" % (i, "S" + str(i) + "s" * 62)
                   for i in range(5))
rep = [f for f in KP.extract(five) if not f.usable]
check("five accounts with the same placeholder are five reports",
      len(rep) == 5, len(rep))
check("...each keeping its own name",
      [f.label for f in rep] == ["acct%d" % i for i in range(5)],
      [f.label for f in rep])

# AND TWO GOOD ACCOUNTS THAT SHARE NOTHING ARE STILL TWO.
two = ("a\nAPI key\n%s\nSecret key\n%s\n\nb\nAPI key\n%s\nSecret key\n%s"
       % (HKEY, HSEC, "H" + "m" * 47, "S" + "t" * 63))
check("two distinct pairs are two entries",
      len([f for f in KP.extract(two) if f.usable]) == 2)

# THE DOWNWARD SEARCH STOPS AT THE NEXT KEY TOO. Without that, a key
# with nothing above it would reach past a SECOND key to borrow a name
# that plainly belongs to the second one.
check("a key does not reach past another key to find a name below",
      names(GK + "\n" + GK2 + "\nbelongs to the second")
      == [("google", ""), ("google", "belongs to the second")],
      names(GK + "\n" + GK2 + "\nbelongs to the second"))

# THE PAIR IS THE IDENTITY, NOT THE API KEY. Two accounts sharing an
# api key but holding different secrets are two credentials; keying the
# de-duplication on the api key alone silently keeps one and drops the
# other — which is exactly how four accounts vanished.
same_key = ("one\nAPI key\n%s\nSecret key\n%s\n\n"
            "two\nAPI key\n%s\nSecret key\n%s"
            % (HKEY, HSEC, HKEY, "S" + "u" * 63))
_sk = [f for f in KP.extract(same_key) if f.usable]
check("two accounts sharing an api key but not a secret stay TWO",
      len(_sk) == 2, [(f.label, f.secret[:6]) for f in _sk])
check("...and each keeps its own name",
      [f.label for f in _sk] == ["one", "two"], [f.label for f in _sk])
# And a genuine duplicate — the same file pasted twice — is still one.
check("the very same pair twice is ONE entry",
      len([f for f in KP.extract(
          "a\nAPI key\n%s\nSecret key\n%s\n\na\nAPI key\n%s\nSecret key\n%s"
          % (HKEY, HSEC, HKEY, HSEC)) if f.usable]) == 1)

check("looks_like_value rejects a nine-character placeholder",
      not KP.looks_like_value("notshown"))
check("...and accepts a real 48-character key", KP.looks_like_value(HKEY))
check("...and rejects anything with a space in it",
      not KP.looks_like_value("this is not a key at all really"))

print()
print("%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
