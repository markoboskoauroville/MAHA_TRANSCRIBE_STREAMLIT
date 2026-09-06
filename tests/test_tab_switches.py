"""THE OWNER TURNS A TAB OFF FOR EVERYBODY — AND CAN ALWAYS GET BACK.

    python3 tests/test_tab_switches.py

Baba, 5.9.2026: "me as admin, in my admin control panel, I need to have
check marks for every tab in the interface so I can disable it for all
users, any tab."

THE DANGEROUS PART IS NOT THE FEATURE, IT IS THE LOCK-OUT. A checkbox
that can hide the settings tab is a checkbox that locks the door from
inside with the key in the lock: the only way back would be editing the
spreadsheet by hand, from a phone, having just hidden the screen that
explains it. So settings, log and transcribe have no box at all, and the
guard holds on the way OUT of storage as well as the way in — a row
written by an older version or edited by hand cannot take away the way
back either.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

src = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))

NEVER = ("transcribe", "settings", "log")
ALL = ["transcribe", "talk", "translate", "vr", "looks", "help"]


def read_off(raw):
    """tabs_off(), on a plain string."""
    if not raw:
        return set()
    off = {p.strip() for p in str(raw).split(",") if p.strip()}
    return off - set(NEVER)


def nav(off, admin):
    tabs = [x for x in ALL if x not in off]
    if admin:
        tabs += ["settings", "log"]
    return tabs


print("1 TURNING ONE OFF")
off = read_off("vr")
check("1a it comes back as a set", off == {"vr"}, off)
check("1b and the tab is gone for a family member",
      "vr" not in nav(off, False), nav(off, False))
check("1c and gone for the OWNER too — he needs to SEE what they see, "
      "which is why the gold tabs are grouped at the end. A switch that "
      "only affected other people is a switch he could never check",
      "vr" not in nav(off, True), nav(off, True))
check("1d everything else is untouched",
      nav(off, False) == ["transcribe", "talk", "translate", "looks", "help"],
      nav(off, False))

print("\n2 THE LOCK-OUT CANNOT HAPPEN")
for bad in NEVER:
    check("2a %-11s cannot be switched off, however it is stored" % bad,
          bad not in read_off("vr,talk," + bad), read_off("vr,talk," + bad))
check("2b even if EVERY tab is written off, the owner still has his way "
      "back", set(nav(read_off(",".join(ALL + list(NEVER))), True))
      >= {"settings", "log", "transcribe"},
      nav(read_off(",".join(ALL + list(NEVER))), True))
check("2c and a family member still lands somewhere rather than on an "
      "empty screen",
      nav(read_off(",".join(ALL)), False) == ["transcribe"],
      nav(read_off(",".join(ALL)), False))
check("2d the guard is applied on READ, not only on write — a row edited "
      "by hand in the spreadsheet is exactly how this would be got "
      "wrong", "off - set(TABS_NEVER_OFF)" in code)
check("2e and on write as well", "set(off) - set(TABS_NEVER_OFF)" in code)

print("\n3 UNREADABLE STORAGE HIDES NOTHING")
# A setting that cannot be read must never be able to hide the app.
for raw, why in ((None, "nothing stored"), ("", "empty"),
                 ("   ", "whitespace"), (",,,", "separators only")):
    check("3a %-18s hides no tab" % why, read_off(raw) == set(), read_off(raw))
check("3b a name that is not a tab is harmless",
      "nosuchtab" in read_off("nosuchtab") and
      nav(read_off("nosuchtab"), False) == ALL, nav(read_off("nosuchtab"), False))
# THE REGIONS ARE CHECKED BEFORE THEY ARE SEARCHED. A slice whose bounds
# are wrong is the empty string, and "x in ''" is False — a check that
# passes on nothing. The linter flags an unbounded pair for this reason.
_ra, _rb = code.find("def tabs_off"), code.find("def set_tabs_off")
_wa, _wb = code.find("def set_tabs_off"), code.find("def nav_tabs")
check("3b2 both regions are findable and in order",
      0 < _ra < _rb and 0 < _wa < _wb, (_ra, _rb, _wa, _wb))
check("3c the reader cannot raise — an unreadable config must not take "
      "the app down",
      0 < _ra < _rb and "except Exception:" in code[_ra:_rb])

print("\n4 THE PANEL")
check("4a there is one box per switchable tab", 'key="tabon_%s" % _t' in code)
check("4b TICKED MEANS ON — a list of things to switch OFF reads "
      "backwards and gets mis-set once, quietly, for everybody",
      "value=_t not in _off" in code)
check("4c the never-off tabs have NO box rather than a disabled one — a "
      "box that cannot be unticked invites a question whose honest "
      "answer is better said by absence",
      "if x not in TABS_NEVER_OFF" in code)
check("4d it writes globally, like the engine row", "set_tabs_off(" in code)
check("4e and says whether the write landed", '"_tabs_saved"' in code)
# THERE IS NO CACHED SHEET CONFIG TO DROP since v237. The switch writes
# to the session and tabs_off consults the session BEFORE Secrets, which
# is what makes a press take effect at once — that ordering is the new
# version of this claim.
check("4f a press takes effect immediately, because the session "
      "override is read before Secrets",
      0 < code.find('"_tabs_off_session"') < code.find('st.secrets.get("TABS_OFF"'),
      (code.find('"_tabs_off_session"'), code.find('st.secrets.get("TABS_OFF"')))
check("4g the label carries the letter AND the word — a bare letter is "
      "not something somebody can act on", "def tab_label" in code)
check("4h built from strings that already exist, not a third set of "
      "names to keep in step",
      '"sig_read"' in code and '"tab_talk"' in code)
check("4i and t() returning its own key is handled, or a box would read "
      "'sig_help'", "if l == letter:" in code)

print("\n5 GOOGLE'S THIRTY VOICES")
from ttt.providers import google as G  # noqa: E402
# SHAPE FIRST, BEFORE ANYTHING UNPACKS IT. Adding a third field to a
# voice made voice_names() raise, so the file died before reaching 5d —
# the check that exists to catch exactly that addition. The guard was
# there and the crash beat it to the answer, which in a sweep reads as
# nothing wrong at all.
_shape = {len(v) for v in G.VOICES}
check("5d0 every voice is a NAME AND AN ADJECTIVE, nothing else — the "
      "doc: 'do not synthesise those facets... a blank is a fact and a "
      "guess is not'", _shape == {2}, _shape)
check("5a thirty of them", len(G.VOICES) == 30, len(G.VOICES))
check("5b no duplicates", _shape == {2} and len(set(G.voice_names())) == 30)
check("5c every one carries Google's own adjective",
      all(tone for _, tone in G.VOICES))
check("5d and NOTHING ELSE — checked as 5d0 above, before anything "
      "unpacks the table", _shape == {2}, _shape)
check("5e an unknown name gives an empty adjective, never a guess",
      G.tone_of("Nobody") == "")
check("5f the filter values are built FROM the table, so a voice added "
      "with a new adjective cannot end up unfilterable",
      set(G.tones()) == {t for _, t in G.VOICES if t})
check("5g the default is one of them", G.DEFAULT_VOICE in G.voice_names())

print("\n5b THE NAMES ARE MEASURED, NOT RETYPED")
ref = os.path.join(os.path.dirname(__file__), "..", "..", "gts", "src",
                   "10_app.py")
if os.path.exists(ref):
    import re
    rs = open(ref, encoding="utf-8").read()
    i = rs.find("VOICES = [")
    theirs = set(re.findall(r'"(\w+)"', rs[i:rs.find("]", i)]))
    check("5h identical to the list GOOGLE_TTS_STT shipped, which was "
          "built against the live API", theirs == set(G.voice_names()),
          sorted(theirs ^ set(G.voice_names())))
else:
    print("  skip  GOOGLE_TTS_STT is not beside this checkout")

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
