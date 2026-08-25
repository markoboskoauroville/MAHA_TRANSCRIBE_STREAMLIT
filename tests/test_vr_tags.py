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

print("\n5b REHEARSE PLANS, IT DOES NOT READ THE TAGS OUT")
# The trap this nearly shipped with: _vr_go read the checkbox store,
# which nothing writes any more. It would have sent a neutral direction
# for the whole line AND spoken the markup out loud.
#
# THE JOIN CHECKS THAT LIVED HERE ARE GONE ON PURPOSE. Blocks are played
# in turn now rather than concatenated, so there is nothing to join and
# no WAV header to trip over. Section 6 checks what replaced them.
check("5j it plans the reading into directed blocks",
      "VR.plan_directed(raw" in tab)
check("5k each block carries its OWN direction",
      "VR.build_direction(words)" in tab)
check("5l it no longer reads the store nothing writes",
      "VR.picked_of(" not in tab and "VR.note_of(" not in tab,
      [x for x in ("VR.picked_of(", "VR.note_of(") if x in tab])
# THE CLAIM IS ABOUT THE READING PATH, NOT THE WHOLE TAB. join_audio
# came back in v207 for the STITCHER, which is a different job: making
# one file to keep, once, on purpose. What must not come back is a join
# on the way to the PLAYER, because that is what made the whole text
# render before a word played. My first version asserted the string was
# absent anywhere and went red on a correct change.
# THE SLICE RAN BACKWARDS. _vr_block is defined ABOVE _vr_go in the
# tab, so [_vr_go : _vr_block] covered NOTHING and the check passed
# on an empty string — it stayed green when a join was injected into
# the reading path. Bounded by the end of _vr_go instead.
_go = tab.index("def _vr_go")
_play = tab[_go:tab.index("with st.container(key=\"nact_vr\")", _go)]
check("5m the READING path joins nothing — blocks are played in turn",
      "join_audio" not in _play, _play[-200:])


# --- 6. TEASPOON GENERATION -------------------------------------------
# Baba: "Generate 1 sentence. While this is playing, generate 4. While
# those 4 are playing, generate the next 4. For any length of text."
print("\n6 THE PLAN — 1, then 4, and never across a direction")
P = V.plan_directed


def shape(text, **kw):
    return [(",".join(w), len(ss)) for w, ss in P(text, **kw)]


check("6a the first block is ONE sentence, so sound starts at once",
      P("One. Two. Three. Four. Five. Six.")[0][1] == ["One."],
      P("One. Two. Three. Four. Five. Six.")[0][1])
check("6b then fours",
      [n for _, n in shape("A. B. C. D. E. F. G. H. I. J.")] == [1, 4, 4, 1],
      shape("A. B. C. D. E. F. G. H. I. J."))
check("6c a long text keeps going in fours, whatever its length",
      set(n for _, n in shape(" ".join("S%d." % i for i in range(41)))[1:-1])
      == {4},
      shape(" ".join("S%d." % i for i in range(41))))

print("\n6b A BLOCK NEVER SPANS TWO DIRECTIONS")
# One Hume request carries ONE description, so a tag ends the block even
# when it has room left.
sh = shape("<calm>One. Two. Three. Four. Five. Six. <angry>Seven. Eight.")
print("       %s" % sh)
check("6d the calm run breaks into 1 then 4 then the remainder",
      [n for w, n in sh if w == "calm"] == [1, 4, 1], sh)
check("6e and the angry text starts its OWN block",
      [w for w, _ in sh][-1] == "angry", sh)
check("6f a tag mid-run does not merge with what came before",
      P("<calm>A. B. <sad>C.")[-1][0] == ["sad"], P("<calm>A. B. <sad>C."))

print("\n6c THE COUNT RUNS ACROSS THE WHOLE READING")
# If it restarted at every tag, the one-sentence wait would come back
# every time the acting turned.
sh2 = shape("<calm>A. <sad>B. C. D. E. F.")
print("       %s" % sh2)
check("6g only the FIRST block of the reading is one sentence",
      [n for _, n in sh2] == [1, 4, 1], sh2)

print("\n6d THE UGLY CASES")
check("6h empty text is no plan", P("") == [])
check("6i text with no tags still plans",
      len(P("One. Two. Three. Four. Five.")) == 2,
      shape("One. Two. Three. Four. Five."))
check("6j a tag with nothing after it produces no empty block",
      P("A. <calm>") == [([], ["A."])], P("A. <calm>"))
huge = "x" * 4000 + "."
check("6k a sentence past the budget is taken alone",
      P(huge + " B. C.")[0][1] == [huge], len(P(huge + " B. C.")[0][1]))
check("6l block_text joins a block for the voice",
      V.block_text(([], ["A.", "B."])) == "A. B.")
check("6m first=0 means no fast start",
      shape("A. B. C. D. E.", first=0) == [("", 4), ("", 1)],
      shape("A. B. C. D. E.", first=0))

print("\n6e THE TAB BUILDS ONE BLOCK AT A TIME")
print("       searched the vr tab for the deck")
check("6n rehearse PLANS rather than synthesising everything",
      "VR.plan_directed(raw" in tab)
check("6o there is a per-block builder", "def _vr_block" in tab)
check("6p the player is told which block of how many",
      '_vr_job["index"] + 1' in tab and 'len(_vr_job["parts"])' in tab)
check("6q a finished block advances the index", '_vr_job["index"] += 1' in tab)
check("6r guarded by a stamp, so one finish is one advance",
      '"_vr_seen"' in tab)
check("6s it builds ahead while playing", "PREFETCH_AHEAD" in tab)
check("6t the prefetch runs AFTER the player is drawn",
      tab.index('key="vr_player"') < tab.index("PREFETCH_AHEAD"))
check("6u ONE AT A TIME, because Hume's limit is per minute — a batch is "
      "what makes a wall of 429s that poisons the next minute too",
      "ThreadPoolExecutor" not in tab)
check("6v a refusing block ends the job instead of retrying every redraw",
      '_cur.get("err")' in tab and 'pop("_vr_job", None)' in tab)
check("6w each block is levelled, since they are played in turn now",
      "normalise_speech(data)" in tab)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
