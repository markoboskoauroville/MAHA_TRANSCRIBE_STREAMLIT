"""THE TEST THAT CATCHES SHAKING.

HANDOVER.md, order of work item 2: "measure a fixed word's bounding box
before and during highlight. If x or y moves one pixel, the approach is
wrong."

Real Chromium, real layout. Not a judgement about whether it looks fine —
a number. A highlight is stepped across a sentence and the position of
EVERY OTHER word is measured at each step. Any word that is not the
highlighted one must not move at all, ever.
"""
import sys

# PLAYWRIGHT IS OPTIONAL — it is in requirements-dev.txt, not in the app's
# own requirements, and Baba's Mac does not have it. Missing, this used to
# be a traceback at import, which under pytest is a collection error rather
# than the honest answer: this test did not run.
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    _WHY = ("playwright is not installed — pip install -r requirements-dev.txt"
            " && python3 -m playwright install chromium")
    if "pytest" in sys.modules:
        import pytest
        pytest.skip(_WHY, allow_module_level=True)
    print(_WHY)
    sys.exit(1)

# The two candidates, written exactly as the app writes them.
CURRENT = ('background:#f59e0b;color:#0b0d10;border-radius:4px;'
           'padding:1px 4px;')

# Colour only. Nothing here participates in layout: colour never does, and
# text-shadow is painted outside the box model, so it can carry the extra
# emphasis that bold or a background would otherwise have to.
# Background fill WITHOUT padding. A background is painted; it does not
# participate in the box model, so it cannot move anything. Only the
# padding ever did. This keeps the amber fill the design language calls
# for, and the 9.06 contrast of dark text on amber, while removing the
# one property that reflows the line.
# READ FROM THE APP, not copied. A test that holds its own copy of the
# style passes forever while the shipped style drifts back to padding.
import re as _re, pathlib as _pl
_src = _pl.Path('app.py').read_text()
SHIPPED = _re.search(r"hl = '([^']+)'", _src).group(1)
PROPOSED = SHIPPED
COLOUR_ONLY = 'color:#ef4444;'   # what actually ships now

# THE SECOND DEFINITION. HANDOVER §0: when a style is fixed in one place,
# look for another rule doing the same job before believing it is done.
# reader.py had its own copy and would have kept shaking on its own.
_rsrc = _pl.Path('ttt/reader.py').read_text()
# reader.py builds its span from a constant, so read the constant.
READER = 'color:' + _re.search(r'HL_WORD = "([^"]+)"', _rsrc).group(1) + ';'

SENTENCE = ("Sound is the first of the elements to reach a child and the "
            "last to leave a dying person which is why every tradition "
            "begins and ends with listening.")


def page_html(style, hi_index):
    words = SENTENCE.split()
    out = []
    for i, w in enumerate(words):
        if i == hi_index:
            out.append(f'<span id="w{i}" style="{style}">{w}</span>')
        else:
            out.append(f'<span id="w{i}">{w}</span>')
    return ("<html><body style='margin:0;padding:20px;width:320px;"
            "font:16px/1.6 system-ui;background:#0b0d10;color:#e5e7eb'>"
            + " ".join(out) + "</body></html>")


def measure(page, style, hi_index):
    page.set_content(page_html(style, hi_index))
    boxes = {}
    for i in range(len(SENTENCE.split())):
        b = page.locator(f"#w{i}").bounding_box()
        boxes[i] = (round(b["x"], 2), round(b["y"], 2))
    return boxes


def run(page, style, label):
    words = SENTENCE.split()
    base = measure(page, style, -1)          # nothing highlighted
    worst_dx = worst_dy = 0.0
    moved_total = 0
    for hi in range(len(words)):
        cur = measure(page, style, hi)
        for i, (x, y) in cur.items():
            if i == hi:
                continue                     # the highlighted word may move
            dx = abs(x - base[i][0])
            dy = abs(y - base[i][1])
            if dx > 0.5 or dy > 0.5:
                moved_total += 1
            worst_dx = max(worst_dx, dx)
            worst_dy = max(worst_dy, dy)
    n = len(words) * (len(words) - 1)
    print(f"{label:<28} worst dx {worst_dx:>6.1f}px   worst dy {worst_dy:>6.1f}px   "
          f"words displaced {moved_total}/{n}")
    return worst_dx, worst_dy


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 500, "height": 700})

    print(f"sentence: {len(SENTENCE.split())} words, 320px column (phone)\n")
    cx, cy = run(page, CURRENT, "CURRENT (padding+bg)")
    px, py = run(page, PROPOSED, "PROPOSED (bg, no padding)")
    ox, oy = run(page, COLOUR_ONLY, "colour only (for comparison)")
    rx, ry = run(page, READER, "reader.py (2nd definition)")
    b.close()

print()
ok = True
if cx <= 0.5 and cy <= 0.5:
    print("UNEXPECTED: the current style does not shake — investigate before changing it")
    ok = False
else:
    print(f"current style SHAKES: unhighlighted words move up to "
          f"{max(cx, cy):.0f}px")
if rx > 0.5 or ry > 0.5:
    print(f"READER VIEW STILL SHAKES by {max(rx, ry):.1f}px — "
          f"the second definition was missed")
    ok = False
else:
    print("reader.py: not one pixel of movement either")
if px > 0.5 or py > 0.5:
    print(f"PROPOSED STILL SHAKES by {max(px, py):.1f}px — not good enough")
    ok = False
else:
    print("proposed style: not one pixel of movement in any word, at any step")


def test_shake():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_shake.py` is how it is meant to be read."""
    assert ok, "a word still moves between steps — see the output above"


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(0 if ok else 1)
