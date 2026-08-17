"""Generic multi-key ring. Knows nothing about any vendor.

One ring per provider. Keys are tried in order starting from the one that
worked last time; a rejected key is buried permanently, a rate-limited one
rests and returns on its own, and a network failure blames nothing.

Ported from Baba's MA_READER_SPEECHIFY / Key_Tester with two rules from
those repos kept verbatim because each was learned the hard way:

  * NEVER DROP A KEY FOR ITS SHAPE. Shape only ranks candidates. A provider
    can change its key format overnight (Google has), and discarding a
    real key silently loses it. Testing a false candidate costs one wasted
    request; losing a real key costs the key.
  * A key file is a working note, not a machine file. Keys are found inside
    whatever text surrounds them, and the line directly above a key becomes
    its label — usually a username or account note.
"""

import hashlib
import re
import threading
import time

COOL_SECONDS = 120.0        # a rate-limited key rests this long, then returns

_URL_RE = re.compile(r"https?://\S+")
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]{11,}")


def fingerprint(key: str) -> str:
    """Short SHA-256 fingerprint. Safe to store or show; reveals nothing."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def mask(key: str) -> str:
    """Never show a key in full; enough to tell two apart."""
    k = (key or "").strip()
    if len(k) <= 10:
        return (k[:2] + "\u2026") if k else ""
    return k[:5] + "\u2026" + k[-4:]


def new_ring() -> dict:
    return {"keys": [], "active": 0}


def pick(ring: dict, start: int = 0):
    """Index of the first usable key at or after `start`, wrapping. A
    resting key revives itself once its time is up; a dead one never does."""
    keys = ring.get("keys") or []
    n = len(keys)
    if not n:
        return None
    now = time.time()
    for j in range(n):
        i = (start + j) % n
        k = keys[i]
        if k.get("state") == "dead":
            continue
        if k.get("state") == "cool":
            if k.get("cool_until", 0) > now:
                continue
            k["state"] = "new"
            k["last_error"] = ""
        return i
    return None


def usable(ring: dict) -> bool:
    return any(k.get("state") != "dead" for k in (ring.get("keys") or []))


def counts(ring: dict) -> dict:
    now = time.time()
    live = dead = cool = 0
    for k in ring.get("keys") or []:
        if k.get("state") == "dead":
            dead += 1
        elif k.get("state") == "cool" and k.get("cool_until", 0) > now:
            cool += 1
        else:
            live += 1
    return {"total": len(ring.get("keys") or []), "live": live,
            "dead": dead, "cool": cool}


def import_keys(ring: dict, raw: str, prefixes=(), min_len: int = 16,
                generic_min: int = 24) -> int:
    """Find every key in a piece of messy text and add the unseen ones.

    Line-aware: the file line directly above a key becomes its label.
    Two passes — if anything carries a known prefix, only prefixed tokens
    are taken (exact, the normal case). If nothing is prefixed, fall back
    to long mixed letter+digit runs, which lets an unknown key format
    through without dragging in words, dates or file names. A provider with
    no distinctive prefix (AssemblyAI's 32-hex) passes an empty `prefixes`
    and so always takes the fallback path.

    Returns how many NEW keys were added; re-importing the same file adds
    nothing.
    """
    lines = (raw or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")

    def tokens_on(line: str):
        cleaned = _URL_RE.sub(
            lambda m: m.group(0) if any(p in m.group(0).lower() for p in prefixes) else " ",
            line)
        return [m.group(0).strip(".-_") for m in _TOKEN_RE.finditer(cleaned)
                if len(m.group(0)) >= 12]

    def is_prefixed(tok: str) -> bool:
        low = tok.lower()
        return bool(prefixes) and any(low.startswith(p) for p in prefixes) and len(tok) >= min_len

    per_line = [tokens_on(ln) for ln in lines]
    found = [(tok, i) for i, toks in enumerate(per_line) for tok in toks if is_prefixed(tok)]
    if not found:
        found = [(tok, i) for i, toks in enumerate(per_line) for tok in toks
                 if len(tok) >= generic_min
                 and any(c.isdigit() for c in tok) and any(c.isalpha() for c in tok)]

    have = {k.get("key") for k in ring.setdefault("keys", [])}
    seen, added = set(), 0
    for key, line_idx in found:
        if key in seen or key in have:
            continue
        seen.add(key)
        label = lines[line_idx - 1].strip() if line_idx > 0 else ""
        ring["keys"].append({
            "key": key, "fp": fingerprint(key), "state": "new",
            "label": label, "last_error": "", "calls": 0, "chars": 0,
            "cool_until": 0, "added": int(time.time()),
        })
        added += 1
    return added


def mark_dead(ring: dict, idx: int, err: str) -> None:
    k = ring["keys"][idx]
    k["state"] = "dead"
    k["last_error"] = err


def mark_cool(ring: dict, idx: int, err: str) -> None:
    k = ring["keys"][idx]
    k["state"] = "cool"
    k["cool_until"] = time.time() + COOL_SECONDS
    k["last_error"] = err


def mark_ok(ring: dict, idx: int, billed: int = 0) -> None:
    k = ring["keys"][idx]
    k["state"] = "ok"
    k["last_error"] = ""
    k["calls"] = int(k.get("calls", 0)) + 1
    if billed:
        k["chars"] = int(k.get("chars", 0)) + int(billed)
    ring["active"] = idx


def revive_all(ring: dict) -> int:
    n = 0
    for k in ring.get("keys") or []:
        if k.get("state") in ("dead", "cool"):
            k["state"] = "new"
            k["last_error"] = ""
            k["cool_until"] = 0
            n += 1
    return n


# One lock for all ring bookkeeping. Blocks of audio are generated in
# PARALLEL now, so several threads reach the same ring at once. Without
# this, two threads can pick the same key at the same instant, or one can
# overwrite the other's verdict — a key buried or a call count lost for
# no reason anyone could later explain.
#
# The lock covers ONLY choosing a key and recording what happened, never
# the network call in between. Holding it across the request would
# serialise every provider call and undo the parallelism entirely.
_LOCK = threading.Lock()


def rotate(ring: dict, attempt):
    """Walk the ring until a key works, applying the standard verdicts.

    `attempt(key_str)` returns `(result, error, kind)` where kind is
    "dead" | "cool" | "soft". A "soft" failure is not the key's fault, so
    it stops immediately rather than burning through every key.

    Returns `(result, error)`. This is the one place rotation policy lives.
    Safe to call from several worker threads at once.
    """
    keys = ring.get("keys") or []
    n = len(keys)
    if not n:
        return None, "No keys yet — add one in Settings."
    with _LOCK:
        idx = ring.get("active", 0) % n
    last = ""
    for _ in range(n):
        with _LOCK:
            i = pick(ring, idx)
            key = keys[i]["key"] if i is not None else None
        if i is None:
            break
        result, err, kind = attempt(key)        # network, deliberately unlocked
        if not err:
            billed = 0
            if isinstance(result, dict):
                billed = result.get("billable_characters_count") or 0
            with _LOCK:
                mark_ok(ring, i, billed)
            return result, None
        last = err
        if kind in ("dead", "cool"):
            with _LOCK:
                if kind == "dead":
                    mark_dead(ring, i, err)
                else:
                    mark_cool(ring, i, err)
        else:
            return None, err        # not the key's fault; keep it, stop here
        idx = (i + 1) % n
    return None, f"All {n} key(s) unavailable. Last: {last}"
