"""THE BOX. Does delivered text actually land in it, and stay there?

Three sessions of "text reaches the archive but not the box" ended in
v88 rewriting the container: the transcript lives in _t1_text, a plain
session key Streamlit does not manage, and the text_area is only a view
of it whose key carries a generation number.

This is the test that would have caught the original bug. It asserts the
box CONTENT, not that a function was called — the old code called
everything correctly and the box was still empty.

    python3 tests/test_box.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402


passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def sget(at, key, default=None):
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def app():
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=60)
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    at.session_state["active"] = "T1"
    return at


def box_text(at):
    """What is ACTUALLY rendered in the transcript box."""
    areas = [a for a in at.text_area if a.key.startswith("tx_area_")]
    return areas[0].value if areas else None


print("THE BOX — delivered text must land, and stay\n")

# --- 1. it lands ------------------------------------------------------
at = app()
at.run()
check("1 the box exists", box_text(at) is not None,
      [a.key for a in at.text_area])
check("2 it starts empty", box_text(at) == "")

at.session_state["_t1_text"] = "Testiramo hrvatski jezik"
at.session_state["_t1_text_gen"] = 1
at.run()
check("3 text put in _t1_text SHOWS in the box",
      box_text(at) == "Testiramo hrvatski jezik", box_text(at))

# --- 2. it SURVIVES a rerun — this is the bug that shipped ------------
# The deck acknowledges every take by posting back, and each post is
# another rerun. The old container lost the value here.
at.run()
check("4 it survives one rerun", box_text(at) == "Testiramo hrvatski jezik",
      box_text(at))
at.run()
at.run()
check("5 it survives three more reruns",
      box_text(at) == "Testiramo hrvatski jezik", box_text(at))

# --- 3. delivering NEW text replaces what is shown --------------------
gen_before = sget(at, "_t1_text_gen", 0)
at.session_state["_t1_text"] = "drugi tekst"
at.session_state["_t1_text_gen"] = gen_before + 1
at.run()
check("6 new text replaces the old in the box",
      box_text(at) == "drugi tekst", box_text(at))
check("7 the widget key changed, which is what makes 6 possible",
      [a.key for a in at.text_area][0] != "tx_area_%d" % gen_before,
      [a.key for a in at.text_area])

# --- 4. typing syncs back, WITHOUT remounting -------------------------
at2 = app()
at2.session_state["_t1_text"] = "start"
at2.session_state["_t1_text_gen"] = 1
at2.run()
key_before = [a.key for a in at2.text_area][0]
[a for a in at2.text_area if a.key.startswith("tx_area_")][0].set_value(
    "typed by hand").run()
check("8 typing syncs back into _t1_text",
      sget(at2, "_t1_text") == "typed by hand", sget(at2, "_t1_text"))
key_after = [a.key for a in at2.text_area][0]
check("9 typing does NOT remount the box under the fingers",
      key_after == key_before, "{} -> {}".format(key_before, key_after))
check("10 what was typed is still shown", box_text(at2) == "typed by hand",
      box_text(at2))

# --- 5. the box and the note are separate surfaces ---------------------
#
# This check used to press "to the box", which copied a note's text back
# into the transcript box. That button is gone in v121 — Baba: "I don't
# know what that means or what it does." He was right: it was the old
# ARCHIVE's habit surviving into a place where the note IS the document,
# not a copy of something that lives elsewhere.
#
# What is worth checking is what remains true: opening a note takes the
# module over, and closing it gives the box back untouched.
from ttt import notes as NOTES  # noqa: E402

at3 = app()
state = {}
NOTES.add(state, "iz biljeske")
at3.session_state[NOTES.KEY] = state[NOTES.KEY]
at3.session_state["_notes_adopted"] = True
at3.session_state["_open_note"] = state[NOTES.KEY][0]["id"]
at3.session_state["_t1_text"] = "u okviru"
at3.session_state["_t1_text_gen"] = 1
at3.run()
check("11a while a note is open there is no box to look at",
      box_text(at3) is None, box_text(at3))
[b for b in at3.get("button") if b.key == "note_close"][0].click().run()
check("11 closing gives the box back, with what was in it",
      box_text(at3) == "u okviru", box_text(at3))

# --- 6. clear empties it ----------------------------------------------
at4 = app()
at4.session_state["_t1_text"] = "to be cleared"
at4.session_state["_t1_text_gen"] = 1
at4.run()
# CLEAR MOVED UNDER THE BOX (v132), with copy, as a link — one rule for
# every text box in the app. Its key moved with it.
[b for b in at4.get("button") if b.key == "bl_clear_tx"][0].click().run()
check("12 clear empties the box", box_text(at4) == "", box_text(at4))
at4.run()
check("13 and it STAYS empty across a rerun", box_text(at4) == "",
      box_text(at4))

# --- 7. the old widget key is gone entirely ---------------------------
at5 = app()
at5.run()
check("14 nothing is keyed 'transcript_box' any more",
      "transcript_box" not in [a.key for a in at5.text_area],
      [a.key for a in at5.text_area])

# --- 8. the layout moved ----------------------------------------------
keys = [b.key for b in at5.get("button")]
check("15 the language and mode row still renders",
      all(k in keys for k in ("tr_hr", "tr_en", "tr_single", "tr_multi")),
      keys)


print("\n{} passed, {} failed".format(passed, failed))


def test_box():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_box.py` is how it is meant to be read."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
