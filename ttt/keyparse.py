"""KEY RECOGNITION — which provider does this string belong to.

Ported from `markoboskoauroville/Key_Tester`,
`app/src/main/java/org/mantra/keytester/KeyParser.kt`, with its comments
carried over rather than summarised. keyring.md §9: port it with the
comments intact, because every one of them is a bug somebody already
paid for, and rewriting from scratch means paying for all of them again.

WHOLE-TOKEN CLASSIFICATION. A token is matched in full, never searched
inside. `find` would let a long line of prose containing a key-shaped
run report a key that is really half a URL.

LINE-AWARE. The description line ABOVE a key is carried with it,
verbatim. "key 7 of 21 is unpaid" is useless; "kalabhumi is unpaid" is
something a person can act on.

ORDER MATTERS INSIDE classify(). Anthropic is tested before the generic
OpenAI shape, because `sk-ant-…` also matches `sk-…`; Google before the
Spotify token, because both can start AQ. The order here is the order in
the Kotlin and it is not alphabetical by accident.

TWO DELIBERATE DIVERGENCES FROM THE ANDROID VERSION, both flagged rather
than done quietly:

1. THE RETIRED GOOGLE PREFIX IS NOT ACCEPTED HERE.
   KeyParser.kt matches `AQ.…` OR the older four-letter prefix.
   MANTRA_MANIFEST/modules/keyring.md is explicit that no tool, script
   or detector in this project looks for the old one — "not as a
   fallback, not as a second guess, not in a comment as an example" —
   because a detector that knows both keeps the dead form alive in
   everybody's memory and eventually matches the wrong thing. Google
   does not issue that format any more.

   So this port takes `AQ.` only. Key_Tester still accepts both; if that
   is wrong it should be changed THERE and pulled here, per the same
   module, rather than the two quietly disagreeing.

2. THE PROVIDER ID FOR GOOGLE IS "google", NOT "gemini".
   The Android app calls it gemini. Every id in this repository — the
   registry, the routes, SECRET_NAMES — says google, and an id that is
   nearly right is worse than one that is plainly wrong, because it
   resolves to None instead of raising.
"""

import re

# --- the shapes, in the order classify() tries them -------------------

HEX32 = re.compile(r"[0-9a-fA-F]{32}")
GOOGLE = re.compile(r"AQ\.[0-9A-Za-z._-]{20,}")
ANTHROPIC = re.compile(r"sk-ant-[0-9A-Za-z_-]{20,}")
OPENAI = re.compile(r"sk-(?!ant-)[0-9A-Za-z_-]{20,}")
GROQ = re.compile(r"gsk_[0-9A-Za-z_-]{20,}")
GITHUB = re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[0-9A-Za-z_]{20,})")
SK_UNDERSCORE = re.compile(r"sk_[0-9A-Za-z_-]{16,}")
SPOTIFY_TOKEN = re.compile(r"(BQ|AQ)[A-Za-z0-9_-]{80,}")
LOOSE = re.compile(r"[A-Za-z0-9._-]{24,220}")

# Everything that can sit between two tokens in a note, a JSON dump, a
# TOML block or a dashboard copy-paste.
SEP = re.compile(r"[\s,;:\"'=|\[\](){}<>]+")

# THE SPEECHIFY / ELEVENLABS SPLIT IS BY LENGTH AND NOTHING ELSE. Both
# are `sk_` with no other distinguishing mark, and 44 is where Speechify's
# sit. Measured, not guessed — and it is the one rule here that will age.
SK_SPEECHIFY_MIN = 44

# Providers this app actually holds secrets for. Anything else is still
# RECOGNISED — so a pasted note does not silently lose it — but it is
# reported rather than written into a secrets block for a provider that
# does not exist here.
KNOWN_HERE = ("google", "groq", "assemblyai", "speechify", "anthropic", "hume")


class Found:
    """One key, its provider, the words above it, and its other half."""

    __slots__ = ("key", "provider", "label", "secret")

    def __init__(self, key, provider, label="", secret=None):
        self.key = key
        self.provider = provider
        self.label = label or ""
        self.secret = secret

    @property
    def known_here(self) -> bool:
        return self.provider in KNOWN_HERE

    def __repr__(self):
        return "Found(%s, %r)" % (self.provider, self.label)


def classify(token: str):
    """Which provider this WHOLE token belongs to, or None.

    `fullmatch`, never `search`: a token is a key or it is not. Searching
    inside would take the tail of a tracking URL as a key, which is how a
    naive splitter once tried to authenticate with a Google `srsltid`.
    """
    if not token:
        return None
    if ANTHROPIC.fullmatch(token):
        return "anthropic"
    if GOOGLE.fullmatch(token):
        return "google"
    if GROQ.fullmatch(token):
        return "groq"
    if GITHUB.fullmatch(token):
        return "github"
    if SK_UNDERSCORE.fullmatch(token):
        return ("speechify" if len(token) >= SK_SPEECHIFY_MIN else "elevenlabs")
    if SPOTIFY_TOKEN.fullmatch(token):
        return "spotify"
    if OPENAI.fullmatch(token):
        return "openai"
    if HEX32.fullmatch(token):
        # THE AWKWARD ONE. Bare hex cannot be told from a commit hash or
        # a colour by shape alone — keyring.md §4 says so and says it is
        # honest to require context rather than guess. It is called
        # assemblyai here because that is the only 32-hex provider this
        # app holds, and the person can see the label and disagree.
        return "assemblyai"
    if (LOOSE.fullmatch(token)
            and any(c.isdigit() for c in token)
            and any(c.isalpha() for c in token)):
        return "unknown"
    return None


def _tokens(line: str):
    for raw in SEP.split(line or ""):
        tok = raw.strip().strip("._-")
        if tok:
            yield tok


def _line_has_key(line: str) -> bool:
    return any(classify(t) is not None for t in _tokens(line))


def _next_non_empty(lines, start: int) -> int:
    j = start
    while j < len(lines) and not lines[j].strip():
        j += 1
    return j


def extract(text: str):
    """Every key in a messy note. Returns [Found], first seen order.

    TWO PASSES, and the order between them is the whole reason this works.

    HUME EXPORTS A PAIR PER ACCOUNT:

        <account name>
        API key
        <api key>
        Secret key
        <secret key>

    Both halves are plain alphanumeric with no prefix, so SHAPE CANNOT
    TAG THEM — only the labels can. Hume's auth needs both (basic
    base64(key:secret) against oauth2-cc/token), so they are stored
    together and the account name is kept beside them.

    Pass 1 takes those pairs and marks both halves CONSUMED. Pass 2 then
    walks every token normally, skipping anything pass 1 took. Run the
    other way round, the generic pass would take twenty-one accounts as
    forty-two keys — half of them secrets that authenticate nothing, in
    a ring where every second key fails for no visible reason.
    """
    lines = (text or "").split("\n")
    out = {}
    consumed = set()

    # --- Pass 1: Hume account pairs -----------------------------------
    i = 0
    prev_non_empty = ""
    while i < len(lines):
        t = lines[i].strip()
        if t.lower() == "api key":
            account = prev_non_empty
            a = _next_non_empty(lines, i + 1)
            api_key = lines[a].strip() if a < len(lines) else ""
            k = a + 1
            while k < len(lines) and lines[k].strip().lower() != "secret key":
                k += 1
            s = _next_non_empty(lines, k + 1)
            secret = (lines[s].strip()
                      if k < len(lines) and s < len(lines) else "")
            if api_key and secret:
                if api_key not in out:
                    out[api_key] = Found(api_key, "hume", account, secret)
                consumed.add(api_key)
                consumed.add(secret)
                prev_non_empty = ""
                i = s + 1
                continue
        if t:
            prev_non_empty = t
        i += 1

    # --- Pass 2: ordinary single-token keys ---------------------------
    for idx, line in enumerate(lines):
        # THE LABEL IS THE LINE ABOVE, unless that line is itself a key.
        # A run of keys one per line would otherwise label each with the
        # one before it, which reads as though somebody named them.
        label = ""
        if idx > 0:
            prev = lines[idx - 1].strip()
            if prev and not _line_has_key(prev):
                label = prev
        for tok in _tokens(line):
            if tok == "DELETED" or tok in out or tok in consumed:
                continue
            pid = classify(tok)
            if pid is None:
                continue
            out[tok] = Found(tok, pid, label)
    return list(out.values())


def by_provider(found):
    """provider id -> [Found], preserving order. Small, but every caller
    wanted it and two of them wrote it slightly differently."""
    groups = {}
    for f in found:
        groups.setdefault(f.provider, []).append(f)
    return groups
