"""The Read tab: MA Reader's workflow, adapted honestly to Streamlit.

MA Reader Termux is a local Flask server driving one HTML page, so it can
do things a Streamlit script cannot. Rather than fake those, this module
takes what genuinely ports and says plainly what does not.

PORTED
    paste text and read it, one sentence at a time
    word-by-word highlight where the engine gives real timings
    an archive of past texts, re-readable without re-pasting
    time to read: "12 / 47   8:30", spoken plus estimated
    speed, and a gap between sentences
    pick up where you left off within a session
    pages, so a long text is never one unbroken session

NOT PORTED, and why
    media / lock-screen keys   needs Android privileged shell (Shizuku or
                               adb). No browser equivalent exists.
    true full screen           Streamlit owns its own chrome and re-renders
                               it constantly; "hide everything" cannot be
                               honoured here the way MA Reader's rule
                               demands, and a half-hidden interface would
                               break that rule rather than meet it. The
                               browser's own full screen (F11, or Add to
                               Home Screen) is the real answer on the web.
    clipboard auto-read        navigator.clipboard can hang forever, and a
                               Streamlit script cannot own that gesture.
                               A textarea does the same job with no trap.
    word pause inside silence  needs a per-clip silence map from ffmpeg on
                               audio the browser is playing. Possible
                               later; deliberately not faked now.

STORAGE. Streamlit Community Cloud keeps nothing on disk reliably, so the
archive lives in the browser via ttt.store. That is finite: it holds the
TEXT of each piece, never audio, and trims oldest-first when it grows past
a sane size. Audio is always re-synthesised, which is why clips are cheap
to re-read but nothing survives a cleared browser.
"""

import time

from . import reader as R

ARCHIVE_NS = "archive"
MAX_PIECES = 40
MAX_CHARS_TOTAL = 120_000        # keep the browser blob sane


def title_of(text: str, limit: int = 60) -> str:
    """First meaningful line, trimmed. No AI needed — MA Reader's Gemini
    titles are optional there and would be an extra key here."""
    for line in (text or "").splitlines():
        line = line.strip()
        if line:
            return (line[:limit] + "…") if len(line) > limit else line
    return "(empty)"


def load_archive(store) -> list:
    data = store.load()
    pieces = data.get("pieces")
    return pieces if isinstance(pieces, list) else []


def save_archive(store, pieces: list) -> None:
    store.save({"pieces": pieces})


def add_piece(pieces: list, text: str) -> list:
    """Newest first, de-duplicated by content, trimmed to fit the browser."""
    text = (text or "").strip()
    if not text:
        return pieces
    dig = R.digest(text)
    pieces = [p for p in pieces if p.get("digest") != dig]
    pieces.insert(0, {
        "digest": dig,
        "title": title_of(text),
        "text": text,
        "chars": len(text),
        "added": int(time.time()),
    })
    return trim(pieces)


def trim(pieces: list, max_pieces: int = MAX_PIECES,
         max_chars: int = MAX_CHARS_TOTAL) -> list:
    """Oldest-first eviction, by count and by total size. The archive is a
    convenience, not an obligation; it must never grow until it breaks the
    storage it lives in."""
    pieces = pieces[:max_pieces]
    total, kept = 0, []
    for p in pieces:
        total += p.get("chars", len(p.get("text", "")))
        if total > max_chars and kept:
            break
        kept.append(p)
    return kept


def remove_piece(pieces: list, digest: str) -> list:
    return [p for p in pieces if p.get("digest") != digest]


def progress_line(spoken_chars: int, total_chars: int, sentence_idx: int,
                  sentence_count: int, speed: float = 1.0,
                  sentence_gap: float = 0.0) -> str:
    """MA Reader's counter: how far in, and how long is left. Time already
    spoken is known; the rest is estimated and folded with speed and gap so
    the number moves the way the reading actually will."""
    remaining = max(0, total_chars - spoken_chars)
    secs = R.estimate_seconds(" " * remaining) / max(speed, 0.05)
    secs += max(0, sentence_count - sentence_idx) * max(0.0, sentence_gap)
    return f"{sentence_idx} / {sentence_count}   {R.format_clock(secs)}"
