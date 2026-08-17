"""Usage logging to a Google Sheet, via an Apps Script web app.

PRIVACY IS THE POINT. This module can only send what its `log()` signature
allows: who, what kind of action, how big, which engine, and how long the
session has been open. There is deliberately no parameter for content, so
no transcript, translation or read text can be sent even by mistake. Baba's
instruction, kept structurally rather than by good behaviour: *"We are
keeping their privacy. We don't want to see what they translate and what
they transcribe. Text is not important."*

NEVER BREAKS THE APP. Logging is a side effect of someone else's work. It
runs on a daemon thread, gives up after a few seconds, and swallows every
error. If the sheet is unreachable, misconfigured, or was never set up at
all, the app must behave exactly as if logging did not exist — that is why
`log()` has no return value worth checking and never raises.

Sending happens per use, as it happens, so the sheet is live rather than a
nightly batch. The rollup into days and totals is the spreadsheet's job,
not this module's.
"""

import json
import threading
import time
import urllib.request

TIMEOUT = 6          # a slow sheet must never hold up a person's work
UNIT_SECONDS = "seconds"
UNIT_CHARS = "chars"


def _num(value) -> float:
    """A number the sheet can actually store.

    json.dumps happily writes Infinity and NaN, which are not valid JSON —
    Apps Script's JSON.parse rejects the whole request, so one bad number
    would silently lose the event. Anything not finite becomes 0.
    """
    try:
        f = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    if f != f or f in (float("inf"), float("-inf")):
        return 0.0
    return round(max(-1e12, min(f, 1e12)), 2)


class UsageLog:
    """Configured once at startup and handed around.

    `url` and `token` come from Streamlit secrets. With either missing the
    logger is simply inert: every call is a no-op, which is the correct
    behaviour before the sheet has been set up.
    """

    def __init__(self, url: str = "", token: str = "", user: str = "",
                 enabled: bool = True):
        self.url = (url or "").strip()
        self.token = (token or "").strip()
        self.user = (user or "unknown").strip().lower()
        self.enabled = bool(enabled and self.url and self.token)
        self.started = time.time()
        self.sent = 0
        self.failed = 0
        self.last_error = ""

    # ---- the only way anything leaves ---------------------------------
    def log(self, action: str, amount: float = 0, unit: str = "",
            engine: str = "") -> None:
        """Record one use. Returns nothing, raises nothing, blocks nobody.

        action  "transcribe" | "translate" | "read" | "login" | ...
        amount  seconds of audio, or number of characters
        unit    UNIT_SECONDS or UNIT_CHARS
        engine  which provider did the work, for cost attribution
        """
        if not self.enabled:
            return
        payload = {
            "token": self.token,
            "user": self.user,
            "action": str(action)[:40],
            "amount": _num(amount),
            "unit": str(unit)[:16],
            "engine": str(engine)[:32],
            "session_seconds": _num(time.time() - self.started),
        }
        threading.Thread(target=self._send, args=(payload,), daemon=True).start()

    def _send(self, payload: dict) -> None:
        try:
            req = urllib.request.Request(
                self.url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                r.read()
            self.sent += 1
        except Exception as e:            # deliberately total
            self.failed += 1
            self.last_error = str(e)[:200]

    # ---- for the admin panel ------------------------------------------
    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "user": self.user,
            "sent": self.sent,
            "failed": self.failed,
            "session_minutes": round((time.time() - self.started) / 60, 1),
            "last_error": self.last_error,
        }


class NullLog(UsageLog):
    """Explicit do-nothing logger, for tests and for when logging is off."""

    def __init__(self):
        super().__init__(enabled=False)

    def log(self, *a, **kw):
        return
