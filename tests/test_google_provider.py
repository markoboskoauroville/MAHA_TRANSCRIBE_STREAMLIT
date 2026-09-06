"""THE GOOGLE PROVIDER. No network, no keys, no Streamlit.

    python3 tests/test_google_provider.py

TEST 2 IS NOT IN HERE. It is the only one of the four that touches a
key (secrets.md §5), it costs one of ten daily TTS requests, and one
account on this ring is already part-spent. It is run by hand, once,
against a real key, and its result is written into the commit message.

What IS in here: the mechanism alone, the ugly cases, and the upgrade —
all deterministic, all offline, so the sweep can run them a hundred
times without spending anything.
"""
import io
import os
import sys
import wave

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from ttt.providers import google as G          # noqa: E402
from ttt.providers import REGISTRY, get        # noqa: E402
from ttt.providers.base import Provider        # noqa: E402
from ttt import engines as EN                  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


# =====================================================================
print("1 THE MECHANISM, ALONE")
# =====================================================================

# ---- the header Google does not send --------------------------------
pcm = b"\x00\x01" * 24000                      # one second, 24 kHz, mono
wav = G.to_wav(pcm)

check("header is exactly 44 bytes", len(wav) - len(pcm) == 44, len(wav) - len(pcm))
check("it starts RIFF and declares WAVE",
      wav[:4] == b"RIFF" and wav[8:12] == b"WAVE", wav[:12])

# AN INDEPENDENT PARTY AGREES. Python's own wave module was written by
# somebody who has never seen this file; if it opens the bytes and reads
# back the numbers we claim, the header is right for reasons that have
# nothing to do with our arithmetic.
with wave.open(io.BytesIO(wav), "rb") as w:
    check("stdlib wave reads 1 channel", w.getnchannels() == 1, w.getnchannels())
    check("stdlib wave reads 24000 Hz", w.getframerate() == 24000, w.getframerate())
    check("stdlib wave reads 16-bit", w.getsampwidth() == 2, w.getsampwidth())
    check("stdlib wave counts 24000 frames", w.getnframes() == 24000, w.getnframes())
    check("the frames come back byte for byte", w.readframes(24000) == pcm)

check("one second of PCM measures 1.0s", abs(G.pcm_seconds(pcm) - 1.0) < 1e-9,
      G.pcm_seconds(pcm))
check("empty PCM measures 0.0s", G.pcm_seconds(b"") == 0.0)
check("the RIFF size field counts everything after it",
      int.from_bytes(wav[4:8], "little") == 36 + len(pcm),
      int.from_bytes(wav[4:8], "little"))

# ---- the five words, translated for a three-word ring ---------------
check("working is not a ring problem", G.ring_kind(G.WORKING) is None)
check("busy rests a key, never buries it", G.ring_kind(G.BUSY) == "cool")
check("no credit is dead, because waiting cannot fix it",
      G.ring_kind(G.NO_CREDIT) == "dead")
check("refused is dead", G.ring_kind(G.REFUSED) == "dead")
check("unknown blames nobody", G.ring_kind(G.UNKNOWN) == "soft")
check("every one of the five words maps",
      all(k in G._RING_KIND for k in G.VERDICTS), G.VERDICTS)
check("an unknown word falls to soft, never dead",
      G.ring_kind("something new") == "soft")

# ---- the trap that cost a live key ----------------------------------
# Both of these are 429. Only the body separates them.
throttle = ('{"error":{"code":429,"status":"RESOURCE_EXHAUSTED",'
            '"message":"Quota exceeded","details":[{"@type":"type.googleapis'
            '.com/google.rpc.RetryInfo","retryDelay":"31s"}]}}')
empty = ('{"error":{"code":429,"status":"RESOURCE_EXHAUSTED",'
         '"message":"Your prepayment credits are depleted.","details":'
         '[{"@type":"type.googleapis.com/google.rpc.RetryInfo",'
         '"retryDelay":"31s"}]}}')
check("a throttle with a hint is busy", G.verdict(429, throttle) == G.BUSY)
check("an empty balance is no credit EVEN WITH a retry hint",
      G.verdict(429, empty) == G.NO_CREDIT)
check("...so the two 429s do not collapse into one verdict",
      G.verdict(429, throttle) != G.verdict(429, empty))
check("only refused is deletable", G.deletable(G.REFUSED)
      and not G.deletable(G.NO_CREDIT) and not G.deletable(G.BUSY))

# EVERY MONEY WORD CARRIES ITS OWN WEIGHT.
#
# The first version of this suite tested one body — "Your prepayment
# credits are depleted" — which holds THREE of the marks at once. Cutting
# "depleted" and "credit" out of MONEY_MARKS left the suite GREEN,
# because "prepayment" was still matching. The check was correct about
# the outcome and proved nothing about the list, which is face 4: an
# assertion that cannot fail when the thing it names is removed.
#
# So each word is now exercised alone, in a body that contains no other.
for _word in G.MONEY_MARKS:
    _body = '{"error":{"code":429,"details":[{"@type":"RetryInfo",' \
            '"retryDelay":"31s"}],"message":"account %s issue"}}' % _word
    check("money word %r alone beats the retry hint" % _word,
          G.verdict(429, _body) == G.NO_CREDIT, G.verdict(429, _body))

# A WORD THAT ANOTHER WORD ALREADY CONTAINS IS NOT DOING ANY WORK.
# Found by this suite: "prepayment" can never be the reason a body is
# classified, because any body holding it also holds "payment". It is
# harmless and it is honest to know it is decoration rather than a rule.
_redundant = sorted(w for w in G.MONEY_MARKS
                    if any(o != w and o in w for o in G.MONEY_MARKS))
check("the only redundant money word is the known one",
      _redundant == ["prepayment"], _redundant)
_load_bearing = [w for w in G.MONEY_MARKS if w not in _redundant]
check("every other money word is load-bearing on its own",
      all(not any(o != w and o in ("account %s issue" % w)
                  for o in _load_bearing) for w in _load_bearing),
      _load_bearing)

# AND THE OTHER DIRECTION: the ordinary throttle wording must NOT be in
# that list. "quota" was the mistake that cost a live key.
for _not_money in ("quota", "exhausted", "resource_exhausted", "free tier",
                   "rate limit"):
    check("%r is NOT treated as money" % _not_money,
          _not_money not in G.MONEY_MARKS)
    check("...so a %r refusal with a hint stays busy" % _not_money,
          G.verdict(429, '{"error":{"message":"%s","details":[{"@type":'
                         '"RetryInfo","retryDelay":"5s"}]}}' % _not_money)
          == G.BUSY)

# ---- what a person is told ------------------------------------------
check("no credit tells them to top up, not that the key is broken",
      "top" in G._explain(G.NO_CREDIT, 429, empty).lower()
      and "broken" not in G._explain(G.NO_CREDIT, 429, empty).lower())
check("no credit says waiting will not help",
      "waiting will not help" in G._explain(G.NO_CREDIT, 429, empty).lower())

daily = ('{"error":{"code":429,"details":[{"@type":"type.googleapis.com/'
         'google.rpc.QuotaFailure","violations":[{"quotaId":"GenerateReq'
         'uestsPerDayPerProjectPerModel-FreeTier","quotaValue":"10"}]}]}}')
check("a daily wall is read as a day, not a minute",
      G.limit_kind(daily) == "day", G.limit_kind(daily))
check("the number Google stated is read back", G.limit_value(daily) == 10,
      G.limit_value(daily))
check("a daily wall names the reset hour",
      "09:00" in G._explain(G.BUSY, 429, daily))
check("a minute throttle quotes the delay Google asked for",
      "31" in G._explain(G.BUSY, 429, throttle), G._explain(G.BUSY, 429, throttle))

# ---- COMPACT JSON, which is what broke an earlier version -----------
# The regex that expected a space after the colon worked against
# Google's pretty-printed output and read every daily wall as a minute.
compact = daily.replace(": ", ":").replace(", ", ",")
check("a daily wall is still a day when the JSON is compact",
      G.limit_kind(compact) == "day", G.limit_kind(compact))
pretty = ('{\n  "error": {\n    "code": 429,\n    "details": [\n      {\n'
          '        "@type": "type.googleapis.com/google.rpc.QuotaFailure",\n'
          '        "violations": [\n          {\n            "quotaId": '
          '"GenerateRequestsPerDayPerProjectPerModel-FreeTier",\n'
          '            "quotaValue": "10"\n          }\n        ]\n'
          '      }\n    ]\n  }\n}')
check("and when it is pretty-printed", G.limit_kind(pretty) == "day",
      G.limit_kind(pretty))

# ---- the key shape ---------------------------------------------------
check("the prefix is AQ.", G.Google.key_prefixes == ("AQ.",),
      G.Google.key_prefixes)

# THE RETIRED PREFIX IS ABSENT FROM THE WHOLE FILE — code AND comments.
# keyring.md: no detector in this project looks for it, "not as a
# fallback, not as a second guess, not in a comment as an example."
# Comments are NOT stripped here on purpose: the rule covers them too.
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "ttt", "providers", "google.py")).read()
_dead_prefix = "AI" + "za"          # built, so this line is not itself a hit
check("the retired key prefix appears nowhere in google.py",
      _dead_prefix not in _src, _src.count(_dead_prefix))

# ---- the fact the reader will ask for -------------------------------
check("google is metered by the call", G.Google.metered_by_call is True)
check("and states its daily allowance", G.Google.calls_per_day == 10,
      G.Google.calls_per_day)
check("the base contract defaults to NOT metered",
      Provider.metered_by_call is False)

# ---- the voices ------------------------------------------------------
check("thirty voices", len(G.VOICES) == 30, len(G.VOICES))
check("no voice name is repeated", len(set(G.voice_names())) == 30)
check("the default is one of them", G.DEFAULT_VOICE in G.voice_names())
gp = G.Google()
vs = gp.voices()
check("the provider hands back all thirty", len(vs) == 30, len(vs))
# GENDER IS PUBLISHED AFTER ALL, and this check used to assert the
# opposite. The old claim came from the AI Studio page, which lists an
# adjective and nothing else; Google Cloud's own Gemini-TTS
# documentation carries a full table of name, gender and an audio demo.
# So the rule did not change — do not synthesise a facet from how a
# name sounds — the FACT did: it is now read off Google's table.
check("every voice carries Google's published gender",
      all(v.gender in ("F", "M") for v in vs),
      sorted({v.gender for v in vs}))
check("fourteen female and sixteen male, as Google lists them",
      (sum(1 for v in vs if v.gender == "F"),
       sum(1 for v in vs if v.gender == "M")) == (14, 16),
      (sum(1 for v in vs if v.gender == "F"),
       sum(1 for v in vs if v.gender == "M")))
check("a name Google does not list has no gender invented for it",
      G.gender_of("Nobody") == "")
# SPOT-CHECKED AGAINST THE TABLE, both directions, including the two
# most easily got wrong: Pulcherrima reads male by ear to some and
# Google lists it Female; Gacrux likewise.
for _n, _g in (("Kore", "F"), ("Zephyr", "F"), ("Pulcherrima", "F"),
               ("Gacrux", "F"), ("Charon", "M"), ("Puck", "M"),
               ("Algieba", "M"), ("Zubenelgenubi", "M")):
    check("Google lists %s as %s" % (_n, _g), G.gender_of(_n) == _g,
          G.gender_of(_n))

# TEN, AND NO MORE. Baba: "I want just ten voices, none more than ten."
for _g in ("F", "M"):
    _top = G.top_voices(_g, 10)
    check("%s gives exactly ten" % _g, len(_top) == 10, len(_top))
    check("...all of that gender",
          all(G.gender_of(n) == _g for n, _t in _top))
    check("...none repeated", len({n for n, _t in _top}) == 10)
    check("...each carrying Google's adjective",
          all(tone for _n, tone in _top))
check("the two lists never overlap",
      not ({n for n, _ in G.top_voices("F", 10)}
           & {n for n, _ in G.top_voices("M", 10)}))
check("asking for fewer gives fewer", len(G.top_voices("F", 3)) == 3)
check("asking for zero gives none", G.top_voices("F", 0) == [])
check("a nonsense gender gives none", G.top_voices("Z", 10) == [])
# THE ORDER IS GOOGLE'S OWN DOCUMENTATION USAGE, not an invented
# popularity — there is no published popularity and no premium tier.
check("the voices Google itself uses come first",
      G.top_voices("F", 1)[0][0] == "Kore"
      and G.top_voices("M", 1)[0][0] == "Charon",
      (G.top_voices("F", 1), G.top_voices("M", 1)))
check("and no language on any voice — Gemini voices are not published "
      "per-language, and filtering by one would hide 29 of 30 on a guess",
      all(v.lang == "" for v in vs))
check("an unknown voice's adjective is blank, not a guess",
      G.tone_of("Nobody") == "")
check("a filter built from the data covers every adjective present",
      set(G.tones()) == {t for _n, t, _g in G.VOICES if t})

# ---- the model chains ------------------------------------------------
check("the TTS chain has a fallback", len(G.TTS_MODELS) >= 2, G.TTS_MODELS)
check("the STT chain has two fallbacks", len(G.STT_MODELS) >= 3, G.STT_MODELS)
check("no retired 2.0 or 2.5 text model is named",
      not any(m.startswith("gemini-2.") and "tts" not in m
              for m in G.STT_MODELS + G.LLM_MODELS),
      G.STT_MODELS + G.LLM_MODELS)
check("ten a day is stated once and read from there",
      G.TTS_PER_DAY == 10 and G.Google.calls_per_day == G.TTS_PER_DAY)

# =====================================================================
print()
print("3 THE UGLY CASES")
# =====================================================================

# JUNK ARRIVES. An HTML 502 from a proxy is not JSON, and must never be
# the reason a reading crashes.
for junk in (None, "", b"", "not json at all", "<html>502 Bad Gateway</html>",
             "{", "[]", "null", b"\xff\xfe\x00", {"error": "flat string"},
             {"error": None}, [1, 2, 3], 12345):
    try:
        v = G.verdict(500, junk)
        ok = v in G.VERDICTS
    except Exception as e:                                   # noqa: BLE001
        ok, v = False, "RAISED %s" % e
    check("verdict survives junk: %.28r" % (junk,), ok, v)

for junk in (None, "", "<html>", "{", b"\xff", [], {"error": {}}, 7):
    for fn in (G.limit_kind, G.limit_value, G.retry_after):
        try:
            fn(junk)
            ok = True
        except Exception as e:                               # noqa: BLE001
            ok = False
        check("%s survives %.14r" % (fn.__name__, junk), ok)

# A body that is huge, and one that is hostile.
check("verdict survives a megabyte of noise",
      G.verdict(429, "x" * 1000000) in G.VERDICTS)
check("a body claiming to be another provider is still classified",
      G.verdict(429, '{"error":"zero_credits E0300"}') in G.VERDICTS)

# THE MONEY WORD WINS WHATEVER THE STATUS WAS.
check("an empty balance dressed as a 200 is still no credit",
      G.verdict(200, "prepayment credits are depleted") == G.NO_CREDIT)
check("a bad key dressed as a 500 is still refused",
      G.verdict(500, '{"error":{"message":"API_KEY_INVALID"}}') == G.REFUSED)
check("a bare 200 with no body is working", G.verdict(200, None) == G.WORKING)
check("status 0 — no network — says nothing about the key",
      G.verdict(0, "") == G.UNKNOWN)

# ---- audio and text out of shapes that are not the happy one --------
for bad in (None, {}, {"candidates": []}, {"candidates": [{}]},
            {"candidates": [{"content": {}}]},
            {"candidates": [{"content": {"parts": []}}]},
            {"candidates": [{"content": {"parts": [{"text": "hi"}]}}]},
            {"candidates": [{"content": {"parts": [
                {"inlineData": {"data": "!!!not base64!!!"}}]}}]}):
    try:
        got = G._audio_of(bad)
        ok = got is None or isinstance(got, bytes)
    except Exception as e:                                   # noqa: BLE001
        ok, got = False, "RAISED %s" % e
    check("_audio_of survives %.34r" % (bad,), ok, got)
    try:
        G._text_of(bad)
        ok = True
    except Exception:                                        # noqa: BLE001
        ok = False
    check("_text_of survives %.34r" % (bad,), ok)

check("snake_case inline_data is read too — the API uses both spellings",
      G._audio_of({"candidates": [{"content": {"parts": [
          {"inline_data": {"data": "aGk="}}]}}]}) == b"hi")

# ---- the format Gemini will not take --------------------------------
check("webm is refused by name, not sent", G._mime_of("a.webm") == "")
check("wav is accepted", G._mime_of("/tmp/A.WAV") == "audio/wav")
check("a file with no extension is refused", G._mime_of("recording") == "")
try:
    G.Google(keys=["AQ.x"]).transcribe("/tmp/nothing.webm")
    ok, msg = False, "it tried to send it"
except RuntimeError as e:
    msg = str(e)
    ok = "webm" in msg and "convert" in msg
except Exception as e:                                       # noqa: BLE001
    ok, msg = False, "wrong exception: %r" % e
check("webm raises BEFORE opening the file, and says what to do", ok, msg)

# ---- an empty ring ---------------------------------------------------
empty_p = G.Google(keys=[])
got, err = empty_p._rotate(lambda k: (None, "never called", "dead"))
check("no keys returns an error rather than raising", got is None and err)
check("...and the error says which provider", "Google" in err, err)

# EVERY KEY DEAD: the rotation must walk them all, not stop at the first.
seen = []


def _all_dead(key):
    seen.append(key)
    return None, "401", "dead"


got, err = G.Google(keys=["AQ.a", "AQ.b", "AQ.c"])._rotate(_all_dead)
# THE ORDER OF THE WALK IS NO LONGER FIXED — every call starts one
# further along the ring, so three parallel prefetch workers do not all
# queue behind key 1. What must still be true is that ALL of them are
# tried, exactly once each.
check("a dead key rolls forward to the next",
      sorted(seen) == ["AQ.a", "AQ.b", "AQ.c"], seen)
check("...each tried exactly once", len(seen) == len(set(seen)), seen)
check("...and the whole ring failing is an error, not a crash", err)

# AN ERROR NO KEY CAN FIX STOPS IMMEDIATELY rather than burning the ring.
seen2 = []


def _soft(key):
    seen2.append(key)
    return None, "the model name is wrong", "soft"


got, err = G.Google(keys=["AQ.a", "AQ.b", "AQ.c"])._rotate(_soft)
# A SOFT ERROR NOW WALKS THE RING TOO, and that is the fix, not a
# regression. Measured 6.9.2026: Google hands out 503s freely, one cost
# 67 SECONDS and then killed the whole sentence with twenty untried keys
# behind it. gemini-speech.md §5b: unknown "says nothing about the key,
# try again". Only a refusal of the REQUEST — a bad model, a malformed
# body — is worth stopping for, and that arrives as 400 and is read as
# refused, not soft.
check("a soft error tries the other keys rather than killing the job",
      len(seen2) == 3, seen2)

# A key that works after two dead ones.
seen3 = []


def _third_works(key):
    seen3.append(key)
    if len(seen3) < 3:
        return None, "401", "dead"
    return "the answer", None, None


got, err = G.Google(keys=["AQ.a", "AQ.b", "AQ.c"])._rotate(_third_works)
check("the third key answering is a success, not a failure",
      got == "the answer" and err is None, (got, err))

# =====================================================================
print()
print("4 THE UPGRADE — what an existing install still sees")
# =====================================================================

check("google now resolves in the registry", get("google") is not None)
check("...as a Provider", isinstance(get("google"), Provider))

# NOTHING ELSE MOVED. Adding a provider must not disturb the six that
# were already there — the failure this closes is a registry edit that
# quietly drops one.
for pid in ("edge", "groq", "speechify", "assemblyai", "hume", "anthropic"):
    check("%s still resolves" % pid, get(pid) is not None)
check("the registry holds seven providers now", len(REGISTRY) == 7, len(REGISTRY))

# EVERY PROVIDER THAT WAS THERE BEFORE IS STILL NOT METERED BY THE CALL.
# A new attribute with a wrong default would silently re-plan every
# reading in the app.
for pid in ("edge", "groq", "speechify", "assemblyai", "hume", "anthropic"):
    check("%s is not metered by the call" % pid,
          get(pid).metered_by_call is False)

# EVERY ROUTE OF EVERY ENGINE RESOLVES. This is the check that was
# failing before this commit: two of the google engine's three routes
# pointed at a provider that did not exist, and nothing said so.
for e in EN.ENGINES:
    for task, pid in e.routes.items():
        check("engine %s route %s -> %s resolves" % (e.id, task, pid),
              get(pid) is not None, pid)

check("google offers all three capabilities",
      set(get("google").capabilities) == {"stt", "tts", "llm"},
      get("google").capabilities)
check("every capability a provider claims has a method",
      all(hasattr(get("google"), m)
          for m in ("transcribe", "synth", "complete", "voices", "test_key")))

print()
print("%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
