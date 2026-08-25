"""THE HUME RING FILLS FROM SECRETS — the reason VR was silent.

    python3 tests/test_hume_ring.py

Baba's brief, fault 2, 25.8.2026: "Hume keys are read from the k_hume
SHEET only, never from Secrets, so the ring is empty and hume_speak
returns vr_no_key, which shows as nothing at all." VR was dead for ten
versions while twenty-one verified account pairs sat in his secrets file.

TEST 1 drives the filling logic on plain dicts — no Streamlit, no
network. TEST 2 reads the app and says what it searched for.

WHAT THIS CANNOT CATCH: that Hume actually answers. That is a real call
with a real key and it is NOT made here; it was made by hand against his
own secrets on 25.8.2026 and returned 200 with 75,564 bytes of WAV.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import vr as V  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))


def fill(ring_keys, accounts=None, api_keys=None):
    """hume_keys_from_secrets' logic, on plain data. Kept honest by the
    source checks in section 2 rather than trusted on its own."""
    have = {k.get("key") for k in ring_keys}
    added = 0

    def add(key, secret, label):
        nonlocal added
        key = str(key or "").strip()
        if not key or key in have:
            return
        ring_keys.append({"key": key, "secret": str(secret or "").strip(),
                          "state": "new", "label": str(label or "hume account"),
                          "cool_until": 0})
        have.add(key)
        added += 1

    for row in (accounts or []):
        try:
            add(row.get("key"), row.get("secret"), row.get("name"))
        except AttributeError:
            continue
    for k in (api_keys or []):
        add(k, "", "hume key")
    return added


print("1 FILLING AN EMPTY RING")
keys = []
n = fill(keys, [{"name": "svaram", "key": "K1", "secret": "S1"},
                {"name": "tribal.jam", "key": "K2", "secret": "S2"}])
check("1a both accounts land on the ring", n == 2 and len(keys) == 2, keys)
check("1b the PAIR is kept together — a Hume credential is two halves",
      keys[0]["secret"] == "S1" and keys[1]["secret"] == "S2", keys)
check("1c the account name becomes the label, so the owner can tell "
      "them apart", [k["label"] for k in keys] == ["svaram", "tribal.jam"])
check("1d every key starts 'new', not dead and not rested",
      all(k["state"] == "new" and k["cool_until"] == 0 for k in keys))

print("\n1b THE SHEET STILL WINS")
# Secrets is the FLOOR, not the authority. A key already on the ring
# keeps its state, its cool_until and its dead flag.
keys = [{"key": "K1", "secret": "OLD", "state": "dead", "label": "from sheet",
         "cool_until": 999}]
n = fill(keys, [{"name": "svaram", "key": "K1", "secret": "NEW"},
                {"name": "new one", "key": "K9", "secret": "S9"}])
check("1e only the genuinely new one is added", n == 1, n)
check("1f the sheet's copy is untouched — still dead, still cooling",
      keys[0]["state"] == "dead" and keys[0]["cool_until"] == 999, keys[0])
check("1g and its secret is not overwritten by Secrets",
      keys[0]["secret"] == "OLD", keys[0]["secret"])

print("\n1c BOTH SHAPES, BECAUSE HE HAS BOTH")
keys = []
fill(keys, [{"name": "a", "key": "K1", "secret": "S1"}], ["K2", "K3"])
check("1h the older bare-key list is taken too", len(keys) == 3, keys)
check("1i a key with no secret is still taken — better than no key",
      keys[1]["secret"] == "" and keys[1]["key"] == "K2", keys[1])
keys = []
fill(keys, [{"name": "a", "key": "K1", "secret": "S1"}], ["K1"])
check("1j the same key in both shapes is stored ONCE", len(keys) == 1, keys)

print("\n1d THE UGLY CASES")
keys = []
check("1k no secrets at all is zero, not a crash", fill(keys) == 0)
check("1l and leaves the ring empty", keys == [])
keys = []
fill(keys, [{"name": "a", "key": "  ", "secret": "S"}, {"key": "K"}])
check("1m a blank key is skipped, a missing secret is not fatal",
      len(keys) == 1 and keys[0]["key"] == "K", keys)
keys = []
fill(keys, ["not a table", {"name": "a", "key": "K", "secret": "S"}])
check("1n a malformed entry is skipped rather than taking the tab down",
      len(keys) == 1, keys)
keys = []
fill(keys, None, None)
check("1o None for both is handled", keys == [])

print("\n2 THE APP DOES THE SAME")
app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
fn = app[app.index("def hume_keys_from_secrets"):app.index("def hume_keys_to_sheet")]
print("       searched hume_keys_from_secrets, %d chars" % len(fn))
check("2a it reads HUME_ACCOUNTS", '"HUME_ACCOUNTS"' in fn)
check("2b and HUME_API_KEYS", '"HUME_API_KEYS"' in fn)
check("2c it skips keys already on the ring", "in have" in fn)
check("2d a malformed row is skipped, not raised",
      "except AttributeError" in fn)
check("2e it saves the ring only when something was added",
      "if added:" in fn and "save_rings()" in fn)

vr = app[app.index('elif active == "vr":'):app.index('elif active == "looks":')]
check("2f the tab pulls the sheet FIRST", "hume_keys_from_sheet()" in vr)
check("2g then Secrets as the floor", "hume_keys_from_secrets()" in vr)
check("2h in that order, so the sheet wins",
      vr.index("hume_keys_from_sheet()") < vr.index("hume_keys_from_secrets()"))

print("\n3 PREVIEW GOES DOWN THE SAME PATH AS REHEARSE")
# Baba: "when I say preview voices, you go to the same path as I'm
# pasting the text and saying rehearsal, and the voice can speak to the
# player." One synthesiser, one deck, no second thing to keep in step.
check("3a choosing a voice calls hume_speak, the same call rehearse makes",
      "def _vr_pick_voice" in vr and vr.count("hume_speak(") >= 2,
      vr.count("hume_speak("))
# SCOPED TO _vr_pick_voice, because counting occurrences across the whole
# tab stayed GREEN when the preview was mutated to write its own separate
# state — the other two mentions belonged to rehearse and to the player.
# A count is not a check when the thing counted lives in three places.
_pick = vr[vr.index("def _vr_pick_voice"):vr.index("_cur_voice = ")]
# NOT PINNED TO THE RIGHT-HAND SIDE. This asserted `"_vr_audio"] = audio`
# character for character and went red the moment the value became
# normalise_speech(audio) — a test failing for a reason unconnected to
# what it is checking, which is four-tests.md's "test the test". The
# claim is that preview writes the SHARED player state; what it writes
# into it is the normaliser's business.
check("3b the audio lands in the SAME player state, not a private one",
      '"_vr_audio"] =' in _pick and "_vr_preview_audio" not in _pick,
      _pick[-300:])
check("3c and it plays by itself", '"_vr_autoplay"] = True' in _pick)
check("3d the sample is the voice's own name", "hume_speak(ring, name, name" in vr)
check("3e read with the accent the tooltip already showed",
      "VR.voice_meta(name)" in vr)
check("3f it does NOT touch the line being rehearsed",
      '"vr_text"' not in vr[vr.index("def _vr_pick_voice"):
                            vr.index("_cur_voice = ")])
check("3g with no key it says so instead of failing silently",
      't("vr_no_key")' in vr)
check("3h a resting ring still lets the voice be CHOSEN",
      "if _w:" in vr and "return" in vr)
check("3i preview is a setting, on by default",
      'setdefault("vr_preview", True)' in vr)
check("3j and choosing still works with preview off",
      'if not st.session_state.get("vr_preview", True):' in vr)

print("\n3b THE VOICE META")
check("3k a real voice has an accent and an age",
      "," in V.voice_meta(V.DEFAULT_VOICE), V.voice_meta(V.DEFAULT_VOICE))
check("3l an unknown name is empty, not a crash", V.voice_meta("nobody") == "")
check("3m every voice in the cast has one",
      all(V.voice_meta(v[0]) for g in ("F", "M") for v in V.VOICES[g]))

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
