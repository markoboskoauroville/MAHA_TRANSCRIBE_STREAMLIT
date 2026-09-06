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
    import tomllib
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

print()
print("%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
