"""AUDIO KEPT ON THE MACHINE, PER PERSON. Marko, 7.9.2026: "the audio is kept on
the machine per user, with the MB shown and a delete for the user, and for the
admin in the portal."

WHAT. Every block the reader makes (one sentence, or a few) is a file that took
seconds of a voice to make. On the Oracle machine the disk is Marko's own, so
the block is kept there and the next reading of the same words by the same
voice plays at once instead of being made again.

WHERE. TTT_AUDIO_CACHE names a folder (e.g. /home/ubuntu/.maha/audio). Under it
one folder per person, and in it <sha>.bin (the audio bytes as the voice gave
them) and <sha>.json (the marks). The sha is over the person, the voice
signature (engine + every voice setting) and the text, so a different voice or
a changed word is a different file.

HOW MUCH. TTT_AUDIO_CACHE_MB caps each person (default 77, Marko's number).
Past the cap the oldest-played files go first; a cache is never a fault.

NEVER A DEPENDENCY. Every function here returns quietly on any failure; a
block that cannot be read from the cache is made again, as it was yesterday.
Where TTT_AUDIO_CACHE is unset (Streamlit Cloud, a laptop) nothing is written.
"""

import hashlib
import json
import os
import re
import time

PATH = os.environ.get("TTT_AUDIO_CACHE", "")
CAP_MB = float(os.environ.get("TTT_AUDIO_CACHE_MB", "77") or 77)


def enabled() -> bool:
    return bool(PATH)


def _safe(user: str) -> str:
    """A folder name from a user name: letters, digits, dot, dash, underscore."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(user or ""))[:64]


def _dir(user: str) -> str:
    return os.path.join(PATH, _safe(user))


def key(user: str, signature: str, text: str) -> str:
    """The name of the block: who, which voice, which words."""
    h = hashlib.sha256()
    for part in (str(user or ""), str(signature or ""), str(text or "")):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def get(user: str, k: str):
    """{"audio": bytes, "marks": list} or None. A hit is touched, so the cap
    drops what has not been played for the longest."""
    if not enabled() or not user or not k:
        return None
    try:
        base = os.path.join(_dir(user), k)
        with open(base + ".bin", "rb") as fh:
            audio = fh.read()
        with open(base + ".json", encoding="utf-8") as fh:
            marks = json.load(fh)
        now = time.time()
        os.utime(base + ".bin", (now, now))
        return {"audio": audio, "marks": marks}
    except Exception:                                    # noqa: BLE001
        return None


def put(user: str, k: str, audio: bytes, marks) -> bool:
    if not enabled() or not user or not k or not audio:
        return False
    try:
        d = _dir(user)
        os.makedirs(d, exist_ok=True)
        base = os.path.join(d, k)
        tmp = base + ".part"
        with open(tmp, "wb") as fh:
            fh.write(audio)
        os.replace(tmp, base + ".bin")
        with open(base + ".json", "w", encoding="utf-8") as fh:
            json.dump(list(marks or []), fh, ensure_ascii=False)
        _trim(user)
        return True
    except Exception:                                    # noqa: BLE001
        return False


def _files(user: str):
    """[(mtime, size, base)] of the person's blocks, oldest first."""
    d = _dir(user)
    out = []
    try:
        for name in os.listdir(d):
            if not name.endswith(".bin"):
                continue
            p = os.path.join(d, name)
            st = os.stat(p)
            out.append((st.st_mtime, st.st_size, p[:-4]))
    except OSError:
        return []
    out.sort()
    return out


def usage(user: str) -> int:
    """Bytes of audio this person holds on the machine."""
    if not enabled() or not user:
        return 0
    return sum(size for _m, size, _b in _files(user))


def count(user: str) -> int:
    if not enabled() or not user:
        return 0
    return len(_files(user))


def _trim(user: str):
    cap = int(CAP_MB * 1024 * 1024)
    files = _files(user)
    total = sum(size for _m, size, _b in files)
    for _m, size, base in files:
        if total <= cap:
            break
        for ext in (".bin", ".json"):
            try:
                os.remove(base + ext)
            except OSError:
                pass
        total -= size


def clear(user: str) -> int:
    """Everything of one person gone. Returns the bytes freed."""
    if not enabled() or not user:
        return 0
    freed = 0
    for _m, size, base in _files(user):
        for ext in (".bin", ".json"):
            try:
                os.remove(base + ext)
            except OSError:
                pass
        freed += size
    try:
        os.rmdir(_dir(user))
    except OSError:
        pass
    return freed


def usage_all():
    """user -> {"bytes": n, "files": n}, for the admin who sees sizes and never hears the audio."""
    if not enabled():
        return {}
    out = {}
    try:
        for name in sorted(os.listdir(PATH)):
            if os.path.isdir(os.path.join(PATH, name)):
                files = _files(name)
                out[name] = {"bytes": sum(s for _m, s, _b in files), "files": len(files)}
    except OSError:
        return {}
    return out
