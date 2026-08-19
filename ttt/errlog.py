"""The error log.

Errors in this app are caught in a lot of places on purpose: a failed
transcription must not lose the audio, a failed highlight must not stop the
reading, a failed Drive write must not cost a transcript. That patience is
right, and it has a cost — **the reason things went wrong kept being
swallowed on the way past.** Baba spent an evening watching a 7 MB take
return nothing at all with no way to see why.

So every caught error is written here as well as handled. This module is a
place to PUT things, never a thing that can fail: `add()` cannot raise, and
if the store is somehow unusable the error is dropped rather than turned
into a second error on top of the first.

Only the admin sees the log module. It holds no audio and no keys — a key
would be the one thing that must never end up in a screenshot pasted into
a chat, so `add()` scrubs anything key-shaped before storing.
"""

import re
import time

KEY = "_errlog"
LIMIT = 300          # newest kept; older fall off the end

# Anything key-shaped is removed before storing. The log exists to be
# copied and pasted to someone else, which is exactly the journey a
# leaked key should never make.
_SECRETS = re.compile(
    r"\b(?:gsk_[A-Za-z0-9]{20,}"
    r"|sk_[A-Za-z0-9]{20,}"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16})\b")


def scrub(text) -> str:
    return _SECRETS.sub("***REDACTED***", str(text or ""))


def add(state, where: str, message, detail: str = "") -> None:
    """Record one error. Never raises, whatever it is handed."""
    try:
        entry = {
            "t": time.strftime("%H:%M:%S"),
            "day": time.strftime("%Y-%m-%d"),
            "where": scrub(where)[:60],
            "msg": scrub(message)[:400],
            "detail": scrub(detail)[:400],
        }
        log = state.setdefault(KEY, [])
        log.append(entry)
        if len(log) > LIMIT:
            del log[:-LIMIT]
    except Exception:
        pass          # a logger that can break the app is worse than none


def entries(state):
    """Newest first, because the thing that just went wrong is the thing
    being looked for."""
    try:
        return list(reversed(state.get(KEY) or []))
    except Exception:
        return []


def clear(state) -> None:
    try:
        state.pop(KEY, None)
    except Exception:
        pass


def as_text(state) -> str:
    """The whole history as one block, ready to paste somewhere else."""
    rows = entries(state)
    if not rows:
        return ""
    out = []
    day = None
    for e in rows:
        if e.get("day") != day:
            day = e.get("day")
            out.append(f"--- {day} ---")
        line = f"{e.get('t','')}  [{e.get('where','')}]  {e.get('msg','')}"
        if e.get("detail"):
            line += f"\n            {e['detail']}"
        out.append(line)
    return "\n".join(out)


def count(state) -> int:
    try:
        return len(state.get(KEY) or [])
    except Exception:
        return 0
