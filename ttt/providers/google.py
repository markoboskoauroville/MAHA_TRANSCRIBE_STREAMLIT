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

AND THE KEYS BEGIN "AQ.", not "AIza". An extraction that assumed the
older prefix sliced three characters off every key and made all
twenty-one look invalid. The loader must not assume a shape.
"""

import json
import re

# ---- the five words --------------------------------------------------

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
