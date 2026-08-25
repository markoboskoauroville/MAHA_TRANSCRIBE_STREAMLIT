"""DIRECTION TAGS — the direction moves into the text.

    python3 tests/test_vr_tags.py

Baba, 25.8.2026: "You remove checkboxes, I don't need checkbox, forget
it... if I press calm it will insert where my cursor is. It starts with
less than sign, it says calm, greater than sign. And that's the emotion
to read the following sentence until the new direction is found. And even
a few directions can be in one line: angry, afraid, tender."

TEST 1 is the tag model on plain strings and dicts — no Streamlit.
TEST 2 reads the VR tab and says what it searched for.

WHAT THIS CANNOT CATCH: that the row WRAPS at 390px, and that the caret
is the person's real caret. See the note at the end of section 2.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import vr as V  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

print("1 THE TAG ITSELF")
check("1a one word", V.tag_for("calm") == "<calm>", V.tag_for("calm"))
check("1b several in ONE pair of brackets, not several pairs",
      V.tag_for(["angry", "afraid", "tender"]) == "<angry, afraid, tender>",
      V.tag_for(["angry", "afraid", "tender"]))
check("1c case and spaces do not matter", V.tag_for(["  CALM "]) == "<calm>")
check("1d nothing in, nothing out", V.tag_for([]) == "" and V.tag_for("") == "")
check("1e blanks are dropped, not turned into empty brackets",
      V.tag_for(["", "  ", "sad"]) == "<sad>")

print("\n2 INSERTING AT THE CARET")
body = "The door opened. Who let you in?"
t1, c1 = V.insert_tag(body, 17, V.tag_for("angry"))
check("2a it lands at the caret", t1 == "The door opened. <angry> Who let you in?", t1)
check("2b and the caret moves past what was inserted", c1 == 17 + len("<angry> "), c1)
t2, c2 = V.insert_tag(body, None, V.tag_for("calm"))
check("2c no caret means the end — the honest answer when nothing said",
      t2.endswith("<calm> "), t2[-20:])
# THESE TWO HAD TO BE SHARPENED. The first version used caret 900 on
# "short" and caret -5 on "short", and BOTH passed with the clamp
# removed — Python slicing tolerates an index past the end, and -5 on a
# 5-character string happens to land on 0 anyway. Two checks that could
# not fail, proven by mutating the clamp away and watching them stay
# green. The returned CARET and a longer string separate them.
t3, c3 = V.insert_tag("short", 900, V.tag_for("sad"))
check("2d a caret past the end is CLAMPED — the text is right",
      t3 == "short<sad> ", t3)
check("2d2 and the caret it hands back is inside the text, not 900",
      c3 == len("short") + len("<sad> "), c3)
t4, c4 = V.insert_tag("abcdefgh", -3, V.tag_for("sad"))
check("2e a negative caret clamps to the START, it does not count "
      "backwards from the end", t4 == "<sad> abcdefgh", t4)
check("2e2 and hands back a caret at the start", c4 == len("<sad> "), c4)
check("2f a space follows the tag, so it is not glued to the next word",
      V.insert_tag("word", 0, "<calm>")[0] == "<calm> word")
check("2g nothing is inserted for an empty tag",
      V.insert_tag("word", 2, "") == ("word", 2))
check("2h inserting into an empty box works",
      V.insert_tag("", None, "<calm>")[0] == "<calm> ")

print("\n3 WHAT THE TAGS MEAN — from here until the next one")
script = "<calm>The door opened. <angry, afraid>Who let you in? Answer me."
segs = V.split_directed(script)
check("3a two segments", len(segs) == 2, segs)
check("3b the first is calm", segs[0] == (["calm"], "The door opened."), segs[0])
check("3c the second carries BOTH words and runs to the end",
      segs[1] == (["angry", "afraid"], "Who let you in? Answer me."), segs[1])
plain = V.split_directed("No markup at all.")
check("3d text with no tag is spoken with NO direction, not with a guess",
      plain == [([], "No markup at all.")], plain)
lead = V.split_directed("Before. <sad>After.")
check("3e text BEFORE the first tag keeps no direction",
      lead[0] == ([], "Before."), lead[0])
check("3f two tags in a row do not make a silent take",
      V.split_directed("<calm><sad>Words.") == [(["sad"], "Words.")],
      V.split_directed("<calm><sad>Words."))
check("3g a tag at the very end is not a request to speak nothing",
      V.split_directed("Words. <calm>") == [([], "Words.")],
      V.split_directed("Words. <calm>"))
check("3h tags_in reads them back in order",
      V.tags_in(script) == [["calm"], ["angry", "afraid"]], V.tags_in(script))
check("3i strip_tags leaves only the words",
      V.strip_tags(script) == "The door opened. Who let you in? Answer me.",
      V.strip_tags(script))

print("\n3b THE UGLY CASES")
check("3j an unclosed bracket is text, not a tag",
      V.tags_in("<calm The door") == [], V.tags_in("<calm The door"))
check("3k empty brackets are ignored", V.tags_in("<>Words") == [])
check("3l a tag written by hand in capitals still works",
      V.tags_in("<CALM>x") == [["calm"]])
check("3m spaces inside the brackets are forgiven",
      V.tags_in("<  angry ,  sad >x") == [["angry", "sad"]],
      V.tags_in("<  angry ,  sad >x"))
check("3n empty text is no segments, not a crash", V.split_directed("") == [])
check("3o Croatian survives a round trip",
      V.strip_tags("<tužno>Čuo sam đavola.") == "Čuo sam đavola.")

print("\n4 HIS OWN DIRECTIONS")
st = {}
V.add_own(st, "like a priest")
V.add_own(st, "half asleep")
check("4a newest first — the one just written is the one wanted again",
      V.own_of(st) == ["half asleep", "like a priest"], V.own_of(st))
V.add_own(st, "LIKE A PRIEST")
check("4b the same words twice do not make two pills",
      len(V.own_of(st)) == 2, V.own_of(st))
check("4c and it moves to the front", V.own_of(st)[0] == "LIKE A PRIEST",
      V.own_of(st))
V.add_own(st, "   ")
check("4d blank is not a direction", len(V.own_of(st)) == 2)
big = {}
for i in range(40):
    V.add_own(big, "d%d" % i)
check("4e the list is capped — a panel, not an archive",
      len(V.own_of(big)) == V.MAX_OWN, len(V.own_of(big)))
V.remove_own(st, "half asleep")
check("4f one can be taken off again", len(V.own_of(st)) == 1)
check("4g a custom direction makes a tag like any other",
      V.tag_for(["like a priest"]) == "<like a priest>")

print("\n5 THE TAB USES IT")
app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
tab = app[app.index('elif active == "vr":'):app.index('elif active == "looks":')]
print("       searched the vr tab, %d chars" % len(tab))
# SCOPED TO THE DIRECTION PANEL. The first version searched the WHOLE vr
# tab and went red when a checkbox arrived on the CAST panel for the
# preview setting — a true statement about the wrong region. The claim is
# that the DIRECTIONS are no longer tick-boxes, not that the tab contains
# no checkbox anywhere.
_dir = tab[tab.index("THE DIRECTION, AS TAGS IN THE TEXT"):]
# THE CLAIM IS ABOUT THE WORDS, NOT ABOUT THE PANEL. There IS a checkbox
# here now — the write/copy switch — and asserting none existed was
# describing the old shape rather than the rule. What must be gone is a
# tick-box PER DIRECTION, which is what `vre_` keyed.
check("5a no direction is a tick-box any more",
      "vre_" not in _dir, [x for x in ("vre_",) if x in _dir])
check("5a2 the only checkbox in the panel is the write/copy switch",
      _dir.count("st.checkbox") == 1, _dir.count("st.checkbox"))
check("5b and so are the ? help marks as separate controls",
      "vr_too_many" not in tab or "help=_phr" in tab)
check("5c pressing a word INSERTS a tag", "VR.insert_tag(" in tab)
check("5d the phrase survives as the pill's own tooltip",
      "help=tip" in tab and "_phr)" in tab, "_phr" in tab)
check("5e his own directions have an add", 't("vr_add")' in tab)
check("5f which saves them for the session", "VR.add_own(" in tab)
check("5g and inserts the tag in the same press",
      "_vr_insert([word])" in tab)
check("5h the field is emptied in the CALLBACK, not after the widget "
      "is drawn — §63",
      '"vr_own_new"] = ""' in tab
      and tab.index('"vr_own_new"] = ""') < tab.index('_oc1.text_input'))
check("5i saved directions are rendered as pills of their own",
      "_tag_rows([(_w, [_w]" in tab)

print("\n5c WRITE IT, OR COPY IT")
# The caret cannot be known — Streamlit has no way to ask. Baba's answer:
# a checkbox that turns every direction pill into a copy, so HE places it.
check("5p there is a switch between writing and copying",
      'key="vr_tag_clip"' in tab)
check("5q it is off by default, so the existing behaviour is unchanged "
      "for anyone who does not touch it",
      'setdefault("vr_tag_clip", False)' in tab)
check("5r in clipboard mode the whole grid is ONE component, not one "
      "iframe per pill — twelve blocks cannot share a row",
      "copybtn.pill_grid(" in tab and "cp_html(" not in tab,
      [x for x in ("cp_html(",) if x in tab])
check("5s and each pill carries the TAG, not the bare word",
      "VR.tag_for(w)" in tab)
check("5t writing mode still inserts", "on_click=_vr_insert" in tab)
check("5u both rows go through ONE helper, so the built-ins and his own "
      "cannot behave differently",
      tab.count("def _tag_rows") == 1 and tab.count("_tag_rows(") >= 3,
      tab.count("_tag_rows("))
check("5u2 the component is given a height, or the last row is clipped "
      "— an iframe does not grow to fit",
      "copybtn.grid_height(" in tab)
check("5u3 and the colours are handed over, since an iframe inherits "
      "none of the page's variables",
      'theme.tone("surface2", _sch)' in tab and '"scheme"' in tab)
check("5v the hint line says WHICH mode is in force",
      't("vr_clip_hint")' in tab and 't("vr_tag_hint")' in tab)

print("\n5b REHEARSE SPEAKS THE TAGS, IT DOES NOT READ THEM OUT")
# The trap this nearly shipped with: _vr_go read the checkbox store,
# which nothing writes any more. It would have sent a neutral direction
# for the whole line AND spoken the markup — "less than calm greater
# than, the door opened."
check("5j it splits the text into directed segments",
      "VR.split_directed(raw)" in tab)
check("5k each segment gets its OWN direction",
      "VR.build_direction(words)" in tab)
check("5l it no longer reads the store nothing writes",
      "VR.picked_of(" not in tab and "VR.note_of(" not in tab,
      [x for x in ("VR.picked_of(", "VR.note_of(") if x in tab])
check("5m WAV answers are joined through ffmpeg, not concatenated — "
      "each is a whole file with its own header",
      "SPEECH.join_audio(" in tab)
check("5n one segment does not pay for a join it does not need",
      "if len(pieces) == 1:" in tab)
check("5o the temporary files are cleaned up on the failure path too",
      tab.count("ttt_audio.cleanup(") >= 2, tab.count("ttt_audio.cleanup("))

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
