import re
"""VR — Virtual Rehearsal. Hume AI, and the emotions it can be given.

Baba, 24.8.2026: "we are creating a third thing called VR, virtual
rehearsal, to experiment with human emotions. Pills for each emotion, a
deck that reads, a box to paste into. Many voices — one pill per voice.
We don't save on pills here."

WHAT HUME ACTUALLY DOES, and why this module is shaped the way it is:
the API takes a `description` alongside the text — a stage direction, not
content. It changes HOW the line is delivered. Measured on 24.8.2026,
same sentence and same voice: calm 2.59s against angry 2.91s; joyful
2.35s against sad 2.87s. The direction is doing real work.

THE THING THAT WILL BITE, from Baba's own operating brief: the limit is
PER MINUTE and returns 429 with no trustworthy Retry-After. Measured
there: 0.2s spacing gave 16 successes and 15 refusals; 3s spacing was
still refused; 12s spacing gave 31 of 31. So this module paces at 12
seconds, serially, concurrency 1 — and never guesses, it asks
`wait_left()` and tells the person in seconds.
"""

# Baba's measurement, not a guess, and not to be "optimised" without
# repeating it: 3s fails, 12s holds.
PACE_SECONDS = 12

# Hume's own text cap per utterance is generous; this is a kindness cap.
# At roughly 15 characters a second of speech, 2000 characters is over
# two minutes of audio from one press.
TEXT_CAP = 2000

# ---------------------------------------------------------------------
# THE VOICES. Every name below was read from the live catalogue on
# 24.8.2026 (160 Hume voices, two pages) and not one is remembered — a
# wrong name is a 4xx in front of somebody who just pressed play.
#
# TWELVE OF EACH. Baba asked for many and the catalogue is lopsided: 18
# male performer voices against 5 female. Holding to performer names
# alone would have shipped a rehearsal tool that offers a woman five
# parts and a man eighteen, so the female roster reaches into the wider
# English catalogue for voices of the same character — journalists,
# storytellers, ladies, mothers. Balance was worth more than the naming
# rule it cost.
# ---------------------------------------------------------------------
VOICES = {
    "F": [
        ("Classical Film Actress",           "Transatlantic", "middle"),
        ("American Lead Actress",             "American",      "middle"),
        ("Seasoned Midwestern Actress",       "American",      "middle"),
        ("Indian Actress",                    "Indian",        "middle"),
        ("Casual Podcast Host",               "American",      "young"),
        ("Cool Journalist",                   "American",      "young"),
        ("Lady Elizabeth",                    "British",       "old"),
        ("Alice Bennett",                     "British",       "young"),
        ("Mysterious Woman",                  "British",       "middle"),
        ("Warm Welsh Lady",                   "Welsh",         "middle"),
        ("Caring Mother",                     "American",      "middle"),
        ("Charming Cowgirl",                  "American",      "young"),
    ],
    "M": [
        ("Male English Actor",                "British",       "young"),
        ("Classical Film Actor",              "Transatlantic", "middle"),
        ("Indian Actor",                      "Indian",        "middle"),
        ("Booming British Narrator",          "British",       "middle"),
        ("Nature Documentary Narrator",       "British",       "middle"),
        ("English Children's Book Narrator",  "British",       "middle"),
        ("Articulate ASMR British Narrator",  "British",       "middle"),
        ("Dramatic Movie Trailer Narrator",   "American",      "middle"),
        ("Booming American Narrator",         "American",      "middle"),
        ("Campfire Narrator",                 "American",      "old"),
        ("Welsh Folk Storyteller",            "Welsh",         "middle"),
        ("Old School Radio Announcer",        "American",      "old"),
    ],
}

DEFAULT_VOICE = "Male English Actor"


def all_voices():
    """Every voice, female first, as (name, accent, age, gender)."""
    out = []
    for g in ("F", "M"):
        for name, accent, age in VOICES[g]:
            out.append((name, accent, age, g))
    return out


def voice_exists(name: str) -> bool:
    return any(v[0] == name for v in all_voices())


# ---------------------------------------------------------------------
# THE EMOTION GRID. Checkboxes rather than one choice, because Baba asked
# for "one emotion or a combination of multiple emotions" — and because
# that is what acting is. Grief that is also angry is a different reading
# from either.
#
# EACH ENTRY CARRIES ITS OWN PHRASE, not just its name. Hume's brief says
# the direction should be short and concrete; "sad" alone is a weaker
# instruction than "heavy, slow, falling at the end". The label is for
# the person, the phrase is for the machine, and they are not the same
# language.
# ---------------------------------------------------------------------
EMOTIONS = [
    ("calm",       "Calm",       "calm, measured, unhurried, even breath"),
    ("joyful",     "Joyful",     "joyful and bright, smiling through the line"),
    ("sad",        "Sad",        "sad and heavy, slow, falling at the end"),
    ("angry",      "Angry",      "angry, clipped, hard consonants, rising"),
    ("afraid",     "Afraid",     "afraid, breath held high, unsteady"),
    ("tender",     "Tender",     "tender and close, almost a whisper"),
    ("urgent",     "Urgent",     "urgent, pressing forward, no pauses"),
    ("weary",      "Weary",      "weary, worn out, the words costing effort"),
    ("amused",     "Amused",     "amused, a laugh sitting just under the words"),
    ("cold",       "Cold",       "cold and flat, withholding, no warmth"),
    ("hopeful",    "Hopeful",    "hopeful, lifting, opening at the end"),
    ("bitter",     "Bitter",     "bitter, a sourness under every word"),
    ("awed",       "Awed",       "awed and hushed, slowed by wonder"),
    ("pleading",   "Pleading",   "pleading, reaching, asking to be believed"),
    ("proud",      "Proud",      "proud, chest open, unhurried and certain"),
    ("ashamed",    "Ashamed",    "ashamed, quiet, turned inward and away"),
    ("sarcastic",  "Sarcastic",  "sarcastic, the meaning bent against the words"),
    ("conspiratorial", "Secretive",
     "conspiratorial, leaning in, sharing something private"),
]

EMOTION_IDS = [e[0] for e in EMOTIONS]

# Above this many at once the direction stops being a direction and
# becomes a contradiction. Four is already a lot to ask of one line.
MAX_EMOTIONS = 4


def emotion_phrase(eid: str) -> str:
    for e in EMOTIONS:
        if e[0] == eid:
            return e[2]
    return ""


def build_direction(picked, extra: str = "") -> str:
    """Turn ticked emotions into one stage direction for Hume.

    ORDER IS THE ORDER OF THE GRID, not the order they were ticked —
    otherwise the same four emotions produce a different direction each
    time and a rehearsal cannot be repeated. Repeatability is the whole
    point of a rehearsal tool.

    An empty pick is not an error and does not invent a mood: it returns
    the neutral direction, which is Hume reading it plainly.
    """
    chosen = [e for e in EMOTIONS if e[0] in set(picked or ())][:MAX_EMOTIONS]
    parts = [c[2] for c in chosen]
    note = (extra or "").strip()
    if not parts and not note:
        return "natural, unforced delivery"
    if note:
        parts.append(note)
    return ", ".join(parts)


def summarise(picked) -> str:
    """What the person sees: the labels they ticked, in grid order."""
    chosen = [e[1] for e in EMOTIONS if e[0] in set(picked or ())]
    return " + ".join(chosen[:MAX_EMOTIONS]) if chosen else "neutral"


# ---------------------------------------------------------------------
# PACING. Baba: "if I need to wait 30 seconds between two reads, no
# problem — just write to the user, please wait, Hume AI is drinking
# coffee." So the wait is stated in seconds and never hidden.
# ---------------------------------------------------------------------

def wait_left(last_at, now, pace: int = PACE_SECONDS) -> int:
    """Whole seconds still to wait, 0 when it is safe to call.

    Takes `now` rather than reading the clock, so the caller's tests can
    move time without sleeping — a timeout that has never been tested is
    a rumour, and one that can only be tested by waiting never gets
    tested at all.
    """
    if not last_at:
        return 0
    try:
        gone = float(now) - float(last_at)
    except (TypeError, ValueError):
        return 0
    if gone < 0:
        # The clock moved backwards. Refuse to trust it and wait the
        # whole pace rather than firing immediately into a 429.
        return int(pace)
    left = float(pace) - gone
    return int(left) + (1 if left > int(left) else 0) if left > 0 else 0


def ready(last_at, now, pace: int = PACE_SECONDS) -> bool:
    return wait_left(last_at, now, pace) == 0


# ---------------------------------------------------------------------
# MANY ACCOUNTS, SO NOBODY WAITS. Baba supplied 21 Hume accounts, all 21
# verified working on 24.8.2026.
#
# THE INSIGHT THAT MAKES THIS ENTERPRISE-GRADE RATHER THAN MERELY
# CORRECT: Hume's limit is per MINUTE and per ACCOUNT. One account means
# one call every 12 seconds. Twenty-one accounts, each rested in turn,
# means twenty-one calls in the time one account would take — and in
# practice nobody ever sees the coffee message, because by the time the
# rotation comes back round to a key, its minute has long passed.
#
# So the pace is PER KEY, not global. A global stamp would have made 21
# working accounts no faster than 1, which is the whole point missed.
# ---------------------------------------------------------------------

def pick_rested(keys, now, pace: int = PACE_SECONDS):
    """(index, wait) — the best key to use right now.

    Returns the first key that has rested long enough, with wait 0. If
    none has, returns the one that will be ready SOONEST and how many
    seconds that is, so the caller can say a true number rather than a
    round guess.

    Skips dead keys entirely and resting ones until their cool_until has
    passed — a key parked by a 429 is not merely unrested, it has been
    told to stop.
    """
    best_i, best_wait = None, None
    for i, k in enumerate(keys or ()):
        if (k.get("state") or "") == "dead":
            continue
        cool = float(k.get("cool_until") or 0)
        if cool and cool > now:
            wait = int(cool - now) + 1
        else:
            wait = wait_left(k.get("last_used"), now, pace)
        if wait == 0:
            return i, 0
        if best_wait is None or wait < best_wait:
            best_i, best_wait = i, wait
    if best_i is None:
        return None, 0          # nothing usable at all — not a wait
    return best_i, best_wait


def usable_count(keys) -> int:
    return sum(1 for k in (keys or ()) if (k.get("state") or "") != "dead")


# ---------------------------------------------------------------------
# THE CHOICES, KEPT WHERE STREAMLIT CANNOT REACH THEM
#
# Splitting VR into two panels — the cast and the direction — means the
# emotion checkboxes are NOT RENDERED while the cast is showing. A
# Streamlit widget's state belongs to Streamlit: a key whose widget does
# not appear in a run is cleaned up, so picking three emotions, looking
# at the voices, and coming back would have found the direction blank.
#
# HOW_WE_WORK.md calls this "the single most useful thing in this
# codebase", and it cost three sessions the first time: keep the value
# somewhere Streamlit does not manage, and let the widget be only a VIEW
# of it. §63.
#
# So the truth lives under `_vr_picked` and `_vr_note_keep`, which are
# plain session entries no widget owns. The checkboxes read from them on
# the way in and write to them on the way out.
#
# These are pure functions on a dict so the behaviour can be tested
# without Streamlit at all — four-tests.md: if the logic cannot be run
# without starting the app, that is itself the finding.
# ---------------------------------------------------------------------

PICKED_KEY = "_vr_picked"
NOTE_KEY = "_vr_note_keep"


def picked_of(state) -> list:
    """The emotions currently chosen, in EMOTION_IDS order, always."""
    held = state.get(PICKED_KEY) or []
    return [e for e in EMOTION_IDS if e in held]


def set_picked(state, eid: str, on: bool) -> list:
    """Tick or untick one emotion. Returns the new list.

    Order is imposed rather than remembered, so the direction sentence
    reads the same however the boxes were pressed. Unticking something
    that was never ticked is not an error — a checkbox can report false
    on a render where it was simply absent.
    """
    held = set(picked_of(state))
    if on:
        held.add(eid)
    else:
        held.discard(eid)
    out = [e for e in EMOTION_IDS if e in held]
    state[PICKED_KEY] = out
    return out


def note_of(state) -> str:
    return str(state.get(NOTE_KEY) or "")


def set_note(state, text: str) -> str:
    state[NOTE_KEY] = str(text or "")
    return state[NOTE_KEY]


def too_many(state) -> bool:
    return len(picked_of(state)) > MAX_EMOTIONS


PANELS = ("cast", "direction")
DEFAULT_PANEL = "cast"


def clamp_panel(value) -> str:
    """A stored panel that is not one of the two would raise ValueError
    inside the widget and take the whole page down — the same trap the
    tier radio already met and clamps for. Same fix, same reason."""
    return value if value in PANELS else DEFAULT_PANEL


# ---------------------------------------------------------------------
# DIRECTION TAGS — the direction moves INTO the text
#
# Baba, 25.8.2026: "You remove checkboxes. I don't need checkbox, forget
# it... So if I press calm, it will insert where my cursor is. Calm. So
# it starts with less than sign, it says calm, greater than sign. And
# that's the emotion or direction to read the following sentence until
# the new direction is found. And even a few directions can be in one
# line: angry, afraid, tender."
#
# THIS CHANGES WHAT A DIRECTION IS. A tick-box says "read the WHOLE line
# like this". A tag says "read from HERE like this, until the next tag".
# One is a setting on the take; the other is punctuation in the script,
# and a script is what an actor actually marks up.
#
#     <calm>The door opened. <angry>Who let you in?
#
# WHAT IT BUYS. One take can carry a turn. With tick-boxes, an angry
# sentence after a calm one is two takes and two waits, and the join is
# audible because the two were rendered separately.
#
# THE TAG IS THE WORD, LOWERCASED, IN ANGLE BRACKETS. Not a name from a
# table — a tag is written by hand as often as it is pressed, and a form
# somebody can type is a form they can also mistype, so parsing is
# forgiving: case is ignored, spaces around the word are ignored, and
# several words inside one pair of brackets are one direction with
# several parts.
# ---------------------------------------------------------------------

TAG_OPEN = "<"
TAG_CLOSE = ">"
_TAG_RE = re.compile(r"<\s*([^<>]{1,80}?)\s*>")


def tag_for(words) -> str:
    """`"calm"` or `["angry", "afraid"]` -> `"<calm>"`, `"<angry, afraid>"`.

    SEVERAL IN ONE PAIR OF BRACKETS, not several pairs. Baba: "even a few
    directions can be in one line: angry, afraid, tender." `<angry>` then
    `<afraid>` would read as the second REPLACING the first, since a tag
    holds until the next one; inside one pair they are one direction with
    three parts, which is what he means and what an actor writes.
    """
    if isinstance(words, str):
        words = [words]
    parts = [str(w).strip().lower() for w in (words or []) if str(w).strip()]
    if not parts:
        return ""
    return TAG_OPEN + ", ".join(parts) + TAG_CLOSE


def insert_tag(text: str, caret, tag: str):
    """Put `tag` into `text` at `caret`. Returns (new_text, new_caret).

    THE CARET IS CLAMPED, because it arrives from a previous render and
    the text may have been shortened since — HOW_WE_WORK says slicing
    past the end silently drops the tail, and that is somebody's writing.
    `None` means the end, which is the honest answer when nothing has
    told us otherwise.

    A SPACE IS ADDED AFTER, never before. A tag governs what FOLLOWS it,
    so it must not be glued to the word it is about to describe; and a
    space in front would be inserted into the middle of somebody's word
    if the caret happens to sit there.
    """
    body = text or ""
    if not tag:
        return body, (len(body) if caret is None else caret)
    pos = len(body) if caret is None else max(0, min(int(caret), len(body)))
    piece = tag if tag.endswith(" ") else tag + " "
    return body[:pos] + piece + body[pos:], pos + len(piece)


def tags_in(text: str) -> list:
    """Every tag in the text, in order, as lists of words.

    Used to tell somebody what their script currently says without
    reading it back to them, and to check a round trip in a test.
    """
    out = []
    for m in _TAG_RE.finditer(text or ""):
        words = [w.strip().lower() for w in m.group(1).split(",")
                 if w.strip()]
        if words:
            out.append(words)
    return out


def split_directed(text: str) -> list:
    """The script as [(words, spoken_text)] — the whole point of tags.

    Text before the first tag is spoken with NO direction, which is the
    right default: somebody who has not marked anything up wants it read
    plainly, not read as whatever the first tag happens to say.

    Segments with nothing to speak are dropped, so two tags in a row do
    not produce a silent take, and a tag at the very end is not a
    request to render an empty string.
    """
    body = text or ""
    out, pos, current = [], 0, []
    for m in _TAG_RE.finditer(body):
        chunk = body[pos:m.start()].strip()
        if chunk:
            out.append((list(current), chunk))
        current = [w.strip().lower() for w in m.group(1).split(",")
                   if w.strip()]
        pos = m.end()
    tail = body[pos:].strip()
    if tail:
        out.append((list(current), tail))
    return out


def strip_tags(text: str) -> str:
    """The words alone, for anything that must not read the markup."""
    return re.sub(r"\s{2,}", " ", _TAG_RE.sub(" ", text or "")).strip()


# ---- THE PERSON'S OWN DIRECTIONS ------------------------------------
# Baba: "when user types direction, there should be one button add and
# then this direction is added on the insertion point... And when user
# press Add, then you need to open one more box for next own direction.
# So we have history of those things, and then the user can in this
# session have multiple of his own presets."
#
# So a custom direction is not a one-off: writing it MAKES it, and it
# stays on the panel beside the built-in ones for the rest of the
# session. The built-in twelve are a starting vocabulary, not the limit
# of what a rehearsal can ask for.

OWN_KEY = "_vr_own"
MAX_OWN = 24


def own_of(state) -> list:
    return list(state.get(OWN_KEY) or [])


def add_own(state, text: str) -> list:
    """Remember one of his own directions. Returns the new list.

    NEWEST FIRST, because the one just written is the one about to be
    used again. De-duped case-insensitively so pressing add twice on the
    same words does not fill the panel with the same pill; the ORIGINAL
    spelling is kept, since he chose it.

    Capped, because this is a panel and not an archive — past MAX_OWN the
    oldest falls off rather than the row growing until it fills a phone.
    """
    word = (text or "").strip()
    if not word:
        return own_of(state)
    have = own_of(state)
    kept = [w for w in have if w.strip().lower() != word.lower()]
    out = ([word] + kept)[:MAX_OWN]
    state[OWN_KEY] = out
    return out


def remove_own(state, text: str) -> list:
    out = [w for w in own_of(state)
           if w.strip().lower() != (text or "").strip().lower()]
    state[OWN_KEY] = out
    return out


def voice_meta(name: str) -> str:
    """The accent and age of a voice, as a stage direction.

    The cast table already carries them and the tooltip already shows
    them; a preview that used a different description would sound like
    something other than what the person just read.
    """
    for g in ("F", "M"):
        for vn, acc, age in VOICES.get(g, ()):
            if vn == name:
                return "%s, %s" % (acc, age)
    return ""
