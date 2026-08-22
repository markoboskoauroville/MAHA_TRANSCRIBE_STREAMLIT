"""THE CLAUDE CALL — the payload we actually send.

    python3 tests/test_anthropic_call.py

The offline checks below need no key: they call complete() with a fake
`fetch` that captures the payload instead of sending it, which is the
only way to assert what goes on the wire.

THE LIVE CHECK NEEDS A REAL KEY and is skipped without one. It is the
half that matters: `temperature` was sent on every call for months and
nothing here noticed, because nothing here had ever sent one. To run it:

    export ANTHROPIC_API_KEY=...   (or see handoff/LAST_RUN.md)
    python3 tests/test_anthropic_call.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ttt.providers.anthropic import Anthropic  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def capture():
    """A fake `fetch` that stands in for the key ring.

    complete() hands `fetch` a callable expecting one key, and uses what
    `fetch` RETURNS — so the fake must hand the attempt's own result
    back, exactly as kr.rotate does. Returning anything else here tests
    the fake instead of the provider.
    """
    seen = {}

    def fetch(attempt):
        seen["result"] = attempt("sk-ant-not-a-real-key")
        return seen["result"]

    return seen, fetch


# The provider builds its request through http_json, so intercept that.
import ttt.providers.anthropic as A  # noqa: E402

CALLS = []


def fake_http_json(url, headers, payload=None, method="GET", timeout=30,
                   classify=None):
    CALLS.append({"url": url, "headers": headers, "payload": payload,
                  "method": method, "timeout": timeout})
    return {"content": [{"type": "text", "text": "ok"}]}, None


A.http_json = fake_http_json

print("THE CLAUDE CALL\n")

prov = Anthropic()

# --- what we send ------------------------------------------------------
CALLS.clear()
_, fetch = capture()
out = prov.complete(fetch, "say ok")

sent = CALLS[0]["payload"] if CALLS else {}
check("1 the call is made at all", bool(CALLS), CALLS)
check("2 NO temperature is sent — current models 400 on it",
      "temperature" not in sent, sorted(sent))
check("3 max_tokens is big enough to hand back a file",
      sent.get("max_tokens", 0) >= 16000, sent.get("max_tokens"))
check("4 the model id carries no date suffix",
      "-2025" not in sent.get("model", "") and "-2026" not in sent.get("model", ""),
      sent.get("model"))
check("5 the timeout grew with the ceiling",
      CALLS[0]["timeout"] >= 300, CALLS[0]["timeout"])
check("6 the answer is the text, joined", out == "ok", out)

# --- an old model may still ask for one --------------------------------
CALLS.clear()
_, fetch = capture()
prov.complete(fetch, "say ok", temperature=0.2)
check("7 temperature is still POSSIBLE when a caller means it",
      CALLS[0]["payload"].get("temperature") == 0.2, CALLS[0]["payload"])

# --- thinking blocks must not become part of the answer ----------------
def thinking_http_json(url, headers, payload=None, method="GET", timeout=30,
                       classify=None):
    # Opus 5 thinks by default, so a real reply carries thinking blocks
    # beside the text. Only the text is the answer.
    return {"content": [{"type": "thinking", "thinking": ""},
                        {"type": "text", "text": "the answer"}]}, None


A.http_json = thinking_http_json
_, fetch = capture()
check("8 a thinking block is not mistaken for the answer",
      prov.complete(fetch, "x") == "the answer")
A.http_json = fake_http_json

# --- THE LIVE CALL -----------------------------------------------------
KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not KEY:
    print("\n  --   9 LIVE CALL SKIPPED: no ANTHROPIC_API_KEY in the"
          " environment.\n         The offline checks above cannot prove the"
          " API accepts this.")
else:
    # Put the real transport back — everything above ran against a fake.
    from ttt.providers.base import http_json as real_http_json
    A.http_json = real_http_json

    def live_fetch(attempt):
        return attempt(KEY)

    try:
        answer = prov.complete(live_fetch,
                               "Reply with exactly the word: ok",
                               max_tokens=16000)
        check("9 THE REAL API ACCEPTS THIS PAYLOAD", bool(answer), answer)
        print("       model replied: " + repr(answer[:60]))
    except Exception as e:
        check("9 THE REAL API ACCEPTS THIS PAYLOAD", False, e)

print("\n{} passed, {} failed".format(passed, failed))


def test_anthropic_call():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_anthropic_call.py` is how it is meant
    to be read."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
