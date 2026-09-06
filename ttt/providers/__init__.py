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
from .speechify import Speechify

REGISTRY = {
    Edge.id: Edge(),
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
