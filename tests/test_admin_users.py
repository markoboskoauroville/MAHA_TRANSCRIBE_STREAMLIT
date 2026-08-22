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
MODE = {"dead": False, "empty": False, "old_deployment": False}
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
            # A CHOSEN PASSWORD IS USED; an empty one is generated. The
            # reply is the only place the caller may read it from — see
            # check 18b, which is the whole reason this stub can return
            # something different from what it was sent.
            chosen = str(body.get("password") or "")
            # A DEPLOYMENT OLDER THAN THIS CHANGE ignores the field and
            # generates one anyway. It is the case the panel has to
            # survive without sending Baba's family a password that does
            # not work, so the stub can be put into it.
            if MODE["old_deployment"]:
                chosen = ""
            PEOPLE[who] = {"engine": "normal", "note": str(body.get("note") or ""),
                           "folder": who, "hashed": True, "must_change": True,
                           "sent_password": chosen}
            return self._reply({"ok": True, "user": who, "must_change": True,
                                "password": chosen or "made-pw-%d" % MADE["n"]})

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


def _engine_options(at):
    for r in at.get("radio"):
        if r.key and r.key.startswith("_adm_engine_"):
            return list(r.options)
    raise AssertionError("no engine choice on the page")


def engine(at, engine_id):
    """Choose an engine for whoever is selected. It is a radio now — one
    choice out of three, which is what three pills were pretending not
    to be."""
    for r in at.radio:
        if r.key and r.key.startswith("_adm_engine_"):
            r.set_value(engine_id).run()
            return
    raise AssertionError("no engine choice on the page")


def pick(at, who):
    """Select a person.

    v109 compacted the panel: one list, one selection, one set of
    actions. Before that every person carried their own buttons, so a
    test could press `ad_del_baba` and never say who it meant. Now who it
    means is a separate act — which is the point, since it is also how
    the panel stops the wrong row being deleted by a mis-tap.
    """
    for sb in at.selectbox:
        if sb.key == "_adm_pick":
            sb.set_value(who).run()
            return
    raise AssertionError("no person list on the page")


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
# v109 compacted the panel to ONE list and ONE selection, so the marks
# moved from a sentence per person into the table. "no pw" beside a name
# is the same fact in less room.
check("7 somebody with no password yet is marked", "no pw" in p, p[:200])
check("8 NO SECRET IS EVER RENDERED — not a hash, not a token",
      ADMIN_TOK not in p and "folder" not in p, p[:200])
# The actions act on WHOEVER IS SELECTED now, so there is one set of
# them rather than one set per person — which is the whole saving. The
# behaviour that matters is unchanged and still checked below: the
# confirm strip names the person, and nothing happens without the
# administrator's own password.
check("9 there are reset and delete actions",
      "ad_reset" in keys(at) and "ad_del" in keys(at), keys(at))
check("9b EVERY person is listed, not just the selected one — the point "
      "of the table is seeing who exists at a glance",
      all(n in p for n in ("admin", "baba", "mama")), p[:220])

rename = [b for b in at.get("button") if b.key == "ad_rename"]
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
# ABOVE THE LIST, measured against the list itself rather than against
# the "Add a person" heading — v110 replaced that heading with a plain
# rule, and a check anchored to a label is a check that breaks when the
# wording changes. The list is the thing it must come before.
check("13 and it is shown ABOVE the list, not under it — under it, it is "
      "below the fold on a phone",
      page(at).index("made-pw-1") < page(at).index("admin"),
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
pick(at, "baba"); press(at, "ad_del")
check("18 delete asks first, and names the person",
      "Delete baba" in page(at), page(at)[:300])
check("19 the strip is about the SELECTED person, and names them",
      "ad_yes" in keys(at) and "Delete baba" in page(at), page(at)[:200])
check("20 and it says the recordings are kept", "recordings are kept" in page(at))

field(at, "_adm_proof").set_value("wrong-password")
pick(at, "baba"); press(at, "ad_yes")
check("21 A WRONG ADMINISTRATOR PASSWORD DELETES NOBODY",
      "baba" in PEOPLE, list(PEOPLE))
check("22 and the refusal is shown", "administrator password" in page(at),
      page(at)[:300])

at = panel()
at.run()
pick(at, "baba"); press(at, "ad_del")
field(at, "_adm_proof").set_value(ADMIN_PW)
pick(at, "baba"); press(at, "ad_yes")
check("23 the right password deletes", "baba" not in PEOPLE, list(PEOPLE))
# NOT "baba" not in page(at) — the panel says "baba is gone", so the
# name is rightly on the screen. What must disappear is the ROW.
check("24 and the list refreshes without their row",
      "baba" not in [r for r in (sget(at, "_adm_people") or [])
                     for r in [r.get("user")]],
      sget(at, "_adm_people"))
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
pick(at, "baba"); press(at, "ad_del")
field(at, "_adm_proof").set_value(ADMIN_PW)
pick(at, "baba"); press(at, "ad_no")
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
pick(at, "baba"); press(at, "ad_del")
check("28 reopening the strip presents an EMPTY password box",
      not (field(at, "_adm_proof").value or ""),
      field(at, "_adm_proof").value)
check("28b and nothing was deleted along the way", "baba" in PEOPLE, list(PEOPLE))

# ── resetting ─────────────────────────────────────────────────────────
at = panel()
at.run()
pick(at, "baba"); press(at, "ad_reset")
check("29 reset asks first too", "New password for baba" in page(at),
      page(at)[:300])
check("30 and warns that their devices are signed out",
      "signed out" in page(at), page(at)[:300])
field(at, "_adm_proof").set_value(ADMIN_PW)
pick(at, "baba"); press(at, "ad_yes")
check("31 the new password is shown once", "reset-pw-1" in page(at),
      page(at)[:300])

# ── engines ───────────────────────────────────────────────────────────
at = panel()
at.run()
pick(at, "mama")
engine(at, "studio")
check("32 an engine can be assigned from here",
      PEOPLE["mama"]["engine"] == "studio", PEOPLE["mama"])
check("33 THROUGH THE ACCOUNTS SCRIPT, not the main one — one script "
      "owns the users tab",
      any(b.get("what") == "user_engine" for b in SEEN), SEEN[-1:])
engine(at, "normal")
check("34 and moved back to normal, which is now a real answer rather "
      "than the absence of one",
      PEOPLE["mama"]["engine"] == "normal", PEOPLE["mama"])
check("34b THE RADIO OFFERS TWO ENGINES AND NO BLANK. The third option "
      "was 'global', a state that is neither of the two real answers",
      sorted(_engine_options(at)) == ["normal", "studio"], _engine_options(at))

# ── §1: none of this may ever shut the door ───────────────────────────
at = panel()
at.run()
MODE["dead"] = True
pick(at, "baba"); press(at, "ad_reset")
field(at, "_adm_proof").set_value(ADMIN_PW)
pick(at, "baba"); press(at, "ad_yes")
check("35 A DEAD SCRIPT IS A SENTENCE, NEVER AN EXCEPTION (§1)",
      not at.exception, at.exception)
check("36 and it says it could not be reached",
      "unreachable" in page(at), page(at)[:300])

# ── the chosen password, and the message he sends ─────────────────────
at = panel()
at.run()
field(at, "_adm_name").set_value("emina")
field(at, "_adm_pw").set_value("kruh-i-more-9")
press(at, "ad_add")
check("41 A PASSWORD I CHOOSE IS THE ONE THAT IS SET",
      PEOPLE.get("emina", {}).get("sent_password") == "kruh-i-more-9",
      PEOPLE.get("emina"))
page41 = page(at)
check("42 and the message names the person, the username and it",
      "emina" in page41 and "kruh-i-more-9" in page41, page41[:400])
check("43 and says the change is coming, so it is not a surprise later",
      "change" in page41.lower() or "lozink" in page41.lower(), page41[:400])
check("44 NO LINK when APP_URL is unset — a placeholder URL in a message "
      "he forwards is worse than no URL",
      "http" not in page41.split("kruh-i-more-9")[0][-400:], page41[:400])

# THE RULE THAT MAKES A HALF-DEPLOYED SCRIPT SAFE.
MODE["old_deployment"] = True
at = panel()
at.run()
field(at, "_adm_name").set_value("marinko")
field(at, "_adm_pw").set_value("ovo-nece-raditi")
press(at, "ad_add")
page45 = page(at)
check("45 AGAINST AN OLD SCRIPT THE MESSAGE CARRIES THE PASSWORD THAT "
      "WORKS, not the one that was typed — the old script ignores the "
      "field and generates its own, and a message with the typed one "
      "would be a person who cannot log in",
      "ovo-nece-raditi" not in page45 and "made-pw" in page45, page45[:400])
MODE["old_deployment"] = False

# ── the table says who has not chosen their own password yet ──────────
at = panel()
at.run()
check("46 the list marks somebody who must still change their password",
      "must" in page(at), page(at)[:400])

# ── an empty box still means "make me one" ────────────────────────────
at = panel()
at.run()
field(at, "_adm_name").set_value("sonia")
press(at, "ad_add")
check("47 an empty password box asks the script to make one",
      PEOPLE.get("sonia", {}).get("sent_password") == ""
      and "made-pw" in page(at), PEOPLE.get("sonia"))

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
