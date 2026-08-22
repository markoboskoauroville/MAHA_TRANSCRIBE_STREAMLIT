"""THE PEOPLE PANEL — step 9, and the owner's power to lock everybody out.

Every check here asks what the panel CONTAINS, never whether a function
was called. §63 is the reason: the box bug survived three sessions of
tests that asserted the right calls were made, because the calls WERE
being made correctly and the value still never arrived.

The accounts script is stood up for real on localhost rather than
patched, for the reason test_accounts.py gives: AppTest reloads
ttt.accounts on every run, so a stubbed function is thrown away before
the app ever calls it.

    python3 tests/test_admin_users.py
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


# ── the stub accounts script ──────────────────────────────────────────

ADMIN_TOK = "ADMIN-TOK"
ADMIN_PW = "admin-password"
SEEN = []
MODE = {"dead": False, "empty": False}
PEOPLE = {}
MADE = {"n": 0}


def reset_world():
    SEEN[:] = []
    MODE.update({"dead": False, "empty": False})
    PEOPLE.clear()
    PEOPLE.update({
        "admin": {"engine": "", "note": "", "folder": "admin", "hashed": True},
        "baba": {"engine": "studio", "note": "grandfather",
                 "folder": "baba", "hashed": True},
        "mama": {"engine": "", "note": "", "folder": "mama", "hashed": False},
    })
    MADE["n"] = 0


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _reply(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n).decode())
        SEEN.append(body)
        if MODE["dead"]:
            self.send_response(500)
            self.end_headers()
            return
        if body.get("token") != ADMIN_TOK:
            return self._reply({"ok": False, "error": "admin token required"})

        what = body.get("what")
        who = str(body.get("username") or "").strip().lower()

        # The second factor, exactly as the real script does it.
        def proved():
            return (str(body.get("admin_user") or "").lower() == "stub"
                    and body.get("admin_password") == ADMIN_PW)

        if what == "users":
            if MODE["empty"]:
                return self._reply({"ok": True, "users": []})
            return self._reply({"ok": True, "users": [
                dict(v, user=k) for k, v in PEOPLE.items()]})

        if what == "user_create":
            if who in PEOPLE:
                return self._reply({"ok": False, "error": "that name is taken"})
            MADE["n"] += 1
            PEOPLE[who] = {"engine": "", "note": str(body.get("note") or ""),
                           "folder": who, "hashed": True}
            return self._reply({"ok": True, "user": who,
                                "password": "made-pw-%d" % MADE["n"]})

        if what == "user_password":
            if not proved():
                return self._reply({"ok": False,
                                    "error": "administrator password required"})
            return self._reply({"ok": True, "user": who, "password": "reset-pw-1"})

        if what == "user_delete":
            if not proved():
                return self._reply({"ok": False,
                                    "error": "administrator password required"})
            PEOPLE.pop(who, None)
            return self._reply({"ok": True, "user": who, "recordings": "kept"})

        if what == "user_engine":
            eng = str(body.get("engine") or "")
            PEOPLE[who]["engine"] = eng
            return self._reply({"ok": True, "user": who, "engine": eng})

        return self._reply({"ok": False, "error": "unknown request"})


srv = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:%d/" % srv.server_address[1]


# ── the app ───────────────────────────────────────────────────────────

def panel(admin=True, token=ADMIN_TOK, url=URL):
    reset_world()
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=90)
    at.secrets["APP_PASSWORDS"] = ["stub"]
    at.secrets["ADMIN_USER"] = "stub"
    at.secrets["GROQ_API_KEYS"] = ["gsk_test"]
    if url:
        at.secrets["AUTH_URL"] = url
    if token:
        at.secrets["AUTH_ADMIN_TOKEN"] = token
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub" if admin else "somebody"
    at.session_state["active_tab"] = "settings"
    return at


def page(at):
    """EVERYTHING THE PANEL PUT ON THE SCREEN, IN DOCUMENT ORDER.

    Walked from at.main rather than collected with at.get(kind), and the
    difference matters: at.get gathers all the text, THEN all the code,
    THEN all the captions, so anything asking what comes before what
    would be answering a question about the collector instead of about
    the page. Check 13 is exactly that question.
    """
    bits = []

    def walk(node):
        kids = getattr(node, "children", None)
        if kids is None:
            return
        for child in (kids.values() if hasattr(kids, "values") else kids):
            v = getattr(child, "value", None)
            if isinstance(v, str):
                bits.append(v)
            walk(child)

    walk(at.main)
    return "  ".join(bits)


def sget(at, key, default=None):
    """AppTest's session_state has no .get()."""
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def keys(at):
    return [b.key for b in at.get("button")]


def field(at, key):
    return [x for x in at.text_input if x.key == key][0]


def press(at, key):
    [b for b in at.get("button") if b.key == key][0].click().run()
    return at


print("THE PEOPLE PANEL\n")

# ── who may see it ────────────────────────────────────────────────────
at = panel(admin=False)
at.run()
check("1 A NON-ADMIN NEVER SEES THE PANEL", "baba" not in page(at)
      and not [k for k in keys(at) if k.startswith("ad_")], keys(at))

at = panel(token="")
at.run()
check("2 no admin token: it says so and lists nobody",
      "not connected" in page(at) and "baba" not in page(at), page(at)[:200])
check("3 and a missing token is not an error — the app still runs",
      not at.exception, at.exception)

# ── None and [] are different answers ─────────────────────────────────
at = panel()
MODE["dead"] = True
at.run()
check("4 A SCRIPT THAT DID NOT ANSWER SAYS SO, and says nobody is locked "
      "out", "did not answer" in page(at), page(at)[:200])

at = panel()
MODE["empty"] = True
at.run()
check("5 AND AN EMPTY TAB IS A DIFFERENT SENTENCE — conflating these two "
      "is what made the old panel say 'no users tab yet'",
      "empty" in page(at) and "did not answer" not in page(at), page(at)[:200])

# ── the list ──────────────────────────────────────────────────────────
at = panel()
at.run()
p = page(at)
check("6 everybody is listed", "baba" in p and "mama" in p and "admin" in p, p[:200])
check("7 somebody with no password yet is marked", "no password yet" in p, p[:200])
check("8 NO SECRET IS EVER RENDERED — not a hash, not a token",
      ADMIN_TOK not in p and "folder" not in p, p[:200])
check("9 each person has reset and delete", "ad_reset_baba" in keys(at)
      and "ad_del_baba" in keys(at), keys(at))

rename = [b for b in at.get("button") if b.key == "ad_rename_baba"]
check("10 RENAME IS PRESENT AND DISABLED — the main script still builds "
      "USERS/<user>/ from the login name", rename and rename[0].disabled,
      [b.key for b in at.get("button")])

# ── making somebody ───────────────────────────────────────────────────
at = panel()
at.run()
field(at, "_adm_name").set_value("deda")
field(at, "_adm_note").set_value("djed")
press(at, "ad_add")
check("11 a new person is created", "deda" in PEOPLE, list(PEOPLE))
check("12 THE PASSWORD IS SHOWN, once", "made-pw-1" in page(at), page(at)[:300])
check("13 and it is shown ABOVE the list, not under it — under it, it is "
      "below the fold on a phone",
      page(at).index("made-pw-1") < page(at).index("Add a person"),
      page(at)[:300])
check("14 with the instruction to write it down", "Write this down" in page(at))

press(at, "adm_written")
check("15 AND IT IS NEVER SHOWN AGAIN once dismissed",
      "made-pw-1" not in page(at), page(at)[:300])

at = panel()
at.run()
field(at, "_adm_name").set_value("baba")
press(at, "ad_add")
check("16 a taken name is refused, in the script's own words",
      "taken" in page(at), page(at)[:300])
# NOT "made-pw" not in page — a create that failed has no password to
# print, so that string is absent whether the box is drawn or not. What
# a half-succeeded create actually looks like is an EMPTY code box under
# the words "write this down", which is the thing to refuse.
check("17 and NO password box appears for a create that failed — not "
      "even an empty one under the instruction to write it down",
      "Write this down" not in page(at)
      and not sget(at, "_adm_shown"), sget(at, "_adm_shown"))

# ── the second factor ─────────────────────────────────────────────────
at = panel()
at.run()
press(at, "ad_del_baba")
check("18 delete asks first, and names the person",
      "Delete baba" in page(at), page(at)[:300])
check("19 the strip appears ONLY for the person pressed",
      "ad_yes_baba" in keys(at) and "ad_yes_mama" not in keys(at), keys(at))
check("20 and it says the recordings are kept", "recordings are kept" in page(at))

field(at, "_adm_proof").set_value("wrong-password")
press(at, "ad_yes_baba")
check("21 A WRONG ADMINISTRATOR PASSWORD DELETES NOBODY",
      "baba" in PEOPLE, list(PEOPLE))
check("22 and the refusal is shown", "administrator password" in page(at),
      page(at)[:300])

at = panel()
at.run()
press(at, "ad_del_baba")
field(at, "_adm_proof").set_value(ADMIN_PW)
press(at, "ad_yes_baba")
check("23 the right password deletes", "baba" not in PEOPLE, list(PEOPLE))
# NOT "baba" not in page(at) — the panel says "baba is gone", so the
# name is rightly on the screen. What must disappear is the ROW.
check("24 and the list refreshes without their row",
      "ad_del_baba" not in keys(at) and "ue_baba_studio" not in keys(at),
      keys(at))
check("24b while saying plainly that they are gone",
      "baba is gone" in page(at), page(at)[-200:])
check("25 THE ADMINISTRATOR'S OWN PASSWORD IS NEVER PUT ON THE SCREEN",
      ADMIN_PW not in page(at), page(at)[:300])
sent = [b for b in SEEN if b.get("what") == "user_delete"][-1]
check("26 it really was sent to the script, with the admin's name",
      sent.get("admin_password") == ADMIN_PW
      and sent.get("admin_user") == "stub", sent)

# ── cancelling ────────────────────────────────────────────────────────
at = panel()
at.run()
press(at, "ad_del_baba")
field(at, "_adm_proof").set_value(ADMIN_PW)
press(at, "ad_no_baba")
check("27 cancel deletes nobody", "baba" in PEOPLE, list(PEOPLE))
# THE OBSERVABLE GUARANTEE, not the mechanism: reopening the strip must
# present an empty box, never the password typed a minute ago.
#
# An honest limit, recorded rather than papered over: Streamlit itself
# drops a widget's key when the widget stops rendering (§63, from the
# other side), so deleting the explicit pop in close_ask() does NOT
# change what happens here — the mutation survives this check and always
# will. The pop stays as belt-and-braces for the day that key is read by
# something other than the widget; it is not what makes this true.
press(at, "ad_del_baba")
check("28 reopening the strip presents an EMPTY password box",
      not (field(at, "_adm_proof").value or ""),
      field(at, "_adm_proof").value)
check("28b and nothing was deleted along the way", "baba" in PEOPLE, list(PEOPLE))

# ── resetting ─────────────────────────────────────────────────────────
at = panel()
at.run()
press(at, "ad_reset_baba")
check("29 reset asks first too", "New password for baba" in page(at),
      page(at)[:300])
check("30 and warns that their devices are signed out",
      "signed out" in page(at), page(at)[:300])
field(at, "_adm_proof").set_value(ADMIN_PW)
press(at, "ad_yes_baba")
check("31 the new password is shown once", "reset-pw-1" in page(at),
      page(at)[:300])

# ── engines ───────────────────────────────────────────────────────────
at = panel()
at.run()
press(at, "ue_mama_studio")
check("32 an engine can be assigned from here",
      PEOPLE["mama"]["engine"] == "studio", PEOPLE["mama"])
check("33 THROUGH THE ACCOUNTS SCRIPT, not the main one — one script "
      "owns the users tab",
      any(b.get("what") == "user_engine" for b in SEEN), SEEN[-1:])
press(at, "ue_mama_none")
check("34 and taken away again, which is the way back to the global one",
      PEOPLE["mama"]["engine"] == "", PEOPLE["mama"])

# ── §1: none of this may ever shut the door ───────────────────────────
at = panel()
at.run()
MODE["dead"] = True
press(at, "ad_reset_baba")
field(at, "_adm_proof").set_value(ADMIN_PW)
press(at, "ad_yes_baba")
check("35 A DEAD SCRIPT IS A SENTENCE, NEVER AN EXCEPTION (§1)",
      not at.exception, at.exception)
check("36 and it says it could not be reached",
      "unreachable" in page(at), page(at)[:300])

print("\n{} passed, {} failed".format(passed, failed))


def test_admin_users():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_admin_users.py` is how it is meant to be read."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
