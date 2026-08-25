"""THE THREE THINGS BABA SAW IN THE SCREENSHOTS, checked as text.

    python3 tests/test_layout_fixes.py

HONEST ABOUT WHAT THIS IS: a source inspection, not a browser. It cannot
tell you the signature LOOKS aligned — only that nothing adds padding on
the side he asked about, and that the elements are in the order he asked
for. G5's lesson from the gate: a pattern check must SAY what it searched
for, because a check that finds nothing and one that runs nothing look
identical from outside. Every check below prints its needle.
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
APP = os.path.join(os.path.dirname(__file__), "..", "app.py")
THEME = os.path.join(os.path.dirname(__file__), "..", "ttt", "theme.py")
passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(APP, encoding="utf-8").read()
theme = open(THEME, encoding="utf-8").read()

print("1 THE SIGNATURE SITS ON THE SAME MARGIN AS THE FRAME")
print("       searched theme.py for '.tabsig {' and '.block-container {'")
sig = theme[theme.index(".tabsig {"):]
sig = sig[:sig.index("}}")]
blk = theme[theme.index(".block-container {"):]
blk = blk[:blk.index("}}")]
m_blk = re.search(r"padding:\s*0\s+(\d+)px\s+(\d+)px", blk)
check("1a the frame's own inset is readable from the stylesheet", bool(m_blk), blk[:120])
check("1b the signature adds NO padding of its own on the right",
      re.search(r"padding-right:\s*0\s*;", sig) is not None,
      re.search(r"padding-right:\s*[^;]+;", sig))
check("1c so it lands on the frame's %spx, like the player and the box"
      % (m_blk.group(1) if m_blk else "?"), bool(m_blk))
check("1d it is still right-aligned", "text-align: right" in sig)
check("1e and the BADGE is dodged by the page, not by this line",
      m_blk is not None and int(m_blk.group(2)) >= 60,
      m_blk.group(2) if m_blk else None)

print("\n2 PRESS PLAY TO READ IS UNDER THE PLAYER")
print("       searched app.py for 'talk_player_idle', 'rd_hint' and the R text box")
# THE IDLE DECK LOST ITS SEPARATE KEY IN v222 — that split WAS the double
# play, and merging it was the fix. index() then raised here and killed
# the file, so this suite has printed nothing since.
i_player = app.rfind('key="talk_player"')
check("0a the idle deck is still rendered at all", i_player > 0, i_player)
i_hint = app.index('t("rd_hint")', i_player)
# THE BOX IS A kept_area NOW, so it no longer carries key="talk_text".
# The claim is about ORDER — hint above the box — not about how the box
# is spelled.
i_box = app.index('kept_area("talk_text"', i_player)
check("2a the hint comes AFTER the player", i_hint > i_player, (i_player, i_hint))
check("2b and BEFORE the text box — not at the bottom", i_hint < i_box, (i_hint, i_box))
check("2c there is exactly one of it in R",
      app.count('t("rd_hint")') == 1, app.count('t("rd_hint")'))

print("\n3 THE TWO SIZE ROWS — stacked, matching, nothing off the edge")
print("       searched app.py between 'looksgroup_size' and 'looksgroup_font'")
blk = app[app.index("looksgroup_size"):app.index("looksgroup_font")]
check("3a interface size has a default at all", 'key="iface_default"' in blk)
check("3b text size still has its own", 'key="size_default"' in blk)
check("3c they call different handlers, not the same one twice",
      "_iface_default" in blk and "_size_default" in blk)
check("3d the default it restores is 100%",
      re.search(r"def _iface_default\(\):.*?ui_scale\"\] = 1\.0", blk, re.S)
      is not None)

# NOTHING GOES OFF THE SCREEN — design-language.md §10, written after
# v190 put six columns on one line and the sixth landed half off a 390px
# phone. The fix is stacking, and a check that only counts controls would
# have stayed green through the whole fault.
rows = re.findall(r"st\.columns\(\[([^\]]*)\]\)", blk)
print("       column rows found: %s" % rows)
check("3e each size is its OWN row, not both crammed into one",
      len(rows) == 2, rows)
check("3f no row asks for more than three columns",
      all(len(r.split(",")) <= 3 for r in rows), rows)
check("3g the two rows have the SAME shape, so they line up down the page",
      len(set(r.replace(" ", "") for r in rows)) == 1, rows)

# SAME JOB, SAME WIDGET. One default rendered as an underlined link and
# the other as a filled pill, in the same row, which reads as two
# different features.
defaults = re.findall(r'_[si]d\.(\w+)\(t\("looks_default"\)', blk)
print("       widgets used for the two defaults: %s" % defaults)
check("3h both defaults are the same kind of control",
      len(defaults) == 2 and len(set(defaults)) == 1, defaults)
check("3i and both are buttons, because a default DOES something",
      defaults == ["button", "button"], defaults)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
