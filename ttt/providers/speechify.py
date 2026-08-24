"""Speechify TTS. Keyed, English only, brings exact word timings.

Everything here was verified against the live API rather than taken from
documentation, and the two traps that cost real bugs are recorded beside
the fact that fixes them.
"""

import base64

from .base import Model, Provider, Voice, http_json, classify_standard

API = "https://api.speechify.ai"

# The seats, per language — Baba's list, 24.8.2026. English is four
# British voices on simba-3.2. Croatian: no hr-HR exists on any model
# (all 988 catalogue voices walked live, 24.8.2026), so Croatian is read
# the Slavic way on simba-multilingual, Lesya first. beatrice_32 sits in
# BOTH sets with DIFFERENT models — the model belongs to the seat, which
# is why voices(lang) must be answered per language and never flattened.
CURATED = [
    Voice("beatrice_32", "Beatrice", "en", "F", "simba-3.2"),
    Voice("imogen_32",   "Imogen",   "en", "F", "simba-3.2"),
    Voice("edmund_32",   "Edmund",   "en", "M", "simba-3.2"),
    Voice("hugh_32",     "Hugh",     "en", "M", "simba-3.2"),
    Voice("lesya",       "Lesya",    "hr", "F", "simba-multilingual"),
    Voice("beatrice_32", "Beatrice", "hr", "F", "simba-multilingual"),
    Voice("dominika",    "Dominika", "hr", "F", "simba-multilingual"),
    Voice("daria",       "Daria",    "hr", "F", "simba-multilingual"),
]


def model_for(voice_id: str) -> str:
    """TRAP, measured live: simba-3.2 answers HTTP 400 for any voice whose
    id does not end _32 — "the selected voice is not available for
    simba-3.2" — and that is almost the whole catalogue. The older API
    guide recommends 3.2 generally; MA Reader v3's handover has it right.
    Never hardcode one model for every voice."""
    return "simba-3.2" if voice_id.endswith("_32") else "simba-english"


class Speechify(Provider):
    id = "speechify"
    label = "Speechify"
    capabilities = ("tts",)
    needs_key = True
    key_prefixes = ("sk_", "sws_", "sa_", "spk_")

    # ---- key testing -------------------------------------------------
    def test_key(self, key: str):
        _, err, kind = self._call(key, "/v1/voices?locale=en&limit=1", timeout=30)
        return err, kind

    def _call(self, key, path, payload=None, method="GET", timeout=60):
        return http_json(API + path,
                         {"Authorization": "Bearer " + key, "Accept": "application/json"},
                         payload=payload, method=method, timeout=timeout,
                         classify=classify_standard)

    # ---- models ------------------------------------------------------
    def models(self, task: str = "", fetch=None):
        """Live from /v1/audio/models, which reports its own `recommended`
        and `deprecated` flags — so the picker steers towards whatever
        Speechify currently recommends rather than what was true the day
        this was written."""
        if fetch is None:
            return [Model(m, m, for_task="tts") for m in ("simba-3.2", "simba-english")], False, "no key"
        data, err = fetch(lambda k: self._call(k, "/v1/audio/models", timeout=30))
        if err or not isinstance(data, dict):
            return ([Model("simba-3.2", "Simba 3.2", for_task="tts", recommended=True),
                     Model("simba-english", "Simba English", for_task="tts")],
                    False, err or "unexpected response")
        out = []
        for m in data.get("models", []):
            mid = m.get("id")
            if not mid:
                continue
            out.append(Model(mid, m.get("name") or mid,
                             note=(m.get("description") or "")[:80],
                             recommended=bool(m.get("recommended")),
                             deprecated=bool(m.get("deprecated")),
                             for_task="tts"))
        out.sort(key=lambda x: (not x.recommended, x.deprecated, x.name.lower()))
        return out, bool(out), None

    # ---- voices ------------------------------------------------------
    def voices(self, lang: str = "en"):
        return [v for v in CURATED if not lang or v.lang == lang]

    def catalogue(self, rotate, locale: str = ""):
        """Every voice on the account, paginated properly.

        THE TRAP, verified live: /v1/voices defaults to a limit of 50 and
        returns alphabetically, so an unpaginated call yields 50 names all
        starting with A and looks like the whole catalogue. Walking the
        cursor gives 979 voices across 36 locales. Always follow
        next_cursor to the end.

        `locale` is optional and deliberately unused by the app: a
        Speechify voice may read ANY text, whatever language it was made
        for. Croatian read in an English voice is a legitimate choice
        here, and the word timings come back correct for it (tested with
        diacritics), so nothing filters voices by language. Only Edge,
        whose voices are language-specific by construction, is matched to
        a language.
        """
        out, cursor, pages = [], None, 0
        while True:
            path = "/v1/voices?limit=200"
            if locale:
                path += f"&locale={locale}"
            if cursor:
                path += f"&cursor={cursor}"
            data, err = rotate(lambda k, p=path: self._call(k, p, timeout=45))
            if err:
                return out, err
            items = (data if isinstance(data, list)
                     else data.get("voices") or data.get("data") or data.get("items") or [])
            for v in items:
                vid = v.get("id") or v.get("voice_id")
                if not vid:
                    continue
                out.append(Voice(
                    vid,
                    v.get("display_name") or v.get("name") or vid,
                    v.get("locale") or "",
                    (v.get("gender") or "")[:1].upper(),
                    model_for(vid)))
            pages += 1
            if not isinstance(data, dict) or not data.get("has_more") \
                    or not data.get("next_cursor") or pages > 20:
                return out, None
            cursor = data["next_cursor"]

    # ---- synthesis ---------------------------------------------------
    def synth(self, rotate, text: str, voice_id: str, model: str = None):
        """Returns (audio_bytes, seconds, marks). Marks are exact: the API
        reports character offsets into the text we sent plus millisecond
        timing measured from the audio it just made, so the highlight lands
        where the voice actually is rather than where a guess put it."""
        payload = {"input": text[:2000], "voice_id": voice_id,
                   "audio_format": "mp3", "model": model or model_for(voice_id)}
        data, err = rotate(lambda k: self._call(k, "/v1/audio/speech", payload,
                                                method="POST", timeout=90))
        if err:
            raise RuntimeError(err)
        audio = base64.b64decode(data["audio_data"])
        marks = _flatten_marks(data.get("speech_marks") or {})
        total = max((m["end_time"] for m in marks), default=0.0)
        if total <= 0:
            total = max(1.0, len(text.split()) * 0.38)
        return audio, total, marks


def _flatten_marks(node, out=None):
    """Chunks nest — a sentence chunk holding word chunks — so flatten
    recursively. Punctuation-only values are skipped."""
    if out is None:
        out = []
    if isinstance(node, dict):
        if node.get("type") == "word":
            val = node.get("value") or ""
            st, en = node.get("start_time"), node.get("end_time")
            if any(c.isalnum() for c in val) and st is not None and en is not None:
                out.append({"start": int(node.get("start", 0)),
                            "end": int(node.get("end", 0)),
                            "start_time": st / 1000.0,
                            "end_time": en / 1000.0})
        for child in (node.get("chunks") or []):
            _flatten_marks(child, out)
    out.sort(key=lambda m: m["start_time"])
    return out
