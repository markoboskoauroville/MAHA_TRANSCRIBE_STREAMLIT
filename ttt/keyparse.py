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
# THREE PROVIDERS NOW. Anything else is still RECOGNISED — so a pasted
# note does not silently lose it — but reported rather than written
# into a secrets block for a provider this app no longer has.
KNOWN_HERE = ("google", "groq")


# WHAT A LABELLED VALUE MUST LOOK LIKE TO BE A KEY AT ALL.
#
# MEASURED on Baba's own Hume export, 6.9.2026: a real Hume API key is
# 48 characters and a real secret is 64. FIVE of his twenty-one accounts
# carry a NINE-CHARACTER placeholder where the API key should be — the
# same nine characters in all five, because the dashboard did not print
# the key.
#
# The old parser took whatever line followed the "API key" label. So
# av.live.vmix was paired with a placeholder and answered 401 "Invalid
# ApiKey", which was read as A DEAD ACCOUNT and reported to Baba as one.
# The account may be perfectly healthy; the key was simply not in the
# file. The other four were dropped without a word, because they carried
# the SAME placeholder and the de-duplication treated them as one.
#
# So a labelled value is now checked before it is believed, and an
# account whose key is missing is REPORTED rather than guessed at.
MIN_LABELLED_LEN = 24


def looks_like_value(v: str) -> bool:
    """Could this line be a credential at all?

    Deliberately loose — providers differ and a new one will differ
    again — but long enough and plain enough to exclude a placeholder,
    a word, a date or "not shown".
    """
    v = (v or "").strip()
    if len(v) < MIN_LABELLED_LEN:
        return False
    if " " in v:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9._\-]+", v))


class Found:
    """One key, its provider, the words above it, and its other half.

    `problem` is set when something was recognised but is NOT USABLE —
    an account whose key is missing from the file, for instance. Such an
    entry is still returned, because "this account has no key here" is
    something a person must be told, and silently dropping it is how
    four accounts disappeared without a word.
    """

    __slots__ = ("key", "provider", "label", "secret", "problem")

    def __init__(self, key, provider, label="", secret=None, problem=""):
        self.key = key
        self.provider = provider
        self.label = label or ""
        self.secret = secret
        self.problem = problem or ""

    @property
    def usable(self) -> bool:
        return not self.problem

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


# WORDS THAT ARE NEVER SOMEBODY'S ACCOUNT NAME.
#
# Baba, 6.9.2026: "In the text I am adding some text which is not the
# key. Usually it's always the name of the account. For some keys I
# don't have account, for some I have. So he must understand to attach
# the name to the account which has like banner or title before it, and
# the one which doesn't just doesn't... The structure of the file can
# change any time."
#
# So a name is found BY ELIMINATION inside its block, never by counting
# lines — keyring.md 10d: "a block sometimes has a URL above the name,
# or a note under the key, and counting lines breaks on the first one
# that does."
#
# AND WHEN NOTHING IN THE BLOCK LOOKS LIKE A NAME, THE ANSWER IS NO
# NAME. An empty label is a fact. Borrowing the line above — which is
# what the first version did — eventually gives one key the name of the
# account before it, and a wrong name is worse than a blank one because
# a person acts on it.
NOT_A_NAME = {
    "api key", "secret key", "api", "key", "keys", "secret", "token",
    "deleted", "cancelled", "canceled", "expired", "revoked", "new",
    "old", "unused", "spent", "dead", "n/a", "na", "none", "null",
    "-", "--", "---", "*", "x",
}

_URLISH = re.compile(r"(https?://|www\.|\S+@\S+\.\S+)", re.I)
_DATEISH = re.compile(r"^\d{1,4}[./-]\d{1,2}[./-]\d{1,4}\.?$")
NAME_MAX = 60


def looks_like_name(line: str) -> bool:
    """Could this line be what somebody called an account?"""
    t = (line or "").strip()
    if not t or len(t) > NAME_MAX:
        return False
    if t.lower() in NOT_A_NAME:
        return False
    if t.startswith("#") or t.startswith("//"):
        return False
    if _URLISH.search(t) or _DATEISH.match(t):
        return False
    if _is_assignmentish(t):
        return False
    if classify(t) is not None:
        return False              # it is a key, not a name
    # A NAME HAS A LETTER IN IT. A bare number, a row of dashes or a
    # stray punctuation line is separator furniture, not a title.
    return any(c.isalpha() for c in t)


def _blocks(text):
    """The file split on blank lines, each a list of stripped lines.

    A file with NO blank lines is ONE block, and everything below still
    works on it: the name is then found by looking upward from each key
    rather than across the whole block.
    """
    out = []
    for chunk in re.split(r"\n\s*\n", text or ""):
        lines = [ln.strip() for ln in chunk.split("\n") if ln.strip()]
        if lines:
            out.append(lines)
    return out


def _name_for(block, key_index, used):
    """The account name for the key at `key_index` in this block.

    NEAREST NAME-LIKE LINE ABOVE, WITHIN THE BLOCK, NOT ALREADY SPOKEN
    FOR. Upward rather than "the block's first line", so a block holding
    two named keys gives each its own name. Stopping at the block edge
    and at any other key means a key with nothing above it gets NOTHING
    rather than the previous account's name.
    """
    for i in range(key_index - 1, -1, -1):
        if i in used:
            break                      # another key owns everything above
        if classify(block[i]) is not None:
            break                      # a key: the boundary between two
        if looks_like_name(block[i]):
            used.add(i)
            return block[i]
    # NOTHING ABOVE. Some exports put the name under the value, so look
    # down — still inside the block, still stopping at the next key.
    for i in range(key_index + 1, len(block)):
        if classify(block[i]) is not None:
            break
        if i not in used and looks_like_name(block[i]):
            used.add(i)
            return block[i]
    return ""


# AN ASSIGNMENT LINE IS NEVER A NAME.
#
# FOUND BY A CLAUDE CODE SESSION ON 6.9.2026, and it had already
# happened: running the v246 tool over a previous secrets.toml printed
# the first characters of SHEETS_TOKEN's VALUE on screen, as the "label"
# of the token beneath it. `SHEETS_TOKEN = "abcde…"` is 52 characters,
# has letters, is not a URL and is not a date, so every rule in
# looks_like_name said yes.
#
# The label is shown in the key tester panel and printed by the report,
# so a name that contains a value puts a credential on a screen. A name
# is a NAME: it does not assign, and it does not contain a long run of
# key-shaped characters.
_ASSIGNMENT = re.compile(r"^\s*[\w.\[\]-]+\s*[:=]\s*\S")
_LONGRUN = re.compile(r"[A-Za-z0-9_.\-]{20,}")


def _is_assignmentish(t: str) -> bool:
    return bool(_ASSIGNMENT.match(t)) or bool(_LONGRUN.search(t))


# READING BACK WHAT WE OURSELVES WROTE.
#
# THE ROUND TRIP WAS BROKEN AND NOBODY HAD TRIED IT. keys_to_toml.py
# writes Hume accounts as TOML tables:
#
#     [[HUME_ACCOUNTS]]
#     name   = "kalabhumi"
#     key    = "..."
#     secret = "..."
#
# and extract() could not read that back — 21 blocks in, ZERO pairs out.
# The parser was written for the dashboard export and only ever tested
# against it, so the one file this project GENERATES was the one shape
# it could not parse. A session running the tool over last time's
# secrets.toml found every Hume account missing.
#
# The lesson is older than this bug: a format you emit is a format you
# must be able to read, and the test for that is a round trip.
_TOML_TABLE = re.compile(r"^\[\[?\s*([A-Za-z_][\w.]*)\s*\]\]?$")
_TOML_ASSIGN = re.compile(r'^\s*([A-Za-z_][\w.-]*)\s*=\s*"([^"]*)"\s*,?\s*$')


def _toml_table(block, out, consumed, problems):
    """A `[[HUME_ACCOUNTS]]` table, or any block of `field = "value"`
    lines carrying a key and a secret. Returns True if it claimed it.

    Only the FIELD NAMES are trusted here, exactly as the labelled
    export is trusted: a Hume key and secret are plain alphanumeric and
    shape can never tag them.
    """
    fields = {}
    header = ""
    for line in block:
        m = _TOML_TABLE.match(line)
        if m:
            header = m.group(1).lower()
            continue
        m = _TOML_ASSIGN.match(line)
        if m:
            fields.setdefault(m.group(1).lower(), m.group(2))
    if "key" not in fields:
        return False
    if header and "hume" not in header:
        return False
    # A HUME TABLE MISSING ITS SECRET IS CLAIMED ANYWAY, so that the
    # account is REPORTED BY NAME rather than falling through to the
    # generic pass, where its key becomes an anonymous token and the
    # account it belongs to is never mentioned. Mutation testing found
    # this: requiring both fields looked safer and quietly lost the
    # more useful answer.
    if "secret" not in fields and "hume" not in header:
        return False
    api, sec = fields.get("key", ""), fields.get("secret", "")
    name = fields.get("name", "")
    if not looks_like_value(api):
        problems.append(Found("", "hume", name,
                              problem="the API key is missing from the file "
                                      "(%d characters where a key should be)"
                                      % len(api)))
        if sec:
            consumed.add(sec)
        return True
    if not looks_like_value(sec):
        problems.append(Found(api, "hume", name,
                              problem="the secret key is missing from the file"))
        consumed.add(api)
        return True
    out.setdefault((api, sec), Found(api, "hume", name, sec))
    consumed.add(api)
    consumed.add(sec)
    return True


def _hume_pairs(block, out, consumed, problems):
    """Pairs read from the LABELS, with the values CHECKED.

    Both halves are plain alphanumeric, so shape cannot tag them and
    only the labels can. But a LABEL DOES NOT MAKE THE LINE BENEATH IT A
    KEY: five of Baba's twenty-one accounts carry a nine-character
    placeholder where the API key should be, and taking it produced a
    401 that was read as a dead account and reported to him as one.
    """
    lower = [ln.lower() for ln in block]
    # BOTH LABELS, OR THIS IS NOT A HUME BLOCK. A block holding only the
    # words "API key" above an ordinary AQ. key is somebody labelling
    # their Google key, and claiming it here swallowed it entirely —
    # the generic pass never ran and the key vanished.
    if "api key" not in lower or "secret key" not in lower:
        return False

    def index_after(label):
        return lower.index(label) + 1 if label in lower else -1

    ai, si = index_after("api key"), index_after("secret key")
    api = block[ai] if 0 <= ai < len(block) else ""
    sec = block[si] if 0 <= si < len(block) else ""

    # THE VALUES ARE NOT NAME CANDIDATES. A Hume api key is 48 plain
    # letters and digits, which is under NAME_MAX and has letters in it —
    # so without excluding it BY POSITION, a pair with no account name
    # took its own api key as its name and put a credential on screen
    # wherever that label is shown.
    name = ""
    for idx, line in enumerate(block):
        if idx in (ai, si):
            continue
        if looks_like_name(line):
            name = line
            break
    if not looks_like_value(api):
        # THE ACCOUNT IS REPORTED, NOT DROPPED. It is named in the file
        # and a person needs to know that its key is not.
        problems.append(Found("", "hume", name,
                              problem="the API key is missing from the file "
                                      "(%d characters where a key should be)"
                                      % len(api)))
        if sec:
            consumed.add(sec)
        return True
    if not looks_like_value(sec):
        problems.append(Found(api, "hume", name,
                              problem="the secret key is missing from the file"))
        consumed.add(api)
        return True
    # KEYED BY THE PAIR, NOT BY THE API KEY ALONE. Keying on the api key
    # meant five accounts sharing one placeholder collapsed into one and
    # FOUR VANISHED WITHOUT A WORD.
    out.setdefault((api, sec), Found(api, "hume", name, sec))
    consumed.add(api)
    consumed.add(sec)
    return True


def extract(text: str):
    """Every key in a messy note. Returns [Found], first seen order.

    BLOCK BY BLOCK, because that is the only structure these files
    reliably have, and the structure inside a block changes without
    warning. Inside a block, keys are found by SHAPE and names by
    ELIMINATION.

    Hume is done first, per block, because its two halves are plain
    alphanumeric and only the labels can tag them; whatever it takes is
    marked consumed so the generic pass cannot report the same secret
    again as a loose key of its own.

    Entries carrying a `problem` come LAST and have `usable` False. They
    are returned rather than dropped because "this account has no key in
    the file" is the most useful thing the parser can say about it.
    """
    out = {}
    consumed = set()
    problems = []
    for block in _blocks(text):
        # OUR OWN OUTPUT FIRST. A previous secrets.toml is the file most
        # likely to be in that folder, and it was the one shape this
        # parser could not read.
        if _toml_table(block, out, consumed, problems):
            continue
        if _hume_pairs(block, out, consumed, problems):
            continue
        used = set()
        # WHOLE LINES FIRST, so a key on its own line can claim the name
        # above it before any token-splitting happens.
        for idx, line in enumerate(block):
            if line in consumed or line == "DELETED":
                continue
            pid = classify(line)
            if pid is None:
                continue
            used.add(idx)
            out.setdefault(line, Found(line, pid, _name_for(block, idx, used)))
        # THEN TOKENS INSIDE LINES — a TOML list, a JSON blob, a
        # comma-separated paste. These get NO name: nothing in the file
        # says which of several tokens on one line a title belongs to,
        # and guessing would put a real account's name on a stranger.
        for line in block:
            if classify(line) is not None:
                continue
            for tok in _tokens(line):
                if tok == "DELETED" or tok in out or tok in consumed:
                    continue
                pid = classify(tok)
                if pid is not None:
                    out.setdefault(tok, Found(tok, pid, ""))
    return list(out.values()) + problems


def by_provider(found):
    """provider id -> [Found], preserving order. Small, but every caller
    wanted it and two of them wrote it slightly differently."""
    groups = {}
    for f in found:
        groups.setdefault(f.provider, []).append(f)
    return groups
