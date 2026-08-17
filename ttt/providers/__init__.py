"""The provider registry.

Ask for a capability, get something that can do it. Never import a vendor
module directly from a tab, the reader, or the settings screen — if calling
code knows a vendor's name, that is a bug.

Adding a provider is one file plus one line in REGISTRY below. Nothing
else in the app changes: the settings screen renders whatever needs a key,
the engine pickers list whatever offers the capability, and the reader
takes whatever function it is handed.
"""

from .assemblyai import AssemblyAI
from .edge import Edge
from .groq import Groq
from .speechify import Speechify

REGISTRY = {
    Edge.id: Edge(),
    Speechify.id: Speechify(),
    AssemblyAI.id: AssemblyAI(),
    Groq.id: Groq(),            # keys injected at startup by the entrypoint
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
    return [p for p in REGISTRY.values()
            if p.needs_key and p.id != Groq.id]


def set_groq_keys(keys) -> None:
    REGISTRY[Groq.id].keys = list(keys or [])
