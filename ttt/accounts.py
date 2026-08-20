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
