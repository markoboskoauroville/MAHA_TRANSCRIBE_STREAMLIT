"""THE READER (R) — voices always on screen, play on the deck.

    python3 tests/test_reader.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def sget(at, key, default=None):
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def app(text="Prva rečenica. Druga rečenica. Treća rečenica."):
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=90)
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    at.session_state["active_tab"] = "talk"
    at.session_state["talk_text"] = text
    return at


def voice_keys(at):
    return [b.key for b in at.get("button")
            if b.key.startswith("talkvoice_") or b.key.startswith("talksp_")]


print("THE READER — voices on screen, play on the deck\n")

# --- writing state ----------------------------------------------------
at = app()
at.run()
check("1 R renders", not at.exception, at.exception)

vk = voice_keys(at)
check("2 the voices are on screen while writing", len(vk) > 0, vk)

keys = [b.key for b in at.get("button")]
check("3 THE SEPARATE PLAY BUTTON IS GONE", "read_btn" not in keys, keys)

# --- the voices are STILL there while playing -------------------------
at2 = app()
at2.run()
# Start a reading the way the deck now does, without synthesising: seed
# the job directly, which is what the start press leads to.
at2.session_state["_talk_job"] = {
    "parts": [(["Prva rečenica."], 0)],
    "full_text": "Prva rečenica.",
    "index": 0,
    "cache": {0: {"audio": b"\0\0", "marks": []}},
    "synth": lambda s: (b"", 0.0, None),
}
at2.run()
vk2 = voice_keys(at2)
check("4 THE VOICES ARE ON SCREEN WHILE PLAYING TOO", len(vk2) > 0, vk2)
check("5 the same voices as when writing", set(vk2) == set(vk),
      "{} vs {}".format(sorted(vk2), sorted(vk)))
check("6 exactly one row of them, not two",
      len(vk2) == len(set(vk2)) and len(vk2) == len(vk), vk2)

# --- changing voice mid-play rebuilds, and KEEPS THE PLACE ------------
at3 = app()
at3.run()
at3.session_state["_talk_job"] = {
    "parts": [(["A."], 0), (["B."], 2), (["C."], 4)],
    "full_text": "A. B. C.",
    "index": 1,
    "cache": {0: {"audio": b"\0", "marks": []},
              1: {"audio": b"\0", "marks": []}},
    "synth": lambda s: (b"", 0.0, None),
}
at3.run()
before = dict(sget(at3, "_talk_job"))
check("7 the reading is on block 1 with a warm cache",
      before["index"] == 1 and len(before["cache"]) == 2)

other = [k for k in voice_keys(at3)
         if k != ("talkvoice_" + sget(at3, "voice", "Gabrijela"))]
[b for b in at3.get("button") if b.key == other[0]][0].click().run()

job3 = sget(at3, "_talk_job") or {}
check("8 changing voice DROPS the cache, so audio is re-rendered",
      job3.get("cache") == {} or 1 not in job3.get("cache", {1: 1}),
      job3.get("cache"))
check("9 and KEEPS the place — it does not restart the whole text",
      job3.get("index") == 1, job3.get("index"))

# --- a new text clears the reading ------------------------------------
at4 = app()
at4.run()
at4.session_state["_talk_job"] = {
    "parts": [(["A."], 0)], "full_text": "A.", "index": 0,
    "cache": {0: {"audio": b"\0", "marks": []}},
    "synth": lambda s: (b"", 0.0, None)}
at4.run()
[b for b in at4.get("button") if b.key == "talk_new"][0].click().run()
check("10 new text ends the reading", sget(at4, "_talk_job") is None,
      sget(at4, "_talk_job"))

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
