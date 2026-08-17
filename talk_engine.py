# -*- coding: utf-8 -*-
"""
Talk engine — real-time reading, no caching.

Per Baba's direction: forget the mp3-cache/word-timing machinery from the
ma-reader-thermux port. This synthesizes one sentence at a time straight to
memory and hands it to the browser immediately — the same shape as asking a
page to read itself aloud. Nothing is written to disk, nothing is reused
across reads, and there is no per-word timing: only the currently-speaking
sentence is tracked, because word-level highlight drifts and sentence-level
does not.

Four voices only:
    Sonia      en-GB-SoniaNeural       English (UK) female   vkey ukF
    Ryan       en-GB-RyanNeural        English (UK) male     vkey ukM
    Gabrijela  hr-HR-GabrijelaNeural   Croatian female       vkey hrF
    Srecko     hr-HR-SreckoNeural      Croatian male         vkey hrM
"""
import re
import asyncio

VOICES = {
    "ukF": ("en-GB-SoniaNeural",     "Sonia",     "en", "F"),
    "ukM": ("en-GB-RyanNeural",      "Ryan",      "en", "M"),
    "hrF": ("hr-HR-GabrijelaNeural", "Gabrijela", "hr", "F"),
    "hrM": ("hr-HR-SreckoNeural",    "Srecko",    "hr", "M"),
    # Added for the Translate tab. Same voices Baba's own prior MA Reader
    # app had already hand-picked for these languages (found in its LANGS
    # table) — reused rather than guessed fresh, so the quality bar matches.
    "itF": ("it-IT-ElsaNeural",      "Elsa",      "it", "F"),
    "itM": ("it-IT-DiegoNeural",     "Diego",     "it", "M"),
    "deF": ("de-DE-KatjaNeural",     "Katja",     "de", "F"),
    "deM": ("de-DE-ConradNeural",    "Conrad",    "de", "M"),
    "frF": ("fr-FR-DeniseNeural",    "Denise",    "fr", "F"),
    "frM": ("fr-FR-HenriNeural",     "Henri",     "fr", "M"),
}
UNIT_CAP = 320

# ---------- text -> sentences (verbatim from the source app) ----------
_SENT_RE = re.compile(r"(?<=[.!?\u2026])\s+")

def split_sentences(text):
    spans, start = [], 0
    for m in _SENT_RE.finditer(text):
        spans.append((start, m.start())); start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return [(a, b) for a, b in spans if text[a:b].strip()]

def split_units(text, cap=UNIT_CAP):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    units = []
    for a, b in split_sentences(text):
        s = a
        while b - s > cap:
            cut = text.rfind(" ", s, s + cap)
            if cut <= s:
                cut = s + cap
            if text[s:cut].strip():
                units.append((s, cut))
            s = cut
            while s < b and text[s] in " \n\t":
                s += 1
        if b > s and text[s:b].strip():
            units.append((s, b))
    return units

def sentences_of(text):
    """Text -> list of clean sentence strings, ready to speak one at a time."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return [text[a:b].strip() for a, b in split_units(text)]

PAGE_CHARS = 1500   # roughly a minute or two of speech; never splits a sentence

def paginate(sentences, max_chars=PAGE_CHARS):
    """Group sentences into reading-length pages, always breaking at a
    sentence boundary, never mid-sentence. A very long single document
    becomes several short, resumable reading sessions instead of one long
    uninterruptible one — see HANDOVER.md for why this exists."""
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

# ---------- live synthesis, one sentence, no disk, no cache ----------
def _communicate(edge_tts, text, voice):
    """edge-tts 7.x defaults to SentenceBoundary; ask for WordBoundary
    explicitly or duration comes back as 0 with no boundary events at all."""
    try:
        return edge_tts.Communicate(text, voice, boundary="WordBoundary")
    except TypeError:
        return edge_tts.Communicate(text, voice)

async def _synth(text, voice):
    import edge_tts
    audio = bytearray()
    total = 0.0
    com = _communicate(edge_tts, text, voice)
    async for ch in com.stream():
        if ch["type"] == "audio":
            audio.extend(ch["data"])
        elif ch["type"] == "WordBoundary":
            end = ch["offset"] / 1e7 + ch["duration"] / 1e7
            if end > total:
                total = end
    return bytes(audio), total

def synth_sentence_voice(text, edge_voice):
    """Speak one sentence with a raw edge-tts voice id. Returns (mp3_bytes,
    seconds). Nothing touches disk — this is a live read, not a cache entry."""
    loop = asyncio.new_event_loop()
    try:
        audio, total = loop.run_until_complete(_synth(text, edge_voice))
    finally:
        loop.close()
    if not audio:
        raise RuntimeError("no audio returned")
    if total <= 0.05:
        total = max(1.0, len(text.split()) * 0.38)   # rough fallback estimate
    return audio, total


def synth_sentence(text, vkey):
    """Speak one sentence in one of the four Talk-tab voices."""
    return synth_sentence_voice(text, VOICES[vkey][0])


