"""The reading loop: sentences, pages, highlighting, playback.

Engine-agnostic by construction. It is handed `synth(text)` and gets back
`(audio_bytes, seconds, marks)`. If marks are present the highlight steps
word by word through their measured windows; if not, whole sentences light
up. That is the entire difference, and it is why word-level highlighting
arrived with Speechify without this file changing shape.

Nothing here imports a provider, and nothing here reaches into
st.session_state directly — state is passed in and handed back, so the
same loop can drive the Talk tab, the Translate tab, and the Read tab
without any of them special-casing the others.
"""

import hashlib
import html

# A page is a reading-length bite, never a cut sentence. Long text becomes
# several resumable pages instead of one unbroken session nobody can leave.
PAGE_CHARS = 1500

HL_BG = "#f59e0b"
# The spoken word. Measured: 5.17:1 on the reading background, and the
# largest separation from the cream prose of the reds tried.
HL_WORD = "#ef4444"
HL_FG = "#0b0d10"


def split_sentences(text: str, splitter):
    """`splitter` is whatever knows how to cut this text (talk_engine's
    sentence splitter today). Kept injectable so a better one can replace
    it without touching the loop."""
    return splitter(text)


def paginate(sentences, max_chars: int = PAGE_CHARS):
    """Group sentences into pages, always breaking at a sentence boundary."""
    pages, cur, cur_len = [], [], 0
    for s in sentences:
        if cur and cur_len + len(s) > max_chars:
            pages.append(cur)
            cur, cur_len = [], 0
        cur.append(s)
        cur_len += len(s) + 1
    if cur:
        pages.append(cur)
    return pages or [[]]


def digest(text: str) -> str:
    """A fingerprint of the text, for noticing it CHANGED.

    MD5 with usedforsecurity=False. Not a security hash and never used as
    one — it answers "is this the same text as last render", nothing more.
    The flag is there because on a FIPS-enabled Python hashlib.md5()
    RAISES without it, which would take the reader down on a machine
    nobody here has tested. Found by bandit at the delivery gate,
    25.8.2026: four call sites, all of them fingerprints.
    """
    return hashlib.md5((text or "").encode("utf-8"),
                       usedforsecurity=False).hexdigest()


def highlight(text: str, start=None, end=None) -> str:
    """The spoken word, coloured. Same rule as _highlight_span in app.py,
    and this is the SECOND definition that HANDOVER §0 warns about — both
    must change together or the reader view keeps the old amber block
    while Talk is clean, which reads as an intermittent bug.

    Colour only: no background, no padding, no weight. Nothing here
    participates in layout, so the line cannot reflow as the highlight
    moves. With no range, nothing is highlighted.
    """
    if start is None or end is None:
        return html.escape(text)
    span_open = '<span style="color:' + HL_WORD + ';">'
    start = max(0, min(int(start), len(text)))
    end = max(start, min(int(end), len(text)))
    if end <= start:
        return html.escape(text)      # nothing to colour; no empty span
    return (html.escape(text[:start]) + span_open +
            html.escape(text[start:end]) + "</span>" + html.escape(text[end:]))



def render_page(sentences, current_idx, word_start=None, word_end=None) -> str:
    """The whole page as HTML, with the current sentence highlighted (by
    word if marks were given, whole otherwise) and the rest plain."""
    parts = []
    for j, s in enumerate(sentences):
        if j == current_idx:
            parts.append(highlight(s, word_start, word_end))
        else:
            parts.append(html.escape(s))
    return " ".join(parts)


def estimate_seconds(text: str, chars_per_second: float = 14.5) -> float:
    """Rough time-to-read for text not yet spoken. MA Reader's own figure;
    good enough to show a total beside a counter."""
    return len(text or "") / max(chars_per_second, 1.0)


def format_clock(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def play_page(sentences, synth, on_frame, sleep, on_error=None):
    """Speak one page, one sentence at a time.

    `synth(text) -> (audio, seconds, marks|None)`   any engine
    `on_frame(html, subtitle_text, sub_start, sub_end, audio, is_new_audio)`
        called whenever the display should change; the caller owns all
        rendering, this module never draws
    `sleep(seconds)`                                 injected so tests can
                                                     run without real time

    Returns the number of sentences actually spoken.
    """
    spoken = 0
    for i, sentence in enumerate(sentences):
        try:
            audio, seconds, marks = synth(sentence)
        except Exception as e:
            if on_error:
                on_error(i, e)
            break

        if marks:
            # Play once, then walk the highlight through each mark's own
            # measured window. Playback rate is never touched.
            on_frame(render_page(sentences, i, marks[0]["start"], marks[0]["end"]),
                     sentence, marks[0]["start"], marks[0]["end"], audio, True)
            for w, m in enumerate(marks):
                if w:
                    on_frame(render_page(sentences, i, m["start"], m["end"]),
                             sentence, m["start"], m["end"], None, False)
                nxt = marks[w + 1]["start_time"] if w + 1 < len(marks) else seconds
                sleep(max(0.02, nxt - m["start_time"]))
        else:
            on_frame(render_page(sentences, i), sentence, None, None, audio, True)
            sleep(seconds + 0.15)
        spoken += 1
    return spoken
