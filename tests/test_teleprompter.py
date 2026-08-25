"""THE TELEPROMPTER, AND SAVE THAT SAVES THE WHOLE MEAL.

    python3 tests/test_teleprompter.py

Baba, 25.8.2026:
  "it doesn't scroll. It should be as a teleprompter. The current
   sentence should always jump in the middle of the view."
  "we're going to copy the same concept to the R tab."
  "it just saves current segment... we need to create a meal out of
   sausages, not to save one sausage."

WHAT THIS CANNOT CATCH: whether it actually scrolls. scrollIntoView is
the browser's, and no test here runs one. What is checked is that the
marker exists, is unique, and that nothing else can claim it.
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import theme  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
front = open(os.path.join(os.path.dirname(__file__), "..",
                          "waveform_frontend", "index.html"),
             encoding="utf-8").read()
css = theme.css("amber", "mono", 1.0)

print("1 THE VR TELEPROMPTER")
vr = app[app.index("def _vr_script"):app.index("_vr_script(_vr_job)")]
check("1a the spoken block carries a marker", "id='vrhere'" in vr)
check("1b exactly ONE block gets it — the current one",
      vr.count("id='vrhere'") == 1 and 'if i == here else ""' in vr)
check("1c it is put in the MIDDLE, not merely scrolled to",
      "block:'center'" in vr)
check("1d smoothly, so it reads as a teleprompter and not a jump",
      "behavior:'smooth'" in vr)
check("1e and it is guarded — a missing element must not throw",
      "if(e&&e.scrollIntoView)" in vr)

print("\n2 THE R TELEPROMPTER — the same idea, its own marker")
# BOUNDED BY THE NEXT def, not by a function 103,000 characters away.
# My first slice ran from _render_page to read_sentences_live and
# swallowed the entire VR tab, so "vrhere is not in R's code" was false
# for a reason that had nothing to do with R.
_i = app.index("def _render_page")
rd = app[_i:app.index("\ndef ", _i + 10)]
print("       R's renderer: %d chars" % len(rd))
check("2a the spoken sentence carries a marker", "id='rdhere'" in rd)
check("2b centred and smooth, exactly as VR",
      "block:'center'" in rd and "behavior:'smooth'" in rd)
check("2c guarded the same way", "if(e&&e.scrollIntoView)" in rd)
check("2d R KEEPS ITS WORD HIGHLIGHT — Whisper gives word timings and "
      "Hume does not, so R can do what VR cannot",
      "_highlight_span(s, word_start, word_end)" in rd)
# CODE, NOT PROSE. "vrhere" IS in R's renderer — in the docstring that
# explains why the two markers differ. A check that cannot tell an
# explanation from an implementation would force the explanation to be
# deleted to stay green, which is the tail wagging the dog.
def _live(block):
    out, indoc = [], False
    for line in block.splitlines():
        if line.count('"""') == 1:
            indoc = not indoc
            continue
        if indoc or line.lstrip().startswith("#"):
            continue
        out.append(line)
    return "\n".join(out)


_rdc, _vrc = _live(rd), _live(vr)
check("2e the two markers are DIFFERENT in the CODE, so the tabs cannot "
      "fight over the same id",
      "vrhere" not in _rdc and "rdhere" not in _vrc,
      [x for x in ("vrhere",) if x in _rdc])
check("2e2 and each renderer emits only its own",
      "rdhere" in _rdc and "vrhere" in _vrc)
check("2f both ids appear exactly once in the whole file",
      app.count("id='rdhere'") == 1 and app.count("id='vrhere'") == 1,
      (app.count("id='rdhere'"), app.count("id='vrhere'")))
check("2g both have a scrolling box in the stylesheet",
      ".rdscript" in css and ".vrscript" in css)
check("2h and both scroll smoothly",
      css.count("scroll-behavior: smooth") >= 2)

print("\n3 SAVE MEANS THE WHOLE READING")
check("3a the deck no longer downloads audio.src — that was one block",
      "a.href=audio.src" not in front, "a.href=audio.src" in front)
check("3b it REPORTS the press instead", '{at: Date.now(), save: true}' in front)
check("3c and PAUSES first, because the download is the priority",
      re.search(r"audio\.pause\(\);\s*\n\s*setPlaying\(false\);\s*\n"
                r"\s*setValue\(\{at: Date\.now\(\), save: true\}\)", front)
      is not None)
check("3d Python answers the press", '_vr_ev.get("save")' in app)
check("3e by stitching EVERY block, building the missing ones",
      "stitch_reading(len(job.get" in app)
check("3f guarded by a stamp, so one press is one file",
      '"_vr_save_seen"' in app)
check("3g the finished file goes back DOWN to the deck",
      "dl=(" in app and "dl_at=" in app)
check("3h and the deck saves it once, guarded by its own stamp",
      "a.dl_at!==DELIVERED" in front)
check("3i the block-finished handler ignores a save press, or one press "
      "would also advance the reading",
      'and not _vr_ev.get("save")' in app)

print("\n3b THERE IS ONLY ONE CONTROL NOW")
# The original complaint: he pressed the obvious one and got a sausage.
check("3j the second stitch button is gone", "vr_stitch_go" not in app)
check("3k and its download button with it", "vr_dl_all" not in app)
check("3l the stitcher is defined BEFORE the player that calls it — "
      "after it, the first press would be a NameError",
      app.index("def _vr_stitch") < app.index('key="vr_player"'),
      (app.index("def _vr_stitch"), app.index('key="vr_player"')))
check("3m R's whole-reading save is still its own button, because R's "
      "deck is a different component instance",
      "rd_stitch_go" in app)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
