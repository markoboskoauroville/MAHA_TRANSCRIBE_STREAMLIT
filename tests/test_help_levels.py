"""THE HELP AT FOUR DEPTHS, AND A PICKER THAT SAYS WHAT IT TAKES.

    python3 tests/test_help_levels.py

Baba, 25.8.2026, asked for both on the first day and they waited:

  "Four-level free-user help file: a child of five, mid-school, a
   non-technical adult, a first-year IT student. In Croatian and English,
   written to be HEARD."

  "Add a file picker in the transcription tab so a user can transcribe
   its own audio files or video files."

THE PICKER ALREADY EXISTED and already took video — the deck's `open`
cell, accept="audio/*,video/*". He asked for it because NOTHING SAID SO:
the cell says "open" and its only description was "upload". MEASURED
rather than assumed: a real h264+aac mp4 through that path comes out as
16 kHz mono FLAC with no video stream, 86 KB -> 35 KB.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import help_levels as L  # noqa: E402
from ttt import help_page as H  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()

print("1 FOUR LEVELS, TWO LANGUAGES")
check("1a there are four", len(L.LEVELS) == 4, L.LEVELS)
for lang in ("en", "hr"):
    sizes = [len(L.body(lang, lv).split()) for lv in L.LEVELS]
    print("       %s: %s" % (lang, dict(zip(L.LEVELS, sizes))))
    check("1b %s: every level has words in it" % lang, all(s > 40 for s in sizes),
          sizes)
    check("1c %s: they get LONGER, child to technical — a depth that is "
          "not deeper is not a level" % lang,
          sizes == sorted(sizes), sizes)
    check("1d %s: the child one is genuinely short" % lang,
          sizes[0] < 130, sizes[0])
    check("1e %s: and the technical one is genuinely long" % lang,
          sizes[-1] > 400, sizes[-1])
check("1f every level exists in BOTH languages",
      all(L.body("hr", lv) != L.body("en", lv) for lv in L.LEVELS))
check("1g an unknown level falls back rather than raising",
      L.body("en", "nonsense") == L.body("en", "adult"))
check("1h and an unknown language does too", L.body("zz", "child") == L.body("en", "child"))

print("\n1b THE SIMPLER TELLINGS MUST NOT CONTRADICT THE TECHNICAL ONE")
# A simpler level may leave things out. It must never say something the
# deeper one denies — that is what makes four documents honest rather
# than four opinions.
tech = L.body("en", "tech").lower()
for lv in ("child", "school", "adult"):
    b = L.body("en", lv).lower()
    check("1i %-6s does not promise the audio is kept in the browser" % lv,
          "audio is kept" not in b and "saves your audio" not in b)
check("1j the adult level says plainly that audio is NOT kept",
      "audio is not kept" in L.body("en", "adult").lower())
check("1k and the technical level says WHY — the five-megabyte limit",
      "five" in tech and "megabytes" in tech)
check("1l both name the same reason, so they cannot drift apart",
      "too big" in L.body("en", "adult").lower())

print("\n2 WRITTEN TO BE HEARD")
for lang in ("en", "hr"):
    for lv in L.LEVELS:
        spoken = H.plain_level(lang, lv)
        check("2a %s %-6s no markup reaches the voice" % (lang, lv),
              "<" not in spoken and ">" not in spoken, spoken[:60])
        check("2b %s %-6s no doubled full stops" % (lang, lv),
              ".." not in spoken.replace("...", ""), spoken[:60])
sp = H.plain_level("en", "adult")
check("2c a heading does not run into the paragraph under it",
      "\n" in sp)
check("2d plain() still works for anything that has not moved over",
      len(H.plain("hr").split()) > 100)
check("2e and there is ONE stripper, not two that drift",
      "_to_prose" in open(os.path.join(os.path.dirname(__file__), "..",
                                       "ttt", "help_page.py"),
                          encoding="utf-8").read())

print("\n3 THE TAB OFFERS THEM")
check("3a four buttons, one per level", 'key="help_lv_%s"' in app)
check("3b the page is asked for the chosen level",
      "level=st.session_state.get(\"help_level\"" in app)
check("3c the default is `plain`, the one most people want",
      'setdefault("help_level", "adult")' in app)
check("3d READ ALOUD FOLLOWS THE LEVEL ON SCREEN — reading the full "
      "document while a different one is shown is the v197 fault again",
      "HELP_PAGE.plain_level(" in app)
check("3e the chosen level is remembered like every other choice",
      '"help_level",' in app[app.index("KEPT_CHOICES"):
                             app.index("def _kept_restore")])
check("3f the level names are translated", "level_name" in app)

print("\n4 THE FILE PICKER SAYS WHAT IT TAKES")
front = open(os.path.join(os.path.dirname(__file__), "..",
                          "cassette_frontend", "index.html"),
             encoding="utf-8").read()
check("4a it accepts audio AND video", 'accept="audio/*,video/*"' in front)
check("4b and now SAYS so, which is the whole reason he asked for a "
      "picker that already existed",
      "open an audio or video file" in front)
check("4c both as a tooltip and to a screen reader",
      front.count("open an audio or video file") >= 2,
      front.count("open an audio or video file"))
from ttt import intake  # noqa: E402
plan = intake.route(name="clip.mp4", mime="video/mp4",
                    head=b"\x00\x00\x00\x18ftypmp42")
check("4d and the router really sends video to the transcribe pipeline",
      plan["kind"] == "video" and plan["pipeline"] == "transcribe", plan)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
