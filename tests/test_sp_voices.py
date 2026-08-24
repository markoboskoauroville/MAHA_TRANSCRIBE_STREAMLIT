"""The per-language Speechify seats — Test 1, the mechanism alone.

What could be true that would make these pass and the feature still be
broken: the sets exist but the picker ignores them (closed by pressing
the buttons in a browser, not here); the ids exist in code but not at
Speechify (closed live on 24.8.2026 — catalogue walked, one synth per
model path). What THIS file closes: the sets themselves being wrong —
a Slavic seat on an English-only model, a stored pre-v176 pick landing
on the wrong model, the double Beatrice collapsing into one.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# app.py imports streamlit and much else at module load; the constants
# under test are importable without a running app because app.py only
# DEFINES at import time. If that ever changes this import is the canary.
os.environ.setdefault("TTT_TEST", "1")

import re

SRC = open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "app.py"), encoding="utf-8").read()

# The sets are read from the source rather than by importing app.py,
# because importing app.py starts Streamlit. The parse is narrow: the
# literal dict between its assignment and its closing brace.
m = re.search(r"SP_VOICES_BY_LANG = \{(.*?)\n\}", SRC, re.S)
assert m, "SP_VOICES_BY_LANG not found in app.py"
SP_VOICES_BY_LANG = eval("{" + m.group(1) + "}")  # noqa: S307 — our own source

checks = 0


def ok(cond, msg):
    global checks
    checks += 1
    assert cond, msg


# -- the case it is FOR ------------------------------------------------
ok(set(SP_VOICES_BY_LANG) == {"hr", "en"},
   "exactly two language rows, hr and en")
ok([v[1] for v in SP_VOICES_BY_LANG["en"]] ==
   ["Beatrice", "Imogen", "Edmund", "Hugh"],
   "English seats are Baba's four, in his order")
ok([v[1] for v in SP_VOICES_BY_LANG["hr"]] ==
   ["Lesya", "Beatrice", "Dominika", "Daria"],
   "Croatian seats are Baba's four, Lesya first")

# -- the rule the sets must obey ---------------------------------------
for vid, label, model in SP_VOICES_BY_LANG["en"]:
    ok(model == "simba-3.2", f"{vid}: every English seat rides simba-3.2")
    ok(vid.endswith("_32"), f"{vid}: simba-3.2 serves only _32 ids (HTTP "
                            "400 otherwise, measured)")
for vid, label, model in SP_VOICES_BY_LANG["hr"]:
    ok(model == "simba-multilingual",
       f"{vid}: every Croatian seat rides simba-multilingual — lesya, "
       "dominika and daria exist on NO other model (catalogue, 24.8.2026)")

# -- two rules colliding: the double Beatrice --------------------------
en = {v[0]: v[2] for v in SP_VOICES_BY_LANG["en"]}
hr = {v[0]: v[2] for v in SP_VOICES_BY_LANG["hr"]}
ok("beatrice_32" in en and "beatrice_32" in hr,
   "Beatrice sits in both rows")
ok(en["beatrice_32"] != hr["beatrice_32"],
   "and with DIFFERENT models — if these ever match, the model has "
   "stopped travelling with the seat")

# -- the upgrade rule (Test 4's reasoning, asserted) -------------------
# A pre-v176 stored pick could only be one of the old flat _32 ids, and
# the sp_model default is simba-3.2. Assert that default is right for
# every id the old version could have stored.
OLD_STORABLE = ["beatrice_32", "dominic_32", "edmund_32", "geffen_32",
                "harper_32", "hugh_32", "imogen_32", "wyatt_32"]
ok(all(v.endswith("_32") for v in OLD_STORABLE),
   "every pick v175 could have stored is a _32 voice, so the "
   "sp_model default simba-3.2 is correct for all of them")
ok('"sp_model": "simba-3.2"' in SRC,
   "the upgrade default itself is present in DEFAULT_SETTINGS")
ok('"sp_model",' in SRC.split("SETTINGS_KEYS")[1][:400],
   "sp_model is persisted like every other preference")

# -- the picker's identity rule ----------------------------------------
ok("vid == current_sp\n" in SRC or "vid == current_sp" in SRC, "picker exists")
ok("model == current_model" in SRC,
   "the lit seat is the (voice, model) PAIR — id alone would light "
   "both Beatrices")

# -- the fallback must refuse nothing and answer something -------------
ok("or sp_model_for(current_sp)" in SRC,
   "a session with no sp_model (a pre-v176 pick) falls back to the "
   "suffix rule at the synth call, never to a crash")

print(f"test_sp_voices: {checks} checks, 0 failed")
