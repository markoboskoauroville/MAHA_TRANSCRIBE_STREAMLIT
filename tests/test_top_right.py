"""THE TOP RIGHT HOLDS EVERYTHING TECHNICAL (Marko, 7.9.2026): the admin
panel, then the version, then log out, one under the other. Behind the
door log out is the door's own /logout; on Streamlit Cloud it stays a
button in the foot (it must call log_out()). The version left the foot.

    python3 tests/test_top_right.py

1  the mechanism: the pieces of the top bar, read off _foot_line's source
2  the running app: on Cloud (no door) the foot has the log out button and
   the top bar has the version and no /logout; behind the door the top bar
   has admin panel, version, /logout in that order and the foot has no
   log out button
3  ugly: a plain user behind the door gets version and log out, no admin
4  upgrade: the foot still has the three engine buttons; the version is
   drawn exactly once on the page
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from streamlit.testing.v1 import AppTest        # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RAW = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
CODE = re.sub(r'"""(?:.|\n)*?"""', "", "\n".join(l for l in RAW.splitlines() if not l.lstrip().startswith("#")))
VERSION = re.search(r'^APP_VERSION = "(v\d+)"', RAW, re.M).group(1)

print("1 THE MECHANISM, ALONE")
foot = CODE[CODE.find("def _foot_line("):CODE.find("def name_the_symbols(")]
check("_foot_line is there", len(foot) > 100)
a, v, lo = foot.find('href="/portal/admin"'), foot.find("mahatop_v"), foot.find('href="/logout"')
check("admin panel, then version, then log out — in that order in the source", 0 < a < v < lo, (a, v, lo))
check("the admin link goes to /portal/admin, which both doors pass to the portal", 'href="/portal/admin"' in foot)
check("log out in the bar only behind the door", re.search(r"if via_door:\s*\n\s*right\.append\('<a class=\"mahatop_r\" href=\"/logout\"", foot) is not None)
check("the foot's log out button only where there is no door", re.search(r"if not via_door:\s*\n\s*st\.button\(t\(\"log_out_link\"\), key=\"foot_logout\"", foot) is not None)
check("the version is not drawn in the foot any more", "tabsig_v" not in foot)
theme = open(os.path.join(ROOT, "ttt", "theme.py"), encoding="utf-8").read()
check("the right column stacks its rows and ends at the right edge",
      re.search(r"\.mahatop_col \{\{[^}]*flex-direction: column[^}]*align-items: flex-end", theme) is not None)
check("the version is dimmer and not underlined", re.search(r"\.mahatop_v \{\{[^}]*opacity: 0\.55[^}]*text-decoration: none", theme) is not None)


def run(door=None):
    """The app under AppTest; door = (user, role) puts the person through the door."""
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=60)
    at.session_state["_authed"] = True
    at.session_state["_user"] = door[0] if door else "cloudy"
    if door:
        at.session_state["_via_portal"] = True
        at.session_state["_view_tier"] = "admin" if door[1] == "admin" else "free"
    at.run()
    return at


def top_bar(at):
    for m in at.markdown:
        if 'class="mahatop"' in m.value:
            return m.value
    return ""


print("2 IN THE RUNNING APP")
cloud = run()
bar = top_bar(cloud)
check("the top bar is drawn on Cloud", bool(bar))
check("it carries the version", VERSION in bar, bar)
check("it carries no /logout on Cloud", "/logout" not in bar)
check("and no admin panel", "admin panel" not in bar)
keys = [b.key for b in cloud.button]
check("the foot's log out button is there on Cloud", "foot_logout" in keys, keys)

door = run(("marko", "admin"))
bar = top_bar(door)
check("the top bar is drawn behind the door", bool(bar))
i_a, i_v, i_l = bar.find("admin panel"), bar.find(VERSION), bar.find('href="/logout"')
check("admin panel, version, log out — in that order on the page", 0 < i_a < i_v < i_l, (i_a, i_v, i_l))
check("admin panel points at /portal/admin", 'href="/portal/admin"' in bar)
keys = [b.key for b in door.button]
check("the foot has no log out button behind the door", "foot_logout" not in keys, keys)

print("3 THE UGLY CASES")
plain = run(("emina", "user"))
bar = top_bar(plain)
check("a plain person behind the door: version and log out", VERSION in bar and 'href="/logout"' in bar)
check("but no admin panel", "admin panel" not in bar)

print("4 UPGRADE")
keys = [b.key for b in door.button]
check("the engine buttons still stand in the foot", any(k.startswith("eng_pick_") for k in keys), keys)
page = "".join(m.value for m in door.markdown)
check("the version is on the page exactly once", page.count(VERSION) == 1, page.count(VERSION))

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
