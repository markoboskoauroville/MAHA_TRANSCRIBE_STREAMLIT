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
