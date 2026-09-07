"""KEYS COME FROM SECRETS, AND FROM NOWHERE ELSE.

    python3 tests/test_keys_from_secrets.py

Baba: "instead of all this manual entering, the API keys we are going to
keep only inside the secret."

THE DANGEROUS HALF OF THIS CHANGE IS NOT THE DELETION, IT IS THE ORDER.
Before it, load_keys() read session_state then localStorage and never
Secrets, and only Hume had a Secrets path. Taking the paste box out
first would have left Speechify, AssemblyAI and Anthropic with no way in
at all — and the symptom would not have been an error, it would have
been the studio tier quietly falling back to free voices. So most of
this suite is about what REPLACED the box, not about the box being gone.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from streamlit.testing.v1 import AppTest        # noqa: E402

from ttt import providers as P                  # noqa: E402

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
    """Comments AND docstrings stripped. Face 2: every comment around
    this change names the widgets it removed, so a check for their
    absence would match the explanation of why they are absent."""
    body = "\n".join(l for l in src.splitlines()
                     if not l.lstrip().startswith("#"))
    body = re.sub(r'(?<!["\'])#.*$', "", body, flags=re.M)
    return re.sub(r'"""(?:.|\n)*?"""', "", body)


CODE = code_only(RAW)


def sget(at, key, default=None):
    """AppTest's session_state is not a dict — it has no .get(), and
    asking for a missing key raises. Every other AppTest suite here
    carries this same helper."""
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def app(tab="settings"):
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=90)
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    at.session_state["active_tab"] = tab
    return at


# =====================================================================
print("1 THE MECHANISM, ALONE — the loader, on hand-made secrets")
# =====================================================================

# app.py is a Streamlit script, not an importable module — it calls
# st.stop() at top level — so the loader cannot be imported and called
# directly here. It is exercised through the rendered app in section 2.
# What section 1 checks is the SHAPE TABLES, because they are what
# decides whether a provider's secret is read correctly at all, and they
# are plain data that can be read without running anything.

# SECRET_NAMES IS THE ONE SOURCE. The template is generated from it and
# the loader is driven by it, so a name in one and not the other is the
# exact drift that ends in somebody pasting a block nothing reads.
names = re.search(r"^SECRET_NAMES = \{(.*?)^\}", RAW, re.S | re.M)
check("SECRET_NAMES is found", names is not None)
mapped = dict(re.findall(r'"(\w+)":\s*\(([^)]*)\)', names.group(1)))
check("every keyed provider has secret names",
      all(p.id in mapped for p in P.keyed_providers()),
      [p.id for p in P.keyed_providers() if p.id not in mapped])
check("google and groq are named too, though they are the app's own",
      "google" in mapped and "groq" in mapped)

# APP-OWNED KEYS DO NOT GET A PERSONAL KEY PANEL. Both live in Secrets
# and are shared by everybody, so a panel offering to manage them shows
# somebody keys they do not own and cannot change — and its ring would
# read 0/0 however many were working. Google turned up in this list
# uninvited the moment it became a provider with needs_key.
_keyed = [p.id for p in P.keyed_providers()]
check("groq is not in the per-person key list", "groq" not in _keyed, _keyed)
check("google is not either — its keys are the app's",
      "google" not in _keyed, _keyed)
check("the studio providers ARE, because those keys are a person's",
      set(_keyed) == {"anthropic"}, _keyed)

check("the loader is driven by SECRET_NAMES, not a second list",
      "SECRET_NAMES.get(provider_id, ())" in CODE)
check("the template is generated from the same tuple",
      "SECRET_NAMES.get(provider)" in CODE)

# THE THREE SHAPES the tables already describe.
check("pairs are read as tables", "if name in SECRET_PAIRS:" in CODE)
check("singles are read as one string", "elif name in SECRET_SINGLE:" in CODE)
check("everything else is read as a list", "for k in (raw or []):" in CODE)

check("a placeholder is never taken as a key",
      "is_placeholder(key)" in CODE)
check("a duplicate is never added twice", "key in have" in CODE)
check("a fingerprint is stored, per keyring.md §5",
      "kr.fingerprint(key)" in CODE)

# =====================================================================
print()
print("2 THE REAL THING — the settings screen, rendered")
# =====================================================================

at = app()
at.run()
check("settings renders without raising", not at.exception, at.exception)

# THE BOX IS GONE. Driven from the rendered page, not from the source:
# a widget can be deleted from one branch and survive in another.
up_keys = [u.key for u in at.get("file_uploader")] if hasattr(at, "get") else []
check("no file uploader anywhere on the settings screen",
      not any("key_file" in str(k) for k in up_keys), up_keys)
ta_keys = [a.key for a in at.text_area]
check("no key paste box on the settings screen",
      not any("key_paste" in str(k) for k in ta_keys), ta_keys)
btn_keys = [b.key for b in at.button]
check("no Import keys button",
      not any(str(k).endswith("_import") for k in btn_keys), btn_keys)

# AND THE SOURCE AGREES, with comments stripped.
check("the widget keys are gone from the code",
      "_key_file" not in CODE and "_key_paste" not in CODE)
check("the import closure is gone", "def _import(" not in CODE)
check("nothing calls the messy-text importers from the panel any more",
      "kr.import_keys(get_ring" not in CODE
      and "kr.import_pairs(get_ring" not in CODE)

# THE REPLACEMENT IS WIRED. This is the half that had to exist first.
check("the general loader exists", "def keys_from_secrets(" in CODE)
check("...and something calls it", "all_keys_from_secrets()" in CODE)
check("the settings screen calls it", "filled = all_keys_from_secrets()" in CODE)

# ---- THE LOADER ACTUALLY LOADING, against real-shaped secrets --------
#
# EVERYTHING ABOVE THIS POINT IS A SOURCE GREP, AND FOUR MUTATIONS PROVED
# THAT IS NOT ENOUGH. Emptying all_keys_from_secrets to return {}, and
# reading Hume's pairs as a flat list, both left this suite GREEN —
# because a grep asks how the code is SPELLED and neither mutation
# changed a spelling it looked for. The rings are what the app actually
# uses, so the rings are what gets asserted.

import shutil                                    # noqa: E402

SEC = os.path.join(ROOT, ".streamlit", "secrets.toml")
BACKUP = SEC + ".testbak"
REAL = "\n".join([
    'SHEETS_URL = "https://example.invalid/exec"',
    'SHEETS_TOKEN = "x"',
    'DRIVE_SECRET = "y"',
    'APP_PASSWORDS = ["pw-one"]',
    'ADMIN_USER = "pw-one"',
    'GROQ_API_KEYS = ["gsk_stub_not_real_aaaaaaaaaaaaaaaaaaaaaaaa"]',
    'SPEECHIFY_API_KEYS = ["sk_speechifyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"]',
    'ASSEMBLYAI_API_KEYS = ["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]',
    'ANTHROPIC_API_KEY = "sk-ant-not-a-real-key-aaaaaaaaaaaaaaaaaaaa"',
    'GOOGLE_API_KEYS = ["AQ.paste_your_first_key_here",',
    '                   "AQ.realLookingKeyAAAAAAAAAAAAAAAAAAAA"]',
    '',
    '[[HUME_ACCOUNTS]]',
    'name = "account.one"',
    'key = "HKEYaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"',
    'secret = "HSECaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"',
]) + "\n"

shutil.copy(SEC, BACKUP)
try:
    open(SEC, "w").write(REAL)
    # THE LOADER LIVES BEHIND is_admin(). account_tier() is derived from
    # the name that matched at the door, so the stub user has to BE the
    # owner named in this secrets file — setting _view_tier alone would
    # be clamped straight back down, which is the point of that clamp.
    at2 = app()
    at2.session_state["_user"] = "pw-one"
    at2.session_state["_via_accounts"] = False
    at2.run()
    check("the app runs against a real-shaped secrets file",
          not at2.exception, at2.exception)
    rings = sget(at2, "_rings") or {}

    def ring_keys(pid):
        return [k.get("key") for k in (rings.get(pid) or {}).get("keys", [])]

    # THE POINT OF THE WHOLE CHANGE: keys reach the ring, no paste box.
    for pid in ("hume"):
        check("%s got its keys from Secrets, with no paste box" % pid,
              len(ring_keys(pid)) >= 1, ring_keys(pid))

    check("anthropic's SINGLE string is one key, not char by char",
          len(ring_keys("anthropic")) == 1
          and str(ring_keys("anthropic")[0]).startswith("sk-ant-"),
          ring_keys("anthropic"))

    # HUME IS A PAIR, and the half easy to lose is the secret.
    hume = (rings.get("hume") or {}).get("keys", [])
    check("hume arrived as ONE key, not two", len(hume) == 1, len(hume))
    check("...keeping its secret, which its account auth needs",
          bool(hume) and hume[0].get("secret", "").startswith("HSEC"))
    check("...and its account name, so a dead key is findable",
          bool(hume) and hume[0].get("label") == "account.one",
          hume[0].get("label") if hume else "")
    check("the api key is stored as the key, never the secret",
          bool(hume) and hume[0].get("key", "").startswith("HKEY"))

    # PLACEHOLDERS REFUSED, a real one beside them is not.
    goog = ring_keys("google")
    check("a pasted-but-unfilled placeholder never reaches a ring",
          not any("paste_your" in str(k) for k in goog), goog)

    # RUNNING IT TWICE ADDS NOTHING. Streamlit re-runs the whole script
    # on every interaction, so a loader that did not de-duplicate would
    # grow the ring on every single click.
    before = {p: len(ring_keys(p)) for p in ("anthropic")}
    at2.run()
    rings = sget(at2, "_rings") or {}
    after = {p: len(ring_keys(p)) for p in ("anthropic")}
    check("a second run adds nothing — the ring does not grow per rerun",
          before == after, (before, after))
finally:
    shutil.move(BACKUP, SEC)

check("the placeholder secrets file was put back",
      "paste_your" in open(SEC).read())

# =====================================================================
print()
print("3 THE UGLY CASES")
# =====================================================================

check("a malformed pair row is skipped, not raised",
      "except AttributeError:" in CODE)
check("a missing secret name is skipped", "if raw is None:" in CODE)
check("a broken secrets read cannot take the screen down",
      CODE.count("except Exception:") >= 2)

# THE PARSER SURVIVES ITS CALLER. keyring.md §9 names it as the
# reference implementation other apps port from; deleting it because one
# caller went would cost every other app the bugs it already fixed.
from ttt import keyring as kr                    # noqa: E402
check("import_keys still exists for other apps to port",
      callable(getattr(kr, "import_keys", None)))
check("import_pairs still exists", callable(getattr(kr, "import_pairs", None)))

# THE ORPHANS ARE GONE, and nothing that is still used went with them.
for dead in ("key_file_label", "key_paste_label", "key_paste_ph"):
    check("the orphaned string %r is removed" % dead, dead not in RAW)
for alive in ("keys_added", "test_keys_btn", "settings_owner_only"):
    check("the still-used string %r survives" % alive, alive in RAW)

# EVERY STRING THE CODE ASKS FOR MUST EXIST. Removing entries from a
# table is exactly how t() starts returning a key name to a screen.
# ANCHORED, because the first version was not. `t\("..."\)` also matches
# the tail of `st.session_state.get("_authed")` — "get(" ends in "t(" —
# so it collected 140 session-state keys and called every one a missing
# translation. A check that reports a real string as broken teaches you
# to ignore it, which is how a real one gets waved through.
asked = set(re.findall(r'(?<![A-Za-z0-9_.])t\("([a-z0-9_]+)"\)', RAW))
defined = set(re.findall(r'^\s{4}"([a-z0-9_]+)":\s*\{', RAW, re.M))
missing = sorted(asked - defined)
check("every t() the code calls has an entry (%d asked, %d defined)"
      % (len(asked), len(defined)), not missing, missing)

# BOTH LANGUAGES, on the string that replaced the removed ones.
blk = re.search(r'"keys_from_secrets":\s*\{(.*?)\}', RAW, re.S)
check("the new caption exists", blk is not None)
check("...in English and Croatian",
      blk and '"en"' in blk.group(1) and '"hr"' in blk.group(1))
check("...and carries the %s the caller formats into it",
      blk and blk.group(1).count("%s") == 2, blk.group(1) if blk else "")

# =====================================================================
print()
print("4 THE UPGRADE — somebody who already pasted keys")
# =====================================================================

# THE RING IS NOT WIPED. Keys pasted by the old version live in
# localStorage and must keep working: this change removes a way IN, not
# the keys already in.
check("load_keys still reads the existing store", "def load_keys(" in CODE)
check("...still from localStorage, so old keys survive the upgrade",
      "LS_DATA.get(PROVIDER_KEYS_LS_KEY)" in CODE)
check("the loader ADDS to the ring rather than replacing it",
      'ring.setdefault("keys", [])' in CODE and 'ring["keys"].append(' in CODE)
check("a key already on the ring is left alone, keeping its state",
      "if not key or key in have" in CODE)

# THE LIST STAYS — keyring.md §6. Removing entry must not remove the
# only honest answer to "why is this key not being used".
check("the key list is still rendered", "render_key_list(ring" in CODE)
check("a key can still be tested deliberately", "test_key(key)" in CODE)
check("hume is still tested as a PAIR", "hume_test_one(key, sec)" in CODE)

# HUME'S OWN LOADER IS NOT DUPLICATED INTO THE NEW ONE.
check("hume_keys_from_secrets still exists for the VR tab",
      "def hume_keys_from_secrets(" in CODE)

at = app()
at.run()
check("the settings screen still renders after all of it",
      not at.exception, at.exception)
check("and a non-owner still gets the owner-only caption, unchanged",
      "settings_owner_only" in RAW)

print()
print("%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
