"""EVERY ACTION IN THE SAME CORNER, AND ALL THE SAME SIZE.

    python3 tests/test_box_links.py

Baba, 25.8.2026, with a photograph: "fix this inconsistency in size of
the action buttons and change the rule. Every action button is at the top
of the text box in the upper right corner. So we are moving all action
buttons related to the text boxes to the upper right corner."

TWO FAULTS IN ONE ROW.

  THE SIZE. `copy` is a COMPONENT in an iframe; `clear` and `add to
  notes` are Streamlit buttons on the page. MEASURED: the buttons are
  0.72rem, which follows the reader's text-size dial, and the component
  was a fixed 14px, which follows nothing. They differ at the default and
  every step on the dial pushes them further apart — they could not have
  matched at any setting. HOW_WE_WORK: two stylesheets cannot be kept in
  step by reasoning about them.

  THE PLACE. The row hung under the box, and each tab puts a different
  number of things under it, so the eye had to find the actions again in
  every tab. Above and right is one corner to learn.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import theme  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
css = theme.css("amber", "mono", 1.0)

print("1 ONE NUMBER, BOTH SIDES")
for scale, want in ((1.0, 12), (1.5, 17), (2.5, 29)):
    got = theme.box_link_px(scale)
    print("       text scale %.1f -> %dpx" % (scale, got))
    check("1a scale %.1f gives %dpx" % (scale, want), got == want, got)
check("1b it never collapses to nothing at a small scale",
      theme.box_link_px(0.1) >= 9, theme.box_link_px(0.1))
check("1c and it GROWS with the reader's dial — a fixed size could not "
      "match a rem at any setting but one",
      theme.box_link_px(2.0) > theme.box_link_px(1.0))
check("1d the rem the page uses is the one this is derived from",
      "font-size: %srem" % theme.BOX_LINK_REM in css
      or str(theme.BOX_LINK_REM) in css, theme.BOX_LINK_REM)

print("\n1b THE COMPONENT IS TOLD, NOT LEFT TO GUESS")
check("1e cp_html takes the pixel size", "link_px" in
      open(os.path.join(os.path.dirname(__file__), "..", "ttt",
                        "copybtn.py"), encoding="utf-8").read())
check("1f and box_links passes it", "link_px=theme.box_link_px(" in app)
check("1g read from the SAME place the page reads it",
      app.count("theme.box_link_px(") >= 2, app.count("theme.box_link_px("))
check("1h the iframe's height follows the size too, or a bigger link is "
      "clipped by a fixed box",
      "height=int(theme.box_link_px(" in app)
check("1i there is no fixed 14 left in the component's link mode",
      "px = int(link_px or 14)" in
      open(os.path.join(os.path.dirname(__file__), "..", "ttt",
                        "copybtn.py"), encoding="utf-8").read())

print("\n2 EVERY ROW ABOVE ITS OWN BOX")
PAIRS = (("tx", "key=_area_key,"),
         ("rd", 'kept_area("talk_text"'),
         ("trsrc", 'kept_area("translate_src_text"'),
         ("trout", 'kept_area("translate_out"'),
         ("vrbox", 'kept_area("vr_text"'))
for slot, box in PAIRS:
    a, b = app.index('box_links("%s"' % slot), app.index(box)
    check("2a %-6s actions are ABOVE the box" % slot, a < b, (a, b))
check("2b all five boxes have a row — none was left behind",
      len(PAIRS) == app.count("box_links(") - 1,
      (len(PAIRS), app.count("box_links(")))

print("\n2b AND IN THE SAME CORNER")
row = css[css.index("st-key-boxlinks_"):]
row = row[:row.index("st-key-note_")] if "st-key-note_" in row else row[:1800]
check("2c right-aligned", "justify-content: flex-end" in row)
check("2d glued DOWNWARD now — the row is the top edge of the writing "
      "surface, so the gap it closes is the one below it",
      "margin-bottom: -" in row, row[:200])
check("2e and not upward any more", "margin-top: -0.7rem" not in row)
check("2f an empty box gets the gap back, or the single link sits on "
      "the border and reads as part of it",
      "_empty" in css and "margin-bottom: 0.2rem" in css)

print("\n3 THE THINGS THAT MOVED WITH IT")
# Moving a row above the box moves it above whatever it depends on.
for name in ("_steps", "_trsrc_body", "_trout_body"):
    check("3a %s is defined before the row that uses it" % name,
          app.index("%s = " % name) < app.index("if %s else None" % name)
          if ("if %s else None" % name) in app
          else app.index("%s = " % name) < app.index("extra=_steps"),
          name)
check("3b _vr_clear is defined before the VR row",
      app.index("def _vr_clear") < app.index('box_links("vrbox"'))

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
