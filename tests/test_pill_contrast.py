"""NO PILL IS EVER ITS OWN BACKGROUND COLOUR.

    python3 tests/test_pill_contrast.py

Baba photographed the VR panel switch as a solid amber lozenge with no
label on it, 25.8.2026: "the button is only colour, I don't see what's
underneath. This is not acceptable in this app."

THE CAUSE was a selector written for one row finding every row that
shared its shape. `button[role="radio"]:last-child p { color: amber
!important }` was meant for the owner's gear at the end of the TAB BAR.
It matched the last pill of every segmented control in the app, including
VR's two-pill switch — and when that pill was selected its background
went amber too. Amber on amber is not poor contrast, it is nothing.

WHAT THIS CANNOT CATCH: how it actually looks. This reads the generated
stylesheet, so it can prove the rules cannot paint a label the colour of
its own background, and cannot prove the result is legible at 390px.
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import theme  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

print("1 THE OWNER-GEAR RULE STAYS IN THE TAB BAR")
for scheme in ("amber", "green", "cyan", "paper"):
    css = theme.css(scheme, "mono", 1.0)
    # every rule that forces a label amber must be scoped to the nav
    unscoped = []
    for m in re.finditer(r'([^{}]*:last-child[^{}]*)\{([^}]*)\}', css):
        sel, body = m.group(1), m.group(2)
        if "--amber" in body and "st-key-active_tab" not in sel:
            unscoped.append(sel.strip()[:70])
    check("1%s in the %s scheme, no unscoped :last-child amber label rule"
          % ("abcd"[("amber","green","cyan","paper").index(scheme)], scheme),
          not unscoped, unscoped)

print("\n2 A SELECTED PILL IS ALWAYS READABLE")
print("       searched the built stylesheet for aria-checked=\"true\" blocks")
css = theme.css("amber", "mono", 1.0)
blocks = re.findall(r'aria-checked="true"\][^{{]*\{([^}]*)\}', css)
check("2a the checked state is styled at all", len(blocks) >= 2, len(blocks))
label = [b for b in blocks if "color:" in b and "background" not in b]
check("2b the checked LABEL colour is !important, so no position rule "
      "can outrank it",
      any("!important" in b and "var(--bg)" in b for b in label), label)
check("2c and it is the page background colour, i.e. the opposite of amber",
      any("var(--bg)" in b for b in label), label)

print("\n2b THE TWO RULES CANNOT BOTH MATCH")
# The v191 scoping made the :last-child rule MORE specific than the
# checked rule, so the LAST tab (H) went amber-on-amber when selected —
# the same fault the scoping cured for VR, moved one tab along.
# Specificity is not the fix; non-overlap is.
#
# A PLAIN SUBSTRING TEST, DELIBERATELY. The first version of this check
# was a regex over selector/body pairs, and it reported GREEN on a
# mutation that removed the guard — a check that passes for the wrong
# reason, which four-tests.md calls the dangerous kind because it is
# invisible. Every :last-child occurrence is now looked at directly.
print("       searched each ':last-child' in the built stylesheet")
for scheme in ("amber", "green", "cyan", "paper"):
    c = theme.css(scheme, "mono", 1.0)
    bad = []
    for m in re.finditer(r":last-child", c):
        # the selector is what sits between the previous '}' or '*/' and
        # the '{' that opens this rule
        opens = c.find("{", m.end())
        closes = c.find("}", opens)
        sel = c[max(c.rfind("}", 0, m.start()),
                    c.rfind("*/", 0, m.start())):m.end()]
        body = c[opens:closes]
        if "--amber" in body and 'aria-checked="true"' not in sel:
            bad.append(sel.strip()[-70:])
    check("2%s in %s, every :last-child amber rule excludes the selected "
          "state" % ("defg"[("amber", "green", "cyan", "paper").index(scheme)],
                     scheme), not bad, bad)

print("\n3 THE VR SWITCH IS NOT THE NAV BAR")
print("       searched app.py for the two segmented_control keys")
app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
check("3a the nav bar is keyed active_tab", 'key="active_tab"' in app)
check("3b the VR switch is keyed _vr_panel", 'key="_vr_panel"' in app)
check("3c they are different keys, so scoping by key separates them",
      'key="active_tab"' in app and 'key="_vr_panel"' in app)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
