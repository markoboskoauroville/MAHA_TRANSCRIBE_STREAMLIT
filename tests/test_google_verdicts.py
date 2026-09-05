"""THE GOOGLE VERDICTS — written BEFORE the mapping it checks.

    python3 tests/test_google_verdicts.py

docs/GOOGLE_ENGINE.md §8 step 3: "Write the test before the mapping.
That trap has already cost a live key once."

So this file was written first, and the mapping was made to satisfy it.

WHAT THE TRAP IS. Google answers a spent account and an impatient one
with the SAME STATUS and the SAME WORD. Match on "quota" alone and you
tell somebody to delete a live key because they pressed Test twice in one
second. That has already happened, to a real key.

FIVE VERDICTS, NOT FOUR. `no credit` is a healthy account with no money.
It must not read as a failure and must not read as something to delete —
those are different sentences to the person holding the key.

    working    it did the work
    busy       throttled this minute. Next key. NEVER delete.
    no credit  real key, live account, no money. Its own word.
    refused    401/403: revoked, mistyped. This is what delete removes.
    unknown    5xx, 404, no network. Says nothing about the key.

A CONTRADICTION IN THE SOURCES, RESOLVED HERE AND STATED OUT LOUD.

    the arrow list says   retry hint -> cool, FIRST, then money words
    the prose says        a prepaid empty balance answers 429, so
                          "check for it BEFORE the rate-limit branch"

Both cannot be literally true. Google attaches RetryInfo to almost every
429, so "hint first" taken literally makes `no credit` UNREACHABLE — and
the doc gives it its own verdict precisely so it can be reached.

The only reading where both hold, and the one implemented:

    an AMBIGUOUS quota refusal, with a retry hint   -> busy
    an UNAMBIGUOUS money word                       -> no credit,
                                                       hint or not

"Quota exceeded" is ambiguous and must never be read as money. "Balance
depleted" is not ambiguous and no delay will fix it.

MEASURED against Baba's live keys on 5.9.2026, and the fixtures below are
those answers rather than invented ones:

    a mangled key      401 UNAUTHENTICATED, ACCESS_TOKEN_TYPE_UNSUPPORTED
    a wrong-shaped key 400 API_KEY_INVALID, "API key not valid"
    a retired model    404 "no longer available"
    working LLM        200 on gemini-3.6-flash
    working TTS        200, audio/L16;codec=pcm;rate=24000, no RIFF header
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


# --- the answers Google actually gave, kept as fixtures ---------------

MANGLED_KEY = json.dumps({"error": {
    "code": 401, "status": "UNAUTHENTICATED",
    "message": "Request had invalid authentication credentials. Expected "
               "OAuth 2 access token.",
    "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo",
                 "reason": "ACCESS_TOKEN_TYPE_UNSUPPORTED"}]}})

BAD_SHAPE = json.dumps({"error": {
    "code": 400, "status": "INVALID_ARGUMENT",
    "message": "API key not valid. Please pass a valid API key.",
    "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo",
                 "reason": "API_KEY_INVALID"}]}})

RETIRED_MODEL = json.dumps({"error": {
    "code": 404,
    "message": "This model models/gemini-2.0-flash is no longer available."}})

MINUTE_LIMIT = json.dumps({"error": {
    "code": 429, "status": "RESOURCE_EXHAUSTED",
    "message": "Quota exceeded for quota metric 'Generate requests per "
               "minute' limit 'GenerateRequestsPerMinutePerProjectPerModel-"
               "FreeTier' of service 'generativelanguage.googleapis.com'.",
    "details": [
        {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
         "violations": [{"quotaId": "GenerateRequestsPerMinutePerProject"
                                    "PerModel-FreeTier", "quotaValue": "3"}]},
        {"@type": "type.googleapis.com/google.rpc.RetryInfo",
         "retryDelay": "31s"}]}})

DAY_LIMIT = json.dumps({"error": {
    "code": 429, "status": "RESOURCE_EXHAUSTED",
    "message": "Quota exceeded for metric: generate_content_free_tier_"
               "requests, limit: 10, model: gemini-2.5-flash-preview-tts",
    "details": [
        {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
         "violations": [{"quotaId": "GenerateRequestsPerDayPerProject"
                                    "PerModel-FreeTier", "quotaValue": "10"}]},
        {"@type": "type.googleapis.com/google.rpc.RetryInfo",
         "retryDelay": "44s"}]}})

# The one the whole file exists for: a 429 that no delay will ever fix,
# arriving WITH a retry hint because Google attaches one to everything.
NO_MONEY = json.dumps({"error": {
    "code": 429, "status": "RESOURCE_EXHAUSTED",
    "message": "Prepaid balance depleted. Please add credit to continue.",
    "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo",
                 "retryDelay": "30s"}]}})


def main():
    from ttt.providers import google as G

    print("1 THE FIVE VERDICTS EXIST AND ARE DISTINCT")
    names = (G.WORKING, G.BUSY, G.NO_CREDIT, G.REFUSED, G.UNKNOWN)
    check("1a five of them", len(set(names)) == 5, names)
    check("1b no credit is its OWN word, not a flavour of refused",
          G.NO_CREDIT != G.REFUSED, (G.NO_CREDIT, G.REFUSED))
    check("1c and not a flavour of busy either — waiting never helps",
          G.NO_CREDIT != G.BUSY)

    print("\n2 THE TRAP: A 429 IS NOT ONE THING")
    check("2a a MINUTE limit is busy — next key, never delete",
          G.verdict(429, MINUTE_LIMIT) == G.BUSY, G.verdict(429, MINUTE_LIMIT))
    check("2b a DAY limit is busy too — the key is fine, the day is spent",
          G.verdict(429, DAY_LIMIT) == G.BUSY, G.verdict(429, DAY_LIMIT))
    check("2c AN EMPTY BALANCE IS NO CREDIT, even though it arrives as 429 "
          "WITH a retryDelay — this is the case that cost a live key",
          G.verdict(429, NO_MONEY) == G.NO_CREDIT, G.verdict(429, NO_MONEY))
    check("2d 'quota exceeded' alone is NEVER read as money — it is the "
          "ordinary throttle wording",
          G.verdict(429, MINUTE_LIMIT) != G.NO_CREDIT)

    print("\n3 THE OTHER STATUSES, AS MEASURED")
    check("3a a mangled key is refused — this is what delete removes",
          G.verdict(401, MANGLED_KEY) == G.REFUSED, G.verdict(401, MANGLED_KEY))
    check("3b 403 likewise", G.verdict(403, "") == G.REFUSED)
    check("3c A WRONG-SHAPED KEY IS REFUSED, not soft. Google answers 400 "
          "API_KEY_INVALID, and a dead key that STOPS THE RING is the "
          "worst failure there is",
          G.verdict(400, BAD_SHAPE) == G.REFUSED, G.verdict(400, BAD_SHAPE))
    check("3d but an ordinary 400 is unknown — a malformed request of "
          "ours says nothing about the key",
          G.verdict(400, '{"error":{"message":"Invalid JSON payload"}}')
          == G.UNKNOWN)
    check("3e a retired model is unknown, never dead — that 404 was our "
          "code being out of date",
          G.verdict(404, RETIRED_MODEL) == G.UNKNOWN,
          G.verdict(404, RETIRED_MODEL))
    check("3f 5xx is unknown", G.verdict(503, "") == G.UNKNOWN)
    check("3g no network at all is unknown, never a judgement on the key",
          G.verdict(0, "") == G.UNKNOWN)
    check("3h 200 is working", G.verdict(200, "{}") == G.WORKING)

    print("\n4 READING THE LIMIT OUT OF THE REFUSAL")
    # "Parse the JSON, not the message string: a regex that expects a
    # space after the colon works against Google's pretty-printed output
    # and silently reads every daily wall as a minute limit."
    check("4a a minute wall is named as such",
          G.limit_kind(MINUTE_LIMIT) == "minute", G.limit_kind(MINUTE_LIMIT))
    check("4b a daily wall is named as such — read as a minute limit, a "
          "key gets retried all day against a wall it has already hit",
          G.limit_kind(DAY_LIMIT) == "day", G.limit_kind(DAY_LIMIT))
    check("4c the number it just stated is recovered, so the ledger "
          "learns", G.limit_value(DAY_LIMIT) == 10, G.limit_value(DAY_LIMIT))
    check("4d and the minute one too", G.limit_value(MINUTE_LIMIT) == 3)
    check("4e it comes from the quotaId, NOT from the message text",
          G.limit_kind(json.dumps({"error": {"details": [
              {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
               "violations": [{"quotaId": "GenerateRequestsPerDayPerProject"
                                          "PerModel-FreeTier"}]}]}})) == "day")
    check("4f compact JSON with no space after the colon parses the same "
          "— the regex that broke was written against pretty output",
          G.limit_value(DAY_LIMIT.replace(": ", ":")) == 10,
          G.limit_value(DAY_LIMIT.replace(": ", ":")))
    check("4g an answer with no quota block says so rather than guessing",
          G.limit_kind(NO_MONEY) is None, G.limit_kind(NO_MONEY))

    print("\n5 HOW LONG TO WAIT")
    check("5a the delay Google asked for is used",
          abs(G.retry_after(MINUTE_LIMIT) - 31.0) < 0.01,
          G.retry_after(MINUTE_LIMIT))
    check("5b not a number we chose", G.retry_after(DAY_LIMIT) == 44.0)
    check("5c nothing said is None, so the caller may default",
          G.retry_after("{}") is None)

    print("\n6 THE UGLY CASES")
    check("6a an empty body does not crash", G.verdict(429, "") in names)
    check("6b junk does not crash", G.verdict(429, "<html>502</html>") in names)
    check("6c None does not crash", G.verdict(500, None) == G.UNKNOWN)
    check("6d a body that is valid JSON but not an error object",
          G.verdict(200, '{"candidates":[]}') == G.WORKING)
    check("6e limit_kind on junk is None, not an exception",
          G.limit_kind("<html>") is None)
    check("6f case does not matter — BALANCE DEPLETED is still money",
          G.verdict(429, '{"error":{"message":"BALANCE DEPLETED"}}')
          == G.NO_CREDIT)
    check("6g a money word inside an ordinary 400 is still no credit",
          G.verdict(400, '{"error":{"message":"insufficient credit"}}')
          == G.NO_CREDIT)

    print("\n7 NO VERDICT MEANS DELETE EXCEPT REFUSED")
    # The whole point of five words: only one of them is an instruction
    # to remove something.
    check("7a busy is not deletable", G.deletable(G.BUSY) is False)
    check("7b no credit is NOT deletable — it is a healthy account that "
          "needs topping up, and deleting it is the exact harm the "
          "module warns about", G.deletable(G.NO_CREDIT) is False)
    check("7c unknown is not deletable — it says nothing about the key",
          G.deletable(G.UNKNOWN) is False)
    check("7d working is not deletable", G.deletable(G.WORKING) is False)
    check("7e refused IS — that is what delete removes",
          G.deletable(G.REFUSED) is True)

    print("\n{} passed, {} failed".format(passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
