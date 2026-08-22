"""THE ACCOUNTS SCRIPT, AND THE DOOR THAT MUST NEVER SHUT.

§1 again: a failure on the login screen is total. So every one of these
asks the same question from a different angle — when the accounts script
does not answer, does APP_PASSWORDS still let you in?

    python3 tests/test_accounts.py
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402

from ttt import accounts  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def fresh(**secrets):
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=90)
    at.secrets["APP_PASSWORDS"] = ["stub"]
    at.secrets["ADMIN_USER"] = "stub"
    # Without a Groq key app.py stops at "no Groq key in Secrets" before
    # it ever draws the tab bar, and every check past the login screen
    # sees an empty page.
    at.secrets["GROQ_API_KEYS"] = ["gsk_test"]
    for k, v in secrets.items():
        at.secrets[k] = v
    return at


def box(at, key):
    return [x for x in at.text_input if x.key == key][0]


def sget(at, key, default=None):
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def sign_in(at, user, pw):
    at.run()
    # A RUN PER BOX, exactly as a person fills the form. Setting both and
    # running once looks the same and is not: the name has to be in
    # session_state before the password fires the attempt.
    if user:
        box(at, "_user_input").set_value(user).run()
    box(at, "_pw_input").set_value(pw).run()
    return at


print("THE ACCOUNTS SCRIPT\n")

# ── the client on its own ─────────────────────────────────────────────
real_post = accounts._post

check("1 no url is not a crash, it is None",
      accounts.login("", "tok", "a", "b") is None)
check("2 no token is not a crash, it is None",
      accounts.login("http://x", "", "a", "b") is None)

sent = {}


def fake_post(url, token, payload, timeout=None):
    sent.clear()
    sent.update({"url": url, "token": token, "payload": dict(payload)})
    return fake_post.reply


accounts._post = fake_post

fake_post.reply = {"ok": True, "user": "Admin", "engine": "studio", "note": "me"}
got = accounts.login("http://x", "LOGIN-TOK", "Admin", "pw")
check("3 a good reply is understood",
      got == {"user": "admin", "engine": "studio", "note": "me",
              "remember": "", "must_change": False}, got)
# A REPLY WITHOUT THE FIELD MEANS NO, NOT YES. A deployment older than
# 22.8.2026 says nothing about must_change, and the safe reading is that
# nobody is stopped — the other way round would put every person in the
# house on a change-your-password screen the app could not clear.
check("3c a script that says nothing about it means nobody is stopped",
      got["must_change"] is False, got)
check("3b a plain login carries no token", got.get("remember") == "")
check("4 it asks the login question", sent["payload"].get("what") == "login", sent)
check("5 it sends the token it was given", sent["token"] == "LOGIN-TOK")
check("6 THE PASSWORD GOES OUT AND NOTHING COMES BACK — no hash, no salt",
      "hash" not in (got or {}) and "salt" not in (got or {}) and "password" not in (got or {}))

fake_post.reply = {"ok": False, "error": "no"}
check("7 a 'no' is None", accounts.login("http://x", "t", "a", "b") is None)

fake_post.reply = {"ok": True}
check("8 ok with no name is NOT believed — that is an old deployment "
      "answering, not our script",
      accounts.login("http://x", "t", "a", "b") is None)

fake_post.reply = None
check("9 an unreachable script is None, not an exception",
      accounts.login("http://x", "t", "a", "b") is None)

accounts._post = real_post

# ── the login screen, against a real stub over HTTP ───────────────────
#
# AppTest RELOADS ttt.accounts on every run, so a stubbed login() is
# thrown away before the app ever calls it — patching cannot test this.
# So the accounts script is stood up for real on localhost, exactly as
# tests/test_drive_text.py does: the transport, the JSON shapes and the
# never-raises contract all get exercised, without Google.

SEEN = []
MODE = {"dead": False, "no_user": False}
ACCOUNT = {"user": "admin", "pw": "moje-lozinka-9", "engine": "studio"}
TOKENS = set()
MINT = {"n": 0}


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

        if body.get("token") != "LOGIN-TOK":
            return self._reply({"ok": False, "error": "bad token"})
        if body.get("what") not in ("login", "remember_login",
                                    "remember_forget", "password_change"):
            return self._reply({"ok": False, "error": "unknown request"})

        user, pw, engine = ACCOUNT["user"], ACCOUNT["pw"], ACCOUNT["engine"]
        who = str(body.get("username", "")).strip().lower()
        what = body.get("what")

        if what == "remember_login":
            if who == user and body.get("remember") in TOKENS:
                return self._reply({"ok": True, "user": user,
                                    "engine": engine, "note": "me"})
            return self._reply({"ok": False, "error": "no"})

        if what == "remember_forget":
            TOKENS.discard(body.get("remember"))
            return self._reply({"ok": True})

        if what == "password_change":
            new = str(body.get("new_password") or "")
            if len(new) < 8:
                return self._reply({"ok": False, "error": "too short"})
            if new == pw:
                return self._reply({"ok": False, "error": "that is the same password"})
            if who != user or body.get("old_password") != pw:
                return self._reply({"ok": False, "error": "no"})
            ACCOUNT["pw"] = new
            TOKENS.clear()                 # every device forgotten
            return self._reply({"ok": True, "user": user})

        if MODE["no_user"]:
            return self._reply({"ok": True})          # an old deployment
        if who == user and body.get("password") == pw:
            out = {"ok": True, "user": user, "engine": engine, "note": "me"}
            if body.get("remember"):
                MINT["n"] += 1
                tok = "tok-%d" % MINT["n"]
                TOKENS.add(tok)
                out["remember"] = tok
            return self._reply(out)
        return self._reply({"ok": False, "error": "no"})


srv = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:{}/".format(srv.server_address[1])


def live(**kw):
    # setdefault, NOT a fixed keyword: check 21 overrides the token on
    # purpose, and passing it twice is a TypeError that kills the whole
    # run rather than failing one check.
    kw.setdefault("AUTH_LOGIN_TOKEN", "LOGIN-TOK")
    return fresh(AUTH_URL=URL, **kw)


at = sign_in(live(), "admin", "moje-lozinka-9")
check("10 the accounts script lets the right pair in",
      sget(at, "_authed") is True, at.exception)
check("11 identity is the NAME, not the password",
      sget(at, "_user") == "admin", sget(at, "_user"))
check("12 the engine it assigns is applied",
      sget(at, "_assigned_engine") == "studio", sget(at, "_assigned_engine"))
check("13 THE LOGIN TOKEN IS THE ONE SENT — never the admin token",
      SEEN and SEEN[-1].get("token") == "LOGIN-TOK", SEEN[-1] if SEEN else None)
check("14 capitals in the name do not matter",
      sget(sign_in(live(), "AdMiN", "moje-lozinka-9"), "_authed") is True)

at = sign_in(live(), "admin", "wrong")
check("15 the wrong password is refused", sget(at, "_authed") is False)

# ── THE DOOR UNDER THE MAT ────────────────────────────────────────────
at = sign_in(live(), "", "stub")
check("16 THE EMERGENCY DOOR: APP_PASSWORDS gets you in with the "
      "username box EMPTY, exactly as ADMIN.md §3.5 promises",
      sget(at, "_authed") is True, sget(at, "_authed"))

at = sign_in(live(), "admin", "stub")
check("17 and with a name typed in too, when the script says no to it",
      sget(at, "_authed") is True, sget(at, "_authed"))

MODE["dead"] = True
at = sign_in(live(), "admin", "stub")
check("18 A DEAD SCRIPT does not lock anybody out",
      sget(at, "_authed") is True, at.exception)
at = sign_in(live(), "admin", "moje-lozinka-9")
check("19 and a real password simply fails while it is dead, "
      "rather than crashing", sget(at, "_authed") is False, at.exception)
MODE["dead"] = False

at = sign_in(fresh(AUTH_URL="http://127.0.0.1:1/", AUTH_LOGIN_TOKEN="t"),
             "admin", "stub")
check("20 A REFUSED CONNECTION does not lock anybody out",
      sget(at, "_authed") is True, at.exception)

at = sign_in(live(AUTH_LOGIN_TOKEN="WRONG-TOK"), "admin", "moje-lozinka-9")
check("21 a wrong token is just a no, not a crash",
      sget(at, "_authed") is False, at.exception)

MODE["no_user"] = True
at = sign_in(live(), "admin", "moje-lozinka-9")
check("22 ok-with-no-name is not believed at the screen either",
      sget(at, "_authed") is False, at.exception)
MODE["no_user"] = False

at = sign_in(fresh(), "admin", "stub")
check("23 no AUTH_URL configured at all and the old way still works",
      sget(at, "_authed") is True, sget(at, "_authed"))

# ── the throttle still bites ──────────────────────────────────────────
at = live()
at.run()
box(at, "_user_input").set_value("admin").run()
check("24 typing a name is still not an attempt",
      not sget(at, "_gate_wait"), sget(at, "_gate_wait"))
for _ in range(6):
    box(at, "_pw_input").set_value("wrong").run()
check("25 repeated wrong passwords still trigger the throttle",
      bool(sget(at, "_gate_wait")), sget(at, "_gate_wait"))

# ── REMEMBER ME, which never worked for the family ────────────────────
from ttt import accounts as AC  # noqa: E402

TOKENS.clear()
r = AC.login(URL, "LOGIN-TOK", "admin", "moje-lozinka-9", remember=True)
check("26 ticking the box mints a token", bool(r and r.get("remember")), r)
TOK = r["remember"]
check("27 the token logs in without a password",
      (AC.remember_login(URL, "LOGIN-TOK", "admin", TOK) or {}).get("user") == "admin")
check("28 a made-up token does not",
      AC.remember_login(URL, "LOGIN-TOK", "admin", "nonsense") is None)
check("29 an unreachable script is a no, not a crash",
      AC.remember_login("http://127.0.0.1:1/", "t", "admin", TOK) is None)
check("30 logging out revokes it",
      AC.remember_forget(URL, "LOGIN-TOK", "admin", TOK) is True
      and AC.remember_login(URL, "LOGIN-TOK", "admin", TOK) is None)

# ── the login screen stores name+token, never the password ────────────
at = live()
at.run()
box(at, "_user_input").set_value("admin").run()
box(at, "_pw_input").set_value("moje-lozinka-9").run()
check("31 logged in with Remember me ticked by default",
      sget(at, "_authed") is True and bool(sget(at, "_remember_token")))
# _pending_ls cannot be watched from out here: app.py POPS it at the top
# of the very run that queued it (line ~844), so it is gone before the
# test can look. What IS observable is what the session keeps — and the
# rule is that the password is not among it.
check("32 the session holds the NAME and a token, never the password",
      sget(at, "_user") == "admin"
      and sget(at, "_remember_token") not in ("", "moje-lozinka-9", None)
      and sget(at, "_pw_input", "") == "",
      (sget(at, "_user"), sget(at, "_pw_input", "")))

# ── log out ───────────────────────────────────────────────────────────
at.session_state["active_tab"] = "looks"
at.run()
btn = [b for b in at.button if b.key == "log_out_btn"]
check("33 there is a visible Log out", len(btn) == 1)

# A WATERMARK, because SEEN is cumulative. Searching the whole list found
# the remember_forget from check 30 and went green even when log out sent
# nothing at all — a mutation that removed the revocation survived. Only
# what arrives AFTER the click counts, and it must carry THIS token.
was = len(SEEN)
mine = sget(at, "_remember_token")
btn[0].click().run()
check("34 logging out ends the session", sget(at, "_authed") is not True)
check("35 and TELLS THE SCRIPT to revoke THIS token",
      any(b.get("what") == "remember_forget" and b.get("remember") == mine
          for b in SEEN[was:]),
      [b.get("what") for b in SEEN[was:]])
check("36 the token is gone from the session", not sget(at, "_remember_token"))

# ── changing your own password ────────────────────────────────────────
def logged_in():
    a = live()
    a.run()
    box(a, "_user_input").set_value("admin").run()
    box(a, "_pw_input").set_value(ACCOUNT["pw"]).run()
    a.session_state["active_tab"] = "looks"
    a.run()
    return a


def fields(a, cur, new, rep):
    box(a, "_pw_cur").set_value(cur)
    box(a, "_pw_new").set_value(new)
    box(a, "_pw_rep").set_value(rep)
    [b for b in a.button if b.key == "pw_change_btn"][0].click().run()
    return sget(a, "_pw_msg") or ("", "")


a = logged_in()
check("37 the password section is there for an accounts user",
      any(x.key == "_pw_cur" for x in a.text_input))

check("38 two different new passwords are refused before any request",
      fields(a, "moje-lozinka-9", "abcdefgh", "abcdefgX")[0] == "bad")
check("39 a short new password is refused",
      fields(a, "moje-lozinka-9", "short", "short")[0] == "bad")
check("40 the WRONG current password is refused",
      fields(a, "not-my-password", "abcdefghij", "abcdefghij")[0] == "bad")
check("41 nothing changed after those refusals",
      ACCOUNT["pw"] == "moje-lozinka-9", ACCOUNT["pw"])

kind, _ = fields(a, "moje-lozinka-9", "nova-lozinka-77", "nova-lozinka-77")
check("42 the right current password changes it", kind == "good", kind)
check("43 the script has the new one", ACCOUNT["pw"] == "nova-lozinka-77")
check("44 THE BOXES ARE EMPTIED — no password left in the session",
      not sget(a, "_pw_cur") and not sget(a, "_pw_new") and not sget(a, "_pw_rep"))
check("45 no password is anywhere in the session state",
      not any("nova-lozinka-77" == str(sget(a, k))
              for k in ("_pw_cur", "_pw_new", "_pw_rep", "_user")))
check("46 the old password no longer logs in",
      AC.login(URL, "LOGIN-TOK", "admin", "moje-lozinka-9") is None)
check("47 the new one does",
      (AC.login(URL, "LOGIN-TOK", "admin", "nova-lozinka-77") or {}).get("user") == "admin")

# ── the emergency door user has no password section ───────────────────
at = sign_in(live(), "", "stub")
at.session_state["active_tab"] = "looks"
at.run()
check("48 APP_PASSWORDS user still gets Log out",
      any(b.key == "log_out_btn" for b in at.button))
check("49 but NOT a change-password box — there is no row to change",
      not any(x.key == "_pw_cur" for x in at.text_input))

print("\n{} passed, {} failed".format(passed, failed))


def test_accounts():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_accounts.py` is how it is meant to be read."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
