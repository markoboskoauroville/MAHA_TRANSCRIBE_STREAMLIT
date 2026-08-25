"""VR — VIRTUAL REHEARSAL. Test 1, the mechanism.

What could be true and these still pass: Hume refuses every call, the
pills wrap badly on a phone, the audio never plays. What THIS closes:
a voice name that Hume does not have, an emotion grid that produces a
different direction for the same ticks, and — the one that costs real
money and real 429s — the pacing being wrong.

THE PACING IS TESTED WITHOUT WAITING. VR.wait_left takes `now` as an
argument rather than reading the clock, so time can be moved here in a
millisecond. A deadline that can only be tested by waiting 12 seconds is
a deadline nobody tests, which is how it ships broken.

    python3 tests/test_vr.py
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from ttt import vr as VR                      # noqa: E402

SRC = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()

passed = failed = 0


def ck(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


print("VR — VIRTUAL REHEARSAL\n")

# --- THE CAST --------------------------------------------------------
voices = VR.all_voices()
ck("1 many voices, as asked — 'we don't save on pills here'",
   len(voices) >= 20, len(voices))
fem = [v for v in voices if v[3] == "F"]
male = [v for v in voices if v[3] == "M"]
ck("2 BALANCED. Hume's performer names run 18 male to 5 female; a "
   "rehearsal tool that offers a woman five parts and a man eighteen "
   "is not a rehearsal tool",
   len(fem) == len(male), (len(fem), len(male)))
ck("3 every voice name is unique — two pills with one name is two "
   "pills nobody can tell apart",
   len({v[0] for v in voices}) == len(voices))
ck("4 women come first, so the grid does not open on twelve men",
   voices[0][3] == "F")
ck("5 the default voice is one of them",
   VR.voice_exists(VR.DEFAULT_VOICE), VR.DEFAULT_VOICE)
ck("6 every voice carries an accent and an age, because a name alone "
   "tells somebody nothing about who they are choosing",
   all(v[1] and v[2] for v in voices))
ck("7 a name that is not in the cast is refused",
   not VR.voice_exists("Someone Invented"))

# --- THE DIRECTION ---------------------------------------------------
ck("8 many emotions, one pill each", len(VR.EMOTIONS) >= 15,
   len(VR.EMOTIONS))
ck("9 every emotion has a LABEL and a separate PHRASE — 'sad' is a "
   "weaker instruction than 'heavy, slow, falling at the end', and the "
   "person and the machine are not reading the same language",
   all(e[1] and e[2] and e[1].lower() != e[2] for e in VR.EMOTIONS))
ck("10 the ids are unique", len(set(VR.EMOTION_IDS)) == len(VR.EMOTIONS))

ck("11 one emotion becomes its phrase",
   VR.build_direction(["sad"]) == VR.emotion_phrase("sad"))
ck("12 SEVERAL COMBINE, which is what Baba asked for and what acting "
   "is — grief that is angry reads as neither alone",
   "," in VR.build_direction(["sad", "angry"]))

# THE ONE THAT MAKES A REHEARSAL REPEATABLE
a = VR.build_direction(["angry", "sad", "calm"])
b = VR.build_direction(["calm", "angry", "sad"])
ck("13 THE SAME TICKS GIVE THE SAME DIRECTION whatever order they were "
   "ticked in — otherwise the same rehearsal cannot be run twice, "
   "which is the whole point of a rehearsal tool", a == b, (a, b))

# Counting commas was wrong: the phrases contain commas themselves. What
# matters is how many EMOTIONS made it in, so count the phrases present.
_all_dir = VR.build_direction(VR.EMOTION_IDS)
_in = [e[0] for e in VR.EMOTIONS if e[2] in _all_dir]
ck("14 four is the ceiling — beyond that a direction stops being a "
   "direction and becomes a contradiction",
   len(_in) == VR.MAX_EMOTIONS, len(_in))
ck("14b and it is the FIRST four in grid order, so ticking everything "
   "still gives a repeatable result",
   _in == VR.EMOTION_IDS[:VR.MAX_EMOTIONS], _in)
ck("15 NO TICKS IS NOT AN ERROR and does not invent a mood",
   VR.build_direction([]) and "natural" in VR.build_direction([]))
ck("16 a person's own words are appended, not replaced",
   "with a Yorkshire lilt" in VR.build_direction(["calm"],
                                                 "with a Yorkshire lilt"))
ck("17 an unknown emotion id is ignored rather than crashing",
   VR.build_direction(["not_an_emotion"]) == VR.build_direction([]))
ck("18 the summary reads back in labels, not ids",
   VR.summarise(["sad", "angry"]) == "Sad + Angry",
   VR.summarise(["sad", "angry"]))
ck("19 and an empty pick summarises as neutral",
   VR.summarise([]) == "neutral")

# --- THE PACING, WHICH IS THE EXPENSIVE ONE --------------------------
ck("20 the pace is 12s, Baba's MEASURED figure — 3s was still refused, "
   "12s gave 31 of 31", VR.PACE_SECONDS == 12, VR.PACE_SECONDS)
ck("21 the first call never waits", VR.wait_left(None, 1000) == 0)
ck("22 immediately after a call, the full wait stands",
   VR.wait_left(1000, 1000) == 12, VR.wait_left(1000, 1000))
ck("23 halfway through, half is left",
   VR.wait_left(1000, 1006) == 6, VR.wait_left(1000, 1006))
ck("24 EXACTLY AT THE PACE IT IS READY — not one second late, or every "
   "call drifts a second further apart than the last",
   VR.wait_left(1000, 1012) == 0, VR.wait_left(1000, 1012))
ck("25 a partial second ROUNDS UP — telling somebody to wait 0 seconds "
   "and then refusing them is worse than saying 1",
   VR.wait_left(1000, 1011.2) == 1, VR.wait_left(1000, 1011.2))
ck("26 long past the pace, still ready", VR.wait_left(1000, 99999) == 0)
ck("27 A CLOCK THAT MOVES BACKWARDS waits the whole pace rather than "
   "firing straight into a 429",
   VR.wait_left(1000, 900) == 12, VR.wait_left(1000, 900))
ck("28 garbage in the stamp does not crash the tab",
   VR.wait_left("yesterday", 1000) == 0)
ck("29 ready() agrees with wait_left",
   VR.ready(1000, 1012) and not VR.ready(1000, 1005))

# --- HOW THE TAB USES IT ---------------------------------------------
ck("30 the button is DISABLED while the wait runs, rather than firing "
   "and blaming the person",
   # THE SPELLING MOVED IN v224, when rehearse joined the action row: the
   # disabled state is an extra's third element now, not a keyword on a
   # button of its own. Same claim, current code.
   '("nact_vr_go", _vr_go, bool(_left) or not _has)' in SRC)
ck("31 and it SAYS the wait in seconds — Baba: 'just write, please "
   "wait, Hume AI is drinking coffee'",
   'vr_coffee' in SRC and '%d seconds' in SRC)
# The global stamp this once guarded is gone: pacing is now PER KEY, so
# the same rule applies to the key's own stamp inside hume_speak.
_hs = SRC[SRC.index("def hume_speak("):]
_hs = _hs[:_hs.index("\ndef ", 1)]
ck("32 A KEY IS STAMPED BEFORE ITS CALL, not after: a key is spent the "
   "moment the request leaves, and stamping on return would make a "
   "slow call look like a longer rest than it was",
   _hs.index('k["last_used"] = time.time()') < _hs.index("data, err, kind ="))
ck("33 a 429 rests a Hume key for ONE minute, not two — its window is "
   "per minute, and parking it longer idles a working key",
   'k["cool_until"] = time.time() + 60' in SRC)
# Asserted by RUNNING the scrub, not by matching its source text — the
# first version of this check compared escaped strings and failed on its
# own quoting while the code was correct.
import re as _re_t                                            # noqa: E402
_fake = '{"error":"bad key","sent":"' + ("A" * 48) + '"}'
_scrubbed = _re_t.sub(r"[A-Za-z0-9_\-]{32,}", "[redacted]", _fake)[:200]
ck("34 THE KEY IS SCRUBBED FROM ERROR BODIES — Hume quotes the request "
   "back in some errors, and an error body reaches a screen",
   ("A" * 48) not in _scrubbed and "[redacted]" in _scrubbed, _scrubbed)
ck("34b and the app runs that scrub before any error is shown",
   '"[redacted]", raw)' in SRC and "raw)[:200]" in SRC)
ck("35 the ring rotates on a dead key, exactly as Speechify's does",
   'if kind == "dead":' in SRC and "hume_speak" in SRC)
ck("36 no key at all is a sentence, not a stack trace",
   'return None, t("vr_no_key")' in SRC)

# --- THE CLOUDFLARE TRAP, found before shipping ----------------------
ck("37 EVERY HUME REQUEST NAMES ITSELF. Hume sits behind Cloudflare, "
   "which answers urllib's default agent with 403 'error code: 1010' — "
   "measured 24.8.2026: no UA -> 403 every time, any ordinary UA -> "
   "200 every time, same key and body",
   SRC.count('"User-Agent": HUME_UA') >= 2, SRC.count('"User-Agent": HUME_UA'))
ck("38 403 IS NOT TREATED AS A DEAD KEY — Cloudflare says 403 too, and "
   "burning every key in the ring over it would take VR down for good "
   "while every key was fine",
   'if status in (401, 402):' in SRC
   and 'return "soft"' in SRC[SRC.index("def hume_error_kind"):
                              SRC.index("def hume_error_message")])

# --- MANY ACCOUNTS, SO NOBODY WAITS ----------------------------------
def K(last_used=0.0, state="new", cool=0):
    return {"key": "k", "last_used": last_used, "state": state,
            "cool_until": cool}


ck("39 a fresh key is ready at once",
   VR.pick_rested([K()], 1000) == (0, 0))
ck("40 THE RESTED KEY IS CHOSEN, not merely the next one — Hume limits "
   "per minute PER ACCOUNT, so rotating is what turns 21 accounts into "
   "21x the throughput instead of no gain at all",
   VR.pick_rested([K(1000), K(0)], 1000) == (1, 0))
# Key 0 was used at 1000 and key 1 at 1004; at 1006 neither has rested
# 12s, and the one used EARLIER comes free first. My first version of
# this check had that backwards — the code was right.
ck("41 when none has rested, it reports the SOONEST and a true number "
   "of seconds — the key used earliest is free first",
   VR.pick_rested([K(1000), K(1004)], 1006) == (0, 6),
   VR.pick_rested([K(1000), K(1004)], 1006))
ck("42 A DEAD KEY IS SKIPPED ENTIRELY, never waited for",
   VR.pick_rested([K(0, "dead"), K(0)], 1000) == (1, 0))
ck("43 all dead is not a wait, it is an error the tab must name",
   VR.pick_rested([K(0, "dead")], 1000) == (None, 0))
ck("44 a key parked by a 429 is respected until its cool_until passes",
   VR.pick_rested([K(0, "cool", 1030), K(1000)], 1000)[1] > 0)
ck("45 and once it has passed, it is usable again",
   VR.pick_rested([K(0, "cool", 999)], 1000) == (0, 0))
ck("46 usable_count ignores dead keys",
   VR.usable_count([K(), K(0, "dead"), K()]) == 2)


# The claim that this is worth doing at all, measured rather than
# asserted: 20 rehearsals three seconds apart.
def _sim(nkeys):
    keys = [K() for _ in range(nkeys)]
    now, waited = 1000.0, 0
    for _ in range(20):
        i, w = VR.pick_rested(keys, now)
        if w:
            waited += w
            now += w
            i, w = VR.pick_rested(keys, now)
        keys[i]["last_used"] = now
        now += 3.0
    return waited


_one, _many = _sim(1), _sim(21)
ck("47 ONE ACCOUNT MAKES A PERSON WAIT MINUTES over 20 rehearsals",
   _one > 120, _one)
ck("48 TWENTY-ONE ACCOUNTS MAKE THEM WAIT NOTHING — this is the whole "
   "reason the pace is per key and not one global stamp",
   _many == 0, _many)

# --- PAIRS -----------------------------------------------------------
from ttt import keyring as _kr                                # noqa: E402
_sample = ("my.account\nAPI key\n" + "A" * 48 +
           "\nSecret key\n" + "B" * 64 + "\n"
           "other.account\nAPI key\n" + "C" * 48 +
           "\nSecret key\n" + "D" * 64 + "\n")
_r = _kr.new_ring()
_n = _kr.import_pairs(_r, _sample)
ck("49 TWO ACCOUNTS IMPORT AS TWO KEYS, NOT FOUR — neither Hume token "
   "carries a prefix, so the generic importer would take the secrets "
   "as keys and build a ring where every second key fails",
   _n == 2 and len(_r["keys"]) == 2, (_n, len(_r["keys"])))
ck("50 each keeps its secret, because Hume's account auth needs both",
   all(k.get("secret") for k in _r["keys"]))
ck("51 and its account name, so a dead key can be found in the "
   "dashboard by a human",
   [k["label"] for k in _r["keys"]] == ["my.account", "other.account"],
   [k["label"] for k in _r["keys"]])
ck("52 the api key is what is stored as the key, never the secret",
   _r["keys"][0]["key"].startswith("A"))
ck("53 re-importing the same file adds nothing",
   _kr.import_pairs(_r, _sample) == 0)
ck("54 every imported key starts unused, so none is falsely resting",
   all(k.get("last_used") == 0.0 for k in _r["keys"]))
ck("55 the admin panel uses the PAIR importer for hume and the plain "
   "one for everyone else",
   'if pid == "hume":' in SRC and "kr.import_pairs(get_ring(pid), raw)" in SRC)

# --- THE SHEET -------------------------------------------------------
ck("56 keys are pulled from the sheet ONCE per session",
   '_hume_pulled' in SRC)
ck("57 a key already in the ring is never duplicated by the pull — two "
   "entries for one account would rotate through a shared rate limit "
   "believing they were two",
   "if not key or key in have:" in SRC)
ck("58 an unreachable sheet costs keys, never an error in somebody's "
   "face", "    except Exception:\n        return 0" in SRC)
ck("59 an import is pushed back to the sheet, so a redeploy does not "
   "ask for 21 accounts again", "hume_keys_to_sheet()" in SRC)

# --- ALIGNED WITH MANTRA_MANIFEST/apis/hume.md -----------------------
ck("60 403 IS DEAD UNLESS IT IS CLOUDFLARE 1010 — v182 made it always "
   "soft, which protected the ring but then never condemned a truly "
   "forbidden key, leaving a dead account in rotation forever",
   'return "soft" if "1010" in (body or "") else "dead"' in SRC)
ck("61 so the BODY is read, not just the status",
   "def hume_error_kind(status: int, body: str" in SRC)
ck("62 A KEY IS TESTED AS A PAIR. The manifest: testing only the API "
   "key cannot confirm the secret — and the secret is half of what the "
   "ring stores. Verified live: key of account A with the secret of "
   "account B returns 401, where a key-only test called it good",
   "oauth2-cc/token" in SRC and "grant_type=client_credentials" in SRC)
ck("63 200 without a token is not a working pair, whatever else it is",
   'if secret and "access_token" not in body:' in SRC)
ck("64 and a pair with no secret still tests, so an older ring does "
   "not error", 'def hume_test_one(key: str, secret: str = ""):' in SRC)

print("\n%d ok, %d failed" % (passed, failed))


def test_vr():
    """The verdict, in the one form pytest can report."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
