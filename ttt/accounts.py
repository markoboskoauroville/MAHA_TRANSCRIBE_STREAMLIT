"""THE ACCOUNTS SCRIPT — the second Apps Script project.

A SECOND SCRIPT, WITH ITS OWN TOKEN, and that is the whole point.
`SHEETS_TOKEN` already unlocks every API key in the `k_` tabs (§19), so
it must not also be the thing that answers questions about passwords. A
login happens on every phone, every day; the credential it carries
should be worth as little as possible if it ever leaks.

So there are two tokens and this module only ever holds one of them:

    AUTH_LOGIN_TOKEN   may ask "is this pair right". Nothing else.
    AUTH_ADMIN_TOKEN   may change users. Sent only by the admin panel.

NONE OF THIS MAY EVER BE A DEPENDENCY. Every function here returns None
rather than raising, because §1 is the rule that outranks the rest: a
failure on the login screen locks out EVERYBODY, including the person
who would have to fix it. An unreachable script, a wrong token, a
missing users tab and a wrong password are all the same answer — no —
and the caller falls back to APP_PASSWORDS exactly as before.
"""

# The same single POST the sheet client uses. One place that swallows
# every network failure, not two that drift apart.
from ttt.sheet import _post

TIMEOUT = 12


def login(url: str, token: str, username: str, password: str,
          remember: bool = False):
    """Ask the accounts script whether this pair is right.

    Returns `{"user":…, "engine":…, "note":…}` or None.

    THE PASSWORD GOES OUT AND NOTHING COMES BACK. The script has no
    endpoint that returns the users table, and the reply carries no
    password, no hash and no salt — so a person's password never travels
    back out of Google, not even to the app that just supplied it.
    """
    out = _post(url, token, {"what": "login",
                             "username": str(username or ""),
                             "password": str(password or ""),
                             "remember": bool(remember)}, timeout=TIMEOUT)
    if not out or not out.get("ok"):
        return None
    user = str(out.get("user") or "").strip().lower()
    if not user:
        # ok:true with no name is a reply we do not understand — an old
        # deployment, or something that is not our script. Not believed.
        return None
    return {"user": user,
            "engine": str(out.get("engine") or "").strip().lower(),
            "note": str(out.get("note") or ""),
            # MISSING IS FALSE, and that is the safe direction: a
            # deployment older than this one returns no such field, and
            # the result is that nobody is asked to change a password —
            # not that everybody is stuck on a screen asking them to.
            "must_change": bool(out.get("must_change")),
            # Present only when Remember me asked for one. The token
            # itself, once — the sheet keeps nothing but its hash.
            "remember": str(out.get("remember") or "")}


def ping(url: str, token: str):
    """Is the script there, and which token is this? Never raises."""
    out = _post(url, token, {"what": "ping"}, timeout=TIMEOUT)
    if not out or not out.get("ok"):
        return None
    return {"admin": bool(out.get("admin")), "rounds": int(out.get("rounds") or 0)}


def remember_login(url: str, token: str, username: str, remember: str):
    """Log in with a remembered token instead of a password.

    The browser holds the token; the sheet holds only its hash. So a
    stolen spreadsheet cannot log in as anybody, and a lost phone costs
    exactly one token — revoked by logging out, or by changing the
    password, which forgets every device at once.

    None means no, exactly as `login` does, and the caller must fall back
    to the login screen rather than treating it as an error.
    """
    out = _post(url, token, {"what": "remember_login",
                             "username": str(username or ""),
                             "remember": str(remember or "")}, timeout=TIMEOUT)
    if not out or not out.get("ok"):
        return None
    user = str(out.get("user") or "").strip().lower()
    if not user:
        return None
    return {"user": user,
            "engine": str(out.get("engine") or "").strip().lower(),
            # A REMEMBERED PHONE MUST NOT WALK PAST THE ONE SCREEN it is
            # not allowed to walk past. Remember me skips the login form
            # entirely, so the flag has to travel on this reply too.
            "must_change": bool(out.get("must_change")),
            "note": str(out.get("note") or "")}


def remember_forget(url: str, token: str, username: str, remember: str):
    """Forget THIS device. The other ones keep working.

    Best effort by design: the browser's copy is removed either way, so a
    script that cannot be reached delays the revocation, it does not
    cancel the log-out.
    """
    out = _post(url, token, {"what": "remember_forget",
                             "username": str(username or ""),
                             "remember": str(remember or "")}, timeout=TIMEOUT)
    return bool(out and out.get("ok"))


def change_password(url: str, token: str, username: str,
                    old_password: str, new_password: str):
    """Change your own password. Returns (ok, error).

    THE OLD PASSWORD IS THE AUTHORISATION, not the token — this endpoint
    is reachable with the login token that every phone in the house
    carries, so knowing the current password is the only thing that
    proves it is really them.

    NOTHING COMES BACK but a yes or a no. No password, no hash, no token.
    """
    out = _post(url, token, {"what": "password_change",
                             "username": str(username or ""),
                             "old_password": str(old_password or ""),
                             "new_password": str(new_password or "")},
                timeout=TIMEOUT + 8)   # two hashings, not one
    if out is None:
        return False, "unreachable"
    if out.get("ok"):
        return True, ""
    return False, str(out.get("error") or "no")


# ══════════════════════════════════════════════════════════════════════
#  THE ADMIN SIDE — everything below needs AUTH_ADMIN_TOKEN
# ══════════════════════════════════════════════════════════════════════
#
# A DIFFERENT TOKEN FROM EVERYTHING ABOVE, and it is only ever read
# inside the owner's panel. The login token rides in every phone in the
# house; this one answers questions about who exists and can unmake
# them, so it should be somewhere far fewer runs ever touch.
#
# DELETE, RENAME AND RESET ALSO NEED THE ADMINISTRATOR'S OWN PASSWORD.
# The script checks it (`adminProved_`), not this module — a client-side
# check would be a suggestion. It is passed through and never kept.
#
# A NEW PASSWORD COMES BACK EXACTLY ONCE, from create and from reset.
# It is not stored here, not logged, and not returned twice. If it is
# lost between this line and the person reading it, the only repair is
# another reset.

ADMIN_TIMEOUT = TIMEOUT + 12   # a proof hashing, then often a second one


def users(url: str, token: str):
    """Everyone, for the owner's panel. `None` when it could not ask.

    NONE AND [] ARE DIFFERENT ANSWERS and the caller must keep them
    apart: `None` is "the script did not answer", `[]` is "the tab is
    there and it is empty". The old engine panel conflated them and told
    the owner there was no users tab when there plainly was one.

    Never passwords, never hashes, never salts — the script has no
    endpoint that returns them.
    """
    out = _post(url, token, {"what": "users"}, timeout=TIMEOUT)
    if not out or not out.get("ok"):
        return None
    rows = out.get("users")
    if not isinstance(rows, list):
        return None
    return [r for r in rows if isinstance(r, dict) and r.get("user")]


def user_create(url: str, token: str, username: str,
                engine: str = "", note: str = "", password: str = ""):
    """Make a person. Returns (password, error).

    THE PASSWORD IS THE SUCCESS SIGNAL. There is no (True, "") to
    misread: either a password came back and the person exists, or it
    did not. That shape is deliberate — a create that half-succeeded
    would otherwise show an empty box under the word "done".
    """
    # An EMPTY password asks the script to make one, which is what it
    # did before this argument existed. A script older than this one
    # ignores the field and generates one anyway — which is why the
    # caller must show what comes BACK, not what it sent.
    out = _post(url, token, {"what": "user_create",
                             "username": str(username or ""),
                             "engine": str(engine or ""),
                             "note": str(note or ""),
                             "password": str(password or "")},
                timeout=ADMIN_TIMEOUT)
    if out is None:
        return "", "unreachable"
    if not out.get("ok"):
        return "", str(out.get("error") or "no")
    pw = str(out.get("password") or "")
    if not pw:
        # ok with no password is a reply we do not understand — an older
        # deployment, or something that is not our script. §47: do not
        # believe the word ok on its own.
        return "", "no password came back"
    return pw, ""


def user_password(url: str, token: str, username: str,
                  admin_user: str, admin_password: str):
    """A new password for somebody. Returns (password, error).

    IT SIGNS THEIR DEVICES OUT TOO. The script clears their remember
    tokens, because a reset exists to get somebody OUT as much as to let
    them back in, and a phone that stayed logged in would defeat half of
    that. Say so where the button is.
    """
    out = _post(url, token, {"what": "user_password",
                             "username": str(username or ""),
                             "admin_user": str(admin_user or ""),
                             "admin_password": str(admin_password or "")},
                timeout=ADMIN_TIMEOUT)
    if out is None:
        return "", "unreachable"
    if not out.get("ok"):
        return "", str(out.get("error") or "no")
    pw = str(out.get("password") or "")
    if not pw:
        return "", "no password came back"
    return pw, ""


def user_delete(url: str, token: str, username: str,
                admin_user: str, admin_password: str):
    """Unmake a person. Returns (ok, error).

    THEIR RECORDINGS ARE LEFT ALONE by the script, on purpose. Losing
    somebody's audio because a spreadsheet was tidied is the wrong
    direction to fail in.
    """
    out = _post(url, token, {"what": "user_delete",
                             "username": str(username or ""),
                             "admin_user": str(admin_user or ""),
                             "admin_password": str(admin_password or "")},
                timeout=ADMIN_TIMEOUT)
    if out is None:
        return False, "unreachable"
    if not out.get("ok"):
        return False, str(out.get("error") or "no")
    # §47 again: the reply must name the person back, or an older
    # deployment falling through to something else answers ok and we
    # would tell the owner a person was deleted who is still there.
    if str(out.get("user") or "").strip().lower() != str(username or "").strip().lower():
        return False, "the script did not confirm the name"
    return True, ""


def user_rename(url: str, token: str, username: str, new_username: str,
                admin_user: str, admin_password: str):
    """Change the name shown. Returns (ok, error).

    THE DRIVE FOLDER KEEPS ITS BIRTH NAME — the script writes a frozen
    folder column and does not touch it here. The MAIN script does not
    read that column yet, so a renamed person's existing recordings stay
    under the old name until it does. That is why the panel does not
    offer this button yet.
    """
    out = _post(url, token, {"what": "user_rename",
                             "username": str(username or ""),
                             "new_username": str(new_username or ""),
                             "admin_user": str(admin_user or ""),
                             "admin_password": str(admin_password or "")},
                timeout=ADMIN_TIMEOUT)
    if out is None:
        return False, "unreachable"
    if not out.get("ok"):
        return False, str(out.get("error") or "no")
    if str(out.get("user") or "").strip().lower() != str(new_username or "").strip().lower():
        return False, "the script did not confirm the name"
    return True, ""


def user_engine(url: str, token: str, username: str, engine: str):
    """Give one person their own engine, or "" for the global one.

    Returns (ok, error). No administrator password: this one is
    reversible and changes nothing about who can get in.
    """
    out = _post(url, token, {"what": "user_engine",
                             "username": str(username or ""),
                             "engine": str(engine or "")}, timeout=TIMEOUT)
    if out is None:
        return False, "unreachable"
    if not out.get("ok"):
        return False, str(out.get("error") or "no")
    if str(out.get("user") or "").strip().lower() != str(username or "").strip().lower():
        return False, "the script did not confirm the name"
    return True, ""
