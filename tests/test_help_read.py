"""HELP YOU CAN LISTEN TO — the text, and the row that speaks it.

    python3 tests/test_help_read.py

THE POINT, in one line: the people this app is written for do not read
easily, which is why R exists. Help that can only be READ is hardest for
exactly the person most likely to need it.

TEST 1 is help_page.plain(), a pure function on a string — no Streamlit,
no voice. TEST 2 greps the tab and says what it searched for.

WHAT THIS CANNOT CATCH: how it SOUNDS. Edge is a real network call and
this file never makes one.
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import help_page as H  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

print("1 THE HELP AS SPEAKABLE PROSE")
for code, name in (("hr", "Croatian"), ("en", "English")):
    p = H.plain(code)
    lines = p.splitlines()
    print("       %s: %d chars, %d lines" % (name, len(p), len(lines)))
    check("1a %s produces text at all" % name, len(p) > 1000, len(p))
    check("1b %s carries no markup — a voice must never read a tag" % name,
          "<" not in p and ">" not in p,
          [x for x in lines if "<" in x][:1])
    check("1c %s has no HTML entities left" % name,
          "&nbsp;" not in p and "&amp;" not in p and "&#" not in p)
    check("1d %s never doubles a full stop after ? or !" % name,
          not [x for x in lines if re.search(r"[.!?:]\.$", x)],
          [x for x in lines if re.search(r"[.!?:]\.$", x)][:1])
    check("1e %s ends every line with something a voice can pause on"
          % name,
          all(x.rstrip().endswith((".", "!", "?", ":", "—")) for x in lines),
          [x for x in lines if not x.rstrip().endswith((".", "!", "?", ":", "—"))][:1])

print("\n1b THE TWO LANGUAGES DO NOT LEAK INTO EACH OTHER")
hr, en = H.plain("hr"), H.plain("en")
check("1f Croatian is not the English text", hr != en)
check("1g the Croatian does not contain the English opening",
      "What is TTT-LLL" not in hr)
check("1h the English does not contain the Croatian opening",
      "Što je TTT-LLL" not in en)
check("1i an unknown language falls back to English, not to a crash",
      H.plain("zz") == en)

print("\n1c SOURCE LINE BREAKS ARE NOT SENTENCE BREAKS")
# The HTML is hand-wrapped at about 76 columns. Keeping those breaks made
# the voice read half a sentence, stop, and read the other half.
check("1j a wrapped paragraph comes back as ONE line",
      any(len(x) > 90 for x in hr.splitlines()),
      max(len(x) for x in hr.splitlines()))
check("1k and a table row reads as a phrase, not a word list",
      any("—" in x for x in en.splitlines()))

print("\n2 THE ROW AT THE TOP OF HELP")
app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
tab = app[app.index('elif active == "help":'):]
tab = tab[:tab.index('elif active == "log":')]
print("       searched the help tab, %d chars, for the player, the two "
      "genders and the read action" % len(tab))
check("2a there is a player", 'key="help_player"' in tab)
check("2b female and male are both there",
      't("tr_voice_f")' in tab and 't("tr_voice_m")' in tab)
check("2c read is there", 't("help_read")' in tab)
check("2d the player is drawn BEFORE the toggle — transport first, "
      "like every other deck",
      tab.index('key="help_player"') < tab.index('t("tr_voice_f")'))
check("2e read comes after the two genders it depends on",
      tab.index('t("help_read")') > tab.index('t("tr_voice_m")'))
check("2f the voice follows the page's own language, not a fixed one",
      'ui_lang' in tab and "tk.vkey_for(lang" in tab)
check("2g it speaks plain(), not the HTML page",
      "HELP_PAGE.plain(lang)" in tab)
check("2h a voice that refuses is a sentence, not a traceback",
      't("help_read_fail")' in tab and "errlog.add" in tab)
check("2i the player is drawn whether or not there is audio — nothing "
      "appears, nothing disappears",
      "startable=bool(_hlp_audio)" in tab)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
