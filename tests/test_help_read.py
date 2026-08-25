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
tab = tab[:tab.index("HELP_PAGE.page(")]
print("       searched the help tab, %d chars" % len(tab))
check("2a female and male are both there",
      't("tr_voice_f")' in tab and 't("tr_voice_m")' in tab)
check("2b read is there", 't("help_read")' in tab)
check("2c read comes after the two genders it depends on",
      tab.index('t("help_read")') > tab.index('t("tr_voice_m")'))
check("2d the voice follows help's OWN language value",
      'st.session_state.get("help_lang"' in tab
      and "VOICES_BY_LANG.get(lang)" in tab)
check("2e it speaks plain(), not the HTML page",
      "HELP_PAGE.plain(lang)" in tab)

print("\n2b IT USES R'S DECK — it does not grow a second one")
# Baba: "it takes forever... generate one paragraph at a time, keep the
# logic of a tape deck." R's _talk_job IS that deck: doubling blocks so
# the first is ONE sentence, three built in parallel while it plays.
# A second copy here is the fault README rule 1 names by name.
check("2f read hands the text to the reader's own job",
      '"talk_text"] = HELP_PAGE.plain' in tab)
check("2g and starts it the way the reader starts",
      '"_auto_read"] = True' in tab)
check("2h it does NOT synthesise the whole document up front",
      "synth_sentence" not in tab and "block_texts" not in tab, tab[:200])
check("2i it does NOT build a second player",
      "_wave_component(" not in tab)
check("2j the gender picks a real reader voice, not an invented name",
      "VOICES_BY_LANG" in tab and '"voice"] = names[' in tab)

print("\n2b2 ONE LANGUAGE CONTROL, NOT TWO THAT DISAGREE")
# Baba switched language with the toggle INSIDE the page, pressed read,
# and got English: the screen followed localStorage and the voice
# followed ui_lang. Two controls for one idea, disagreeing in silence.
check("2l the tab has its own HR/ENG buttons",
      'key="help_l_hr"' in tab and 'key="help_l_en"' in tab)
# BOUNDED SLICE. The first version searched from the help tab to the END
# OF THE FILE and stayed green when the toggle was turned back on — a
# check that cannot fail is a rumour. It reads the actual page call now.
_pc = app.index("HELP_PAGE.page(")
_pcall = app[_pc:app.index(")", app.index("show_toggle", _pc)) + 1]
print("       the page call: %s" % " ".join(_pcall.split()))
check("2m the page's own toggle is hidden, so there is only one",
      "show_toggle=False" in _pcall, _pcall)
check("2n the SAME value drives the page and the voice",
      tab.count('"help_lang"') >= 2, tab.count('"help_lang"'))
check("2o it starts from ui_lang but never overwrites it — reading help "
      "in Croatian must not retranslate the whole app",
      '"ui_lang"' in tab and '"ui_lang"] =' not in tab)
hp = open(os.path.join(os.path.dirname(__file__), "..", "ttt",
                       "help_page.py"), encoding="utf-8").read()
check("2p a hidden toggle cannot blank the page — the wiring is guarded",
      "if (_h)" in hp and "if (_e)" in hp)

print("\n2c AND PLAY STARTS IT, because R's idle deck already does")
rtab = app[app.index('key="talk_player_idle"'):]
rtab = rtab[:rtab.index("def _clear_talk")]
check("2k a press of play on the idle deck is a start",
      '_ev0.get("start")' in rtab and "_start = True" in rtab)

print("\n2d A NEW READING REPLACES THE ONE PLAYING")
# The fault that trapped him: _auto_read is consumed in the WRITING
# branch, so with a job already running the script took the playing
# branch and never saw the flag. Nothing on screen could clear it,
# because everything that starts a reading sets that same flag.
rj = app[app.index('    job = st.session_state.get("_talk_job")\n\n'):]
rj = rj[:rj.index("# ---- PLAYING")]
check("2q a pending _auto_read drops a job already running",
      'st.session_state.get("_auto_read") and job' in rj, rj[-200:])
check("2r and the stamps go with it, or the new reading skips a hand-off",
      "_talk_player_seen" in rj and "_talk_start_seen" in rj)
check("2s the fix lives in R, not in the help tab — five callers set "
      "that flag",
      '_auto_read' not in tab or tab.count('"_auto_read"') == 1)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
