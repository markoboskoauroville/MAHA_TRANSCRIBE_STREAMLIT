"""ONE LIST, FILTERED — not tabs.

    python3 tests/test_vr_filter.py

Baba, 27.8.2026: "There are no filters by male and female. So we need to
put filters as checkboxes. It's one list and it's filtered out. Checkbox
male, female, then find all nationalities like Indian, UK, American, and
they by role, actor, narrator, and other roles."

HE IS RIGHT THAT CHECKBOXES BEAT TABS. Tabs make you choose ONE axis;
boxes let you ask for a British narrator, which is the question somebody
casting actually has.

WHERE THE THREE AXES COME FROM, because two are Hume's and one is not:

    GENDER   Hume's own tag. Twelve and twelve, exactly.
    ACCENT   one per voice, the accent ALREADY ON THE PILL. Hume's raw
             tags overlap and are finer than what we display.
    ROLE     NOT A HUME TAG. Derived from the name — a guess, and
             labelled as one in the panel.

VERIFIED against the live library on 27.8.2026: all 24 names exist in
Hume's catalogue and their GENDER tags match.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import vr as V  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
_va, _vb = app.find('elif active == "vr":'), app.find('elif active == "looks":')
vr = app[_va:_vb] if 0 < _va < _vb else ""
ALL = sum(len(V.VOICES[g]) for g in ("F", "M"))

check("0 the vr tab is findable", 0 < _va < _vb, (_va, _vb))

print("1 THE FACETS COME FROM THE CAST")
f = V.facets()
print("       gender %s" % f["gender"])
print("       accent %s" % f["accent"])
print("       role   %s" % f["role"])
check("1a three axes", sorted(f) == ["accent", "gender", "role"], sorted(f))
check("1b every voice has a gender", sum(f["gender"].values()) == ALL)
check("1c every voice has exactly ONE accent — overlapping tags would "
      "give boxes that select the same people",
      sum(f["accent"].values()) == ALL, f["accent"])
# THE ACCENT IS A LOOKUP, NOT A DERIVATION, and that was learned from a
# mutation: removing the overlap-reduction changed nothing, because the
# app never passed live tags and VOICES already stores one clean accent
# per voice. A branch no test can turn red is a branch nothing reaches.
_vr_src = open(os.path.join(os.path.dirname(__file__), "..", "ttt",
                            "vr.py"), encoding="utf-8").read()
# find(), with the region checked. index() kills a suite instead of
# reporting, and the sweep then shows a blank where a number belongs.
_aa, _ab = _vr_src.find("def accent_of"), _vr_src.find("ROLE_WORDS")
check("1c1 accent_of is findable", 0 < _aa < _ab, (_aa, _ab))
_af = _vr_src[_aa:_ab] if 0 < _aa < _ab else ""
_af_code = "\n".join(l for l in _af.splitlines()
                     if not l.lstrip().startswith("#"))
check("1c2 accent_of reads the stored accent rather than reducing tags",
      "BRITISH_TAGS" not in _af_code and "VOICES.get(g" in _af_code,
      [x for x in ("BRITISH_TAGS", "ACCENT_ORDER") if x in _af_code])
check("1c3 and every accent it can return is one somebody put there",
      set(f["accent"]) <= {a for g in ("F", "M")
                           for _, a, _ in V.VOICES[g]}, f["accent"])
check("1d and exactly one role", sum(f["role"].values()) == ALL, f["role"])
check("1e no facet is empty — a box that always finds nothing is worse "
      "than no box",
      all(v > 0 for axis in f.values() for v in axis.values()))
check("1f twelve and twelve, which is what Hume's tags say",
      f["gender"] == {"female": 12, "male": 12}, f["gender"])

print("\n2 NOTHING TICKED MEANS EVERYTHING")
check("2a no filter at all returns the whole cast",
      len(V.filter_cast()) == ALL, len(V.filter_cast()))
check("2b an empty list per axis is the same as no filter",
      len(V.filter_cast(gender=[], accents=[], roles=[])) == ALL)
check("2c ticking one axis leaves the others alone — he should not have "
      "to tick all four roles to see them all",
      len(V.filter_cast(gender=["male"])) == 12,
      len(V.filter_cast(gender=["male"])))

print("\n3 AXES AND, VALUES OR")
brit_narr = [n for _, n, _, _ in
             V.filter_cast(accents=["British"], roles=["narrator"])]
print("       British + narrator: %d" % len(brit_narr))
check("3a two axes narrow each other", 0 < len(brit_narr) < 12, brit_narr)
check("3b and every one really is both",
      all(V.accent_of(n) == "British" and V.role_of(n) == "narrator"
          for n in brit_narr), brit_narr)
two = [n for _, n, _, _ in V.filter_cast(accents=["Indian", "Welsh"])]
check("3c two values on ONE axis widen — British OR Indian, not both",
      len(two) == 4, two)
check("3d which is how the question is asked out loud",
      all(V.accent_of(n) in ("Indian", "Welsh") for n in two))

print("\n3b AN IMPOSSIBLE COMBINATION IS EMPTY, NOT WRONG")
none = V.filter_cast(gender=["female"], roles=["narrator"])
check("3e there are no female narrators in this cast, and it says so "
      "with an empty list rather than guessing", none == [], none)
check("3f the panel SAYS so — a blank space reads as the app breaking",
      't("vr_f_none")' in vr)

print("\n4 ROLE IS A GUESS AND IS LABELLED AS ONE")
check("4a every voice classifies — no voice falls through unlabelled",
      all(V.role_of(n) in ("actor", "narrator", "presenter", "character")
          for g in ("F", "M") for n, _, _ in V.VOICES[g]))
check("4b narrator catches storytellers and announcers too",
      V.role_of("Welsh Folk Storyteller") == "narrator"
      and V.role_of("Old School Radio Announcer") == "narrator")
check("4c actress counts as actor", V.role_of("Indian Actress") == "actor")
check("4d a name matching nothing is 'character', which means 'none of "
      "the three' — not 'we decided it is a character'",
      V.role_of("Mysterious Woman") == "character")
check("4e the panel says the role is not Hume's",
      "not from Hume" in app or "ne od Humea" in app)
check("4f and the code says so where the rule lives",
      "NOT A HUME TAG" in open(os.path.join(
          os.path.dirname(__file__), "..", "ttt", "vr.py"),
          encoding="utf-8").read())

print("\n5 THE PANEL")
check("5a it builds the boxes from facets(), not a hard-coded list",
      "VR.facets()" in vr)
check("5b it filters through filter_cast()", "VR.filter_cast(" in vr)
check("5c and the pills are drawn from the FILTERED list, or the "
      "filter would be decorative",
      "for g2, n, a, ag in _cast" in vr, "_rows is not built from _cast")
check("5d each box shows how many it would find",
      '_facets[_axis][_v]' in vr)
check("5e an accent keeps its proper name — t() returns the KEY when it "
      "does not know it, so `t(x) or x` never falls back",
      '_lbl == "vrf_%s" % _v' in vr)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
