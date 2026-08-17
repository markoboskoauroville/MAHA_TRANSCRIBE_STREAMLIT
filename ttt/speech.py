"""Turn a whole text into ONE audio file, with timings that still line up.

Why this exists. The reader used to synthesise a sentence, play it, wait,
synthesise the next — which meant a visible audio bar per sentence, an
unnatural gap at every full stop, and no way to see how long was left.
Baba's words: *"users should not be aware of the engine beneath. It's
just a player for the whole text."* He is right, and it is also simply
better: one file plays gaplessly, seeks anywhere, and reports its own
elapsed and remaining time for free.

HOW IT WORKS

  1. The text is cut into pieces that fit the provider's per-request
     limit, always at a sentence boundary so no word is split across a
     request.
  2. Each piece is synthesised, giving audio plus (for Speechify) exact
     word marks with character offsets and millisecond timings.
  3. The pieces are joined into one file with ffmpeg.
  4. Every mark is shifted by the cumulative duration of the pieces
     before it, and by its piece's character offset in the full text, so
     the timings and the highlight positions refer to the WHOLE text.

Step 4 is the part that has to be right. A mark says "characters 10-15 of
this piece, at 0.4s into this piece"; after joining it must say
"characters 210-215 of the whole text, at 37.2s into the whole file".
Getting either offset wrong makes the highlight drift, which is worse
than no highlight at all.

DURATIONS COME FROM THE AUDIO, NOT FROM THE PROVIDER. The concatenated
file is measured with ffprobe rather than trusting the sum of reported
lengths, because an encoder can add a frame here and there and the error
accumulates across a long text — exactly the drift this design exists to
remove.
"""

import os
import subprocess
import tempfile

# Per-request input size. Speechify accepts more, but smaller pieces mean
# the first audio arrives sooner and one failure costs less. A sentence
# boundary always wins over hitting this exactly.
CHUNK_CHARS = 1500


def plan_chunks(sentences, max_chars: int = CHUNK_CHARS):
    """Group sentences into request-sized pieces.

    Returns [(text, char_offset)] where char_offset is where that piece
    begins in the joined text, which is what the marks must be shifted by.
    """
    chunks, cur, cur_len, offset = [], [], 0, 0
    for s in sentences:
        if cur and cur_len + len(s) + 1 > max_chars:
            text = " ".join(cur)
            chunks.append((text, offset))
            offset += len(text) + 1
            cur, cur_len = [], 0
        cur.append(s)
        cur_len += len(s) + 1
    if cur:
        chunks.append((" ".join(cur), offset))
    return chunks


def join_audio(paths, out_path: str = None) -> str:
    """One file out of many. Re-encodes rather than stream-copying:
    concatenating MP3 frames directly leaves gaps and confuses seeking in
    some browsers, which would defeat the whole point."""
    if not paths:
        raise ValueError("nothing to join")
    out_path = out_path or tempfile.mktemp(suffix=".mp3")
    if len(paths) == 1:
        subprocess.run(["ffmpeg", "-y", "-i", paths[0], "-c", "copy", out_path],
                       check=True, capture_output=True, timeout=300)
        return out_path
    listfile = tempfile.mktemp(suffix=".txt")
    with open(listfile, "w", encoding="utf-8") as f:
        for p in paths:
            f.write("file '%s'\n" % p.replace("'", "'\\''"))
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
             "-codec:a", "libmp3lame", "-q:a", "4", out_path],
            check=True, capture_output=True, timeout=1800)
    finally:
        try:
            os.remove(listfile)
        except Exception:
            pass
    return out_path


def duration_of(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out)
    except Exception:
        return 0.0


def shift_marks(marks, time_offset: float, char_offset: int):
    """Move one piece's marks into the coordinates of the whole text."""
    out = []
    for m in marks or []:
        out.append({
            "start": int(m.get("start", 0)) + char_offset,
            "end": int(m.get("end", 0)) + char_offset,
            "start_time": float(m.get("start_time", 0.0)) + time_offset,
            "end_time": float(m.get("end_time", 0.0)) + time_offset,
        })
    return out


def sentence_marks(sentences, marks, full_text: str):
    """Word marks -> one mark per SENTENCE.

    The subtitle box shows a sentence at a time, so it needs to know when
    each sentence starts and ends. Derived from the word marks that fall
    inside each sentence's character span; a sentence with no marks (a
    provider that reports none) is given a share of the remaining time so
    the subtitle still advances rather than freezing.
    """
    spans, pos = [], 0
    for s in sentences:
        i = full_text.find(s, pos)
        if i < 0:
            i = pos
        spans.append((i, i + len(s)))
        pos = i + len(s)

    out = []
    for (a, b), text in zip(spans, sentences):
        inside = [m for m in marks if m["start"] >= a and m["end"] <= b]
        if inside:
            out.append({"start": a, "end": b, "text": text,
                        "start_time": min(m["start_time"] for m in inside),
                        "end_time": max(m["end_time"] for m in inside)})
        else:
            out.append({"start": a, "end": b, "text": text,
                        "start_time": None, "end_time": None})
    return out


def fill_missing_times(sent_marks, total_seconds: float):
    """Give any sentence without real timings a proportional slot.

    Edge reports no word marks at all, so without this the subtitle would
    sit on the first sentence for the whole file. Proportional to length
    is a guess, but a moving guess is far more useful than a frozen
    truth, and the audio itself is unaffected either way.
    """
    known = [m for m in sent_marks if m["start_time"] is not None]
    if len(known) == len(sent_marks):
        return sent_marks
    total_chars = sum(len(m["text"]) for m in sent_marks) or 1
    t = 0.0
    for m in sent_marks:
        if m["start_time"] is None:
            share = (len(m["text"]) / total_chars) * total_seconds
            m["start_time"] = t
            m["end_time"] = t + share
            t += share
        else:
            t = m["end_time"]
    return sent_marks


def build_part(part_sentences, synth, char_offset: int, full_text: str,
               tmpdir: str = None):
    """One PART: audio plus sentence marks in the part's own timeline.

    Parts exist because of WAITING, not because of any limit. Measured on
    Edge: 9000 characters synthesise fine, so there is no ceiling to dodge
    — but 1500 chars takes about 21 seconds to make and yields about 100
    seconds of speech, while 6000 chars takes 107 seconds before a single
    word is heard. Splitting means listening starts after one short wait
    and every later part is prepared while the previous one plays.

    Marks are in the PART's timeline (starting at 0), because each part is
    its own audio element. Character offsets stay absolute so the text can
    still be located in the whole.
    """
    tmpdir = tmpdir or tempfile.mkdtemp(prefix="ttt_part_")
    chunks = plan_chunks(part_sentences)
    paths, all_marks, elapsed = [], [], 0.0
    for i, (text, rel_off) in enumerate(chunks):
        audio, seconds, marks = synth(text)
        p = os.path.join(tmpdir, f"seg_{i:04d}.mp3")
        with open(p, "wb") as f:
            f.write(audio)
        paths.append(p)
        real = duration_of(p) or seconds
        all_marks.extend(shift_marks(marks, elapsed, char_offset + rel_off))
        elapsed += real

    out = os.path.join(tmpdir, "part.mp3")
    join_audio(paths, out)
    total = duration_of(out) or elapsed

    sm = sentence_marks(part_sentences, all_marks, full_text)
    # rebase char spans that sentence_marks resolved against full_text
    sm = fill_missing_times(sm, total)
    return out, sm, total, [tmpdir]


def plan_blocks(sentences, max_chars: int = 1500, max_sentences: int = 32):
    """Doubling blocks: 1, 2, 4, 8, 16 ... then a steady size.

    Baba's algorithm, and it is the right shape. The first block is ONE
    sentence, so sound starts after about three seconds instead of the
    twenty a full-size request takes. Each block then doubles, so a long
    text needs few requests rather than many — and by the time the
    blocks are large, there is plenty of already-recorded speech playing
    to cover the longer wait.

    Growth stops at whichever comes first: max_sentences, or the point
    where a block would exceed the per-request character budget. A block
    is never split mid-sentence.

        20 sentences -> 1, 2, 4, 8, 5
        60 sentences -> 1, 2, 4, 8, 16, 29

    Returns [(sentences, char_offset)].
    """
    blocks, i, size, offset = [], 0, 1, 0
    n = len(sentences)
    while i < n:
        take, chars = [], 0
        while len(take) < size and i + len(take) < n:
            nxt = sentences[i + len(take)]
            if take and chars + len(nxt) + 1 > max_chars:
                break
            take.append(nxt)
            chars += len(nxt) + 1
        if not take:                       # one sentence longer than the budget
            take = [sentences[i]]
        blocks.append((take, offset))
        offset += sum(len(x) + 1 for x in take)
        i += len(take)
        size = min(size * 2, max_sentences)
    return blocks


def plan_parts(sentences, part_chars: int = 1500):
    """Group sentences into PARTS. Returns [(sentences, char_offset)].

    Sized so one part is a short wait and a comfortable listen — see
    build_part for the measurements behind the number.
    """
    parts, cur, cur_len, offset = [], [], 0, 0
    for s in sentences:
        if cur and cur_len + len(s) + 1 > part_chars:
            parts.append((cur, offset))
            offset += sum(len(x) + 1 for x in cur)
            cur, cur_len = [], 0
        cur.append(s)
        cur_len += len(s) + 1
    if cur:
        parts.append((cur, offset))
    return parts


def build(sentences, synth, tmpdir: str = None):
    """One audio file for the whole text.

    `synth(text) -> (audio_bytes, seconds, marks|None)` is any TTS engine.
    Returns (mp3_path, sentence_marks, total_seconds, temp_paths).
    """
    tmpdir = tmpdir or tempfile.mkdtemp(prefix="ttt_speech_")
    chunks = plan_chunks(sentences)
    full_text = " ".join(sentences)

    paths, all_marks, elapsed = [], [], 0.0
    for i, (text, char_off) in enumerate(chunks):
        audio, seconds, marks = synth(text)
        p = os.path.join(tmpdir, f"part_{i:04d}.mp3")
        with open(p, "wb") as f:
            f.write(audio)
        paths.append(p)
        # Measure what was actually produced rather than trusting the
        # reported length; small per-piece errors would accumulate.
        real = duration_of(p) or seconds
        all_marks.extend(shift_marks(marks, elapsed, char_off))
        elapsed += real

    out = os.path.join(tmpdir, "whole.mp3")
    join_audio(paths, out)
    total = duration_of(out) or elapsed

    sm = fill_missing_times(sentence_marks(sentences, all_marks, full_text), total)
    return out, sm, total, [tmpdir]
