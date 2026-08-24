"""NOTES: SELECTING, DELETING, AND READING — Test 1, the mechanism.

What could be true and these still pass: the ticks never appear on a
phone, the row wraps at 390px, the player does not start (all browser
work). What THIS closes: select-all reaching past what is on screen,
a delete leaving a tick behind that then selects somebody else's note,
Read carrying nothing, and the note path and the transcript path
drifting apart on voices.

    python3 tests/test_notes_select.py
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

SRC = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()

from ttt import notes as NOTES      # noqa: E402

passed = failed = 0


def ck(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


print("NOTES: SELECT, DELETE, READ\n")

# --- the module still does what the UI assumes -----------------------
state = {}
NOTES.add(state, "prva biljeska o poslu", language="hr")
NOTES.add(state, "second note in english", language="en")
NOTES.add(state, "treca biljeska", language="hr")
items = NOTES.items(state)
ck("1 three notes exist to select", len(items) == 3, len(items))
ck("2 every note has an id, which is what a tick is keyed on",
   all(n.get("id") for n in items))
ck("3 the ids are unique — a duplicate is a crashed app, not a bad list",
   len({n["id"] for n in items}) == 3)

NOTES.remove(state, items[1]["id"])
ck("4 remove takes one and leaves the rest", NOTES.count(state) == 2)
ck("5 and the right one went",
   items[1]["id"] not in {n["id"] for n in NOTES.items(state)})

# --- SELECT ALL MUST NOT REACH PAST WHAT IS ON SCREEN ----------------
ck("6 SELECT ALL IS BUILT FROM THE FILTERED LIST, not the notebook — "
   "with a search typed, 'all' meaning the invisible 200 is how "
   "somebody deletes everything while looking at three results",
   re.search(r'ids = \[x\["id"\] for x in shown\]', SRC) is not None)
ck("7 and the picked list is built from those same ids",
   'picked = [i_ for i_ in ids if st.session_state.get("_np_%s" % i_)]'
   in SRC)

# --- A DELETE MUST NOT LEAVE ITS TICK BEHIND -------------------------
ck("8 DELETING A NOTE CLEARS ITS TICK — a surviving tick would select "
   "whatever note later takes that place in the list",
   'st.session_state.pop("_np_%s" % nid, None)' in SRC)
ck("9 and an open note that was just deleted does not stay open",
   "if st.session_state.get(OPEN_KEY) in doomed:" in SRC)
ck("10 THE DELETE HAPPENS BEFORE THE LIST IS READ, never mid-render",
   SRC.index("_note_delete_pending()") < SRC.index(
       "all_notes = NOTES.items(st.session_state)"))
ck("11 delete arms before it fires — one press never destroys anything",
   "_note_del_armed_many" in SRC and 'key="note_deln2_' in SRC)

# --- THE ROW IS FURNITURE, NOT A POPUP -------------------------------
ck("12 THE LINKS ARE ALWAYS DRAWN AND GREY OUT — the rule Baba locked "
   "for text boxes, and what the recordings row already does",
   'disabled=not one' in SRC and 'disabled=not n' in SRC)
ck("13 select-all doubles as select-none",
   't("note_none_sel") if everything else t("note_all")' in SRC)
ck("14 READ IS ONE NOTE ONLY, greyed for many — reading two at once "
   "is not a thing", 'key="note_read_%s" % where' in SRC
   and re.search(r'note_read_%s.*\n.*disabled=not one', SRC) is not None)
ck("15 delete works on many, which is the one act that means the same "
   "thing repeated", '"_note_del_many": list(picked)' in SRC)

# --- READ CARRIES THE WORDS ------------------------------------------
ck("16 read_note puts the note's TEXT into R's box",
   'st.session_state["talk_text"] = body' in SRC)
ck("17 AN EMPTY NOTE IS NOT READ — a player that starts and says "
   "nothing reads as the app being broken",
   re.search(r'if not body:\s*\n\s*return', SRC) is not None)
ck("18 it switches to R and starts by itself, no second tap",
   '"active_tab"] = "talk"' in SRC and '"_auto_read"] = True' in SRC)
ck("19 the note gives up the screen when R takes over",
   re.search(r'close_note\(\)\s*# the note gave up', SRC) is not None)

# --- ONE IMPLEMENTATION, NOT TWO -------------------------------------
ck("20 THE VOICE LOGIC IS SHARED between the note path and the "
   "transcript path — two copies is exactly what drifted when the "
   "Speechify seats changed at v176",
   SRC.count("def _match_voice_to") == 1
   and SRC.count("_match_voice_to(") == 3)
ck("21 and it is defined above both callers, so a callback cannot "
   "meet a name that is not there yet",
   SRC.index("def _match_voice_to") < SRC.index("def read_this")
   and SRC.index("def _match_voice_to") < SRC.index("def read_note"))
ck("22 read_note is defined after close_note, which it calls",
   SRC.index("def close_note") < SRC.index("def read_note"))

# --- AND IT DOES NOT REINVENT SAVING ---------------------------------
ck("23 the multi-delete does NOT call persist_notes itself — the foot "
   "of the module already saves whatever differs, and that guard "
   "exists so the tenth place cannot forget",
   "NO persist_notes() HERE" in SRC)

print("\n%d ok, %d failed" % (passed, failed))


def test_notes_select():
    """The verdict, in the one form pytest can report."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
