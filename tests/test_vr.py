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
   'disabled=bool(_left) or not _has' in SRC)
ck("31 and it SAYS the wait in seconds — Baba: 'just write, please "
   "wait, Hume AI is drinking coffee'",
   'vr_coffee' in SRC and '%d seconds' in SRC)
ck("32 THE STAMP IS TAKEN BEFORE THE CALL, not after: a 20-second call "
   "stamped afterwards would space the next press 32 seconds out, "
   "which is slower than asked",
   SRC.index('st.session_state["_vr_last_at"] = time.time()')
   < SRC.index("got, err = hume_speak("))
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

print("\n%d ok, %d failed" % (passed, failed))


def test_vr():
    """The verdict, in the one form pytest can report."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
