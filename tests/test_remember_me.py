"""STAYING SIGNED IN — the session that survives a phone call.

    python3 tests/test_remember_me.py

Baba, 25.8.2026: "I start something in the app, I put the app in the
background, I come back and it asks me to log in again and I lose my
session... I come back and my work is gone. I'm very, very frustrated."

ANDROID IS WHY. Switching to WhatsApp suspends the tab, the websocket
drops, Streamlit ends the session, and session_state goes with it —
including _authed. Nothing was broken; the app had no way to know him on
the way back.

WHAT IS STORED IS NOT THE NAME. It is an HMAC of the name keyed by a
secret only the server has, with the name beside it so the server knows
whose signature to check. The stored blob is worthless on any other
deployment and cannot be computed by someone holding the phone.
"""
import hashlib, hmac, json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
code = "\n".join(l for l in app.splitlines() if not l.lstrip().startswith("#"))


def sig(user, key):
    if not key:
        return ""
    return hmac.new(key.encode(), (user or "").strip().lower().encode(),
                    hashlib.sha256).hexdigest()


SECRET = "a-server-side-secret"

print("1 THE TOKEN")
blob = {"u": "emina108", "s": sig("emina108", SECRET)}
check("1a the name is stored so the server knows whose signature to check",
      blob["u"] == "emina108")
check("1b but the LOGIN VALUE itself is not the whole of it — there is a "
      "signature beside it", len(blob["s"]) == 64, blob["s"][:8])
check("1c the signature cannot be made without the server's secret",
      sig("emina108", "") == "")
check("1d a different secret gives a different signature — so a token "
      "from one deployment is useless on another",
      sig("emina108", "other") != blob["s"])
check("1e case does not matter, because the door is case-insensitive",
      sig("EMINA108", SECRET) == sig("emina108", SECRET))
check("1f a different person gets a different signature",
      sig("marinko108", SECRET) != blob["s"])

print("\n2 WHAT THE DOOR DOES WITH IT")


def door(stored, people, secret):
    """The restore logic, on plain data."""
    try:
        b = json.loads(stored) if str(stored).startswith("{") else {}
    except Exception:
        return None, False
    who, s = str(b.get("u") or "").strip(), str(b.get("s") or "")
    want = sig(who, secret)
    if who and s and want and hmac.compare_digest(s, want) \
            and who.lower() in people:
        return who, False
    if who and s:
        return None, True          # remove the token
    return None, False


PEOPLE = {"emina108": "free", "marinko108": "free"}
who, drop = door(json.dumps(blob), PEOPLE, SECRET)
check("2a a good token signs him straight in", who == "emina108", who)
check("2b and is not thrown away", drop is False)

bad = json.dumps({"u": "emina108", "s": "0" * 64})
who, drop = door(bad, PEOPLE, SECRET)
check("2c a FORGED signature does not get in", who is None)
check("2d and the token is REMOVED, not retried on every visit for ever",
      drop is True)

gone = json.dumps({"u": "someone_removed", "s": sig("someone_removed", SECRET)})
who, drop = door(gone, PEOPLE, SECRET)
check("2e a name taken out of Secrets does not get in", who is None)
check("2f and its token is removed too", drop is True)

who, drop = door(json.dumps(blob), PEOPLE, "ROTATED")
check("2g rotating the server secret logs everyone out — the only "
      "revocation this app has", who is None)
check("2h and clears their tokens", drop is True)

print("\n2b THE UGLY CASES")
for stored, why in (("", "nothing stored"),
                    ("not json at all", "junk"),
                    ("{}", "empty object"),
                    ('{"u":"emina108"}', "no signature"),
                    ('{"s":"abc"}', "no name"),
                    ('{"u":"","s":""}', "both blank")):
    who, drop = door(stored, PEOPLE, SECRET)
    check("2i %-18s does not sign anybody in" % why, who is None, who)
check("2j and a missing secret cannot accidentally authorise anyone",
      door(json.dumps({"u": "emina108", "s": ""}), PEOPLE, "")[0] is None)

print("\n3 THE APP IS WIRED THIS WAY")
print("       searched app.py CODE for the door, the signature and the box")
# SCOPED TO THE DOOR BLOCK. My first version asked whether
# "hmac.compare_digest" appeared ANYWHERE in app.py — and it does, in the
# older accounts path — so replacing the actual comparison with `and True`
# left the check GREEN. A check that cannot fail is a rumour.
_door = code[code.index('if not st.session_state.get("_authed")'):]
# ANCHORED ON CODE, NOT A COMMENT. My first end marker was a comment
# line — and `code` has the comments stripped, so index() raised and the
# whole file died instead of reporting. Bounded by the next top-level
# statement instead.
_door = _door[:_door.index("def _small(")] if "def _small(" in _door \
    else _door[:2600]
print("       the door block: %d chars" % len(_door))
check("3a the remembered login is ON — v185 turned it off and the reason "
      "no longer applies", "AUTH_LS_KEY" in _door, _door[:80])
check("3a2 and the signature is compared with compare_digest, IN THE "
      "DOOR, not merely mentioned somewhere in the file",
      "hmac.compare_digest(_sig, _want)" in _door, _door[-300:])
check("3b it checks LOCALLY — no Apps Script round trip, which is why it "
      "was switched off before",
      "ACCOUNTS.remember_login" not in code.split("if not st.session_state"
                                                  ".get(\"_authed\")")[-1])
check("3c the secret comes from Secrets, never a constant in the file",
      "REMEMBER_SECRET" in code and "st.secrets.get(name)" in code)
check("3d with no secret at all it signs NOTHING rather than signing "
      "with something everyone can read", 'return ""' in code)
check("3e the name must still be in Secrets, signature or not",
      "_named_people()" in code)
check("3f a token that no longer checks out is REMOVED",
      "queue_ls(removes=[AUTH_LS_KEY])" in code)
check("3g the box is ticked by default, as asked",
      'setdefault("_remember_me", True)' in code)
check("3h and unticking it forgets instead of remembering",
      re.search(r'if st\.session_state\.get\("_remember_me", True\):'
                r'\s*\n\s*remember_me\(typed\)\s*\n\s*else:', code) is not None)
check("3i logging out forgets too",
      code.count("queue_ls(removes=[AUTH_LS_KEY])") >= 3,
      code.count("queue_ls(removes=[AUTH_LS_KEY])"))
check("3j nothing here can raise on the login screen — the whole restore "
      "is inside a try",
      "except Exception:" in code[code.index("if not st.session_state"
                                             '.get("_authed")'):][:2600])

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
