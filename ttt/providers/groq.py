"""Groq: speech-to-text (Whisper) and text work (translation, rewriting).

Unlike Speechify and AssemblyAI, Groq's keys are the app's own — they live
in Streamlit secrets, not in a user's key file — so this provider is handed
its key list at construction and rotates over it directly. Everything else
about it is an ordinary provider.

Transcription goes through the official groq SDK because it handles the
multipart upload; the text side is a plain HTTP call.
"""

from .base import Provider, http_json, classify_standard

API = "https://api.groq.com/openai/v1"

FAST_STT = "whisper-large-v3-turbo"     # first pass
ACCURATE_STT = "whisper-large-v3"       # what Correct re-runs
TEXT_MODEL = "openai/gpt-oss-120b"      # chosen by testing; see HANDOVER


class Groq(Provider):
    id = "groq"
    label = "Groq"
    capabilities = ("stt", "llm")
    needs_key = True
    key_prefixes = ("gsk_",)

    def __init__(self, keys=None):
        self.keys = list(keys or [])

    # ---- key testing -------------------------------------------------
    def test_key(self, key: str):
        _, err, kind = http_json(API + "/models",
                                 {"Authorization": "Bearer " + key,
                                  "User-Agent": "TTT-LLL/1.0"},
                                 timeout=30, classify=classify_standard)
        return err, kind

    # ---- speech to text ----------------------------------------------
    def transcribe(self, path: str, language: str = "hr", model: str = None):
        """Rotates over the app's own keys. Raises if all of them fail, so
        the caller can decide what to tell the person."""
        from groq import Groq as GroqSDK      # imported late: heavy, optional

        if not self.keys:
            raise RuntimeError("No Groq keys configured.")
        last = "unknown error"
        for key in self.keys:
            try:
                client = GroqSDK(api_key=key)
                with open(path, "rb") as f:
                    return client.audio.transcriptions.create(
                        file=(path, f.read()),
                        model=model or FAST_STT,
                        language=language,
                        response_format="text",
                        temperature=0.0,
                    ).strip()
            except Exception as e:
                last = str(e)
                continue
        raise RuntimeError(f"All Groq keys failed. Last: {last}")

    # ---- text --------------------------------------------------------
    def complete(self, prompt: str, system: str = None, model: str = None,
                 temperature: float = 0.2, max_tokens: int = 2048) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": model or TEXT_MODEL, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        last = "no keys"
        for key in self.keys:
            data, err, _ = http_json(
                API + "/chat/completions",
                {"Authorization": "Bearer " + key, "User-Agent": "TTT-LLL/1.0"},
                payload=payload, method="POST", timeout=120,
                classify=classify_standard)
            if not err:
                return (data["choices"][0]["message"]["content"] or "").strip()
            last = err
        raise RuntimeError(f"All Groq keys failed. Last: {last}")
