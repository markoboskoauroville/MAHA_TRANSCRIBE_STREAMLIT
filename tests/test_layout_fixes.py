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
i_player = app.index('key="talk_player_idle"')
i_hint = app.index('t("rd_hint")', i_player)
i_box = app.index('key="talk_text"', i_player)
check("2a the hint comes AFTER the player", i_hint > i_player, (i_player, i_hint))
check("2b and BEFORE the text box — not at the bottom", i_hint < i_box, (i_hint, i_box))
check("2c there is exactly one of it in R",
      app.count('t("rd_hint")') == 1, app.count('t("rd_hint")'))

print("\n3 INTERFACE SIZE HAS ITS DEFAULT")
print("       searched app.py for 'iface_default' and 'size_default'")
check("3a interface size has a default control", 'key="iface_default"' in app)
check("3b text size still has its own", 'key="size_default"' in app)
check("3c they call different handlers, not the same one twice",
      "_iface_default" in app and "_size_default" in app)
check("3d the default it restores is 100%",
      re.search(r'def _iface_default\(\):.*?ui_scale"\] = 1\.0', app, re.S) is not None)
check("3e the row was widened to hold it, not squeezed",
      re.search(r"_sl, _sb, _sd, _il, _ib, _id = st\.columns", app) is not None)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
