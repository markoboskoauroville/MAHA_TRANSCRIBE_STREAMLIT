"""ffmpeg work: transcoding, chunking, and the big-file strategy.

Knows nothing about any transcription provider — it is handed a
`transcribe(path) -> text` function and works out how to feed it something
it can actually swallow. That is why the same strategy serves Groq today
and anything else tomorrow.

Every temporary file this module makes is tracked so the caller can clean
up; Streamlit Cloud containers are long-lived and shared, so leaking a
temp file per upload is a real leak, not a theoretical one.
"""

import glob
import os
import shutil
import subprocess
import tempfile
import time

# Groq's hard limit is 25MB. Baba's own margin, kept.
SAFE_BYTES = 20 * 1024 * 1024
CHUNK_SECONDS = 600          # 10 min; far under the limit even for dense speech

FFMPEG_MISSING = "ffmpeg not found on the server — check packages.txt."


def _run(cmd, timeout):
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError(FFMPEG_MISSING)
    except subprocess.CalledProcessError as e:
        tail = e.stderr.decode(errors="ignore")[-300:]
        raise RuntimeError(f"ffmpeg failed: {tail}")


# Levelling matters as much as resampling. A phone recording of someone
# speaking softly across a room arrives quiet and uneven, and Whisper
# mishears quiet audio in a particular way — it DROPS short words rather
# than guessing at them, so the transcript looks fluent and is missing
# things. loudnorm is EBU R128; -16 LUFS is the streaming convention and
# leaves headroom, and -1.5 dBTP keeps it from clipping on the way.
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"

# MEASURED TRAP, 18.8.2026. loudnorm works internally in floating point, so
# adding it to Groq's documented command silently changes the FLAC encoder's
# output from 16-bit to 24-bit. Groq's own command has no filter, which is
# why the docs never show this. The result was files 48% larger than needed
# for a transcript Groq returns BYTE-IDENTICAL either way (verified against
# the real API, 398 chars both ways). Whisper takes 16-bit; the extra depth
# buys nothing and costs half the storage, half the upload and half the
# Drive quota. Do not remove this without re-measuring both.
SAMPLE_FMT = "s16"


def to_flac16k(in_path: str, out_path: str = None) -> str:
    """16kHz mono FLAC, levelled — Groq's own documented target, and a
    good idea for every other STT too.

    ffmpeg reads the input format from CONTENT rather than extension, so
    this takes whatever the picker hands over: any audio container, and
    video too — `-map 0:a` lifts the audio track straight out of a film
    and throws the pictures away.
    """
    out_path = out_path or (in_path + ".flac")
    _run(["ffmpeg", "-y", "-i", in_path, "-af", LOUDNORM,
          "-ar", "16000", "-ac", "1", "-sample_fmt", SAMPLE_FMT,
          "-map", "0:a", "-c:a", "flac", out_path], timeout=1800)
    return out_path


def bytes_to_flac16k(raw: bytes, suffix: str = ".wav") -> str:
    """Same, for bytes straight from a browser recorder."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(raw)
        src = f.name
    try:
        return to_flac16k(src)
    finally:
        try:
            os.remove(src)
        except Exception:
            pass


def duration_seconds(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out)
    except Exception:
        return 0.0


def split_into_chunks(flac_path: str, chunk_seconds: int = CHUNK_SECONDS):
    """Returns (chunk_paths, temp_dir). The caller owns temp_dir and should
    pass it to cleanup() when done."""
    out_dir = tempfile.mkdtemp(prefix="maha_chunks_")
    pattern = os.path.join(out_dir, "chunk_%04d.flac")
    _run(["ffmpeg", "-y", "-i", flac_path, "-f", "segment",
          "-segment_time", str(chunk_seconds), "-ar", "16000", "-ac", "1",
          "-sample_fmt", SAMPLE_FMT, "-c:a", "flac", pattern], timeout=3600)
    return sorted(glob.glob(os.path.join(out_dir, "chunk_*.flac"))), out_dir


def cleanup(*paths) -> None:
    """Remove files and directories, never raising. Safe to call twice."""
    for p in paths:
        if not p:
            continue
        try:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.exists(p):
                os.remove(p)
        except Exception:
            pass



# ---------------------------------------------------------------------
# Never lose a portion of audio
# ---------------------------------------------------------------------
# A chunk that fails is not automatically lost. Most failures at this
# layer are TEMPORARY — every key resting off a rate limit at the same
# moment, a timeout, a gateway hiccup — and all of them cure themselves
# if you wait. Giving up on the first exception threw away real audio
# for a condition that lasts two minutes.
#
# So: retry with a widening wait, and only leave a gap once the waiting
# is genuinely exhausted. A gap then NAMES THE MINUTES it covers, so the
# missing stretch can be found and re-run instead of silently vanishing
# in the middle of a transcript.

TRANSIENT_HINTS = (
    "unavailable", "rate limit", "429", "too many requests",
    "timeout", "timed out", "temporarily", "try again",
    "connection", "reset", "broken pipe",
    "502", "503", "504", "server error",
)

# 5s catches a blip, 30s a short queue, 125s outlasts a full 120s rest of
# every key at once. Worst case per chunk is about 160 seconds of waiting
# before a gap is allowed — cheap next to losing ten minutes of someone's
# voice.
WAIT_SCHEDULE = (5, 30, 125)


def is_transient(err) -> bool:
    """Will waiting plausibly help? Unknown errors are treated as
    transient ON PURPOSE: retrying something permanent costs a little
    time, while giving up on something temporary costs the audio."""
    text = str(err).lower()
    permanent = ("does not exist", "model_not_found", "invalid_request",
                 "no keys", "not found (404)", "unsupported")
    if any(h in text for h in permanent):
        return False
    return any(h in text for h in TRANSIENT_HINTS) or True


def clock(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def transcribe_one_chunk(transcribe_fn, path, waits=WAIT_SCHEDULE,
                         sleep=time.sleep, on_wait=None):
    """One chunk, with patience. Returns (text, error).

    `transcribe_fn` already rotates across every key once per call — this
    adds the waiting that lets keys come back from a rest before the chunk
    is written off.
    """
    last = ""
    for attempt in range(len(waits) + 1):
        try:
            return transcribe_fn(path), None
        except Exception as e:
            last = str(e)
            if not is_transient(e) or attempt >= len(waits):
                return None, last
            pause = waits[attempt]
            if on_wait:
                on_wait(attempt + 1, pause, last)
            sleep(pause)
    return None, last


def transcribe_any_size(path: str, transcribe_fn, progress_cb=None,
                        safe_bytes: int = SAFE_BYTES,
                        gap_marker: str = "[…]",
                        chunk_seconds: int = CHUNK_SECONDS,
                        waits=WAIT_SCHEDULE, sleep=time.sleep, on_wait=None):
    """Get a transcript out of a file of any size.

    `transcribe_fn(path) -> text` is any provider. Three tiers, each tried
    only if the one before did not already produce something small enough:

      1. direct      already small — no transcoding cost at all
      2. transcoded  16kHz mono FLAC, routinely 5-10x smaller
      3. chunked     split, transcribe each, stitch back together

    A single chunk failing leaves a gap marker rather than losing every
    chunk that already succeeded.

    Returns (text, method, reusable_path, temps) where `reusable_path` is
    whichever file was actually transcribed (so a later second pass with a
    different model has something valid to work from) and `temps` is a list
    of paths the caller should pass to cleanup() once finished with
    reusable_path.
    """
    temps = []
    if os.path.getsize(path) <= safe_bytes:
        try:
            return transcribe_fn(path), "direct", path, temps
        except Exception:
            pass                      # even a small file can fail to upload

    flac_path = to_flac16k(path)
    temps.append(flac_path)
    if os.path.getsize(flac_path) <= safe_bytes:
        try:
            return transcribe_fn(flac_path), "transcoded", flac_path, temps
        except Exception:
            pass                      # fall through to chunking, don't give up

    chunk_paths, chunk_dir = split_into_chunks(flac_path, chunk_seconds)
    temps.append(chunk_dir)
    parts, ok, gaps = [], 0, []
    for i, cp in enumerate(chunk_paths):
        if progress_cb:
            progress_cb(i, len(chunk_paths))
        text, err = transcribe_one_chunk(
            transcribe_fn, cp, waits=waits, sleep=sleep,
            on_wait=(lambda n, secs, e, idx=i: on_wait(idx, n, secs, e)) if on_wait else None)
        if err is None:
            parts.append(text)
            ok += 1
        else:
            # Name the minutes so the hole can be found and re-run.
            start, end = i * chunk_seconds, (i + 1) * chunk_seconds
            gaps.append((start, end, err))
            parts.append(f"{gap_marker}[{clock(start)}-{clock(end)}]")
    if not ok:
        raise RuntimeError(
            "Every part failed to transcribe. Last reason: "
            + (gaps[-1][2][:200] if gaps else "unknown"))
    return " ".join(p for p in parts if p), "chunked", flac_path, temps
