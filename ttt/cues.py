"""Sentence cues — the SRT-shaped layer.

Word timings say when each word is spoken. A player needs something
coarser: where each SENTENCE begins and ends, so it can show one line at a
time and jump a whole sentence forward or back.

This is that layer, and it is deliberately its own module with no
Streamlit and no browser in it, so the rules can be tested on a laptop
with no audio and no keys.

WHY NOT JUST SPLIT THE TEXT. Because the player needs the two views to
agree exactly. The subtitle shows a sentence; the highlight colours a word
INSIDE that sentence; the jump button moves to the next one. If the
sentence boundaries came from one place and the word times from another,
they would drift apart by a word here and there and the highlight would
appear to belong to the wrong line. So both are derived from the SAME
word list, and a cue holds the indices of its own words.
"""

import re

# A sentence ends at . ! ? … or a line break, possibly followed by quotes
# or brackets. Croatian and English share this, which is the only reason
# one rule serves both.
_END = re.compile(r'[.!?…]+["\'»”’\)\]]*\s*$|\n\s*$')

# Abbreviations that end in a full stop and do NOT end a sentence. Without
# these, "g. Marko" and "e.g. this" each break a line in half.
_ABBREV = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "eg",
    "ie", "no", "fig", "approx",
    # Croatian
    "g", "gđa", "gdin", "dr", "prof", "npr", "tj", "itd", "sl", "br", "st",
}


def _ends_sentence(word: str) -> bool:
    """Does this word close a sentence?"""
    w = str(word or "").strip()
    if not w:
        return False
    if not _END.search(w):
        return False
    # A single letter plus a dot is an INITIAL, not an ending: "J. R. R.
    # Tolkien" must stay one sentence. A one-letter sentence is not a real
    # thing in either language, so this costs nothing real — but it does
    # mean a synthetic test using "a." and "b." will see one cue, not two,
    # and that is the test being unrealistic rather than the rule.
    core = re.sub(r'[^\w]', '', w).lower()
    if len(core) <= 1:
        return False
    return core not in _ABBREV


def cues(words, times, min_seconds=0.0, text=""):
    """Group words into sentence cues.

    words  : the words as displayed, in order
    times  : [(start, end)] for each word, same length
    text   : the ORIGINAL text, when there is one. STRONGLY RECOMMENDED.

    WHY `text` MATTERS, found by testing against real audio: the app's
    tokeniser deliberately excludes trailing punctuation from a word's
    span, so `what?` arrives here as `what` and `it.` as `it`. Judging
    sentence ends from the word list alone therefore finds NOTHING, and a
    whole paragraph becomes one eight-second cue — which is exactly what
    happened on the first real run. Given the original text, the character
    that FOLLOWS each word is read from it instead, which is where the
    punctuation actually is.
    returns: [{'text','start','end','first','last'}] where first/last are
             indices INTO `words`, so a caller can colour word i and know
             which cue it belongs to without a second search.

    A cue never spans a gap in the lists, and never has an end before its
    start. If the two lists disagree in length, the shorter wins — a
    caller that has lost a word should get a shorter subtitle, not an
    exception in the middle of a reading.
    """
    words = list(words or [])
    times = list(times or [])
    n = min(len(words), len(times))
    if not n:
        return []

    # Where each word sits in the original, so the punctuation after it
    # can be read. marks_for() gives character offsets; without them fall
    # back to searching, and without text at all fall back to the word.
    tails = _tails(words, text)

    out = []
    start_i = 0
    for i in range(n):
        last_one = (i == n - 1)
        ends = (_ends_sentence(words[i] + tails[i]) if tails
                else _ends_sentence(words[i]))
        if not (ends or last_one):
            continue
        t0 = float(times[start_i][0])
        t1 = float(times[i][1])
        if t1 < t0:
            t1 = t0
        out.append({
            "text": " ".join(words[start_i:i + 1]),
            "start": t0,
            "end": t1,
            "first": start_i,
            "last": i,
        })
        start_i = i + 1

    if min_seconds > 0:
        out = merge_short(out, min_seconds)
    return out


def _tails(words, text):
    """For each word, the punctuation that follows it in the original.

    Returns [] when there is no text to read, so the caller falls back to
    judging the word itself.
    """
    text = str(text or "")
    if not text:
        return []
    tails, pos = [], 0
    for w in words:
        core = str(w or "")
        j = text.find(core, pos) if core else -1
        if j < 0:
            tails.append("")
            continue
        k = j + len(core)
        # everything up to the next letter or digit belongs to this word
        end = k
        while end < len(text) and not text[end].isalnum():
            end += 1
        tails.append(text[k:end])
        pos = k
    return tails


def merge_short(cue_list, min_seconds):
    """Fold very short cues into the next one.

    A subtitle that flashes for 300 ms cannot be read. "Yes." and "No."
    are real sentences and still need to be joined to their neighbour to
    be legible, which is what every subtitle tool does and why this exists
    rather than being left to the caller.
    """
    if not cue_list:
        return []
    out = [dict(cue_list[0])]
    for c in cue_list[1:]:
        prev = out[-1]
        if (prev["end"] - prev["start"]) < min_seconds:
            prev["text"] = (prev["text"] + " " + c["text"]).strip()
            prev["end"] = c["end"]
            prev["last"] = c["last"]
        else:
            out.append(dict(c))

    # THE LAST CUE HAS NOTHING AFTER IT TO FOLD INTO, so folding forward
    # alone leaves a final "Yes." flashing for 200 ms — and the end of a
    # reading is exactly where a short sentence is most likely to be. It
    # folds BACKWARD instead, into the one before.
    while len(out) > 1 and (out[-1]["end"] - out[-1]["start"]) < min_seconds:
        tail = out.pop()
        prev = out[-1]
        prev["text"] = (prev["text"] + " " + tail["text"]).strip()
        prev["end"] = tail["end"]
        prev["last"] = tail["last"]
    return out


def at(cue_list, seconds):
    """The index of the cue playing at this moment, or -1.

    Boundaries belong to the LATER cue: at exactly the moment one ends and
    the next begins, the next one is what should be on screen, because
    that is the one about to be spoken.
    """
    if not cue_list:
        return -1
    t = float(seconds)
    for i, c in enumerate(cue_list):
        if c["start"] <= t < c["end"]:
            return i
    if t >= cue_list[-1]["end"]:
        return len(cue_list) - 1
    if t < cue_list[0]["start"]:
        return -1
    # inside a gap between cues: the one about to start
    for i, c in enumerate(cue_list):
        if t < c["start"]:
            return i
    return -1


def jump(cue_list, seconds, direction):
    """Where a skip button should move the playhead to, in seconds.

    BACK GOES TO THE START OF THIS SENTENCE FIRST, not the previous one —
    the same as every music player, and for the same reason: the common
    wish is "say that again", not "go back one".  Only when already near
    the start does it step to the previous cue.
    """
    if not cue_list:
        return 0.0
    t = float(seconds)
    i = at(cue_list, t)
    if i < 0:
        return cue_list[0]["start"]
    if direction >= 0:
        return (cue_list[i + 1]["start"] if i + 1 < len(cue_list)
                else cue_list[-1]["end"])
    if t - cue_list[i]["start"] > 1.2:
        return cue_list[i]["start"]
    return cue_list[i - 1]["start"] if i > 0 else cue_list[0]["start"]


def to_srt(cue_list):
    """The cues as an SRT file. Not used by the player, which has the list
    already — this is so a reading can be exported, and so the timings can
    be opened in any subtitle tool and looked at by eye."""
    def clock(s):
        s = max(0.0, float(s))
        h, rem = divmod(int(s), 3600)
        m, sec = divmod(rem, 60)
        return "%02d:%02d:%02d,%03d" % (h, m, sec, int(round((s % 1) * 1000)))

    lines = []
    for i, c in enumerate(cue_list, 1):
        lines.append(str(i))
        lines.append(f"{clock(c['start'])} --> {clock(c['end'])}")
        lines.append(c["text"])
        lines.append("")
    return "\n".join(lines)
