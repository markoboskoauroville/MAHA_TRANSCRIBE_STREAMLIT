"""MUST CHANGE ON FIRST LOGIN — the one screen a new person cannot skip.

    python3 tests/test_must_change.py

The password they were given was typed into a panel, read aloud and sent
through a chat app. This is where it stops being the one that opens the
door — so the test that matters is not that the screen renders, it is
that NOTHING ELSE DOES while the flag is set.

The accounts script is a real stub over HTTP, not a patched function:
AppTest re-imports `ttt.accounts` on every run, so a patched module is
thrown away before the app calls it (HANDOVER §75).
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402

passed = failed = 0
LOGIN_TOK = "login-token"
SEEN = []
STATE = {"must": True, "password": "given-pw-1", "change_ok": True}


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


class H(BaseHTTPRequestHandler):
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
        body = json.loads(self.rfile.read(
            int(self.headers.get("Content-Length", 0))) or b"{}")
        SEEN.append(body)
        what = body.get("what")
        if what == "login":
            if str(body.get("password")) != STATE["password"]:
                return self._reply({"ok": False, "error": "no"})
            return self._reply({"ok": True, "user": "emina", "engine": "normal",
                                "note": "", "must_change": STATE["must"]})
        if what == "password_change":
            if not STATE["change_ok"]:
                return self._reply({"ok": False, "error": "no"})
            if str(body.get("old_password")) != STATE["password"]:
                return self._reply({"ok": False, "error": "no"})
            STATE["must"] = False
            STATE["password"] = str(body.get("new_password"))
            return self._reply({"ok": True, "user": "emina"})
        return self._reply({"ok": False, "error": "unknown request"})


srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:{}/".format(srv.server_port)


def app(must=True, done=False):
    STATE["must"] = must
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=90)
    at.secrets["APP_PASSWORDS"] = ["stub"]
    at.secrets["ADMIN_USER"] = "stub"
    at.secrets["GROQ_API_KEYS"] = ["gsk_test"]
    at.secrets["AUTH_URL"] = URL
    at.secrets["AUTH_LOGIN_TOKEN"] = LOGIN_TOK
    at.session_state["_authed"] = True
    at.session_state["_user"] = "emina"
    # THE PANEL ONLY EXISTS FOR AN ACCOUNTS LOGIN. Somebody who came
    # through APP_PASSWORDS has no row in the users tab to change, and
    # the script would answer a flat no that reads like a bug. This flag
    # is what the app sets on a real login, so the test says the same
    # thing rather than working around the condition.
    at.session_state["_via_accounts"] = True
    at.session_state["active_tab"] = "transcribe"
    if must:
        at.session_state["_must_change"] = True
    if done:
        at.session_state["_must_done"] = True
    return at


def page(at):
    out = []
    for kind in ("markdown", "text", "header", "subheader", "caption",
                 "error", "success", "code"):
        for el in at.get(kind):
            out.append(str(getattr(el, "value", "")))
    return "\n".join(out)


def sget(at, key, default=None):
    """AppTest's session_state is not a dict and has no .get()."""
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def field(at, key):
    return [x for x in at.text_input if x.key == key][0]


print("CHANGE YOUR PASSWORD — A RECOMMENDATION\n")

# WHAT A NORMAL SESSION LOOKS LIKE, measured rather than guessed. The
# first version of this listed key prefixes it expected to see and was
# checking its own guesses; this asks the app.
plain = app(must=False)
plain.run()
normal_keys = set(k for k in (b.key for b in plain.get("button")) if k)

# --- the notice, with the app behind it -------------------------------
at = app(must=True)
at.run()
check("1 the app renders", not at.exception, at.exception)
# IT IS A NOTICE NOW, NOT A GATE (v136).
#
# Baba: "just recommend to change the password, but it should work
# immediately without stopping user from using the app... we are not
# torturing the user or forcing it to do anything."
#
# THE CHECK BELOW USED TO ARGUE THE OTHER WAY, and its argument is kept
# here rather than deleted, because it was not wrong — it said: "a
# banner can be dismissed; a screen cannot, and the password that went
# through WhatsApp is still the one that opens the door until this is
# done." That is exactly what this change costs.
#
# It is still the right call. Standing between his mother and the one
# thing she opened the app to do, over a password she did not choose
# and cannot yet type, is the larger harm. The flag is NOT cleared by
# dismissing, so the nudge returns next session: a reminder that does
# not give up, rather than a wall.
# SHORT ENOUGH FOR ONE LINE. The first wording ran to two and broke
# mid-sentence — "Worth / changing." — which made the widest thing on
# the screen the one saying the least. Baba: "it looks unprofessional
# and amateurish", and a sentence broken in the wrong place was most of
# why. The check is on the MEANING, not on the exact words, so a better
# sentence does not fail it.
_p = page(at).lower()
check("2 it says why",
      "chosen for you" in _p or "odabrao netko drugi" in _p, page(at)[:200])

keys = [b.key for b in at.get("button")]
check("3 THE APP IS RIGHT THERE. Not stopped, not hidden — the notice "
      "sits above it and the person can ignore it",
      bool(normal_keys) and normal_keys <= set(k for k in keys if k),
      sorted(normal_keys - set(k for k in keys if k)))
check("3b including the writing surface, so the app is usable",
      bool(at.get("text_area")), len(at.get("text_area")))
check("4 a link straight to where it is done",
      "_must_go" in keys, keys)
check("4b and a way past it",
      "_must_later_btn" in keys, keys)

# DISMISSING IT DOES NOT CLEAR THE FLAG. "later" means later, not never
# — the reminder is still owed next session, and only an actual change
# settles it.
[b for b in at.get("button") if b.key == "_must_later_btn"][0].click().run()
check("4c dismissing hides it for this session",
      "_must_later_btn" not in [b.key for b in at.get("button")],
      [b.key for b in at.get("button")])
check("4d but the flag stands, so it asks again next time",
      sget(at, "_must_change") is True, sget(at, "_must_change"))


# ── the change itself now lives in Settings ───────────────────────────
#
# There is no longer a separate full-screen form with its own fields.
# Baba: "offer the link directly to that" — the notice sends people to
# the grey gear, where the change-password panel already existed. Two
# forms doing one job was two places to keep right, and the gate's copy
# is the one that went.
#
# So these drive the panel that survived: _pw_cur / _pw_new / _pw_rep,
# on the `looks` tab.

# --- it will not accept two different passwords -----------------------
at = app(must=True)
at.session_state["active_tab"] = "looks"
at.run()
field(at, "_pw_cur").set_value("given-pw-1")
field(at, "_pw_new").set_value("moja-nova-lozinka")
field(at, "_pw_rep").set_value("nesto-drugo")
[b for b in at.get("button") if b.key == "pw_change_btn"][0].click().run()
# THE PANEL SAYS IT IN ITS OWN WORDS. The gate said "do not match";
# this one has always had its own phrasing, and asserting the gate's
# copy against the panel would be testing a string that never existed
# here.
check("5 two that do not match are refused, before the script is asked",
      ("match" in page(at).lower() or "isti" in page(at).lower())
      and not any(b.get("what") == "password_change" for b in SEEN), page(at)[:200])

# --- the real change --------------------------------------------------
at = app(must=True)
at.session_state["active_tab"] = "looks"
at.run()
field(at, "_pw_cur").set_value("given-pw-1")
field(at, "_pw_new").set_value("moja-nova-lozinka")
field(at, "_pw_rep").set_value("moja-nova-lozinka")
[b for b in at.get("button") if b.key == "pw_change_btn"][0].click().run()
sent = [b for b in SEEN if b.get("what") == "password_change"]
check("6 THE CURRENT PASSWORD IS THE PROOF, and it is the one they were "
      "given — the login token alone changes nothing",
      bool(sent) and sent[-1].get("old_password") == "given-pw-1", sent[-1:])
check("7 the flag is cleared in the session once it succeeds",
      not sget(at, "_must_change")
      and sget(at, "_must_done") is True,
      sget(at, "_must_change"))

# --- a wrong current password does not clear anything -----------------
STATE["password"] = "given-pw-1"
at = app(must=True)
at.session_state["active_tab"] = "looks"
at.run()
field(at, "_pw_cur").set_value("wrong-one")
field(at, "_pw_new").set_value("moja-nova-lozinka")
field(at, "_pw_rep").set_value("moja-nova-lozinka")
[b for b in at.get("button") if b.key == "pw_change_btn"][0].click().run()
check("8 a wrong current password leaves them on the screen",
      sget(at, "_must_change") is True
      and not sget(at, "_must_done"),
      sget(at, "_must_change"))

# --- and it never appears for anybody else ----------------------------
at = app(must=False)
at.run()
check("9 nobody without the flag is stopped",
      "Choose your own password" not in page(at), page(at)[:200])
check("10 NOR IS ANYONE WHEN THE SCRIPT SAYS NOTHING AT ALL — an older "
      "deployment returns no such field, and the safe direction is that "
      "nobody is asked rather than everybody being stuck",
      not sget(at, "_must_change"),
      sget(at, "_must_change"))

at = app(must=True, done=True)
at.run()
check("11 and a stale reply cannot ask twice in one session",
      "Choose your own password" not in page(at), page(at)[:200])

srv.shutdown()
print("\n{} passed, {} failed".format(passed, failed))


def test_must_change():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_must_change.py` is how it is meant to
    be read."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
