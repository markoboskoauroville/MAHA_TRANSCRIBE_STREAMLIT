"""Read settings and spare keys from the Google Sheet.

The sheet is the one durable, shared store this deployment has — Cloud
disk is not durable, Streamlit secrets are read-only at runtime, and
localStorage is trapped in a single browser. So it holds the things that
must be the same for everybody and editable without a deploy: the wording
of the AI prompts, a few switches, and API keys that are not in secrets.

THE RULE THAT OUTRANKS EVERYTHING HERE: the sheet is a convenience, never
a dependency. If it is slow, unreachable, misconfigured or full of
nonsense, the app must behave exactly as it does with no sheet at all.
Every function below returns a default rather than raising, and the fetch
swallows everything.

Read ONCE per session and cached. A settings read on every rerun would be
several fetches a second, which would make the app feel broken in exactly
the way this file exists to avoid.

PRECEDENCE for a setting: the user's own row, then the global row, then
the built-in default. That way one person can be given a different prompt
without disturbing anyone else, and a blank sheet changes nothing.
"""

import json
import urllib.parse
import urllib.request

TIMEOUT = 8

# What the app falls back to when the sheet says nothing. These are the
# same words the sheet is seeded with, so behaviour is identical whether
# or not the sheet has been set up.
DEFAULTS = {
    "prompt_grammar": ("Fix spelling, punctuation and obvious slips. "
                       "Do not change the wording or the style."),
    "prompt_reshape": ("Tidy this into clear paragraphs. Remove filler and "
                       "repetition. Keep every fact and the speaker's own voice."),
    "allow_user_keys": "TRUE",
    "allow_patch_bay": "FALSE",
    "store_audio": "TRUE",
}

# A prompt from the sheet is untrusted text: it is typed by a person and
# goes into an LLM instruction. Length is capped so a pasted essay cannot
# push the actual material out of the model's attention.
MAX_PROMPT = 600


def fetch(url: str, token: str) -> dict:
    """Everything the sheet has to say. `{}` on any failure at all."""
    if not url or not token:
        return {}
    try:
        q = urllib.parse.urlencode({"token": token, "what": "config"})
        req = urllib.request.Request(url + ("&" if "?" in url else "?") + q,
                                     headers={"User-Agent": "TTT-LLL/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        if not isinstance(data, dict) or not data.get("ok"):
            return {}
        return data
    except Exception:
        return {}


def settings_map(config: dict) -> dict:
    """`{(scope, key): value}` from the raw rows, lowercased scopes."""
    out = {}
    for row in (config or {}).get("settings") or []:
        try:
            scope, key, value = row[0], row[1], row[2]
        except Exception:
            continue
        scope = str(scope or "").strip().lower()
        key = str(key or "").strip()
        if scope and key:
            out[(scope, key)] = str(value)
    return out


def setting(config: dict, key: str, user: str = "") -> str:
    """The user's row, else the global row, else the built-in default."""
    m = settings_map(config)
    u = (user or "").strip().lower()
    if u and (u, key) in m and str(m[(u, key)]).strip():
        return str(m[(u, key)]).strip()
    if ("global", key) in m and str(m[("global", key)]).strip():
        return str(m[("global", key)]).strip()
    return DEFAULTS.get(key, "")


def flag(config: dict, key: str, user: str = "") -> bool:
    """A TRUE/FALSE setting. Anything unrecognised reads as False, so a
    typo can never silently switch something on."""
    v = setting(config, key, user).strip().lower()
    return v in ("true", "yes", "1", "on")


def prompt(config: dict, key: str, user: str = "") -> str:
    """A prompt, capped. Never empty: falls back to the built-in."""
    v = setting(config, key, user).strip()
    if not v:
        v = DEFAULTS.get(key, "")
    return v[:MAX_PROMPT]


def keys_for(config: dict, provider: str) -> list:
    """Spare keys for a provider, in sheet order. Never raises."""
    got = (config or {}).get("keys") or {}
    vals = got.get((provider or "").lower()) or []
    out = []
    for v in vals:
        v = str(v or "").strip()
        if v and v not in out:
            out.append(v)
    return out
