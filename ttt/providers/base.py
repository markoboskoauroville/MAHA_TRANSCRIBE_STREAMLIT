"""What every provider must look like.

Three capabilities, three shapes. Calling code asks the registry for a
capability and gets something with these methods — it never learns which
vendor answered.

    STT   transcribe(path, language) -> str
    TTS   voices(lang) -> [Voice]
          synth(text, voice_id) -> (audio_bytes, seconds, marks|None)
    LLM   complete(prompt, system) -> str

`marks` is the one interesting piece of the contract. A TTS provider that
can report exactly when each word is spoken returns a list of
`{start, end, start_time, end_time}` — character offsets into the text
*sent*, and seconds into the audio. A provider that cannot returns None,
and the reader falls back to highlighting whole sentences. Nothing else in
the app needs to know the difference.

Do not return guessed marks. Edge can emit word boundaries from its own
model and they drift out of sync over a sentence; MA Reader re-pins them to
the real waveform to fix that. Until that work is ported, Edge returns None
and highlights by sentence, which is honest and never wrong.
"""

import json
import urllib.error
import urllib.request


class Model:
    """One model a provider offers.

    `live` on the returned list (not here) says whether it came from the
    provider's own API or from a written-down fallback. `recommended` and
    `deprecated` come straight from the provider where it reports them, so
    the picker can steer without this app having an opinion that goes
    stale.
    """

    __slots__ = ("id", "name", "note", "recommended", "deprecated", "for_task")

    def __init__(self, id, name="", note="", recommended=False,
                 deprecated=False, for_task=""):
        self.id = id
        self.name = name or id
        self.note = note
        self.recommended = recommended
        self.deprecated = deprecated
        self.for_task = for_task

    def label(self) -> str:
        mark = "★ " if self.recommended else ("· " if self.deprecated else "")
        return f"{mark}{self.name}"

    def __repr__(self):
        return f"Model({self.id!r})"


class Voice:
    __slots__ = ("id", "name", "lang", "gender", "model")

    def __init__(self, id, name, lang="", gender="", model=""):
        self.id = id
        self.name = name
        self.lang = lang
        self.gender = gender
        self.model = model

    def __repr__(self):
        return f"Voice({self.name!r}, {self.lang!r})"


class Provider:
    """Base for every provider.

    `id`           short stable string, used in settings and the registry
    `label`        what a person sees
    `capabilities` any of "stt", "tts", "llm"
    `needs_key`    False for keyless providers like Edge
    `key_prefixes` shape hint for the key ring; empty tuple = no distinctive
                   prefix, so the ring's generic fallback finds them
    """

    id = ""
    label = ""
    capabilities = ()
    needs_key = True
    key_prefixes = ()

    def test_key(self, key: str):
        """Return (error, kind) — (None, None) when the key is good.
        kind is "dead" | "cool" | "soft" so the ring knows what to do."""
        raise NotImplementedError

    def models(self, task: str = "", fetch=None):
        """Return (models, live, error).

        Asked fresh from the provider whenever possible, so a model
        released next year appears without anyone editing this app. A
        provider with no model-list endpoint returns its written-down list
        with live=False, and the picker says so rather than pretending.

        `fetch(key) -> (data, err, kind)` is supplied by the caller for
        keyed providers, so this module never touches a key ring.
        """
        return [], False, None


# Every request identifies itself. This is not cosmetic: Groq sits behind
# Cloudflare, which answers a request with NO User-Agent with "403, error
# code: 1010" for every endpoint and every model — a bot block, nothing to
# do with the key. Verified directly: no UA -> 403, any UA -> 200.
#
# A descriptive string works exactly as well as a browser one (also
# verified, side by side), so there is no reason to impersonate Chrome —
# and pretending to be a browser to an API we authenticate to honestly is
# both unnecessary and the sort of thing that ages badly. Setting it here,
# once, means no provider can forget it.
USER_AGENT = "TTT-LLL/1.0 (+https://ttt-lll.streamlit.app)"


def http_json(url: str, headers: dict, payload=None, data: bytes = None,
              method: str = "GET", timeout: int = 60, classify=None):
    """One HTTP call, returning (parsed_json, error, kind).

    `classify(status) -> "dead"|"cool"|"soft"` maps a provider's status
    codes onto the ring's verdicts. A transport failure is always "soft" —
    the network being down is never a key's fault.
    """
    body = None
    h = dict(headers)
    h.setdefault("User-Agent", USER_AGENT)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    elif data is not None:
        body = data
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = r.read().decode("utf-8", "replace")
        return (json.loads(text) if text.strip() else {}), None, None
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode("utf-8", "replace")
        except Exception:
            text = ""
        kind = classify(e.code) if classify else "soft"
        return None, _message(e.code, text), kind
    except Exception as e:
        return None, f"Could not reach the service: {e}", "soft"


def _detail(body: str) -> str:
    """The provider's own explanation, if it sent one.

    Almost every provider answers errors with {"error": {"message": ...}}
    or {"error": "..."} or {"message": ...}. Their message names the actual
    problem ("The model `x` does not exist or you do not have access to
    it") where a generic status line cannot, so prefer theirs over ours.
    """
    try:
        data = json.loads(body or "")
    except Exception:
        return ""
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or err.get("code")
        elif isinstance(err, str):
            msg = err
        else:
            msg = data.get("message") or data.get("detail")
        if msg:
            return str(msg)[:200]
    return ""


def _message(status: int, body: str) -> str:
    detail = _detail(body)
    common = {
        401: "The key was rejected (401).",
        402: "This account has no credit left (402).",
        403: "This key is not allowed to do that (403).",
        404: "Not found (404).",
        429: "Rate limit reached (429).",
    }
    base = common.get(status)
    if base:
        # 401/403 detail can echo key material back; the others are safe
        # and usually far more useful than the generic line.
        return base if status in (401, 403) or not detail else f"{base} {detail}"
    if status >= 500:
        return f"The service had an error ({status})."
    return f"Refused ({status}) {detail or (body or '')[:150]}"


# THE TWO THINGS A STATUS CODE ALONE CANNOT TELL YOU
#
# Audited 25.8.2026 across all four rings, after the Hume one was found
# broken. Every classifier here took ONLY the status, and two whole
# classes of failure are invisible that way:
#
#   A 403 THAT IS CLOUDFLARE, NOT THE PROVIDER. api.groq.com and
#     api.hume.ai both sit behind it, and a request it does not like
#     comes back 403 with "error code: 1010" — for EVERY key at once.
#     MANTRA_MANIFEST/apis/hume.md measured it across 21 pairs: all 21
#     gave 403/1010 without a User-Agent and all 21 gave 200 with one.
#     Classified on status alone it reads as "every key is dead" and
#     buries the whole ring permanently, with no way back but editing
#     the store by hand.
#
#   A 400 THAT MEANS THE ACCOUNT IS EMPTY. MEASURED on Hume, 25.8.2026:
#     an exhausted account answers 400 with slug zero_credits, code
#     E0300 — not 402, which is what everyone codes for. 400 fell to
#     "soft", and soft STOPS instead of rotating, so one empty account
#     killed a reading while twenty others had credit.
#
# Both are decided by the BODY, so the body is read. This lives here
# rather than in each provider because it is the same rule everywhere,
# and the Hume bug existed precisely because its version lived alone.


CLOUDFLARE_BLOCK = "1010"

# Words a provider uses when the money has run out. Kept as substrings
# rather than a status because every provider picks a different code for
# it — Hume 400, Speechify 402, and AssemblyAI is unverified.
NO_CREDIT_MARKS = ("zero_credits", "e0300", "credit balance",
                   "insufficient", "quota exceeded", "out of credits",
                   "payment required", "billing")


def classify_standard(status: int, body: str = "") -> str:
    """The verdict map almost every provider wants.

    auth and credit problems bury the key, 429 rests it, a Cloudflare
    block blames nobody, and everything else blames nobody either.

    `body` is optional so old call sites keep working, but a caller that
    has the body and does not pass it is throwing away the only thing
    that separates a dead ring from a missing header.
    """
    low = (body or "").lower()
    if status == 403 and CLOUDFLARE_BLOCK in low:
        # NEVER condemn on this. It is the client being refused, not the
        # key — and it hits every key identically, so condemning means
        # losing the whole ring to a missing header.
        return "soft"
    if status in (401, 402, 403):
        return "dead"
    if status == 429:
        return "cool"
    if status == 400 and any(m in low for m in NO_CREDIT_MARKS):
        # An empty account is dead, not soft. Condemned rather than
        # rested, because credit does not come back in sixty seconds.
        return "dead"
    return "soft"
