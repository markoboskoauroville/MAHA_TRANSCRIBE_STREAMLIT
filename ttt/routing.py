"""Which provider does which job.

One switchboard instead of engine toggles scattered through the settings
screen. Tasks are declared here; the options for each are discovered from
the provider registry, so a newly registered provider appears in the right
places automatically and this file does not change.

The rule that keeps it honest: a task's options are
`providers.with_capability(task.capability)` filtered by whether the
provider is actually usable right now — keyless ones always are, keyed
ones only once a working key exists. An option a person cannot use should
not be offered, and a provider whose keys all died should stop being
chosen without anyone having to notice.
"""


class Task:
    """One function that can be patched to an engine.

    `short` is what fits above a column in the patch bay on a phone; `en`
    and `hr` are the full names shown in the legend beneath it.
    """

    __slots__ = ("id", "capability", "en", "hr", "short", "default")

    def __init__(self, id, capability, en, hr, short, default):
        self.id = id
        self.capability = capability
        self.en = en
        self.hr = hr
        self.short = short
        self.default = default

    def label(self, lang="hr"):
        return self.hr if lang == "hr" else self.en

    @property
    def setting_key(self):
        return f"route_{self.id}"


TASKS = [
    Task("stt", "stt", "Transcription", "Transkripcija", "REC", "groq"),
    Task("tts", "tts", "Reading aloud", "Čitanje naglas", "VOX", "edge"),
    Task("llm", "llm", "Translation and AI text", "Prijevod i AI tekst", "AI", "groq"),
]

BY_ID = {t.id: t for t in TASKS}


def options(task, providers, is_usable) -> list:
    """Providers that can do this task AND are usable right now.

    `is_usable(provider) -> bool` is supplied by the caller because only it
    knows about key rings — this module stays free of storage and of
    Streamlit.
    """
    return [p for p in providers.with_capability(task.capability) if is_usable(p)]


def resolve(task, providers, is_usable, chosen: str = ""):
    """The provider that should actually do this job.

    Falls back deliberately rather than failing: the chosen one if it is
    still usable, else the task's default if that is usable, else the first
    usable option, else None. Someone whose Speechify credit ran out
    mid-session should quietly go back to the free voice, not hit an error.
    """
    usable = options(task, providers, is_usable)
    if not usable:
        return None
    by_id = {p.id: p for p in usable}
    if chosen and chosen in by_id:
        return by_id[chosen]
    if task.default in by_id:
        return by_id[task.default]
    return usable[0]


def all_routes(providers, is_usable, settings: dict) -> dict:
    """task id -> chosen provider (or None). One call gives the whole
    picture, which is what the settings screen and the tabs both want."""
    return {t.id: resolve(t, providers, is_usable, settings.get(t.setting_key, ""))
            for t in TASKS}


# ---------------------------------------------------------------------
# The patch bay
# ---------------------------------------------------------------------
# Engines down the side, functions across the top, and a crosspoint where
# they meet — the way an X32 routes buses. Reading a row tells you what one
# engine is doing; reading a column tells you who is doing one job.
#
# A crosspoint is in exactly one of four states, and the UI shows each
# differently rather than hiding any of them, because "why can I not
# choose this?" should be answerable by looking:
#
#   patched     this engine is doing this job now
#   open        it could, and a key exists — press to patch
#   nokey       it could, but there is no working key for it yet
#   blank       this engine cannot do this job at all
#
# Patching is radio, not a toggle: one engine per function. Pressing an
# open point patches it and unpatches whatever held that column, so the
# grid can never end up with two engines claiming one job or with a
# function patched to nothing.

PATCHED, OPEN, NOKEY, BLANK = "patched", "open", "nokey", "blank"


def crosspoint(task, provider, is_usable, active_id: str) -> str:
    if task.capability not in provider.capabilities:
        return BLANK
    if not is_usable(provider):
        return NOKEY
    return PATCHED if provider.id == active_id else OPEN


def matrix(providers, is_usable, settings: dict):
    """Rows of (provider, [(task, state), ...]) plus the resolved routes.

    Every registered provider gets a row, including ones that can only do
    one job — an engine with a single crosspoint still belongs on the
    panel, the same way an unused bus still has a strip.
    """
    routes = all_routes(providers, is_usable, settings)
    rows = []
    for provider in providers.REGISTRY.values():
        cells = []
        for task in TASKS:
            active = routes.get(task.id)
            cells.append((task, crosspoint(task, provider, is_usable,
                                           active.id if active else "")))
        rows.append((provider, cells))
    return rows, routes
