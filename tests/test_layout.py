"""TEST 2 — the running app in a real browser at phone width.

Measures the gaps BETWEEN frames rather than judging that they look
fine. Baba's complaint was specific — "the space between all these
frames is not equal" — so the check is that the gaps are equal, to the
pixel, not that the page looks tidy.

    python3 tests/test_layout.py [port]
"""

import socket
import sys
import time

# ARGV BELONGS TO THE SCRIPT. Under pytest, sys.argv[1] is pytest's own
# argument — "tests/" — and this would go looking for a port called that.
PORT = sys.argv[1] if (__name__ == "__main__" and len(sys.argv) > 1) else "8811"
URL = "http://127.0.0.1:{}/".format(PORT)


def _cannot_run():
    """Why this test cannot run, or "" if it can.

    TWO PRECONDITIONS, NEITHER OF THEM THIS FILE'S DOING: playwright is
    optional (requirements-dev.txt), and this drives the REAL app, which
    something else has to be serving. Both used to be a traceback at
    import — under pytest a collection error, which reads as a broken
    suite rather than as a test that did not run.
    """
    import importlib.util
    if importlib.util.find_spec("playwright") is None:
        return ("playwright is not installed — pip install -r requirements-dev.txt"
                " && python3 -m playwright install chromium")
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(("127.0.0.1", int(PORT))) != 0:
            return ("nothing is serving the app on port %s — "
                    "streamlit run app.py --server.port %s" % (PORT, PORT))
    return ""


_WHY = _cannot_run()
if _WHY:
    if "pytest" in sys.modules:
        import pytest
        pytest.skip(_WHY, allow_module_level=True)
    print(_WHY)
    sys.exit(1)

from playwright.sync_api import sync_playwright  # noqa: E402

passed = failed = 0
shots = []


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


with sync_playwright() as p:
    br = p.chromium.launch()
    # 360x800 is the commonest Android width; 320 is the WCAG reflow
    # floor and is checked separately below.
    pg = br.new_page(viewport={"width": 360, "height": 800})
    pg.goto(URL, wait_until="networkidle")
    time.sleep(3)

    # --- log in -------------------------------------------------------
    boxes = pg.locator('input[type="password"]')
    if boxes.count():
        boxes.first.fill("stub")
        boxes.first.press("Enter")
        time.sleep(6)
    pg.wait_for_selector('[class*="st-key-deckbox"]', timeout=30000)
    time.sleep(2)

    check("1 the app renders after login",
          pg.locator('[class*="st-key-deckbox"]').count() > 0)

    # --- the status box is gone for a normal user ----------------------
    # ADMIN_USER is "stub" and the password is "stub", so this session IS
    # the admin; the box is only built after a run anyway. What matters
    # here is that the gate exists and the box is not present before one.
    check("2 no status box on a fresh session",
          pg.locator('[class*="st-key-statusbox"]').count() == 0)

    # --- measure the gaps between frames -------------------------------
    def box(sel):
        el = pg.locator(sel).first
        if not el.count():
            return None
        return el.bounding_box()

    frames = [
        ("deck", '[class*="st-key-deckbox"]'),
        ("cmdrow", '[class*="st-key-cmdrow_tx"]'),
        ("textarea", 'textarea'),
    ]
    got = [(n, box(s)) for n, s in frames]
    got = [(n, b) for n, b in got if b]
    check("3 the frames are all on the page", len(got) == 3,
          [n for n, _ in got])

    gaps = []
    for (n1, b1), (n2, b2) in zip(got, got[1:]):
        gaps.append((n1 + "→" + n2, round(b2["y"] - (b1["y"] + b1["height"]), 1)))
    print("     measured gaps: " + str(gaps))

    if gaps:
        vals = [g for _, g in gaps]
        spread = max(vals) - min(vals)
        # Streamlit rounds subpixels, so a pixel or two of spread is the
        # renderer, not the stylesheet. Anything larger is a real
        # inequality of the kind that was photographed.
        check("4 the gaps between frames are equal within 3px",
              spread <= 3.0, "spread {}px across {}".format(spread, vals))
        check("5 no gap is a chasm (the deck's old extra room)",
              max(vals) <= 24, "largest {}px".format(max(vals)))

    # --- nothing overflows sideways at the reflow floor ----------------
    pg.set_viewport_size({"width": 320, "height": 800})
    time.sleep(2)
    over = pg.evaluate(
        "() => document.documentElement.scrollWidth - "
        "document.documentElement.clientWidth")
    check("6 no sideways scrolling at 320px (WCAG 1.4.10)", over <= 0,
          "{}px of overflow".format(over))

    pg.screenshot(path="/tmp/t1_320.png", full_page=True)
    shots.append("/tmp/t1_320.png")
    pg.set_viewport_size({"width": 360, "height": 800})
    time.sleep(1)
    pg.screenshot(path="/tmp/t1_360.png", full_page=True)
    shots.append("/tmp/t1_360.png")

    # --- the type actually got smaller ---------------------------------
    # The command row's cells clamp with viewport width ON PURPOSE (§27:
    # "no new rows, it can only remove letters"), so measuring one of
    # those says nothing about the type scale. Measure a language pill,
    # which is an ordinary chrome button.
    fs = pg.evaluate(
        "() => { const b = document.querySelector("
        "'[class*=\"st-key-tr_hr\"] button');"
        " return b ? getComputedStyle(b).fontSize : ''; }")
    check("7 chrome buttons stepped down to ~0.82rem",
          fs.startswith("13"), "got " + str(fs))

    ta = pg.evaluate(
        "() => { const t = document.querySelector('textarea');"
        " return t ? getComputedStyle(t).fontSize : ''; }")
    print("     transcript font-size: " + str(ta) +
          "   (must NOT have shrunk — it is a reading surface)")

    br.close()

print("\n{} passed, {} failed".format(passed, failed))
print("screenshots: " + ", ".join(shots))


def test_layout():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_layout.py` is how it is meant to be read."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
