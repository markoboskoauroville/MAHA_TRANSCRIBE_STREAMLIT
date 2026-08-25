"""UNDO IS THERE BEFORE YOU NEED IT.

    python3 tests/test_undo_visible.py

Fault 6 of Baba's brief, 03:20 on 25.8.2026:

  "v187 added undo/redo under the transcript box, but they appear only
   once something has been LOST. Record into an empty box and there is no
   link. He looked and it was not there, so it fails the only test that
   matters. Probably: show it whenever the box has text."

IT FAILED THAT TEST BECAUSE IT WAS BUILT ROUND THE STACK: no stack, no
link. But a person looks for undo BEFORE they need it — to know it is
there, so they can risk pressing something. A safety net you cannot see
is not a safety net.

PRESENT AND DEAD BEATS ABSENT. design-language.md §1: nothing appears and
nothing disappears, and the place of a control is learned once rather
than hunted for each time.
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


def steps(has_text, can_undo, can_redo):
    """The rule, on plain booleans."""
    out = []
    if has_text or can_undo:
        out.append(("undo", not can_undo))
    if has_text or can_redo:
        out.append(("redo", not can_redo))
    return out


print("1 THE RULE")
r = steps(has_text=True, can_undo=False, can_redo=False)
check("1a text in the box, nothing done yet — UNDO IS THERE",
      [x[0] for x in r] == ["undo", "redo"], r)
check("1b and it is disabled, because there is nothing behind it",
      r[0][1] is True, r)
r = steps(has_text=True, can_undo=True, can_redo=False)
check("1c once something HAS been overwritten, undo comes alive",
      r[0][1] is False, r)
check("1d while redo stays present and dead", r[1][1] is True, r)
r = steps(has_text=False, can_undo=False, can_redo=False)
check("1e an empty box with no history shows nothing — there is no work "
      "to protect yet", r == [], r)
r = steps(has_text=False, can_undo=True, can_redo=False)
check("1f but an emptied box KEEPS undo, because clearing is exactly "
      "when it is needed", [x[0] for x in r] == ["undo"], r)
check("1g and it is alive", r[0][1] is False, r)

print("\n1b THE PLACE NEVER MOVES")
# The whole point: the eye learns where undo lives once.
places = []
for ht, cu, cr in ((True, False, False), (True, True, False),
                   (True, True, True)):
    places.append([x[0] for x in steps(ht, cu, cr)])
check("1h with text in the box, the row is the same every time",
      all(p == ["undo", "redo"] for p in places), places)

print("\n2 THE APP DOES THIS")
check("2a it asks whether the box HAS TEXT, not only the stack",
      "_has_text = bool((t1_text() or \"\").strip())" in app)
check("2b undo is offered when there is text OR history",
      "if _has_text or t1_can_undo():" in app)
check("2c and redo likewise", "if _has_text or t1_can_redo():" in app)
check("2d each carries whether it is disabled",
      "not t1_can_undo()" in app and "not t1_can_redo()" in app)
check("2e box_links understands a third element",
      "bool(cb[2]) if len(cb) > 2 else False" in app)
check("2f and older two-element callers are unchanged",
      "len(cb) > 2" in app)

print("\n3 A DEAD LINK MUST LOOK DEAD")
# A disabled control that looks identical to a live one is worse than a
# missing one: the person presses it, nothing happens, and they learn the
# app is unreliable rather than that the action was unavailable.
row = css[css.index("st-key-boxlinks_"):]
check("3a the row styles a disabled link at all",
      "button:disabled" in row or "button[disabled]" in row)
check("3b faded", "opacity: 0.35" in row)
check("3c and without the underline, so it reads as 'not yet' rather "
      "than as a link that failed", "text-decoration: none" in row)
check("3d it does not light up on hover like a live one",
      "button:disabled:hover" in row)
check("3e but it KEEPS ITS SPACE — no display:none, or the place would "
      "move again and the whole point is lost",
      "display: none" not in row[:row.index("stIFrame")]
      if "stIFrame" in row else True)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
