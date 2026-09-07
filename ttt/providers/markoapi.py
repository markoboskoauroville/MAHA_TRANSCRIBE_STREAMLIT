"""MARKO API: Marko's own transcription and speech service, on his machine,
through the door at https://ttt-lll.pages.dev/api/v1 (TTT_PORTAL).

Marko, 7.9.2026: "three buttons to switch between engines: Edge, Google, and
Marko API. So everything is under the same hood, and I can see my Marko APIs."
So this provider does not run an engine; it calls the API any other app would
call, with an API key made in the admin panel (MARKO_API_KEY in secrets;
MARKO_API_URL to point elsewhere). Whisper and Piper today; whatever he puts
behind the API later.

TTS returns real word marks (the API measures them), Speechify's shape, so the
reader lights the word. STT posts the file and gets the words.
"""

import json
import os

from .base import Provider, Voice, USER_AGENT

DEFAULT_URL = "https://ttt-lll.pages.dev"


class MarkoAPI(Provider):
    id = "markoapi"
    label = "Marko API"
    capabilities = ("stt", "tts")
    needs_key = False           # the app's own key, from secrets, like Groq's
    key = ""
    url = DEFAULT_URL

    @property
    def installed(self):
        return bool(self.key)

    def test_key(self, key: str):
        return None, None

    def _headers(self, extra=None):
        h = {"Authorization": "Bearer " + self.key, "User-Agent": USER_AGENT}
        h.update(extra or {})
        return h

    # ------------------------------------------------------------ stt
    def transcribe(self, path: str, language: str = "hr", model: str = None) -> str:
        import requests                                # late; the app has it
        with open(path, "rb") as f:
            r = requests.post(self.url + "/api/v1/transcribe", headers=self._headers(),
                              files={"file": (os.path.basename(path), f)},
                              data={"language": language or "auto"}, timeout=180)
        r.raise_for_status()
        return (r.json().get("text") or "").strip()

    # ------------------------------------------------------------ tts
    def voices(self, lang: str = ""):
        import requests
        try:
            r = requests.get(self.url + "/api/v1/voices", headers=self._headers(), timeout=20)
            r.raise_for_status()
            out = [Voice(v["id"], v.get("name") or v["id"], v.get("lang", ""), v.get("gender", "")) for v in r.json()]
        except Exception:                              # noqa: BLE001
            out = [Voice("en_GB-alan-medium", "Alan", "en", "M")]
        return [v for v in out if not lang or v.lang == lang] or out

    def default_for(self, lang: str):
        vs = self.voices(lang)
        return vs[0] if vs else None

    def synth(self, text: str, voice_id: str):
        """(wav_bytes, seconds, marks): the marks are measured on the machine,
        [{start, end, start_time, end_time}] over the text sent."""
        import base64
        import requests
        r = requests.post(self.url + "/api/v1/speech?format=json", headers=self._headers({"Content-Type": "application/json"}),
                          data=json.dumps({"text": text, "voice": voice_id, "marks": True}), timeout=180)
        r.raise_for_status()
        j = r.json()
        audio = base64.b64decode(j.get("audio_base64") or "")
        marks = j.get("marks") if isinstance(j.get("marks"), list) else None
        return audio, float(j.get("seconds") or 0), marks
