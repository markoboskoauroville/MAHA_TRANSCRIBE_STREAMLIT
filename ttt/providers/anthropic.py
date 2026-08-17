"""Anthropic (Claude) for text work: translation and the AI text box.

Keyed by the person, like Speechify and AssemblyAI. Lists its models live
from /v1/models, so a model released after this file was written shows up
in the picker on its own.
"""

from .base import Model, Provider, http_json, classify_standard

API = "https://api.anthropic.com"
VERSION = "2023-06-01"

# Only used if the live list cannot be fetched — a sensible current default
# rather than a hardcoded catalogue that would rot.
FALLBACK = [Model("claude-sonnet-4-5-20250929", "Claude Sonnet 4.5")]


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
                 model: str = None, temperature: float = 0.2,
                 max_tokens: int = 2048) -> str:
        payload = {
            "model": model or FALLBACK[0].id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        data, err = fetch(lambda k: http_json(
            API + "/v1/messages", self._headers(k), payload=payload,
            method="POST", timeout=120, classify=classify_standard))
        if err:
            raise RuntimeError(err)
        parts = [b.get("text", "") for b in (data.get("content") or [])
                 if b.get("type") == "text"]
        return "".join(parts).strip()
