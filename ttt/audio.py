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


def to_flac16k(in_path: str, out_path: str = None) -> str:
    """16kHz mono FLAC — Groq's own documented target, and a good idea for
    every other STT too. ffmpeg detects the input format from content, not
    extension, so this works on whatever a file picker hands over."""
    out_path = out_path or (in_path + ".flac")
    _run(["ffmpeg", "-y", "-i", in_path, "-ar", "16000", "-ac", "1",
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
          "-c:a", "flac", pattern], timeout=3600)
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


def transcribe_any_size(path: str, transcribe_fn, progress_cb=None,
                        safe_bytes: int = SAFE_BYTES,
                        gap_marker: str = "[…]"):
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

    chunk_paths, chunk_dir = split_into_chunks(flac_path)
    temps.append(chunk_dir)
    parts, ok = [], 0
    for i, cp in enumerate(chunk_paths):
        if progress_cb:
            progress_cb(i, len(chunk_paths))
        try:
            parts.append(transcribe_fn(cp))
            ok += 1
        except Exception:
            parts.append(gap_marker)
    if not ok:
        raise RuntimeError("Every chunk failed to transcribe — check the keys.")
    return " ".join(p for p in parts if p), "chunked", flac_path, temps
