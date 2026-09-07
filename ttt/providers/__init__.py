"""The provider registry.

Ask for a capability, get something that can do it. Never import a vendor
module directly from a tab, the reader, or the settings screen — if calling
code knows a vendor's name, that is a bug.

Adding a provider is one file plus one line in REGISTRY below. Nothing
else in the app changes: the settings screen renders whatever needs a key,
the engine pickers list whatever offers the capability, and the reader
takes whatever function it is handed.
"""

from .anthropic import Anthropic
from .assemblyai import AssemblyAI
from .edge import Edge
from .google import Google
from .groq import Groq
from .hume import Hume
from .local import Local
from .markoapi import MarkoAPI
from .speechify import Speechify

# WHAT THIS MODULE PROMISES app.py, AS A NUMBER.
#
# RAISE IT whenever app.py starts depending on something new in here — a
# new function, a new REGISTRY entry, a changed signature. app.py checks
# it at startup and refuses with a sentence a person can act on.
#
# WHY A NUMBER AND NOT A hasattr CHECK. On 6.9.2026 the live app died at
# import with a redacted AttributeError on set_google_keys, on a commit
# where that function was provably present — verified byte for byte
# against the remote and re-imported from a clean clone.
#
# Streamlit RE-READS app.py on every run but keeps imported packages in
# sys.modules. A deploy that reruns without restarting the process
# therefore executes a NEW app.py against the OLD copy of this module,
# still in memory. Every symptom follows: the new line is there, the
# function it calls is not, and the traceback names a function that
# exists in the file on disk.
#
# hasattr would have caught only the one missing name. The mismatch is
# the whole module being old, so the whole module states its level and
# app.py compares it.
API_LEVEL = 2          # 2: google is a provider, set_google_keys exists

REGISTRY = {
    Edge.id: Edge(),
    Local.id: Local(),          # offline Whisper + Piper; usable only where installed (the machine)
    MarkoAPI.id: MarkoAPI(),    # the same engines through Marko's API; key injected at startup
    Speechify.id: Speechify(),
    AssemblyAI.id: AssemblyAI(),
    Groq.id: Groq(),            # keys injected at startup by the entrypoint
    Google.id: Google(),        # keys injected at startup, same as Groq
    Hume.id: Hume(),            # VR's voice — paced, see ttt/vr.py
    Anthropic.id: Anthropic(),
}


def get(provider_id: str):
    return REGISTRY.get(provider_id)


def with_capability(capability: str):
    """Every provider offering a capability, in registration order."""
    return [p for p in REGISTRY.values() if capability in p.capabilities]


def keyed_providers():
    """Providers a person supplies their own keys for — exactly what the
    Settings screen should render a key section for, in order. Groq is
    excluded: its keys are the app's own, in Streamlit secrets."""
    # GOOGLE JOINS GROQ IN THE EXCLUSION, and it is not a style choice.
    # Both providers' keys are the APP's, held in Streamlit secrets and
    # shared by everybody. Listing them here would put a key panel in
    # front of a person for keys they do not own and cannot change, and
    # the ring behind it would always read 0/0 however many keys were
    # actually working. Added when Google became a provider and turned up
    # in that list uninvited.
    APP_OWNED = (Groq.id, Google.id)
    return [p for p in REGISTRY.values()
            if p.needs_key and p.id not in APP_OWNED]


def set_groq_keys(keys) -> None:
    REGISTRY[Groq.id].keys = list(keys or [])


def set_google_keys(keys) -> None:
    """Google's keys are the APP's, exactly like Groq's — they live in
    Streamlit secrets, not in a person's key file. So the provider is
    constructed empty and handed them at startup, and anything asking the
    registry for a Google capability depends on that call having run."""
    REGISTRY[Google.id].keys = list(keys or [])


def set_marko(key, url=None) -> None:
    """The app's own key for Marko's API (MARKO_API_KEY in secrets) and, if
    given, where it lives (MARKO_API_URL); without a key the provider is not
    usable and the Marko API button stays grey."""
    p = REGISTRY[MarkoAPI.id]
    p.key = (key or "").strip()
    if url:
        p.url = str(url).rstrip("/")
