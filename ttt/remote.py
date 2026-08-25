"""ttt/remote.py — the window to the transcript, on another device.

Baba, 25.8.2026: "I need an HTTPS address to type in my other device and
to see transcripts only... And push-pull can be initiated for either
side. The user in the tablet transcribes and says push on the web, and it
pushes to the web browser and refreshes it. And the same for the web
browser in a remote location: when the user pastes text to be read, it
says push to device, and the device is forced to receive the text and
starts automatically to read it."

TWO CHANNELS, ONE WINDOW. They point in opposite directions and neither
knows about the other:

    say    the device's transcript  ->  the remote page      (T pushes)
    hear   text pasted remotely     ->  the device reads it  (R pulls)

Each is a slot with its own sequence number, so "has anything new
arrived" is a comparison of two integers and not of two strings. That
matters on the receiving side: the reader must start when text ARRIVES,
not every time the same text is seen again, and comparing the text itself
cannot tell those apart when somebody pushes the same line twice.

---

THE PROBLEM THAT DECIDES THE DESIGN

A second device is a second BROWSER SESSION, and `st.session_state`
belongs to one session. The transcript on his phone is invisible to his
laptop no matter how the page is drawn. So something has to sit between
them, and the choice of what is the whole design:

    THE SHEET or DRIVE   works across restarts, and puts every free
                         user's transcript into Google. The free tier is
                         session-only BY OBSERVATION (see LAST_RUN) and
                         that promise is worth more than durability
    A FILE ON DISK       Streamlit Cloud's disk is not his, and a
                         transcript written there outlives the session
                         that made it with nobody to delete it
    THIS PROCESS'S OWN   one Streamlit server, one Python process, all
    MEMORY               sessions inside it. Nothing is written, nothing
                         is sent, and a restart empties it

The third. `st.cache_resource` hands every session in the process the
same object, which is exactly the relay this needs and nothing more.

**IT IS A WINDOW, NOT A STORE.** Nothing here is durable and nothing here
is meant to be. Close the app, redeploy, or leave it long enough and the
text is gone — which is the same promise the free tier already makes.

---

THE CODE, AND WHAT IT IS AND IS NOT

The link carries a short random code. That code is the only thing
standing between a stranger and the text, so:

    IT IS NOT A PASSWORD. Anyone holding the URL sees the transcript —
    and now, because the channel runs both ways, anyone holding it can
    also PUSH TEXT THAT THE DEVICE WILL SPEAK. That is the feature Baba
    asked for and it is worth saying out loud rather than discovering:
    the link is the whole credential. Treat it like a key, not like a
    bookmark, and do not paste it anywhere it will be indexed.
    IT IS PER SESSION, so closing the app and coming back gives a new
    one and the old link goes dark.
    IT EXPIRES ON ITS OWN, so a phone left on a table does not leave a
    window open all week.

Said plainly on the page rather than implied, because a person who thinks
it is private will paste it somewhere a person who knows it is not
would not.
"""

import secrets
import time

# How long a window stays open with nothing written to it. Long enough to
# carry a working session, short enough that a forgotten tab closes
# itself. Measured against nothing — it is a judgement, and it is here in
# one place so it can be changed in one place.
IDLE_SECONDS = 6 * 60 * 60

# The refresh cadence of the remote page. Fast enough that the text
# appears while he is still looking at the other screen; slow enough that
# a page left open all day is not a request every second.
POLL_SECONDS = 5

CODE_ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"   # no l, o, 0, 1
# SEVEN characters of a 32-symbol alphabet is about 35 bits. That is not
# a secret worth defending against somebody who wants it; it is enough
# that nobody arrives at his window by typing. The defence is that the
# code is per session and expires, not that it is long.
CODE_LENGTH = 7

# The two directions, named from the DEVICE's point of view so the words
# stay true wherever they are read.
SAY = "say"      # the device transcribed it, the remote page reads it
HEAR = "hear"    # the remote page pasted it, the device speaks it
CHANNELS = (SAY, HEAR)


def new_code() -> str:
    """A code that survives being read aloud and typed on a phone.

    No l/1, no o/0 — the two confusions that make somebody type a link
    wrong and conclude the feature is broken.
    """
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def _window(store, code, now):
    w = store.get(code)
    if not w:
        w = {"created": now, "at": now,
             SAY: {"text": "", "seq": 0, "at": now},
             HEAR: {"text": "", "seq": 0, "at": now}}
        store[code] = w
    return w


def put(store: dict, code: str, text: str, channel: str = SAY,
        force: bool = False, now: float = None) -> dict:
    """Publish `text` on one channel. Returns that channel's slot.

    THE SEQUENCE ONLY MOVES WHEN THE TEXT DOES, unless `force`. This is
    called on every render of the tab that owns the text — sixty times
    while somebody types — and a sequence that ticked every time would
    make the far end re-read the same line sixty times.

    `force` is the PUSH BUTTON. Pressing push with the text unchanged
    must still send, because the person pressing it means "again", and a
    button that silently does nothing when it looks like it should work
    is the worst control on any screen.
    """
    now = time.time() if now is None else now
    if channel not in CHANNELS:
        raise ValueError("unknown channel: %r" % (channel,))
    w = _window(store, code, now)
    slot = w[channel]
    if force or (text or "") != slot.get("text"):
        slot["seq"] = int(slot.get("seq", 0)) + 1
        slot["at"] = now
    slot["text"] = text or ""
    w["at"] = now                    # ANY traffic keeps the window alive
    return slot


def get(store: dict, code: str, channel: str = SAY, now: float = None):
    """Read one channel's slot. None when the window is gone or idle.

    An expired window is DELETED on the way past rather than left to sit,
    so a process up for a week is not holding a hundred dead transcripts.
    """
    now = time.time() if now is None else now
    if channel not in CHANNELS:
        raise ValueError("unknown channel: %r" % (channel,))
    w = store.get(code)
    if not w:
        return None
    if now - float(w.get("at", 0)) > IDLE_SECONDS:
        store.pop(code, None)
        return None
    return w.get(channel)


def arrived(slot, seen_seq) -> bool:
    """Is there something on this slot that has not been taken yet?

    THE WHOLE RECEIVING SIDE IS THIS ONE COMPARISON. A sequence number
    that has moved past the last one acted on means new text; anything
    else means the same text seen again. Text that is empty is never an
    arrival, so clearing the far end does not make a device start
    speaking silence.
    """
    if not slot:
        return False
    if not (slot.get("text") or "").strip():
        return False
    return int(slot.get("seq", 0)) > int(seen_seq or 0)


def sweep(store: dict, now: float = None) -> int:
    """Drop every window that has gone idle. Returns how many went."""
    now = time.time() if now is None else now
    dead = [c for c, w in list(store.items())
            if now - float(w.get("at", 0)) > IDLE_SECONDS]
    for c in dead:
        store.pop(c, None)
    return len(dead)


def age_words(seconds: float) -> str:
    """How long ago, in words a tired person reads at a glance."""
    s = int(max(0, seconds))
    if s < 5:
        return "just now"
    if s < 60:
        return "%ds ago" % s
    if s < 3600:
        return "%dm ago" % (s // 60)
    return "%dh ago" % (s // 3600)


def link_for(base: str, code: str) -> str:
    """The address to type on the other device.

    Built from whatever the app knows about its own URL rather than
    hardcoded, because the same code runs on ttt-lll.streamlit.app and on
    localhost and the link has to be right in both.
    """
    base = (base or "").rstrip("/")
    return "%s/?remote=%s" % (base, code)
