"""The archive.

Everything transcribed is kept, automatically. Baba works in sittings —
record five minutes, stop, eat, come back — and before this the only copy
of a take was whatever happened to be in the box. Pressing `new` or
recording again over it lost the earlier one for good.

WHAT IT HOLDS: the text, when it arrived, how it arrived, and its
language. No audio. Audio is large and already handled elsewhere; this is
so that words are never lost.

THIS MODULE NEVER RAISES. Archiving is a courtesy on top of the real
work, and a store that can throw would take the transcript down with it —
which is exactly the thing it exists to protect.

WHERE IT LIVES, AND THE LIMIT OF THIS VERSION: session state. It survives
pressing `new`, switching modules, recording again, and clearing the box.
It does NOT survive a page reload or the tab closing, because session
state is per-session by definition. Making it durable means writing to
localStorage through the ls_bridge component or to the sheet, and that is
a separate piece of work — see the note in HANDOVER.
"""

import itertools
import time

# NOT "_archive". The R module has owned that session key since long
# before this module existed, holding a DIFFERENT shape with no "at"
# field. Claiming it here meant that opening R replaced T1's archive with
# R's, and T1 then crashed with a KeyError on the next render — a crash in
# one module caused by visiting another, which is about the hardest kind
# to trace back.
#
# Session state is one flat namespace shared by every module. A generic
# name is a collision waiting to happen; prefix by owner.
KEY = "_t1_archive"
LIMIT = 60           # newest kept

# A COUNTER, NOT A CLOCK. Two takes added in the same millisecond got the
# same id, and then deleting one deleted both — which is precisely what
# happens when Streamlit reruns and delivery is reached twice.
_seq = itertools.count(1)
PREVIEW = 90         # characters shown in the list


def _now():
    return time.strftime("%H:%M")


def add(state, text, language="", method="", note="", rec_id=""):
    """Keep a transcript. Returns its id, or None if nothing was kept.

    The SAME TEXT TWICE IN A ROW IS NOT KEPT TWICE. Streamlit reruns the
    whole script constantly, and delivery can be reached more than once
    for one recording; without this the list would fill with copies of
    the last take and the real history would scroll away.
    """
    try:
        body = (text or "").strip()
        if not body:
            return None
        items = state.setdefault(KEY, [])
        if items and items[-1].get("text") == body:
            return items[-1].get("id")
        rec = {
            "id": "a%d_%d" % (int(time.time() * 1000) % 100000000,
                              next(_seq)),
            "at": _now(),
            "day": time.strftime("%Y-%m-%d"),
            "text": body,
            "chars": len(body),
            "language": str(language or ""),
            "method": str(method or ""),
            "note": str(note or ""),
            # The Drive recording this text came from, when there is
            # one. Session state dies on reload; Drive does not, so
            # this is what lets a row still be retranscribed or
            # deleted in a session that starts tomorrow.
            "rec_id": str(rec_id or ""),
        }
        items.append(rec)
        if len(items) > LIMIT:
            del items[:-LIMIT]
        return rec["id"]
    except Exception:
        return None


def items(state):
    """Newest first — the last thing said is the thing most likely wanted."""
    try:
        return list(reversed(state.get(KEY) or []))
    except Exception:
        return []


def get(state, item_id):
    try:
        for r in state.get(KEY) or []:
            if r.get("id") == item_id:
                return r
    except Exception:
        pass
    return None


def remove(state, item_id):
    try:
        items_ = state.get(KEY) or []
        state[KEY] = [r for r in items_ if r.get("id") != item_id]
        return True
    except Exception:
        return False


def clear(state):
    try:
        state.pop(KEY, None)
        return True
    except Exception:
        return False


def count(state):
    try:
        return len(state.get(KEY) or [])
    except Exception:
        return 0


def preview(rec, width=PREVIEW):
    """One line for the list. Newlines collapse, because a multi-line
    preview makes every row a different height and the list stops being
    scannable."""
    try:
        body = " ".join(str(rec.get("text", "")).split())
        if len(body) > width:
            body = body[:width - 1].rstrip() + "…"
        return body or "—"
    except Exception:
        return "—"
