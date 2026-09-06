"""GOOGLE GEMINI — reading what an answer means.

Every rule here comes from `MANTRA_MANIFEST/modules/gemini-speech.md` and
`docs/GOOGLE_ENGINE.md`, both written from measurements against the live
API rather than from a documentation page. Where this file departs from
either, it says so and why.

WHY FIVE WORDS AND NOT FOUR. The rest of the app classifies a failure as
dead, cool or soft. Google needs one more, and the reason is a person
rather than a protocol:

    working    it did the work
    busy       throttled. Next key. NEVER delete. Costs nothing.
    no credit  a real key on a live account with no money. Its own word.
    refused    401/403/bad key: revoked, mistyped. Delete removes THIS.
    unknown    5xx, 404, no network. Says nothing about the key at all.

`no credit` exists so that somebody with an empty balance is told to top
it up rather than told their key is broken. Collapsing it into `refused`
has people delete live accounts, which is not a hypothetical: it has
already happened once.

THE TRAP, AND IT HAS COST A LIVE KEY. Google answers a spent account and
an impatient one with the SAME STATUS and the SAME WORD. Matching on
"quota" alone reads an empty account as a throttle and retries a wall for
ever, or reads a throttle as an empty account and buries a good key.

A CONTRADICTION IN THE TWO SOURCES, RESOLVED HERE.

    the arrow list says   retry hint -> cool, checked FIRST
    the prose says        an empty prepaid balance answers 429, so
                          "check for it BEFORE the rate-limit branch"

Both cannot be literally true. Google attaches RetryInfo to nearly every
429, so "hint first" taken literally makes `no credit` UNREACHABLE — and
the doc gives it its own verdict precisely so it can be reached.

The reading that satisfies both, and the one implemented:

    an AMBIGUOUS quota refusal, with a retry hint  ->  busy
    an UNAMBIGUOUS money word                      ->  no credit,
                                                       hint or not

"Quota exceeded" is the ordinary throttle wording and is never money.
"Balance depleted" is not ambiguous, and no delay will fix it.

MEASURED against Baba's own keys on 5.9.2026:

    a mangled key      401 UNAUTHENTICATED, ACCESS_TOKEN_TYPE_UNSUPPORTED
    a wrong-shaped key 400 API_KEY_INVALID
    a retired model    404 "no longer available"
    LLM                200 on gemini-3.6-flash
    TTS                200, audio/L16;codec=pcm;rate=24000, NO RIFF header

AND THE KEYS BEGIN "AQ." — that is the only format Google issues now.
An extraction written for the retired prefix sliced three characters off
every key and made all twenty-one look invalid. The retired prefix is
not written down anywhere in this file, deliberately: keyring.md says no
detector in this project looks for it, "not as a fallback, not as a
second guess, not in a comment as an example", because a comment holding
it keeps the dead form alive in everybody's memory. The loader must not
assume a shape.
"""

import json
import re

# ---- the five words --------------------------------------------------

# WHERE THE NEXT CALL BEGINS ITS WALK. Module level and locked, so
# parallel workers in one reading genuinely get different accounts.
import threading as _threading
_START = [0]
_START_LOCK = _threading.Lock()

WORKING = "working"
BUSY = "busy"
NO_CREDIT = "no credit"
REFUSED = "refused"
UNKNOWN = "unknown"

VERDICTS = (WORKING, BUSY, NO_CREDIT, REFUSED, UNKNOWN)

# ---- what the words are made of --------------------------------------

# A RETRY HINT. Any of these and Google is asking us to wait, which means
# the key is fine.
RETRY_MARKS = ("retrydelay", "retry-after", "retryinfo", "quotafailure",
               "per minute", "try again in", "resource_exhausted")

# MONEY, AND ONLY UNAMBIGUOUS MONEY. "quota" is deliberately NOT here: it
# is the ordinary throttle wording and putting it in this list is exactly
# the mistake that cost a key.
MONEY_MARKS = ("credit", "balance", "depleted", "insufficient",
               "billing", "payment", "prepayment")

# A KEY GOOGLE WILL NOT ACCEPT. It answers 400 for a wrong-shaped key,
# not 401 — so a classifier that only buries 401/403 leaves a dead key in
# the ring, and a dead key that STOPS the ring is the worst failure of
# all.
BAD_KEY_MARKS = ("api_key_invalid", "api key not valid",
                 "api key expired", "invalid api key")


def _body(raw) -> str:
    """The answer as lowercase text, whatever shape it arrived in."""
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8", "replace")
        except Exception:                                    # noqa: BLE001
            return ""
    if isinstance(raw, (dict, list)):
        try:
            raw = json.dumps(raw)
        except Exception:                                    # noqa: BLE001
            return ""
    return str(raw).lower()


def _error(raw):
    """The `error` object, or {} — never an exception.

    Junk arrives. An HTML 502 from a proxy is not JSON and must not be
    the reason a reading crashes.
    """
    if isinstance(raw, dict):
        d = raw
    else:
        try:
            d = json.loads(raw or "")
        except Exception:                                    # noqa: BLE001
            return {}
    if not isinstance(d, dict):
        return {}
    err = d.get("error")
    return err if isinstance(err, dict) else {}


def verdict(status: int, raw=None) -> str:
    """One of the five words. Never raises.

    THE ORDER IS THE WHOLE POINT and it is not the order either source
    lists, for the reason set out in this module's docstring.
    """
    low = _body(raw)

    # 1. MONEY FIRST, and only unambiguous money. An empty balance
    #    arrives as 429 with a retryDelay attached, so anything that
    #    checks the hint first can never reach this line.
    if any(m in low for m in MONEY_MARKS):
        return NO_CREDIT

    # 2. A KEY GOOGLE WILL NOT ACCEPT, whatever status it wore. This is
    #    the 400 API_KEY_INVALID case measured on 5.9.2026: soft would
    #    have stopped the ring on a genuinely dead key.
    if any(m in low for m in BAD_KEY_MARKS):
        return REFUSED

    if status in (401, 403):
        return REFUSED

    # 3. THROTTLED. After money, so a wall is never read as a wait.
    if status == 429 or any(m in low for m in RETRY_MARKS):
        return BUSY

    if status == 200:
        return WORKING

    # 4. EVERYTHING ELSE SAYS NOTHING ABOUT THE KEY. 5xx is theirs, 404
    #    is a model name of ours gone stale, 0 is no network. None of
    #    them is evidence to bury an account on.
    return UNKNOWN


def deletable(v: str) -> bool:
    """Only one of the five words is an instruction to remove something.

    Written as a function rather than left to each caller's judgement,
    because the harm this module exists to prevent is somebody deleting
    a live account, and that decision should be made in exactly one
    place.
    """
    return v == REFUSED


# ---- reading the limit out of the refusal -----------------------------
#
# "Parse the JSON, not the message string: a regex that expects a space
#  after the colon works against Google's pretty-printed output and
#  silently reads every daily wall as a minute limit."
#
# An earlier version elsewhere did exactly that, and a key was retried
# all day against a wall it had already hit. So the quotaId is read from
# the structure and the message text is never consulted.

_DAY = re.compile(r"perday", re.I)
_MIN = re.compile(r"perminute", re.I)


def _violations(raw):
    for d in (_error(raw).get("details") or []):
        if not isinstance(d, dict):
            continue
        if "QuotaFailure" in str(d.get("@type", "")):
            for v in (d.get("violations") or []):
                if isinstance(v, dict):
                    yield v


def limit_kind(raw):
    """'day', 'minute', or None. From the quotaId, never the message."""
    for v in _violations(raw):
        qid = str(v.get("quotaId") or "")
        if _DAY.search(qid):
            return "day"
        if _MIN.search(qid):
            return "minute"
    return None


def limit_value(raw):
    """The number Google just stated, so the ledger can learn it.

    The point of reading this is that the published tables disagree with
    each other and with the API. A 429 states the limit it just enforced,
    and that is the only figure worth believing.
    """
    for v in _violations(raw):
        try:
            return int(str(v.get("quotaValue")).strip())
        except (TypeError, ValueError):
            continue
    return None


def retry_after(raw):
    """Seconds Google asked us to wait, or None.

    None means "nothing was said", so the caller may apply its own
    default — it does not mean zero. A key rested for a number we chose
    rather than the one we were given is the fault recorded in
    quota-and-fallback.md.
    """
    for d in (_error(raw).get("details") or []):
        if not isinstance(d, dict):
            continue
        if "RetryInfo" in str(d.get("@type", "")):
            m = re.match(r"([\d.]+)s?$", str(d.get("retryDelay") or "").strip())
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    return None
    return None


# ---- THE THIRTY VOICES ----------------------------------------------
#
# GENDER IS PUBLISHED AFTER ALL, AND THIS FILE SAID IT WAS NOT.
#
# The claim came from the AI Studio page, which lists an adjective and
# nothing else. Google Cloud's OWN Gemini-TTS documentation carries a
# full table — name, gender, and an audio demo for each of the thirty:
#
#     https://docs.cloud.google.com/text-to-speech/docs/gemini-tts
#
# So the gender below is DATA, read off Google's table on 6.9.2026, and
# not a guess made from how a name sounds. The old rule — "do not
# synthesise those facets" — stands unchanged and is the reason this
# was checked against Google rather than filled in by ear: fourteen
# female, sixteen male, and every one of them theirs.
#
# The ADJECTIVES are still docs-only and there is still no /voices
# endpoint (404, measured). Where Google gives nothing, the entry stays
# empty: a blank is a fact and a guess is not.
#
# That rule is the whole of this table. Hume's cast carries an accent and
# an age because Hume publishes them; Google publishes an adjective and
# nothing else, and inventing the rest would put a filter on screen that
# looks like Hume's and is made up. Somebody would cast from it.
#
# THE NAMES ARE MEASURED. They are the thirty in GOOGLE_TTS_STT's
# src/10_app.py, which was built against the live API — not retyped from
# a documentation page. Verified 5.9.2026: all thirty present.
#
# THE ADJECTIVES ARE GOOGLE'S OWN, from their TTS voice table. There is
# NO API THAT PUBLISHES THEM — checked on 5.9.2026: there is no /voices
# endpoint (404) and the model record carries no voice list. So they are
# data here, and where Google gives none the entry is EMPTY rather than
# filled with something plausible.
VOICES = (
    ("Zephyr", "Bright", "F"),
    ("Puck", "Upbeat", "M"),
    ("Charon", "Informative", "M"),
    ("Kore", "Firm", "F"),
    ("Fenrir", "Excitable", "M"),
    ("Leda", "Youthful", "F"),
    ("Orus", "Firm", "M"),
    ("Aoede", "Breezy", "F"),
    ("Callirrhoe", "Easy-going", "F"),
    ("Autonoe", "Bright", "F"),
    ("Enceladus", "Breathy", "M"),
    ("Iapetus", "Clear", "M"),
    ("Umbriel", "Easy-going", "M"),
    ("Algieba", "Smooth", "M"),
    ("Despina", "Smooth", "F"),
    ("Erinome", "Clear", "F"),
    ("Algenib", "Gravelly", "M"),
    ("Rasalgethi", "Informative", "M"),
    ("Laomedeia", "Upbeat", "F"),
    ("Achernar", "Soft", "F"),
    ("Alnilam", "Firm", "M"),
    ("Schedar", "Even", "M"),
    ("Gacrux", "Mature", "F"),
    ("Pulcherrima", "Forward", "F"),
    ("Achird", "Friendly", "M"),
    ("Zubenelgenubi", "Casual", "M"),
    ("Vindemiatrix", "Gentle", "F"),
    ("Sadachbia", "Lively", "M"),
    ("Sadaltager", "Knowledgeable", "M"),
    ("Sulafat", "Warm", "F"),
)

DEFAULT_VOICE = "Kore"


def voice_names() -> tuple:
    return tuple(n for n, _t, _g in VOICES)


# HOW OFTEN GOOGLE ITSELF REACHES FOR A VOICE.
#
# Baba asked for the voices ordered by popularity with the best at the
# top. Google publishes no popularity and no premium tier — all thirty
# cost the same — so inventing a ranking would be exactly the guess this
# module refuses to make elsewhere.
#
# What IS observable: which voices Google uses in its own documentation
# examples. Counted from the Gemini-TTS page on 6.9.2026 — Kore appears
# in nearly every sample, then Charon and Puck, then Callirrhoe, Aoede,
# Leda, Algieba, Achernar. That is a real signal about which voices
# their own writers consider representative, and it is stated as what it
# is rather than dressed up as popularity.
#
# Everything not in this list keeps Google's own table order behind it.
DOC_FAVOURITES = ("Kore", "Charon", "Puck", "Callirrhoe", "Aoede", "Leda",
                  "Algieba", "Achernar")


def gender_of(name: str) -> str:
    """"F", "M", or "" — from Google's table, never from the name."""
    for n, _tone, g in VOICES:
        if n == name:
            return g
    return ""


def top_voices(gender: str, limit: int = 10):
    """The best `limit` voices of one gender, best first.

    TEN IS THE CAP, and it is his: "I want just ten voices, none more
    than ten." Thirty names in a dropdown is a list nobody reads to the
    end of, and the ones past ten were never going to be chosen.
    """
    want = (gender or "").upper()[:1]
    pool = [(n, t) for n, t, g in VOICES if not want or g == want]
    order = {n: i for i, n in enumerate(DOC_FAVOURITES)}
    pool.sort(key=lambda nt: (order.get(nt[0], len(DOC_FAVOURITES)),))
    return pool[:max(0, int(limit))]


def tone_of(name: str) -> str:
    """Google's own adjective, or "" — never a guess.

    An empty answer is the honest one for a voice Google says nothing
    about. The caller shows a blank; it does not fill one in.
    """
    for n, tone, _g in VOICES:
        if n == name:
            return tone
    return ""


def tones() -> tuple:
    """Every adjective actually present, for a filter built from the data.

    Built from the table rather than written beside it, so a voice added
    with a new adjective cannot end up unfilterable.
    """
    return tuple(sorted({t for _n, t, _g in VOICES if t}))


# =====================================================================
#  THE PROVIDER
# =====================================================================
#
# Everything above this line is verdicts and data, and it was written and
# tested before any of it had a caller. This is the body around it.
#
# WHY THIS FILE DOES NOT USE base.http_json FOR THE WORK CALLS.
#
# `http_json` hands its `classify` hook the STATUS AND NOTHING ELSE:
#
#     kind = classify(e.code) if classify else "soft"
#
# For every other provider here that is enough. For Google it destroys
# the one distinction this module exists to make. A spent account and an
# impatient one BOTH answer 429, and only the body separates them —
# keyring.md §2e: "match on WORDS rather than on the code, because the
# code is the thing providers disagree about." Classified on 429 alone,
# an empty balance is rested for sixty seconds, for ever, and a person is
# never told the thing they need to know, which is that no amount of
# waiting will help.
#
# So the work calls go through `_post` below, which keeps the raw body
# and asks `verdict()`. `test_key` is the same call. Nothing here
# re-implements the verdict logic; it only makes the body reach it.

import base64
import struct
import urllib.error
import urllib.request

from .base import Model, Provider, USER_AGENT, Voice

API = "https://generativelanguage.googleapis.com/v1beta"

# THE MODEL CHAINS ARE MEASURED, NOT CHOSEN. gemini-speech.md §5a, from
# calls made on 5.9.2026. Order matters: the first is the cheapest that
# does the job, and the fallbacks exist because a model is retired
# without notice — gemini-2.0-flash and the whole 2.5 family answer 404
# today and were current in the spring.
TTS_MODELS = ("gemini-2.5-flash-preview-tts", "gemini-3.1-flash-tts-preview")
STT_MODELS = ("gemini-3.1-flash-lite", "gemini-3.6-flash", "gemini-3.5-flash")
LLM_MODELS = ("gemini-3.1-flash-lite", "gemini-3.6-flash", "gemini-3.5-flash")

# TEN A DAY, PER ACCOUNT, PER MODEL. gemini-speech.md §1. This is not
# trivia and it is not an optimisation target: it is the number that
# decides how the reader plans a reading. See `metered_by_call`.
TTS_PER_DAY = 10

# HOW MANY SLOW FAILURES BEFORE GIVING UP ON A SENTENCE, and how long
# one call may hang. Both measured 6.9.2026: a working call is 17s, a
# 503 is 67s. A 120-second timeout across 21 keys is 42 minutes of
# "Making part 1 of 3…", which is what a person reads as a freeze.
# TIGHTENED AGAIN AFTER HE SAW IT STILL SPINNING. 4 x 45s is three
# minutes on one sentence, and three minutes of "Making part 1 of 3…"
# is indistinguishable from a freeze. 2 x 25s is fifty seconds worst
# case, and a working call measured 17s — so a healthy key still fits
# comfortably inside one try.
SOFT_TRIES = 2
TTS_TIMEOUT = 25

# Raw PCM, 24 kHz, mono, 16-bit — and NO RIFF HEADER, which nothing warns
# you about. Measured: audio/L16;codec=pcm;rate=24000.
PCM_RATE = 24000
PCM_CHANNELS = 1
PCM_BYTES_PER_SAMPLE = 2

# Gemini takes wav, mp3, flac, ogg, aac and aiff as inlineData. It does
# NOT take webm, which is exactly what a browser recorder produces, so
# the refusal is stated here rather than discovered as a 400 that reads
# like a bad key.
AUDIO_MIME = {
    ".wav": "audio/wav", ".mp3": "audio/mp3", ".flac": "audio/flac",
    ".ogg": "audio/ogg", ".aac": "audio/aac", ".aiff": "audio/aiff",
    ".aif": "audio/aiff", ".m4a": "audio/aac",
}


def wav_header(pcm_len: int, rate: int = PCM_RATE,
               channels: int = PCM_CHANNELS,
               width: int = PCM_BYTES_PER_SAMPLE) -> bytes:
    """The 44 bytes Google does not send.

    Without this the bytes are perfectly good audio that no browser and
    no player will open, and the failure looks like a broken voice rather
    than a missing header.
    """
    byte_rate = rate * channels * width
    return (b"RIFF" + struct.pack("<I", 36 + pcm_len) + b"WAVE"
            + b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, rate,
                                    byte_rate, channels * width, width * 8)
            + b"data" + struct.pack("<I", pcm_len))


def to_wav(pcm: bytes) -> bytes:
    return wav_header(len(pcm)) + pcm


def pcm_seconds(pcm: bytes) -> float:
    return len(pcm) / float(PCM_RATE * PCM_CHANNELS * PCM_BYTES_PER_SAMPLE)


def _post(path: str, key: str, payload: dict, timeout: int = 120):
    """One call. Returns (data, error_text, ring_kind, raw_body).

    `raw_body` is kept because it is the only thing that separates an
    empty account from a busy one, and the ring kind is derived from the
    five words rather than from the status.
    """
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API + path, data=body, method="POST",
        headers={"x-goog-api-key": key, "Content-Type": "application/json",
                 "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = r.read().decode("utf-8", "replace")
        return (json.loads(text) if text.strip() else {}), None, None, text
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode("utf-8", "replace")
        except Exception:                                    # noqa: BLE001
            text = ""
        v = verdict(e.code, text)
        return None, _explain(v, e.code, text), ring_kind(v), text
    except Exception as e:                                   # noqa: BLE001
        # No network says nothing about the key. Never dead.
        return None, "Could not reach Google: %s" % e, "soft", ""


# THE FIVE WORDS, TRANSLATED FOR A RING THAT KNOWS THREE.
#
# The rest of the app's rings speak dead / cool / soft. Collapsing five
# into three loses information, so the loss is made deliberate and
# written down rather than left to each call site:
#
#     working    -> None   nothing to do
#     busy       -> cool   rest it. NEVER dead.
#     no credit  -> dead   condemned, because credit does not come back
#                          in sixty seconds and resting it spins against
#                          a wall all day. The WORD survives in the error
#                          text so a person is told to top up rather than
#                          told the key is broken.
#     refused    -> dead   this is what delete removes
#     unknown    -> soft   says nothing about the key
_RING_KIND = {WORKING: None, BUSY: "cool", NO_CREDIT: "dead",
              REFUSED: "dead", UNKNOWN: "soft"}


def ring_kind(v: str):
    return _RING_KIND.get(v, "soft")


def _explain(v: str, status: int, raw) -> str:
    """A sentence naming what a person should DO, not what HTTP said."""
    if v == NO_CREDIT:
        return ("This Google account has no credit left. Waiting will not "
                "help — it needs topping up.")
    if v == BUSY:
        kind = limit_kind(raw)
        if kind == "day":
            got = limit_value(raw)
            return ("This Google account has used its allowance for today"
                    + (" (%d)." % got if got else ".")
                    + " It resets at midnight Pacific, 09:00 in Zagreb.")
        wait = retry_after(raw)
        return ("This Google account is busy"
                + (" — try again in %gs." % wait if wait else " this minute."))
    if v == REFUSED:
        return "Google rejected this key (%d)." % status
    return "Google could not answer (%d)." % status


class Google(Provider):
    """Gemini: all three capabilities on one key.

    Baba, 5.9.2026: *"We have Edge/Groq or Google because the Google
    option second can do everything through API keys. We can do TTS, STT,
    and we can do translations as well."*
    """

    id = "google"
    label = "Google Gemini"
    capabilities = ("stt", "tts", "llm")
    needs_key = True

    # "AQ." AND NOTHING ELSE. The retired prefix is not named here, and
    # writing this comment is where I learned the rule has teeth: my
    # first draft quoted the dead form as an example of the form not to
    # quote. test_google_provider.py greps this file WITHOUT stripping
    # comments, on purpose, and it went red.
    key_prefixes = ("AQ.",)

    # THE FACT THAT DECIDES HOW THE READER PLANS.
    #
    # Edge is free and local: a hundred sentences is a hundred calls and
    # costs nothing. Google's free tier is TEN TTS REQUESTS PER ACCOUNT
    # PER DAY, so a hundred sentences is ten accounts spent on one
    # paragraph. Anything choosing how to cut a reading into requests
    # must be able to ask which of those two worlds it is in — WITHOUT
    # naming a vendor, per §0 rule 2.
    metered_by_call = True
    calls_per_day = TTS_PER_DAY

    def __init__(self, keys=None, ring=None):
        self.keys = list(keys or [])
        self.ring = ring
        self.active_key = 0

    def _rotate(self, attempt):
        """Same contract as Groq._rotate: run `attempt(key)` down the ring
        until one works, and stop early on an error no key can fix."""
        if self.ring is not None:
            from .. import keyring
            return keyring.rotate(self.ring, attempt)
        # EVERY CALL STARTS AT A DIFFERENT KEY.
        #
        # Measured 6.9.2026, and it is the difference between a reading
        # that starts in seconds and one that does not start at all.
        # Three sentences are prefetched IN PARALLEL, and every worker
        # used to begin at key 1 — so all three queued behind the same
        # account, walked the same dead ones in lockstep, and shared one
        # account's three-per-minute wall.
        #
        # Several of the twenty-one accounts are out of credit and answer
        # in 0.1s, so walking them is cheap; what is NOT cheap is three
        # workers waiting on the same slow account at once. Starting each
        # call one further along spreads them across the ring.
        #
        # NOT keyring.md's "sort by budget remaining" — that answers a
        # different question, spending evenly across a DAY. This is about
        # not colliding within a SECOND, and the two do not conflict:
        # this only chooses where to begin.
        with _START_LOCK:
            _START[0] = (_START[0] + 1) % max(1, len(self.keys))
            begin = _START[0]
        order = self.keys[begin:] + self.keys[:begin]
        # A CAP, OR THE RING BECOMES THE HANG.
        #
        # v257 made an unknown rotate instead of stopping, which was
        # right: one 503 used to kill a sentence with twenty untried
        # keys behind it. What I did not do is bound it — and the
        # measured numbers make that fatal. A 503 costs up to 67s and
        # the timeout was 120s, so one sentence could walk 21 keys and
        # sit there for the better part of an hour, showing "Making part
        # 1 of 3…" and never finishing. Baba: "Just in loop and nothing
        # is happening."
        #
        # FOUR IS ENOUGH TO SURVIVE A BAD KEY AND SHORT ENOUGH TO FAIL
        # LOUDLY. Spent accounts answer in 0.1s and do not count against
        # it — only calls that actually cost TIME do, so a ring full of
        # empty accounts still walks straight past them to a working one.
        tried_slow = 0
        last = "no keys"
        for n, key in enumerate(order, 1):
            i = ((begin + n - 1) % len(self.keys)) + 1
            result, err, kind = attempt(key)
            if not err:
                # THE POSITION OF THE KEY THAT ACTUALLY WORKED, for the
                # status line. Recorded on success only: a key that was
                # tried and refused is not the key in use.
                self.active_key = i
                return result, None
            last = err
            # A 503 IS NOT A REASON TO GIVE UP ON THE WHOLE SENTENCE.
            #
            # This stopped on anything that was not dead or cool, which
            # meant one `unknown` ended the reading — and Google hands
            # out 503s freely: measured 6.9.2026, a single 503 cost 67
            # SECONDS and then killed the sentence with twenty untried
            # keys sitting behind it.
            #
            # gemini-speech.md §5b: unknown "says nothing about the key,
            # try again". So it rotates like the others. Only a REFUSAL
            # of the request itself — a bad model name, a malformed body
            # — is worth stopping for, and that arrives as a 400, which
            # verdict() reads as refused and buries the key rather than
            # returning soft.
            if kind is None:
                return None, err
            # ONLY A SLOW FAILURE COUNTS. A dead or spent key answers
            # instantly, so walking a hundred of them is free; what must
            # be bounded is waiting.
            if kind == "soft":
                tried_slow += 1
                if tried_slow >= SOFT_TRIES:
                    return None, ("Google did not answer after %d tries. "
                                  "%s" % (tried_slow, err))
        return None, "All Google keys failed. Last: %s" % last

    # ---- key testing -------------------------------------------------
    def test_key(self, key: str):
        """A REAL PIECE OF WORK, never a listing.

        keyring.md §2c, measured across six providers: a spent Gemini key
        answers 200 to GET /models and 429 to anything real. Both answers
        are honest; they answer different questions. Testing with a list
        showed GREEN, the ring handed the key out, the real call failed,
        and the account was condemned as broken when it was merely empty.

        So: the smallest billable thing Google sells. One token.
        """
        model = LLM_MODELS[0]
        _, err, kind, _ = _post(
            "/models/%s:generateContent" % model, key,
            {"contents": [{"parts": [{"text": "hi"}]}],
             "generationConfig": {"maxOutputTokens": 1}}, timeout=30)
        return err, kind

    # ---- models ------------------------------------------------------
    def models(self, task: str = "", fetch=None):
        """Live from /models where a key allows it, else the measured
        chains with live=False so the picker says which it is."""
        want = {"stt": STT_MODELS, "tts": TTS_MODELS,
                "llm": LLM_MODELS}.get(task)
        for key in self.keys:
            try:
                req = urllib.request.Request(
                    API + "/models", method="GET",
                    headers={"x-goog-api-key": key, "User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read().decode("utf-8", "replace"))
            except Exception:                                # noqa: BLE001
                continue
            out = []
            for m in (data.get("models") or []):
                mid = str(m.get("name") or "").split("/")[-1]
                if not mid:
                    continue
                is_tts = "tts" in mid
                kind = "tts" if is_tts else "llm"
                if task == "stt" and is_tts:
                    continue
                if task and task != "stt" and kind != task:
                    continue
                out.append(Model(mid, m.get("displayName") or mid,
                                 for_task=task or kind,
                                 recommended=bool(want and mid == want[0])))
            if out:
                out.sort(key=lambda x: (not x.recommended, x.name.lower()))
                return out, True, None
        chain = want or (STT_MODELS + TTS_MODELS)
        return ([Model(m, m, for_task=task, recommended=(i == 0))
                 for i, m in enumerate(chain)], False, "no key answered")

    # ---- speech out --------------------------------------------------
    def voices(self, lang: str = ""):
        """The thirty, with Google's own adjective and NOTHING ELSE.

        `lang` is accepted and ignored on purpose: the Gemini voices are
        not published per-language, and filtering them by a language they
        do not declare would hide twenty-nine of thirty on a guess.
        `gender` stays empty for the same reason — a blank is a fact.
        """
        return [Voice(n, n, "", g, "gemini") for n, _tone, g in VOICES]

    def default_for(self, lang: str = ""):
        return Voice(DEFAULT_VOICE, DEFAULT_VOICE, "", "", "gemini")

    def synth(self, text: str, voice_id: str, direction: str = ""):
        """(wav_bytes, seconds, None).

        The None is the contract saying THERE ARE NO WORD TIMINGS — not a
        failure. Edge streams word-boundary events; Gemini returns audio
        and nothing else.

        `direction` is prose, compiled into the prompt, because Gemini
        has no per-utterance description field: one direction for the
        whole call. Measured, and not subtle — and a word in it is taken
        literally, which is why "Grateful" comes back 84% quieter than
        neutral. The caller's words are passed through unchanged.
        """
        voice = voice_id or DEFAULT_VOICE
        prompt = ("%s: %s" % (direction.strip().rstrip(":"), text)
                  if direction and direction.strip() else text)
        last = None
        for model in TTS_MODELS:
            def attempt(key, _m=model):
                data, err, kind, _raw = _post(
                    "/models/%s:generateContent" % _m, key,
                    {"contents": [{"parts": [{"text": prompt}]}],
                     "generationConfig": {
                         "responseModalities": ["AUDIO"],
                         "speechConfig": {"voiceConfig": {
                             "prebuiltVoiceConfig": {"voiceName": voice}}}}},
                    timeout=TTS_TIMEOUT)
                return data, err, kind
            data, err = self._rotate(attempt)
            if err:
                last = err
                continue
            pcm = _audio_of(data)
            if pcm is None:
                last = "Google answered without audio."
                continue
            return to_wav(pcm), pcm_seconds(pcm), None
        raise RuntimeError(last or "Google produced no audio.")

    # ---- speech in ---------------------------------------------------
    def transcribe(self, path: str, language: str = "hr", model: str = None):
        mime = _mime_of(path)
        if not mime:
            # SAID PLAINLY, NOT SENT AND REFUSED. A browser recorder
            # makes webm and Gemini answers a 400 that reads exactly like
            # a bad key, which would send the ring walking through every
            # account condemning each one.
            raise RuntimeError(
                "Google cannot read this audio format. It takes wav, mp3, "
                "flac, ogg, aac or aiff — a browser recording (webm) has "
                "to be converted first.")
        with open(path, "rb") as f:
            blob = base64.b64encode(f.read()).decode("ascii")
        ask = "Transcribe this audio. Return only the words spoken."
        if language and language != "auto":
            ask += " The language is %s." % language
        last = None
        for m in ([model] if model else list(STT_MODELS)):
            def attempt(key, _m=m):
                data, err, kind, _raw = _post(
                    "/models/%s:generateContent" % _m, key,
                    {"contents": [{"parts": [
                        {"text": ask},
                        {"inlineData": {"mimeType": mime, "data": blob}}]}]},
                    timeout=300)
                return data, err, kind
            data, err = self._rotate(attempt)
            if err:
                last = err
                continue
            return _text_of(data).strip()
        raise RuntimeError(last or "Google could not transcribe that.")

    # ---- text --------------------------------------------------------
    def complete(self, prompt: str, system: str = None, model: str = None,
                 temperature: float = 0.2, max_tokens: int = 2048) -> str:
        payload = {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"temperature": temperature,
                                        "maxOutputTokens": max_tokens}}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        last = None
        for m in ([model] if model else list(LLM_MODELS)):
            def attempt(key, _m=m):
                data, err, kind, _raw = _post(
                    "/models/%s:generateContent" % _m, key, payload)
                return data, err, kind
            data, err = self._rotate(attempt)
            if err:
                last = err
                continue
            return _text_of(data).strip()
        raise RuntimeError(last or "Google could not answer that.")


def _parts(data):
    try:
        return (data["candidates"][0]["content"]["parts"]) or []
    except Exception:                                        # noqa: BLE001
        return []


def _audio_of(data):
    """The PCM bytes, or None. Never raises on a shape it did not expect."""
    for p in _parts(data):
        blob = (p.get("inlineData") or p.get("inline_data") or {})
        raw = blob.get("data")
        if raw:
            try:
                return base64.b64decode(raw)
            except Exception:                                # noqa: BLE001
                return None
    return None


def _text_of(data) -> str:
    return "".join(str(p.get("text") or "") for p in _parts(data))


def _mime_of(path: str) -> str:
    import os
    return AUDIO_MIME.get(os.path.splitext(str(path))[1].lower(), "")
