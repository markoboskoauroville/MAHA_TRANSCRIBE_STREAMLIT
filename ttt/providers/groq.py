"""Groq: speech-to-text (Whisper) and text work (translation, rewriting).

Unlike Speechify and AssemblyAI, Groq's keys are the app's own — they live
in Streamlit secrets, not in a user's key file — so this provider is handed
its key list at construction and rotates over it directly. Everything else
about it is an ordinary provider.

Transcription goes through the official groq SDK because it handles the
multipart upload; the text side is a plain HTTP call.
"""

from .. import keyring
from .base import Model, Provider, http_json, classify_standard, USER_AGENT

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

    def __init__(self, keys=None, ring=None):
        self.keys = list(keys or [])
        # The ring is optional so this provider still works standalone in a
        # test with a plain key list. When the app supplies one, every call
        # rotates through it and a 429 becomes a hand-off instead of a
        # failure — which is what makes hours of audio possible.
        self.ring = ring

    def _rotate(self, attempt):
        """Run `attempt(key) -> (result, err, kind)` through the ring if
        there is one, else straight down the key list with the same rules
        (a non-key error stops immediately rather than burning keys)."""
        if self.ring is not None:
            return keyring.rotate(self.ring, attempt)
        last = "no keys"
        for key in self.keys:
            result, err, kind = attempt(key)
            if not err:
                return result, None
            last = err
            if kind not in ("dead", "cool"):
                return None, err
        return None, f"All Groq keys failed. Last: {last}"

    # ---- key testing -------------------------------------------------
    def test_key(self, key: str):
        _, err, kind = http_json(API + "/models",
                                 {"Authorization": "Bearer " + key,
                                  "User-Agent": "TTT-LLL/1.0"},
                                 timeout=30, classify=classify_standard)
        return err, kind

    # ---- models ------------------------------------------------------
    def models(self, task: str = "", fetch=None):
        """Live from /openai/v1/models, classified by the API's OWN
        modality fields rather than by matching "whisper" in the name —
        a future audio model with a different name still lands in the
        right list."""
        last = "no keys"
        for key in self.keys:
            data, err, _ = http_json(
                API + "/models",
                {"Authorization": "Bearer " + key, "User-Agent": "TTT-LLL/1.0"},
                timeout=30, classify=classify_standard)
            if err:
                last = err
                continue
            out = []
            for m in data.get("data", []):
                mid = m.get("id")
                if not mid or m.get("active") is False:
                    continue
                ins = m.get("input_modalities") or []
                outs = m.get("output_modalities") or []
                if "transcription" in outs or "audio" in ins:
                    kind = "stt"
                elif "speech" in outs:
                    kind = "tts"
                elif "text" in outs:
                    kind = "llm"
                else:
                    continue
                if task and kind != task:
                    continue
                out.append(Model(mid, m.get("name") or mid, for_task=kind,
                                 recommended=(mid == (FAST_STT if kind == "stt"
                                                      else TEXT_MODEL))))
            out.sort(key=lambda x: (not x.recommended, x.name.lower()))
            return out, True, None
        return _fallback(task), False, last

    # ---- raw, for callers that need the API's own shapes --------------
    #
    # models() classifies and returns Model objects, which is right for
    # the dropdowns but throws away `input_modalities` — the very field
    # vision.find_vision_models reads to discover which models accept a
    # picture. These two hand back what Groq actually said, still through
    # the key ring, so no caller ever touches a key.

    def raw_models(self):
        """Groq's model list, unclassified. [] if it cannot be reached."""
        for key in self.keys:
            data, err, _ = http_json(
                API + "/models",
                {"Authorization": "Bearer " + key, "User-Agent": "TTT-LLL/1.0"},
                timeout=30, classify=classify_standard)
            if not err:
                return data.get("data", []) or []
        return []

    def raw_chat(self, payload):
        """A chat payload the caller built. Returns (data, error), which
        is the contract ttt/vision.py expects."""
        return self._rotate(lambda key: http_json(
            API + "/chat/completions",
            {"Authorization": "Bearer " + key, "User-Agent": "TTT-LLL/1.0"},
            payload=payload, method="POST", timeout=120,
            classify=classify_standard))

    # ---- speech to text ----------------------------------------------
    def transcribe(self, path: str, language: str = "hr", model: str = None):
        """Rotates over the ring (or the key list) exactly like everything
        else. The SDK raises instead of returning a status, so its errors
        are translated back into the ring's verdicts by
        classify_exception() below — otherwise a rate limit would look
        like a dead key and the ring would bury a perfectly good one.
        """
        from groq import Groq as GroqSDK      # imported late: heavy

        with open(path, "rb") as f:
            audio = f.read()

        def attempt(key):
            try:
                client = GroqSDK(api_key=key,
                                 default_headers={"User-Agent": USER_AGENT})
                # "auto" AND EMPTY ARE OMITTED, NOT SENT.
                #
                # Whisper detects the language itself when the parameter
                # is absent; sending "auto" or "" is an error. AssemblyAI
                # spells the same idea differently — it takes
                # language_detection=True — so the APP stores "auto" and
                # each provider says it in its own words. Neither the
                # app nor the other provider has to know how this one
                # spells it.
                kw = dict(file=(path, audio),
                          model=model or FAST_STT,
                          response_format="text",
                          temperature=0.0)
                if language and language != "auto":
                    kw["language"] = language
                text = client.audio.transcriptions.create(**kw).strip()
                return text, None, None
            except Exception as e:
                return None, str(e)[:250], classify_exception(e)

        text, err = self._rotate(attempt)
        if err:
            raise RuntimeError(err)
        return text

    # ---- text --------------------------------------------------------
    def complete(self, prompt: str, system: str = None, model: str = None,
                 temperature: float = 0.2, max_tokens: int = 2048) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": model or TEXT_MODEL, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        data, err = self._rotate(lambda key: http_json(
            API + "/chat/completions",
            {"Authorization": "Bearer " + key},
            payload=payload, method="POST", timeout=120,
            classify=classify_standard))
        if err:
            raise RuntimeError(err)
        return (data["choices"][0]["message"]["content"] or "").strip()


def _fallback(task: str = ""):
    """Only if the live list cannot be reached."""
    known = [Model(FAST_STT, FAST_STT, for_task="stt", recommended=True),
             Model(ACCURATE_STT, ACCURATE_STT, for_task="stt"),
             Model(TEXT_MODEL, TEXT_MODEL, for_task="llm", recommended=True)]
    return [m for m in known if not task or m.for_task == task]


def classify_exception(exc) -> str:
    """Turn an SDK exception into a ring verdict.

    The SDK raises rather than returning a status, so without this a 429
    would be indistinguishable from a bad key and the ring would bury a
    key that was merely tired — exactly the failure that makes long
    transcriptions impossible. Status code first, message text only as a
    fallback for wrappers that do not carry one.
    """
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    text = str(exc).lower()
    if isinstance(status, int):
        # THE MESSAGE IS PASSED AS THE BODY. api.groq.com is behind
        # Cloudflare exactly as api.hume.ai is, and a 403 carrying
        # "error code: 1010" is the CLIENT being refused, not the key —
        # it hits all five keys identically. Classified on status alone
        # it read as "every key is dead" and buried the whole ring, with
        # no way back but editing the store by hand.
        #
        # This client already sends a User-Agent everywhere, so the trap
        # is avoided at source; this is the second line of defence for
        # the day a proxy strips it. MANTRA_MANIFEST/apis/groq.md.
        return classify_standard(status, text)
    if "429" in text or "rate limit" in text or "too many requests" in text:
        return "cool"
    if "401" in text or "invalid api key" in text or "unauthorized" in text:
        return "dead"
    if "1010" in text:
        return "soft"          # Cloudflare, not the key — see above
    if "402" in text or "403" in text or "insufficient" in text or "quota" in text:
        return "dead"
    if "model_not_found" in text or "does not exist" in text \
            or "invalid_request" in text or "400" in text:
        return "soft"      # a request problem; no key can fix it
    return "soft"
