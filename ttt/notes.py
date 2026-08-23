"""NOTES — what the archive became.

The archive could only do one thing: put a transcript back in the box.
Baba: *"Imagine the first tab is Keep from Google, with the ability to
talk to create a note, and once the note is created the user can talk
directly to the note. He does not need to edit with the fingers."*

So a note is not a saved copy of something — it is the thing itself,
opened, spoken into, and closed again.

WHY THIS FILE AND NOT ARCHIVE.PY. The archive's record is a *take*: one
recording, immutable, identified by when it arrived. A note is a
*document*: it has a title, it changes, and its history is the point.
Bolting edits onto a take would have left `add()` meaning two different
things. Old archive items are read once on first use and become notes,
so nothing anybody recorded is lost.

STILL SESSION STATE, FOR NOW. Notes live where the archive lived, which
means they still do not survive a reload. The Drive half exists already
— §60's paired archive stores audio and `text.txt` together — so a note
that carries a `rec_id` can be pushed there and pulled back. Wiring that
is the next piece and is deliberately not done here: the shape of a note
had to settle first.
"""

import itertools
import time

KEY = "_t1_notes"
LIMIT = 200          # notes kept; far more than the archive's 60

# A COUNTER, NOT A CLOCK — the same lesson archive.py learned. Two notes
# made in one millisecond got one id, and deleting either deleted both.
_seq = itertools.count(1)

TITLE_WORDS = 5      # words taken for an untitled note's heading


def _stamp():
    """Baba's format: 7:36/23/08/26.

    Hour without a leading zero, then day, month, and the year in two
    digits — no century, because nobody needs telling which one it is.
    Kept short because it sits in a corner as a mark on the frame, not
    as a sentence: "made 2026-08-23 07:36" was nineteen characters
    saying what nine can.

    %-H is not portable (it fails on Windows), so the hour is trimmed by
    hand.
    """
    t = time.localtime()
    return "%d:%02d/%02d/%02d/%s" % (
        t.tm_hour, t.tm_min, t.tm_mday, t.tm_mon,
        time.strftime("%y", t))


def _short():
    return time.strftime("%H:%M")


def title_for(text, fallback="—"):
    """A heading from the first few words.

    Not the first N characters: cutting mid-word reads as damage. Not the
    first line either — dictation arrives as one long line, so that gives
    back the whole note.
    """
    words = " ".join(str(text or "").split()).split(" ")
    words = [w for w in words if w]
    if not words:
        return fallback
    head = " ".join(words[:TITLE_WORDS])
    return head + ("…" if len(words) > TITLE_WORDS else "")


def _all(state):
    got = state.get(KEY)
    if isinstance(got, list):
        return got
    state[KEY] = []
    return state[KEY]


def adopt_archive(state, archive_key="_t1_archive"):
    """Turn anything left in the old archive into notes, once.

    Runs on first use and then never again — the marker is what stops a
    second pass re-adding notes the person has since deleted.
    """
    if state.get("_notes_adopted"):
        return 0
    state["_notes_adopted"] = True
    # THROUGH archive.items(), NOT the raw list. The archive stores
    # oldest-first and items() reverses on the way out — reading the raw
    # list and reversing it again put the OLDEST archive item at the top
    # of the notes. Caught by a test; the lesson is to use the documented
    # order rather than the storage order.
    try:
        from . import archive as _archive
        old = _archive.items(state)          # newest first
    except Exception:
        old = state.get(archive_key) or []
    if not isinstance(old, list) or not old:
        return 0
    taken = 0
    # Oldest added first, so the newest archive item ends the newest note.
    for rec in reversed(old):
        try:
            body = (rec.get("text") or "").strip()
            if not body:
                continue
            add(state, body, language=rec.get("language", ""),
                rec_id=rec.get("rec_id", ""), at=rec.get("at", ""))
            taken += 1
        except Exception:
            continue
    return taken


def add(state, text, language="", rec_id="", at=""):
    """Make a note. Returns its id, or None if there was nothing to keep.

    THE SAME TEXT TWICE IN A ROW IS NOT KEPT TWICE, for the reason
    archive.py gives: Streamlit reruns constantly and delivery can be
    reached more than once for one recording.
    """
    try:
        body = (text or "").strip()
        if not body:
            return None
        notes = _all(state)
        if notes and (notes[0].get("text") or "").strip() == body:
            return notes[0].get("id")
        note = {
            "id": "n%d" % next(_seq),
            "title": "",                 # empty means "use the first words"
            "text": body,
            "at": at or _short(),
            "made": _stamp(),
            "edited": "",
            "language": language or "",
            "rec_id": rec_id or "",
        }
        notes.insert(0, note)
        del notes[LIMIT:]
        return note["id"]
    except Exception:
        return None


def items(state):
    return list(_all(state))


def get(state, note_id):
    for n in _all(state):
        if n.get("id") == note_id:
            return n
    return None


def update(state, note_id, text=None, title=None):
    """Change a note in place, and record that it changed.

    The note KEEPS ITS POSITION in the list. Moving an edited note to the
    top would mean that opening a note, adding one line and closing it
    reshuffles everything under the person's hand — and someone who
    cannot see well loses the list they had just learned.
    """
    note = get(state, note_id)
    if note is None:
        return False
    if text is not None:
        note["text"] = text
    if title is not None:
        note["title"] = title.strip()
    note.pop(_HAY, None)             # what it says changed; re-fold later
    note["edited"] = _stamp()
    return True


def append(state, note_id, text, at=None):
    """Speak more into an existing note — AT THE CURSOR when there is one.

    Baba: "it does not insert when I put my cursor, it just appends
    normally... it ignores my cursor and just puts a line at the end."
    He is right, and it made the note a log rather than a document: you
    could add to the bottom and nowhere else.

    `at` is the caret position the editor reported. None means the end,
    which is what a take from the DECK gets — the deck has no cursor,
    and appending is the only honest answer there.

    A BLANK LINE AROUND IT, not a space. Each burst of dictation is a
    paragraph — that is how a person talks into a note, in passes — and
    running them together makes one wall of text nobody can find
    anything in.
    """
    note = get(state, note_id)
    if note is None:
        return False
    more = (text or "").strip()
    if not more:
        return False
    old = (note.get("text") or "")

    if at is None or not old.strip():
        # APPENDING IS A NEW PASS, so it gets a blank line. A take from
        # the deck has no cursor and lands at the end, and each burst of
        # dictation is its own paragraph — that is how somebody talks
        # into a note, in sittings.
        note["text"] = (old.rstrip() + "\n\n" + more) if old.strip() else more
    else:
        # INSERTING IS THE MIDDLE OF A SENTENCE, so it gets NOTHING.
        #
        # Baba: "it presses Enter or New Line after. I do not want that.
        # Just insert that sentence, no New Line, no Enter."
        #
        # This wrapped every insert in blank lines, which is right for a
        # new pass and wrong for the thing he is actually doing: putting
        # the cursor inside a line and speaking a clause into it. The
        # words arrived and the sentence they belonged to was broken in
        # three.
        #
        # ONE SPACE WHERE ONE IS NEEDED, and none where it is not. A
        # caret sitting straight after a word needs a space or the two
        # run together; a caret already after a space or a newline needs
        # nothing, and adding one would leave a double space that has to
        # be hunted down later.
        #
        # CLAMPED, because a caret from a previous render can be past the
        # end of text that has since been shortened — and slicing beyond
        # the end silently drops the tail.
        i = max(0, min(int(at), len(old)))
        before, after = old[:i], old[i:]
        lead = "" if (not before or before[-1].isspace()) else " "
        tail = "" if (not after or after[0].isspace()) else " "
        note["text"] = before + lead + more + tail + after
    note.pop(_HAY, None)             # what it says changed; re-fold later
    note["edited"] = _stamp()
    return True


def remove(state, note_id):
    notes = _all(state)
    for i, n in enumerate(notes):
        if n.get("id") == note_id:
            del notes[i]
            return True
    return False


def clear(state):
    state[KEY] = []


def count(state):
    return len(_all(state))


def when_of(note):
    """The one date worth showing: when it was last touched.

    A note carries both `made` and `edited`, and showing both was two
    timestamps a centimetre apart differing by minutes. The later one
    answers the only question anybody asks of a note in a list.
    """
    return (note.get("edited") or note.get("made")
            or note.get("at") or "")


def heading(note):
    """What the card shows as its title."""
    t = (note.get("title") or "").strip()
    return t if t else title_for(note.get("text", ""))


def body_preview(note, width=120):
    """The taste under the heading — and NOT a repeat of it.

    An untitled note is headed by its own first words, so showing the
    text from the beginning printed those words twice on every card. The
    preview therefore starts AFTER the heading when the heading came from
    the text, and from the beginning when the person wrote a title of
    their own.
    """
    body = " ".join(str(note.get("text", "")).split())
    if not (note.get("title") or "").strip():
        rest = body.split(" ")[TITLE_WORDS:]
        body = " ".join(rest)
    if not body:
        return ""
    if len(body) > width:
        body = body[:width - 1].rstrip() + "…"
    return body


_HAY = "_hay"        # the folded haystack, cached on the note itself


def _haystack(note):
    """The folded text this note is searched against, computed once.

    SEARCH RUNS ON EVERY KEYSTROKE, and Streamlit reruns the whole script
    besides — so folding two hundred notes' full text each time was 22 ms
    of the same work repeated, measured on a full notebook. The cache is
    dropped explicitly by update() and append(), which are the only two
    things that can change what a note says; a stale-cache bug is far
    worse than a slow search, so invalidation is not left to a guess
    about lengths or timestamps.
    """
    got = note.get(_HAY)
    if isinstance(got, str):
        return got
    made = _fold(heading(note) + " " + (note.get("text") or ""))
    note[_HAY] = made
    return made


def search(state, query):
    """Notes matching every word of the query, in title or body.

    EVERY WORD, NOT ANY. Typing two words to narrow a list and getting
    MORE results back is the thing that makes people stop using a search
    box. Case-insensitive, and accent-blind for Croatian, so "cekaj"
    finds "čekaj" — nobody dictating should have to produce a diacritic
    to find their own note.
    """
    q = _fold(query).split()
    if not q:
        return items(state)
    out = []
    for n in _all(state):
        hay = _haystack(n)
        if all(word in hay for word in q):
            out.append(n)
    return out


# "dž" was in here mapping to "d" and could never fire: by the time it
# was reached "ž" had already become "z", so the pair read "dz" and the
# rule matched nothing. It was also the wrong answer — "dz" is what a
# person types. Removed rather than reordered.
_FOLD = {
    "č": "c", "ć": "c", "ž": "z", "š": "s", "đ": "d",
    "Č": "c", "Ć": "c", "Ž": "z", "Š": "s", "Đ": "d",
}


def _fold(s):
    s = str(s or "").lower()
    for a, b in _FOLD.items():
        s = s.replace(a, b)
    return s
