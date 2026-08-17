"""Microsoft Edge neural voices. Free, keyless, many languages.

Returns no word marks. Edge can emit word boundaries from its own model,
but they run on a separate clock and drift out of sync across a sentence —
MA Reader only trusts them after re-pinning every word to the decoded
waveform. Until that is ported here, returning None is the honest answer
and the reader highlights whole sentences, which is never wrong.
"""

from .base import Provider, Voice

# Croatian first, always.
VOICES = [
    Voice("hr-HR-GabrijelaNeural", "Gabrijela", "hr", "F"),
    Voice("hr-HR-SreckoNeural",    "Srecko",    "hr", "M"),
    Voice("en-GB-SoniaNeural",     "Sonia",     "en", "F"),
    Voice("en-GB-RyanNeural",      "Ryan",      "en", "M"),
    Voice("it-IT-ElsaNeural",      "Elsa",      "it", "F"),
    Voice("de-DE-KatjaNeural",     "Katja",     "de", "F"),
    Voice("fr-FR-DeniseNeural",    "Denise",    "fr", "F"),
]

BY_ID = {v.id: v for v in VOICES}
BY_NAME = {v.name: v for v in VOICES}


class Edge(Provider):
    id = "edge"
    label = "Standard"
    capabilities = ("tts",)
    needs_key = False

    def test_key(self, key: str):
        return None, None          # nothing to test; it is keyless

    def voices(self, lang: str = ""):
        return [v for v in VOICES if not lang or v.lang == lang]

    def default_for(self, lang: str):
        for v in VOICES:
            if v.lang == lang:
                return v
        return VOICES[0]

    def synth(self, text: str, voice_id: str):
        """(audio_bytes, seconds, None) — the None is the contract saying
        'no reliable word timing', not a failure."""
        import talk_engine as tk     # existing, working; left where it is

        vkey = _vkey_for(voice_id)
        audio, seconds = tk.synth_sentence(text, vkey)
        return audio, seconds, None


# talk_engine addresses voices by its own short keys; map both ways so
# callers can pass either an Edge voice id or one of those short keys.
_VKEY_BY_ID = {
    "hr-HR-GabrijelaNeural": "hrF", "hr-HR-SreckoNeural": "hrM",
    "en-GB-SoniaNeural": "ukF", "en-GB-RyanNeural": "ukM",
    "it-IT-ElsaNeural": "itF", "de-DE-KatjaNeural": "deF",
    "fr-FR-DeniseNeural": "frF",
}


def _vkey_for(voice_id: str) -> str:
    if voice_id in _VKEY_BY_ID:
        return _VKEY_BY_ID[voice_id]
    if voice_id in BY_NAME:
        return _VKEY_BY_ID[BY_NAME[voice_id].id]
    return voice_id            # already a short key
