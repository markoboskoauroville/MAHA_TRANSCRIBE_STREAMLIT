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
check("3 a good reply is understood", got == {"user": "admin", "engine": "studio", "note": "me"}, got)
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
ACCOUNT = ("admin", "moje-lozinka-9", "studio")


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
        if body.get("what") != "login":
            return self._reply({"ok": False, "error": "unknown request"})

        user, pw, engine = ACCOUNT
        if MODE["no_user"]:
            return self._reply({"ok": True})          # an old deployment
        if str(body.get("username", "")).strip().lower() == user \
                and body.get("password") == pw:
            return self._reply({"ok": True, "user": user,
                                "engine": engine, "note": "me"})
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

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
