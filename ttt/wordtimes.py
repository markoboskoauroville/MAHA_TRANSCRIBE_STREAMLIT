"""Word-level timings for read-aloud highlighting.

Full method, measurements and the failed approaches: docs/WORD_TIMINGS.md.
The short version, because it is counter-intuitive:

  * Speech has NO silence between words. Measured against exact engine
    marks, 99.2% of inter-word intervals are exactly zero seconds. Any
    attempt to find word boundaries by detecting gaps is looking for
    something that does not exist, and will find stop consonants instead.
  * Whisper reports word-level timestamps. Used purely as a measuring
    instrument — the transcript is discarded except as a key for
    alignment — it puts the median word within 48 ms of truth, against
    119 ms for proportional timing.
  * The hard part is not the timing, it is MAPPING the words Whisper
    heard onto the words on screen. It hears '12%' for '12 percent' and
    '1,' for 'One'. That is a sequence alignment, done here with
    Needleman-Wunsch over normalised tokens.

Three layers, degrading in order:
  1. engine marks, when the engine gives them (exact)
  2. Whisper word timestamps  (median 48 ms)
  3. proportional             (median 119 ms, always available)

THIS MODULE NEVER RAISES. A highlight is a courtesy; the audio is the
point. Every failure falls through to the next layer.
"""

import json
import pathlib
import re
import urllib.request
import uuid

TIMEOUT = 60
MODEL = "whisper-large-v3-turbo"
ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"

# Groq sits behind Cloudflare, which returns 403 "error code: 1010" to
# Python's default User-Agent. It looks exactly like a dead key and is not.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_ONES = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
         'eight', 'nine', 'ten', 'eleven', 'twelve']


# --------------------------------------------------------------------
#  layer 3 — always available
# --------------------------------------------------------------------

def proportional(words, total_seconds):
    """Divide the time by word length. Never good, never unavailable."""
    if not words or not total_seconds:
        return []
    n = sum(max(1, len(w)) for w in words)
    out, t = [], 0.0
    for w in words:
        d = max(1, len(w)) / n * total_seconds
        out.append((t, t + d))
        t += d
    return out


# --------------------------------------------------------------------
#  layer 2 — Whisper word timestamps
# --------------------------------------------------------------------

def fetch_word_times(audio_path, key, language=None, model=MODEL,
                     timeout=TIMEOUT):
    """[{'word','start','end'}] from Groq, or None. Never raises.

    response_format MUST be verbose_json and the granularity parameter
    MUST be sent, brackets included — with anything else the response
    arrives looking fine and carrying no timings at all.
    """
    try:
        data = pathlib.Path(audio_path).read_bytes()
        if not data:
            return None
        b = uuid.uuid4().hex
        fields = {"model": model, "response_format": "verbose_json",
                  "timestamp_granularities[]": "word"}
        if language:
            fields["language"] = language
        body = b""
        for k, v in fields.items():
            body += (f"--{b}\r\nContent-Disposition: form-data; "
                     f"name=\"{k}\"\r\n\r\n{v}\r\n").encode()
        body += (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; "
                 f"filename=\"audio{pathlib.Path(audio_path).suffix or '.wav'}\"\r\n"
                 f"Content-Type: application/octet-stream\r\n\r\n").encode()
        body += data + b"\r\n" + f"--{b}--\r\n".encode()
        req = urllib.request.Request(
            ENDPOINT, data=body,
            headers={"Authorization": "Bearer " + str(key), "User-Agent": UA,
                     "Content-Type": f"multipart/form-data; boundary={b}"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read().decode("utf-8"))
        words = out.get("words")
        if not words:
            return None
        clean = []
        for w in words:
            if w.get("start") is None:
                continue
            clean.append({"word": str(w.get("word", "")),
                          "start": float(w["start"]),
                          "end": float(w.get("end", w["start"]))})
        return clean or None
    except Exception:
        return None


def normalise(tok):
    """See through the spelling differences that break the alignment.

    Whisper writes digits where the text has words and the reverse, so
    without this every numeral becomes a mismatch and drags the whole
    alignment out of step for the rest of the sentence.
    """
    t = re.sub(r"[^\w]", "", str(tok).lower(), flags=re.UNICODE)
    if t.isdigit() and len(t) <= 2 and int(t) < len(_ONES):
        return _ONES[int(t)]
    return t


def map_heard_to_text(heard, words):
    """Needleman-Wunsch. Returns, per displayed word, the heard index or None."""
    n, m = len(words), len(heard)
    if not n or not m:
        return [None] * n
    a = [normalise(w) for w in words]
    b = [normalise(h.get("word", "")) for h in heard]

    GAP = -1.0
    sc = [[0.0] * (m + 1) for _ in range(n + 1)]
    bk = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        sc[i][0] = i * GAP
        bk[i][0] = 1
    for j in range(1, m + 1):
        sc[0][j] = j * GAP
        bk[0][j] = 2
    for i in range(1, n + 1):
        ai = a[i - 1]
        for j in range(1, m + 1):
            bj = b[j - 1]
            if ai and ai == bj:
                s = 2.0
            elif ai and bj and (ai.startswith(bj) or bj.startswith(ai)):
                s = 1.0          # 'people' inside '3,500 people'
            else:
                s = -1.0
            diag = sc[i - 1][j - 1] + s
            up = sc[i - 1][j] + GAP
            left = sc[i][j - 1] + GAP
            best = diag if diag >= up and diag >= left else (
                up if up >= left else left)
            sc[i][j] = best
            bk[i][j] = 0 if best == diag else (1 if best == up else 2)

    out = [None] * n
    i, j = n, m
    while i > 0 and j > 0:
        d = bk[i][j]
        if d == 0:
            out[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif d == 1:
            i -= 1
        else:
            j -= 1
    return out


def times_from_heard(heard, words, total_seconds=None):
    """Turn heard timings into one (start, end) per displayed word.

    Tolerates malformed entries. This is a public function and callers
    pass raw API output straight into it; an entry with no 'start' is
    something the upstream service is entitled to send, and it must cost
    that one word's precision rather than the whole highlight.
    """
    if not heard or not words:
        return None

    def start_of(h):
        try:
            v = h.get("start")
            return None if v is None else float(v)
        except (AttributeError, TypeError, ValueError):
            return None

    idx = map_heard_to_text(heard, words)
    if all(j is None for j in idx):
        return None

    starts = [None] * len(words)
    for i, j in enumerate(idx):
        if j is not None:
            starts[i] = start_of(heard[j])

    if all(s is None for s in starts):
        return None

    if starts[0] is None:
        first = next((s for s in starts if s is not None), 0.0)
        starts[0] = min(0.0, first) if first < 0 else 0.0
    if starts[-1] is None:
        starts[-1] = max(s for s in starts if s is not None)

    # Interpolate anything unmatched. A word without a time would freeze
    # the highlight, which reads as worse than being slightly early.
    i = 0
    while i < len(words):
        if starts[i] is not None:
            i += 1
            continue
        j = i
        while j < len(words) and starts[j] is None:
            j += 1
        left = starts[i - 1] if i > 0 else 0.0
        right = starts[j] if j < len(words) else (total_seconds or left)
        for k in range(i, j):
            starts[k] = left + (right - left) * (k - i + 1) / (j - i + 1)
        i = j

    # Monotonic, always. A highlight that jumps backwards is a bug the
    # reader sees instantly.
    for i in range(1, len(starts)):
        if starts[i] < starts[i - 1]:
            starts[i] = starts[i - 1]

    try:
        last_end = float(heard[-1].get("end") or starts[-1])
    except (AttributeError, TypeError, ValueError):
        last_end = starts[-1]
    ends = starts[1:] + [max(starts[-1], total_seconds or last_end)]
    return list(zip(starts, ends))


# --------------------------------------------------------------------
#  the layered entry point
# --------------------------------------------------------------------

def word_times(words, total_seconds, audio_path=None, rotate=None,
               language=None, engine_marks=None):
    """Best available timings for `words`. Returns (times, source).

    engine_marks : timings the TTS engine already gave (Speechify). Used
                   as-is when their count matches; they are exact.
    rotate       : the app's key-ring caller, rotate(fn) -> fn(key). If
                   absent, the Whisper layer is skipped entirely.

    source is 'engine', 'whisper' or 'proportional' so the caller can say
    honestly how good the highlight is.
    """
    words = list(words or [])
    if not words:
        return [], "none"

    if engine_marks and len(engine_marks) == len(words):
        return list(engine_marks), "engine"

    if audio_path and rotate:
        try:
            heard = rotate(lambda k: fetch_word_times(
                audio_path, k, language=language))
        except Exception:
            heard = None
        if heard:
            t = times_from_heard(heard, words, total_seconds)
            if t:
                return t, "whisper"

    return proportional(words, total_seconds), "proportional"
