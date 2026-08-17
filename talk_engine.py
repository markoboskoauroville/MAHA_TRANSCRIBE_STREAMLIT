# -*- coding: utf-8 -*-
"""
Talk engine — ported from markoboskoauroville/ma-reader-thermux
(pinned commit be376fd, 3sh_i_ma_reader_v3_termux.sh, server.py half).

This is the per-sentence TTS + waveform-alignment pipeline, kept as close to
byte-identical as the change of host allows. Nothing about the DSP, the
thresholds, or the alignment algorithm has been touched — only the delivery
layer around it changed (see app.py): there is no live per-sentence HTTP
route on Streamlit Cloud, so the caller synthesizes a whole text up front
instead of on first request. Every function below is unchanged logic.

Four voices only, per the handover:
    Sonia      en-GB-SoniaNeural       English (UK) female   vkey ukF
    Ryan       en-GB-RyanNeural        English (UK) male     vkey ukM
    Gabrijela  hr-HR-GabrijelaNeural   Croatian female       vkey hrF
    Srecko     hr-HR-SreckoNeural      Croatian male         vkey hrM
"""
import os, re, json, time, shutil, asyncio, unicodedata, subprocess

VOICES = {
    "ukF": ("en-GB-SoniaNeural",     "Sonia",     "en", "F"),
    "ukM": ("en-GB-RyanNeural",      "Ryan",      "en", "M"),
    "hrF": ("hr-HR-GabrijelaNeural", "Gabrijela", "hr", "F"),
    "hrM": ("hr-HR-SreckoNeural",    "Srecko",    "hr", "M"),
}
UNIT_CAP = 320

# ---------- text -> sentences -> units (verbatim) ----------
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

# ---------- clean: strip links + Markdown so only plain words are read (verbatim) ----------
_FENCE_RE    = re.compile(r"^\s*(?:```+|~~~+).*$", re.M)
_IMG_RE      = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_AUTOLINK_RE = re.compile(r"<((?:https?|ftp|mailto):[^>\s]+)>", re.I)
_LINK_RE     = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_REFLINK_RE  = re.compile(r"\[([^\]]+)\]\[[^\]]*\]")
_REFDEF_RE   = re.compile(r"^\s{0,3}\[[^\]]+\]:\s+\S.*$", re.M)
_URL_RE      = re.compile(r"(?:(?:https?|ftp)://|www\.)[^\s<>)\]}\"']+", re.I)
_MAILTO_RE   = re.compile(r"\bmailto:[^\s<>)\]}\"']+", re.I)
_HTML_RE     = re.compile(r"</?[A-Za-z][^>]*>")
_CODE_RE     = re.compile(r"`+([^`]*)`+")
_EMPH_AST_RE = re.compile(r"(\*\*|\*|~~)(?=\S)(.+?)(?<=\S)\1", re.S)
_EMPH_US_RE  = re.compile(r"(?<![\w])(__|_)(?=\S)(.+?)(?<=\S)\1(?![\w])", re.S)
_HEADING_RE  = re.compile(r"^\s{0,3}#{1,6}\s*")
_QUOTE_RE    = re.compile(r"^\s{0,3}>+\s?")
_BULLET_RE   = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+")
_RULE_RE     = re.compile(r"^\s{0,3}(?:(?:[-*_]\s*){3,}|=+)\s*$")

def clean_text(text):
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _FENCE_RE.sub("", text)
    text = _IMG_RE.sub("", text)
    text = _AUTOLINK_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _REFLINK_RE.sub(r"\1", text)
    text = _REFDEF_RE.sub("", text)
    text = _URL_RE.sub("", text)
    text = _MAILTO_RE.sub("", text)
    text = _HTML_RE.sub("", text)
    text = _CODE_RE.sub(r"\1", text)
    for _ in range(3):
        new = _EMPH_AST_RE.sub(r"\2", text)
        new = _EMPH_US_RE.sub(r"\2", new)
        if new == text:
            break
        text = new
    out = []
    for ln in text.split("\n"):
        if _RULE_RE.match(ln):
            continue
        ln = _HEADING_RE.sub("", ln)
        ln = _QUOTE_RE.sub("", ln)
        ln = _BULLET_RE.sub(r"\1", ln)
        if "|" in ln:
            stripped = ln.strip()
            if stripped and set(stripped) <= set("|:- "):
                continue
            ln = ln.replace("|", " ")
        out.append(ln)
    text = "\n".join(out)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\[\s*\]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r" *\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

# ---------- align edge-tts word timings to exact character ranges (verbatim) ----------
_TOKEN_RE = re.compile(r"\S+")

def _norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c.lower() for c in s if c.isalnum())

def align_tokens(sentence, bounds, total=None):
    tokens = [(m.start(), m.end()) for m in _TOKEN_RE.finditer(sentence)]
    out = [{"s": a, "e": b, "t": None, "d": None} for (a, b) in tokens]
    n = len(tokens)
    if not n:
        return []
    bn = [(_norm(x["w"]), x["t"], x.get("d", 0.0)) for x in bounds]
    bn = [(w, t, d) for (w, t, d) in bn if w]
    bi, nB = 0, len(bn)
    for ti, (a, b) in enumerate(tokens):
        tok = _norm(sentence[a:b])
        if not tok:
            continue
        start_bi = bi
        guard = 0
        found = False
        while bi < nB and guard < 6:
            bw = bn[bi][0]
            if tok.startswith(bw) or bw.startswith(tok) or bw == tok:
                found = True; break
            bi += 1; guard += 1
        if not found:
            bi = start_bi
            continue
        out[ti]["t"] = bn[bi][1]
        last_t, last_d = bn[bi][1], bn[bi][2]
        acc = ""
        while bi < nB:
            acc += bn[bi][0]
            last_t, last_d = bn[bi][1], bn[bi][2]
            bi += 1
            if acc == tok or not tok.startswith(acc):
                break
        out[ti]["d"] = last_t + last_d

    known = [(i, o["t"]) for i, o in enumerate(out) if o["t"] is not None]
    widths = [max(1, b - a) for (a, b) in tokens]

    if not known:
        span = total if (total and total > 0.1) else (0.32 * n)
        acc = 0.0
        wsum = float(sum(widths))
        for i, w in enumerate(widths):
            out[i]["t"] = span * (acc / wsum)
            acc += w
            out[i]["d"] = span * (acc / wsum)
        return out

    fi, ft = known[0]
    for i in range(fi):
        out[i]["t"] = ft
    for (i0, t0), (i1, t1) in zip(known, known[1:]):
        gap = i1 - i0
        if gap <= 1:
            continue
        seg = widths[i0 + 1:i1]
        ws = float(sum(seg)) or 1.0
        acc = 0.0
        for k, j in enumerate(range(i0 + 1, i1)):
            acc += seg[k]
            out[j]["t"] = t0 + (t1 - t0) * (acc / ws) - (t1 - t0) * (seg[k] / ws)
    li, lt = known[-1]
    tail_end = total if (total and total > lt + 0.05) else lt + 0.45 * (n - li)
    rest = list(range(li + 1, n))
    if rest:
        seg = [widths[j] for j in rest]
        ws = float(sum(seg)) or 1.0
        acc = 0.0
        for k, j in enumerate(rest):
            out[j]["t"] = lt + (tail_end - lt) * (acc / ws)
            acc += seg[k]

    prev = 0.0
    for o in out:
        if o["t"] is None or o["t"] < prev:
            o["t"] = prev
        prev = o["t"]
    for i in range(n):
        nxt = out[i + 1]["t"] if i + 1 < n else (
            total if (total and total > out[i]["t"]) else out[i]["t"] + 0.4)
        if out[i]["d"] is None or out[i]["d"] <= out[i]["t"] or out[i]["d"] > nxt:
            out[i]["d"] = nxt
        if out[i]["d"] <= out[i]["t"]:
            out[i]["d"] = nxt
    return out

# ---------- waveform alignment: the v11/v23 engine (verbatim) ----------
_FFMPEG = shutil.which("ffmpeg")
_ENV_SR = 16000
_ENV_HOP_MS = 5
_ENV_WIN_MS = 20

try:
    import numpy as _np
except Exception:
    _np = None

def _pcm_env(mp3_path):
    if not _FFMPEG:
        return None, None, 0.0
    try:
        p = subprocess.run(
            [_FFMPEG, "-v", "quiet", "-i", mp3_path,
             "-ac", "1", "-ar", str(_ENV_SR), "-f", "s16le", "-"],
            capture_output=True, timeout=90)
        raw = p.stdout
    except Exception:
        return None, None, 0.0
    if not raw or len(raw) < _ENV_SR // 5:
        return None, None, 0.0

    n_hop = _ENV_SR * _ENV_HOP_MS // 1000
    n_win = _ENV_SR * _ENV_WIN_MS // 1000

    if _np is not None:
        a = _np.frombuffer(raw[:len(raw) // 2 * 2], dtype="<i2").astype(_np.float64)
        dur = len(a) / float(_ENV_SR)
        count = (len(a) - n_win) // n_hop + 1
        if count < 4:
            return None, None, dur
        pre = _np.empty_like(a)
        pre[0] = a[0]
        pre[1:] = a[1:] - 0.97 * a[:-1]
        idx = _np.arange(count) * n_hop
        bands = []
        for sig in (a, pre):
            sq = _np.concatenate(([0.0], _np.cumsum(sig * sig)))
            bands.append(_np.sqrt((sq[idx + n_win] - sq[idx]) / n_win).tolist())
        return bands[0], bands[1], dur

    import array
    a = array.array("h")
    a.frombytes(raw[:len(raw) // 2 * 2])
    dur = len(a) / float(_ENV_SR)
    count = (len(a) - n_win) // n_hop + 1
    if count < 4:
        return None, None, dur
    n = len(a)
    sq = [0.0] * (n + 1)
    sqp = [0.0] * (n + 1)
    prev = 0
    t1 = t2 = 0.0
    for i in range(n):
        v = a[i]
        t1 += float(v) * v
        sq[i + 1] = t1
        d = v - 0.97 * prev
        prev = v
        t2 += d * d
        sqp[i + 1] = t2
    def _win_rms(sqv, n_hop, n_win, count):
        out = []
        for k in range(count):
            a2 = k * n_hop
            out.append(((sqv[a2 + n_win] - sqv[a2]) / n_win) ** 0.5)
        return out
    return _win_rms(sq, n_hop, n_win, count), _win_rms(sqp, n_hop, n_win, count), dur

def _levels(env):
    s = sorted(env)
    floor = s[int(len(s) * 0.05)]
    peak = s[int(len(s) * 0.97)]
    if peak <= floor:
        peak = s[-1]
    return floor, peak, max(peak - floor, 1e-9)

def _speech_span(env, hi, W):
    f1, p1, s1 = _levels(env)
    f2, p2, s2 = _levels(hi)
    thr1, thr2 = f1 + s1 * 0.10, f2 + s2 * 0.10
    onset = None
    for i in range(len(env) - 3):
        if ((env[i] > thr1 and env[i + 1] > thr1 and env[i + 2] > thr1) or
                (hi[i] > thr2 and hi[i + 1] > thr2 and hi[i + 2] > thr2)):
            onset = i * W
            break
    last = None
    for i in range(len(env) - 1, 0, -1):
        if ((env[i] > thr1 and env[i - 1] > thr1) or
                (hi[i] > thr2 and hi[i - 1] > thr2)):
            last = (i + 1) * W
            break
    return onset, last

# ---------- the quiet between words (v26, verbatim) ----------
_SIL_THR = 0.06
_SIL_MIN_MS = 70
_SIL_GUARD_MS = 18

def silence_runs(env, hi, W, onset, last):
    if not env or not hi:
        return []
    f1, p1, s1 = _levels(env)
    f2, p2, s2 = _levels(hi)
    thr1, thr2 = f1 + s1 * _SIL_THR, f2 + s2 * _SIL_THR
    n = min(len(env), len(hi))
    raw, i = [], 0
    while i < n:
        if env[i] <= thr1 and hi[i] <= thr2:
            j = i
            while j < n and env[j] <= thr1 and hi[j] <= thr2:
                j += 1
            raw.append((i * W, j * W))
            i = j
        else:
            i += 1
    lo = onset if onset is not None else 0.0
    hg = last if last is not None else 1e9
    g = _SIL_GUARD_MS / 1000.0
    out = []
    for (a, b) in raw:
        a, b = max(a, lo) + g, min(b, hg) - g
        if b - a >= _SIL_MIN_MS / 1000.0:
            out.append([round(a, 3), round(b, 3)])
    return out

def measure_silence(mp3_path):
    env, hi, dur = _pcm_env(mp3_path)
    if not env or not hi or dur <= 0.2:
        return []
    W = _ENV_HOP_MS / 1000.0
    onset, last = _speech_span(env, hi, W)
    return silence_runs(env, hi, W, onset, last)

_MIN_PAUSE_MS = 90
_BACKTRACK_MS = 220

def _rise_points(env, hi, W):
    f1, p1, s1 = _levels(env)
    f2, p2, s2 = _levels(hi)
    thr1, low1 = f1 + s1 * 0.10, f1 + s1 * 0.04
    thr2, low2 = f2 + s2 * 0.10, f2 + s2 * 0.04
    gap = int(_MIN_PAUSE_MS / (W * 1000.0))
    look = max(3, int(50 / (W * 1000.0)))
    back = int(_BACKTRACK_MS / (W * 1000.0))
    need = look * 0.6
    rises = []
    quiet = 10 ** 6
    n = len(env)
    for i in range(n):
        loud = env[i] > thr1 or hi[i] > thr2
        if env[i] < low1 and hi[i] < low2:
            quiet += 1
            continue
        if loud and quiet >= gap:
            hits = 0
            for k in range(i, min(i + look, n)):
                if env[k] > thr1 * 0.7 or hi[k] > thr2 * 0.7:
                    hits += 1
            if hits >= need:
                j = i
                stop = max(0, i - back)
                while j > stop:
                    q = j - 1
                    if env[q] < low1 and hi[q] < low2:
                        break
                    if env[q] > env[j] and hi[q] > hi[j]:
                        break
                    j = q
                rises.append(j * W)
        if loud:
            quiet = 0
    out = []
    for r in rises:
        if not out or r > out[-1] + 0.03:
            out.append(r)
    return out

_ANCHOR_SKIP = 0.35
_ANCHOR_CAP = 0.50

def _match_anchors(word_ts, rises):
    n, m = len(word_ts), len(rises)
    if not n or not m:
        return []
    SKIP = _ANCHOR_SKIP
    CAP = _ANCHOR_CAP
    dp = [[0.0] * (n + 1) for _ in range(m + 1)]
    for j in range(1, m + 1):
        dp[j][0] = dp[j - 1][0] + SKIP
    for j in range(1, m + 1):
        for i in range(1, n + 1):
            best = dp[j][i - 1]
            c = dp[j - 1][i] + SKIP
            if c < best:
                best = c
            pair = abs(word_ts[i - 1] - rises[j - 1])
            if pair <= CAP:
                c = dp[j - 1][i - 1] + pair
                if c < best:
                    best = c
            dp[j][i] = best
    out = []
    j, i = m, n
    while j > 0 and i > 0:
        pair = abs(word_ts[i - 1] - rises[j - 1])
        if pair <= CAP and abs(dp[j][i] - (dp[j - 1][i - 1] + pair)) < 1e-9:
            out.append((i - 1, rises[j - 1]))
            j -= 1
            i -= 1
        elif abs(dp[j][i] - (dp[j - 1][i] + SKIP)) < 1e-9:
            j -= 1
        else:
            i -= 1
    out.reverse()
    return out

def refine_tokens(mp3_path, tokens):
    """Re-anchor word times onto the real decoded waveform. Returns
    (tokens, dur, changed). On any trouble the original tokens come back."""
    if not tokens:
        return tokens, 0.0, False
    env, hi, dur = _pcm_env(mp3_path)
    if not env or not hi or dur <= 0.2:
        return tokens, dur if dur else 0.0, False
    W = _ENV_HOP_MS / 1000.0
    onset, last = _speech_span(env, hi, W)
    if onset is None or last is None or last - onset < 0.15:
        return tokens, dur, False

    t0 = float(tokens[0].get("t", 0.0))
    t1 = max(float(t.get("d", t.get("t", 0.0))) for t in tokens)
    if t1 - t0 < 0.05:
        return tokens, dur, False

    a = (last - onset) / (t1 - t0)
    if not (0.5 < a < 2.0):
        a = 1.0
    b = onset - a * t0
    ref = []
    for t in tokens:
        nt = a * float(t.get("t", 0.0)) + b
        nd = a * float(t.get("d", t.get("t", 0.0))) + b
        ref.append({"s": t.get("s", 0), "e": t.get("e", 0), "t": nt, "d": nd})

    rises = _rise_points(env, hi, W)
    word_ts = [w["t"] for w in ref]
    pairs = _match_anchors(word_ts, rises)
    anchors = [(word_ts[i], r) for (i, r) in pairs]
    anchors.append((max(ref[-1]["d"], anchors[-1][0] + 0.01 if anchors else 0),
                    min(last, dur)))
    clean = []
    for (x, y) in anchors:
        if not clean or (x > clean[-1][0] + 1e-3 and y > clean[-1][1] + 1e-3):
            clean.append((x, y))
    if len(clean) >= 2:
        def warp(x):
            if x <= clean[0][0]:
                return clean[0][1] + (x - clean[0][0])
            for (x0, y0), (x1, y1) in zip(clean, clean[1:]):
                if x <= x1:
                    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)
            xN, yN = clean[-1]
            return yN + (x - xN)
        for w in ref:
            w["t"] = warp(w["t"])
            w["d"] = warp(w["d"])

    prev = -1.0
    for w in ref:
        if w["t"] <= prev:
            w["t"] = prev + 0.01
        prev = w["t"]
    for i, w in enumerate(ref):
        nxt = ref[i + 1]["t"] if i + 1 < len(ref) else min(last + 0.05, dur)
        if w["d"] <= w["t"] or w["d"] > nxt:
            w["d"] = nxt
        if w["d"] <= w["t"]:
            w["d"] = w["t"] + 0.05
        w["t"] = round(w["t"], 3)
        w["d"] = round(w["d"], 3)
    return ref, dur, True

# ---------- speech (verbatim except: sync wrapper, no Flask) ----------
def _communicate(edge_tts, text, voice):
    """edge-tts 7.x defaults to SentenceBoundary; ask for WordBoundary
    explicitly or the align step silently gets no word events at all."""
    try:
        return edge_tts.Communicate(text, voice, boundary="WordBoundary")
    except TypeError:
        return edge_tts.Communicate(text, voice)

def synth_unit(text, voice, mp3_path, json_path):
    """Speak one sentence into mp3_path with a timing json beside it.
    Returns "" on success or an error string."""
    import edge_tts

    async def go():
        bounds = []
        com = _communicate(edge_tts, text, voice)
        with open(mp3_path + ".part", "wb") as f:
            async for ch in com.stream():
                if ch["type"] == "audio":
                    f.write(ch["data"])
                elif ch["type"] == "WordBoundary":
                    bounds.append({"t": ch["offset"] / 1e7,
                                   "d": ch["duration"] / 1e7, "w": ch["text"]})
        return bounds
    loop = asyncio.new_event_loop()
    try:
        bounds = loop.run_until_complete(go())
    except Exception as e:
        try:
            os.remove(mp3_path + ".part")
        except Exception:
            pass
        return "TTS failed: %s" % e
    finally:
        loop.close()
    try:
        if not os.path.getsize(mp3_path + ".part"):
            return "no audio"
    except Exception:
        return "no audio"
    os.replace(mp3_path + ".part", mp3_path)

    total = 0.0
    for b in bounds:
        end = b.get("t", 0.0) + b.get("d", 0.0)
        if end > total:
            total = end
    tokens = align_tokens(text, bounds, total or None)
    engine = "edge2"
    ref, dur, changed = refine_tokens(mp3_path, tokens)
    if changed:
        tokens = ref
        engine = "pcm2"
        if dur > 0:
            total = dur
    json.dump({"tokens": tokens, "total": total, "engine": engine,
               "sil": measure_silence(mp3_path)},
              open(json_path, "w", encoding="utf-8"), ensure_ascii=False)
    return ""

# ---------- orchestration (adapted: no Flask, no thread lock — one
#            synchronous Streamlit script run never has two requests for the
#            same unit at once the way a multi-client server did) ----------
def unit_paths(cache_dir, tid, vkey, idx):
    ad = os.path.join(cache_dir, tid, vkey)
    os.makedirs(ad, exist_ok=True)
    base = os.path.join(ad, "s%04d" % idx)
    return base + ".mp3", base + ".tok.json"

def ensure_unit(cache_dir, tid, vkey, idx, sentence):
    """Make sure sentence (tid,vkey,idx) has an mp3 + timing json, generating
    it if missing. Returns (mp3_path, json_path, error)."""
    if vkey not in VOICES:
        return None, None, "bad voice"
    mp3, js = unit_paths(cache_dir, tid, vkey, idx)
    if os.path.isfile(mp3) and os.path.isfile(js):
        return mp3, js, ""
    err = synth_unit(sentence, VOICES[vkey][0], mp3, js)
    if err:
        return None, None, err
    return mp3, js, ""

def tid_for(text, vkey):
    """Content-addressed id: same text + voice always lands in the same
    cache slot, so re-reading something already spoken costs nothing."""
    import hashlib
    return hashlib.sha1((vkey + "|" + text).encode("utf-8")).hexdigest()[:16]
