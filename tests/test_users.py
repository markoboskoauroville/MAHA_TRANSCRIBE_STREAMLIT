"""USERS IN THE SHEET — login by name, and an engine each.

    python3 tests/test_users.py
"""

import json as _json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ttt import sheet as SHEET  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


# A fake script holding a users tab. Passwords live here and must never
# come back out of it.
USERS = [
    {"user": "baba", "password": "tajna1", "engine": "studio"},
    {"user": "emina", "password": "tajna2", "engine": ""},
    {"user": "marko", "password": "tajna3", "engine": "free"},
]
SEEN = []
MODE = {"old_deployment": False, "down": False}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = _json.loads(self.rfile.read(n).decode())
        SEEN.append(body)
        out = {"ok": False, "error": "unknown"}
        if body.get("token") != "TOK":
            out = {"ok": False, "error": "bad token"}
        elif MODE["old_deployment"]:
            out = {"ok": True}          # falls through to appendRow (§47)
        elif body.get("what") == "login":
            u = str(body.get("username", "")).strip().lower()
            p = str(body.get("password", ""))
            row = next((r for r in USERS
                        if r["user"] == u and r["password"] == p), None)
            out = ({"ok": True, "user": row["user"], "engine": row["engine"]}
                   if row else {"ok": False, "error": "no"})
        elif body.get("what") == "users":
            out = {"ok": True,
                   "users": [{"user": r["user"], "engine": r["engine"]}
                             for r in USERS]}
        elif body.get("what") == "user_engine":
            u = str(body.get("username", "")).strip().lower()
            e = str(body.get("engine", "")).strip().lower()
            row = next((r for r in USERS if r["user"] == u), None)
            if row is None:
                out = {"ok": False, "error": "no such user"}
            elif e not in ("", "free", "studio"):
                out = {"ok": False, "error": "not an engine"}
            else:
                row["engine"] = e
                out = {"ok": True, "user": u, "engine": e}
        raw = _json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:{}/".format(srv.server_port)

print("USERS IN THE SHEET\n")

# --- login ------------------------------------------------------------
got = SHEET.login(URL, "TOK", "baba", "tajna1")
check("1 a right pair logs in", got and got["user"] == "baba", got)
check("2 and brings that person's engine", got["engine"] == "studio", got)

check("3 a wrong password is refused",
      SHEET.login(URL, "TOK", "baba", "wrong") is None)
check("4 an unknown username is refused",
      SHEET.login(URL, "TOK", "nobody", "tajna1") is None)
check("5 an empty password is refused",
      SHEET.login(URL, "TOK", "baba", "") is None)

got2 = SHEET.login(URL, "TOK", "emina", "tajna2")
check("6 a blank engine cell comes back blank, not as an engine",
      got2 and got2["engine"] == "", got2)

check("7 the username is matched case-insensitively",
      (SHEET.login(URL, "TOK", "BABA", "tajna1") or {}).get("user") == "baba")

# THE PASSWORD MUST NEVER COME BACK
for reply_field in ("password", "pass", "pw"):
    check("8 the reply carries no %s field" % reply_field,
          reply_field not in (SHEET.login(URL, "TOK", "baba", "tajna1") or {}))

# --- it cannot lock anyone out ---------------------------------------
check("9 an unreachable sheet returns None, so the caller falls back",
      SHEET.login("http://127.0.0.1:1/", "TOK", "baba", "tajna1") is None)
check("10 no url returns None", SHEET.login("", "TOK", "baba", "x") is None)
check("11 a bad token returns None",
      SHEET.login(URL, "WRONG", "baba", "tajna1") is None)

MODE["old_deployment"] = True
check("12 an old deployment answering a bare ok is NOT a login",
      SHEET.login(URL, "TOK", "baba", "tajna1") is None)
MODE["old_deployment"] = False

# --- the owner's list -------------------------------------------------
people = SHEET.list_users(URL, "TOK")
check("13 every user is listed", len(people) == 3, people)
check("14 THE LIST CARRIES NO PASSWORDS",
      all("password" not in p for p in people), people)
check("15 and it carries each engine",
      {p["user"]: p["engine"] for p in people}
      == {"baba": "studio", "emina": "", "marko": "free"}, people)
check("16 an unreachable sheet lists nobody rather than raising",
      SHEET.list_users("http://127.0.0.1:1/", "TOK") == [])

# --- assigning ---------------------------------------------------------
check("17 an engine can be assigned",
      SHEET.set_user_engine(URL, "TOK", "emina", "studio") is True)
check("18 and it stuck",
      {p["user"]: p["engine"] for p in SHEET.list_users(URL, "TOK")}["emina"]
      == "studio")
check("19 it can be cleared back to the global engine",
      SHEET.set_user_engine(URL, "TOK", "emina", "") is True)
check("20 and the cell is blank again",
      {p["user"]: p["engine"] for p in SHEET.list_users(URL, "TOK")}["emina"]
      == "")
check("21 a name that is not an engine is refused",
      SHEET.set_user_engine(URL, "TOK", "emina", "banana") is False)
check("22 an unknown user is refused",
      SHEET.set_user_engine(URL, "TOK", "nobody", "free") is False)

MODE["old_deployment"] = True
check("23 an old deployment's bare ok is not believed here either",
      SHEET.set_user_engine(URL, "TOK", "emina", "free") is False)
MODE["old_deployment"] = False

# --- the script itself -------------------------------------------------
gs = open(os.path.join(os.path.dirname(__file__), "..", "apps_script",
                       "Code.gs"), encoding="utf-8").read()
check("24 the script has a login branch", "'login'" in gs)
check("25 and a users branch", "'users'" in gs)
check("26 and a user_engine branch", "'user_engine'" in gs)
check("27 THE SCRIPT HAS NO ENDPOINT RETURNING PASSWORDS — listUsers_ "
      "maps only user, engine and note",
      "listUsers_" in gs and "r[1]" not in gs.split("function listUsers_")[1]
      .split("function ")[0])

# --- the download cell -------------------------------------------------
wf = open(os.path.join(os.path.dirname(__file__), "..",
                       "waveform_frontend", "index.html"), encoding="utf-8").read()
check("28 the fourth cell is a save button, not an empty one",
      "bSave" in wf and 'id="bSpare"' not in wf)
check("29 it downloads what is loaded", "a.download=" in wf)
check("30 and it is dead when there is nothing to save",
      "body.idle #bSave{pointer-events:none}" in wf)

srv.shutdown()
print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
