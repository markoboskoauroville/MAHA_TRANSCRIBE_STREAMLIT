"""THE OFFLINE ENGINE: Whisper and Piper on the machine itself, no key, no network.

Marko, 7.9.2026, through the Universal Teacher and Assistant: "the app which
can transcribe, which can talk, needs to be installed on that virtual machine,
and we use these offline engines to run transcription and talking."

STT is faster-whisper (CTranslate2, int8, CPU; ARM builds exist), `small` by
default, `medium` for an accent (env TTT_WHISPER). TTS is Piper (fast,
offline, many languages, no cloning); the voices are .onnx files in
TTT_PIPER_DIR (~/models/piper), downloaded by `python -m piper.download_voices`.
Croatian is not among Piper's languages; the nearest is Serbian, and the
online voices (Edge) still exist for it.

INSTALLED OR NOT is decided cheaply at import (find_spec), never by importing
the engines: the same code runs on Streamlit Cloud, where none of this is
installed, and there the provider is simply not usable and the "offline"
engine does not appear. The models load lazily, once, on first use.
"""

import glob
import importlib.util
import io
import os
import wave

from .base import Provider, Voice

WHISPER_SIZE = os.environ.get("TTT_WHISPER", "small")
PIPER_DIR = os.path.expanduser(os.environ.get("TTT_PIPER_DIR", "~/models/piper"))

INSTALLED = (importlib.util.find_spec("faster_whisper") is not None
             and importlib.util.find_spec("piper") is not None)

# Piper voice file name -> (shown name, language, gender)
KNOWN = {
    "en_GB-alan-medium": ("Alan", "en", "M"),
    "en_US-lessac-medium": ("Lessac", "en", "F"),
    "de_DE-thorsten-medium": ("Thorsten", "de", "M"),
    "it_IT-riccardo-x_low": ("Riccardo", "it", "M"),
    "fr_FR-siwis-medium": ("Siwis", "fr", "F"),
    "sr_RS-serbski_institut-medium": ("Srpski", "sr", "M"),
}


class Local(Provider):
    id = "local"
    label = "Offline (Whisper / Piper)"
    capabilities = ("stt", "tts")
    needs_key = False
    installed = INSTALLED

    def __init__(self):
        self._whisper = None
        self._piper = {}

    def test_key(self, key: str):
        return None, None

    # ------------------------------------------------------------ stt
    def _model(self):
        if self._whisper is None:
            from faster_whisper import WhisperModel      # late: heavy
            self._whisper = WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")
        return self._whisper

    def transcribe(self, path: str, language: str = "hr", model: str = None) -> str:
        """The words in a file. "auto" or "" lets Whisper decide the language,
        the way the other providers spell it in their own words."""
        lang = None if (language or "").lower() in ("", "auto") else language
        segs, _info = self._model().transcribe(path, language=lang, beam_size=1,
                                               vad_filter=True, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segs).strip()

    # ------------------------------------------------------------ tts
    def voices(self, lang: str = ""):
        out = []
        for onnx in sorted(glob.glob(os.path.join(PIPER_DIR, "*.onnx"))):
            key = os.path.basename(onnx)[:-5]
            name, vlang, gender = KNOWN.get(key, (key, key.split("_")[0], ""))
            if not lang or vlang == lang:
                out.append(Voice(key, name, vlang, gender))
        return out

    def default_for(self, lang: str):
        vs = self.voices(lang) or self.voices()
        return vs[0] if vs else None

    def _voice(self, voice_id: str):
        if voice_id not in self._piper:
            from piper import PiperVoice                 # late: heavy
            self._piper[voice_id] = PiperVoice.load(os.path.join(PIPER_DIR, voice_id + ".onnx"))
        return self._piper[voice_id]

    def synth(self, text: str, voice_id: str):
        """(wav_bytes, seconds, None): Piper has no word marks, so the reader
        highlights by sentence, honestly."""
        v = self._voice(voice_id)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            v.synthesize_wav(text, w)
        data = buf.getvalue()
        with wave.open(io.BytesIO(data)) as w:
            seconds = w.getnframes() / float(w.getframerate() or 22050)
        return data, seconds, None
