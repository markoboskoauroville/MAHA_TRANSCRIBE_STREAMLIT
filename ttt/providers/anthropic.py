"""Anthropic (Claude) for text work: translation and the AI text box.

Keyed by the person, like Speechify and AssemblyAI. Lists its models live
from /v1/models, so a model released after this file was written shows up
in the picker on its own.
"""

from .base import Model, Provider, http_json, classify_standard

API = "https://api.anthropic.com"
VERSION = "2023-06-01"

# Only used if the live list cannot be fetched — a sensible current default
# rather than a hardcoded catalogue that would rot. It rotted anyway: this
# said claude-sonnet-4-5-20250929 until 22.8.2026. Current ids carry no date
# suffix, and appending one is its own way of getting a 404.
FALLBACK = [Model("claude-opus-5", "Claude Opus 5")]


class Anthropic(Provider):
    id = "anthropic"
    label = "Claude"
    capabilities = ("llm",)
    needs_key = True
    key_prefixes = ("sk-ant-",)

    def _headers(self, key):
        return {"x-api-key": key, "anthropic-version": VERSION}

    def test_key(self, key: str):
        _, err, kind = http_json(API + "/v1/models?limit=1", self._headers(key),
                                 timeout=30, classify=classify_standard)
        return err, kind

    def models(self, task: str = "", fetch=None):
        """Live from /v1/models. Newest first, which is how Anthropic
        returns them, so the picker's first entry is the current model."""
        if fetch is None:
            return FALLBACK, False, "no key"
        data, err = fetch(lambda k: http_json(
            API + "/v1/models?limit=100", self._headers(k),
            timeout=30, classify=classify_standard))
        if err or not isinstance(data, dict):
            return FALLBACK, False, err or "unexpected response"
        out = []
        for m in data.get("data", []):
            mid = m.get("id")
            if not mid:
                continue
            out.append(Model(mid, m.get("display_name") or mid, for_task="llm"))
        if out:
            out[0].recommended = True      # newest, as returned by the API
        return (out or FALLBACK), bool(out), None

    def complete(self, fetch, prompt: str, system: str = None,
                 model: str = None, temperature: float = None,
                 max_tokens: int = 16000) -> str:
        """One turn, one answer.

        NO TEMPERATURE UNLESS ASKED FOR, and that is not a preference.
        Sampling parameters were REMOVED from the current models — Opus
        5, Opus 4.8, 4.7, Sonnet 5 all answer a request carrying
        `temperature` with a 400 and nothing else. This used to send
        0.2 on every call, so the first call to any current model failed,
        and it failed in a way that reads like the feature is wrong
        rather than one line of it. It is still accepted explicitly, for
        an older model that wants it — passing it to a current one is
        the caller asking for that 400.

        `max_tokens` is a CEILING, not a reservation: unused tokens cost
        nothing. 2048 was small enough to cut a long translation off
        mid-sentence, and far too small to hand back an edited file.
        """
        payload = {
            "model": model or FALLBACK[0].id,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if system:
            payload["system"] = system
        # A bigger ceiling means a longer answer is possible, so the wait
        # has to be allowed to be longer too — 120s was sized for 2048.
        data, err = fetch(lambda k: http_json(
            API + "/v1/messages", self._headers(k), payload=payload,
            method="POST", timeout=300, classify=classify_standard))
        if err:
            raise RuntimeError(err)
        parts = [b.get("text", "") for b in (data.get("content") or [])
                 if b.get("type") == "text"]
        return "".join(parts).strip()
