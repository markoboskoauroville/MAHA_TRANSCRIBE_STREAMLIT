"""ENGINES — a named set of routes, and a way to prove it works.

An engine is not a new mechanism. `ttt/routing.py` already patches each
TASK (stt, tts, llm) to a provider independently, and that stays the
truth. An engine is a PRESET over those three routes with one name, so
choosing one is a single press instead of three crosspoints.

Baba: *"one engine we developed, that's the Edge plus Groq, and this is
another engine... this is main engine for your every user."*

    FREE      stt groq        tts edge        llm groq
    STUDIO    stt assemblyai  tts speechify   llm anthropic

WHY A PRESET AND NOT A MODE. Nothing downstream learns about engines.
The tabs, the reader and the settings screen keep asking the registry
for a capability, exactly as §0 rule 2 requires — "if a tab knows a
vendor's name, that is a bug." Selecting an engine writes the same
`route_*` settings the patch bay writes, so the two can never disagree
and the patch bay still works for anyone who wants a mixed set.

THE CHECK IS THE POINT. Baba: *"there will be also check engine... it
will just check if it can connect, it means keys are good, engine can
work."* A green light that only means "a key is present" is worse than
no light — it is the §47 failure again, where a success path and a
failure path both answered ok. So the check calls each provider's own
`test_key` against a real endpoint, and a provider is only reported
working when the network agrees.

This module imports no Streamlit and no vendor. It is handed a
`test_one(provider) -> (ok, detail)` by the caller, because only the
caller knows about key rings.
"""


from . import routing as _routing

# What each task falls back to when nothing has been patched. Taken from
# routing.TASKS rather than written again here, so there is one place a
# default is stated and the two files cannot drift.
TASK_DEFAULTS = {t.id: t.default for t in _routing.TASKS}


class Engine:
    """A named set of routes.

    `routes` maps a routing task id to a provider id. Any task left out
    keeps whatever it is patched to, so an engine can deliberately
    describe only part of the board.
    """

    __slots__ = ("id", "label", "routes", "note")

    def __init__(self, id, label, routes, note=""):
        self.id = id
        self.label = label
        self.routes = dict(routes)
        self.note = note

    @property
    def provider_ids(self):
        """Every distinct provider this engine relies on, in task order —
        which is also the order the check reports them, so the reading
        matches the picture."""
        seen, out = set(), []
        for task_id in ("stt", "tts", "llm"):
            pid = self.routes.get(task_id)
            if pid and pid not in seen:
                seen.add(pid)
                out.append(pid)
        return out

    def __repr__(self):
        return "Engine(%s)" % self.id


# The names are Baba's own, and they name the PARTS rather than a tier,
# because "which engine am I on" is answered by reading the vendors.
ENGINES = [
    Engine("free", "Edge / Groq",
           {"stt": "groq", "tts": "edge", "llm": "groq"},
           note="the app's own keys"),
    Engine("studio", "Speechify / AssemblyAI / Claude",
           {"stt": "assemblyai", "tts": "speechify", "llm": "anthropic"},
           note="your own keys"),
]

BY_ID = {e.id: e for e in ENGINES}
DEFAULT = "free"

SETTING_KEY = "engine"


def get(engine_id):
    return BY_ID.get(engine_id or "")


def route_settings(engine):
    """The `route_*` settings this engine implies.

    Written straight into the same settings the patch bay uses, so the
    two views of the board cannot drift apart.
    """
    return {"route_%s" % task_id: provider_id
            for task_id, provider_id in engine.routes.items()}


def current(settings: dict):
    """Which engine the CURRENT ROUTES amount to.

    Deliberately derived from the routes rather than trusted from the
    stored name: someone can patch a single crosspoint by hand, and the
    corner of the screen must then say "mixed" rather than keep claiming
    an engine that is no longer what is running. A label that can be
    wrong is worse than no label.
    """
    # AN UNSET ROUTE IS ITS DEFAULT, NOT A MISMATCH.
    #
    # Nothing writes route_* until an engine is chosen or a crosspoint is
    # patched, so a brand-new person had every route unset and the corner
    # read "mixed" on a board that was plainly running Edge and Groq.
    # That is the label being wrong in the one case where it matters
    # most — the first time anybody looks at it.
    def _route(task_id):
        value = settings.get("route_%s" % task_id)
        return value if value else TASK_DEFAULTS.get(task_id, "")

    for engine in ENGINES:
        if all(_route(task_id) == provider_id
               for task_id, provider_id in engine.routes.items()):
            return engine
    return None


# ---------------------------------------------------------------------
#  THE CHECK
# ---------------------------------------------------------------------

OK = "ok"
FAIL = "fail"
SKIP = "skip"          # keyless — nothing to prove, and it cannot fail


def check(engine, test_one):
    """Try every provider this engine needs. Returns (state, rows).

    `test_one(provider_id) -> (state, detail)` does the real work; this
    function only decides what the whole engine's verdict is.

    THE VERDICT IS THE WORST PART, not an average. An engine whose
    reading works and whose transcription does not is a broken engine —
    reporting it as "mostly fine" would be the same lie as §47's
    `ok: true` on a request that stored nothing.
    """
    rows = []
    for pid in engine.provider_ids:
        state, detail = test_one(pid)
        rows.append({"provider": pid, "state": state, "detail": detail or ""})
    if any(r["state"] == FAIL for r in rows):
        return FAIL, rows
    return OK, rows


def tasks_for(engine, provider_id):
    """Which jobs this provider does in this engine — so a failure can
    say WHAT stops working, not merely which vendor refused."""
    return [task_id for task_id in ("stt", "tts", "llm")
            if engine.routes.get(task_id) == provider_id]
