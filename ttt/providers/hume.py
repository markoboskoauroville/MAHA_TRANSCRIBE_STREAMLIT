"""Hume AI — the voice behind VR (Virtual Rehearsal).

Registered as a provider so it inherits the machinery every other key
already has: the ring, rotation, the dead / cool / soft vocabulary, the
admin file-picker import, and the per-key Test button. A fourth way of
handling keys would be a fourth thing to get wrong.

WHAT MAKES HUME DIFFERENT, and it is one thing: its rate limit is PER
MINUTE and a 429 is ordinary rather than exceptional. Baba measured it
(31 clips, sequentially): 0.2s spacing gave 16 successes and 15
refusals; 3s spacing was still refused; 12s spacing gave 31 of 31. So
the app PACES rather than retries, and a key that reports 429 rests for
one minute rather than the two Speechify uses — Hume's window is a
minute, so parking it longer idles a working key for no reason.
"""

from .base import Provider, Voice, http_json

API = "https://api.hume.ai/v0"

# NOT OPTIONAL. api.hume.ai is behind Cloudflare and answers a request
# with no User-Agent with 403 "error code: 1010" — measured across 21
# pairs: all 21 refused without one, all 21 accepted with one. A
# descriptive name, never an impersonated browser (MANIFEST apis/hume.md).
UA = "TTT-LLL/1.0 (+https://ttt-lll.streamlit.app)"

# Hume keys carry no distinguishing prefix — they are a plain 48-char
# token. So the importer matches on SHAPE rather than on a prefix, which
# is why this tuple is empty and not a guess: a wrong prefix here would
# silently reject every real key at import time.
KEY_PREFIXES = ()


def classify(status: int, body: str = "") -> str:
    """403 is dead UNLESS Cloudflare's 1010 — see MANIFEST apis/hume.md."""
    if status in (401, 402):
        return "dead"
    if status == 429:
        return "cool"
    if status == 403:
        return "soft" if "1010" in (body or "") else "dead"
    return "soft"


class Hume(Provider):
    id = "hume"
    label = "Hume AI"
    capabilities = ("tts",)
    needs_key = True
    key_prefixes = KEY_PREFIXES

    def test_key(self, key: str, secret: str = ""):
        """Listing one voice, never generating one.

        A test that synthesised would spend a rate-limit slot the person
        is about to want, and on a per-minute limit that is the
        difference between a working Test button and one that breaks the
        next thing you press.
        """
        import base64
        if secret:
            basic = base64.b64encode(
                ("%s:%s" % (key, secret)).encode()).decode()
            _, err, kind = http_json(
                "https://api.hume.ai/oauth2-cc/token",
                {"Authorization": "Basic " + basic,
                 "Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": UA},
                payload="grant_type=client_credentials", method="POST",
                timeout=30, classify=classify)
            return err, kind
        _, err, kind = http_json(
            API + "/tts/voices?provider=HUME_AI&page_size=1",
            {"X-Hume-Api-Key": key, "Accept": "application/json",
             "User-Agent": UA},
            timeout=30, classify=classify)
        return err, kind

    def voices(self, lang: str = ""):
        """The cast, from ttt/vr.py — the one list, so the tab and the
        provider cannot disagree about who exists."""
        from ttt import vr as VR
        return [Voice(name, name, "en", gender)
                for name, _accent, _age, gender in VR.all_voices()]
