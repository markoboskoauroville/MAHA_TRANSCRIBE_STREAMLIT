"""Speechify TTS. Keyed, English only, brings exact word timings.

Everything here was verified against the live API rather than taken from
documentation, and the two traps that cost real bugs are recorded beside
the fact that fixes them.
"""

import base64

from .base import Provider, Voice, http_json, classify_standard

API = "https://api.speechify.ai"

# The curated simba-3.2 set. Four seats are shown at a time, two women and
# two men, which is what MA Reader settled on as the whole picker.
CURATED = [
    Voice("beatrice_32", "Beatrice", "en", "F", "simba-3.2"),
    Voice("imogen_32",   "Imogen",   "en", "F", "simba-3.2"),
    Voice("geffen_32",   "Geffen",   "en", "M", "simba-3.2"),
    Voice("dominic_32",  "Dominic",  "en", "M", "simba-3.2"),
    Voice("harper_32",   "Harper",   "en", "F", "simba-3.2"),
    Voice("edmund_32",   "Edmund",   "en", "M", "simba-3.2"),
    Voice("hugh_32",     "Hugh",     "en", "M", "simba-3.2"),
    Voice("wyatt_32",    "Wyatt",    "en", "M", "simba-3.2"),
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

    # ---- voices ------------------------------------------------------
    def voices(self, lang: str = "en"):
        return [v for v in CURATED if not lang or v.lang == lang]

    def catalogue(self, rotate, locale="en"):
        """The whole account catalogue, paged properly.

        TRAP: /v1/voices defaults to 50 and 50 alphabetically is all
        A-names — one British voice out of the thirty-odd that really
        exist. Walk the cursor to the end or the list is a lie.
        """
        out, cursor = [], None
        while True:
            path = f"/v1/voices?locale={locale}&limit=200"
            if cursor:
                path += f"&cursor={cursor}"
            data, err = rotate(lambda k, p=path: self._call(k, p))
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
                    v.get("display_name") or v.get("name") or v.get("title") or vid,
                    (v.get("locale") or v.get("language") or "")[:2],
                    (v.get("gender") or "")[:1].upper(),
                    model_for(vid)))
            if not isinstance(data, dict) or not data.get("has_more") or not data.get("next_cursor"):
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
