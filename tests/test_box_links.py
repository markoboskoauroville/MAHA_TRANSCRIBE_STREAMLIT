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
from ttt import a11y  # noqa: E402


def _root_rule():
    """The html/:root font-size rule, or '' if there is none.

    The whole sizing rule rests on there being none, so it is measured
    here rather than asserted in a comment.
    """
    import re
    m = re.search(r"(?:html|:root)\s*\{[^}]*font-size:\s*[^;]+;",
                  a11y.css(1.5))
    return m.group(0) if m else ""

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
css = theme.css("amber", "mono", 1.0)

print("1 ONE NUMBER, BOTH SIDES")
# THIS SECTION ASSERTED THE WRONG RULE AND WAS GREEN. It said the
# component size must GROW with the text dial, and mutated correctly, and
# was wrong: MEASURED, a11y.css never sets a root font-size, so `0.72rem`
# on the Streamlit links resolves against the BROWSER DEFAULT and is
# 11.5px at every setting. Multiplying by the scale made the component
# disagree with its neighbours at every scale except 1.0 — the exact
# mismatch v220 claimed to fix. Baba photographed it.
#
# checking-the-checks.md face 8: a test perfectly correct about the wrong
# rule. Written the same day as the module.
sizes = [theme.box_link_px(sc) for sc in (0.6, 0.8, 1.0, 1.5, 2.5)]
print("       link px across the whole dial: %s" % sizes)
print("       what the neighbours render at: %.1fpx" % (0.72 * 16))
check("1a it is the SAME at every text size, because the neighbours are",
      len(set(sizes)) == 1, sizes)
check("1b and it matches what 0.72rem actually resolves to",
      abs(sizes[0] - 0.72 * 16) <= 1, sizes[0])
check("1c a11y really does NOT scale the root — the fact the whole rule "
      "rests on",
      "font-size" not in _root_rule(), _root_rule())
check("1d the rem the page uses is the one this is derived from",
      str(theme.BOX_LINK_REM) in css, theme.BOX_LINK_REM)

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

print("\n2c EVERY ACTION FOR A BOX IS IN ITS ROW — INCLUDING REHEARSE")
# Baba photographed this: "the rehearse is flying in the air and they're
# not the same size and font." It sat in its own container, LEFT-aligned,
# with a gap under it, while copy and clear were right-aligned in the row
# — two action links for the same box, in two places, at two sizes.
#
# Mutation C put it back in its own container and NOTHING WENT RED,
# because nothing asserted where it lived. A rule with no check is a
# rule until the next person moves it.
check("2g rehearse is an extra ON the row, not a container of its own",
      't("vr_speak")' in app
      and app.index('t("vr_speak")') > app.index('box_links("vrbox"')
      and app.index('t("vr_speak")') < app.index('kept_area("vr_text"'),
      "rehearse is not between box_links and the box")
check("2h its old container is gone", 'key="nact_vr"' not in app,
      'key="nact_vr"' in app)
check("2i and it keeps its disabled state and its countdown, which is "
      "what an extra's third element is for",
      '("nact_vr_go", _vr_go, bool(_left) or not _has)' in app)

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
