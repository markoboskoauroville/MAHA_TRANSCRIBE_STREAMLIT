"""The archive's select-and-delete wiring, with a seeded archive.

The block only renders when there are items, so the browser test never
reaches it on a fresh session. AppTest can seed session state directly,
which is the only way to exercise the ticks without recording anything.

    python3 tests/test_archive_select.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from streamlit.testing.v1 import AppTest  # noqa: E402

from ttt import archive  # noqa: E402

def sget(at, key, default=None):
    """AppTest's session_state has NO .get — documented in HANDOVER §6 and
    forgotten anyway. One helper so it cannot be forgotten again."""
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def seeded(n=3):
    """An app already logged in, with n items in T1's archive."""
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=60)
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    at.session_state["active"] = "T1"
    state = {}
    for i in range(n):
        archive.add(state, "transcript number %d" % i, language="hr")
    at.session_state[archive.KEY] = state[archive.KEY]
    return at


print("ARCHIVE — select and delete\n")

at = seeded(3)
at.run()
check("1 the app runs with a seeded archive", not at.exception,
      at.exception)

ids = [r["id"] for r in at.session_state[archive.KEY]]
check("2 three items are present", len(ids) == 3, ids)

boxes = [c for c in at.checkbox if c.key.startswith("arcsel_")]
check("3 one tick per archive item", len(boxes) == 3,
      [c.key for c in at.checkbox])

keys = [b.key for b in at.get("button")]
check("4 delete-selected exists", "arc_del_sel" in keys, keys)
check("5 delete-all still exists", "arc_clear_all" in keys, keys)

sel_btn = [b for b in at.get("button") if b.key == "arc_del_sel"][0]
check("6 delete-selected is DISABLED with nothing ticked",
      sel_btn.disabled is True)

# --- tick one, delete it ---------------------------------------------
at2 = seeded(3)
at2.run()
# The ids come from a counter, so a second seeded app does NOT reuse the
# first one's ids. Taking `target` from `at` made this look like a
# missing checkbox when it was the test holding a stale id.
ids2 = [r["id"] for r in at2.session_state[archive.KEY]]
target = ids2[0]
[c for c in at2.checkbox if c.key == "arcsel_" + target][0].check().run()
check("7 ticking records the selection",
      target in sget(at2, "_t1_arc_sel", set()),
      sget(at2, "_t1_arc_sel"))

sel_btn2 = [b for b in at2.get("button") if b.key == "arc_del_sel"][0]
check("8 delete-selected becomes ENABLED once something is ticked",
      sel_btn2.disabled is False)

sel_btn2.click().run()
left = [r["id"] for r in at2.session_state[archive.KEY]]
check("9 the ticked item is gone", target not in left, left)
check("10 the OTHER two survive — only what was ticked is deleted",
      len(left) == 2, left)
check("11 the selection is emptied after deleting",
      not sget(at2, "_t1_arc_sel"))

# --- tick two of three ------------------------------------------------
at3 = seeded(3)
at3.run()
ids3 = [r["id"] for r in at3.session_state[archive.KEY]]
for t in ids3[:2]:
    [c for c in at3.checkbox if c.key == "arcsel_" + t][0].check().run()
[b for b in at3.get("button") if b.key == "arc_del_sel"][0].click().run()
left3 = [r["id"] for r in at3.session_state[archive.KEY]]
check("12 two ticked, two deleted, one left", len(left3) == 1, left3)
check("13 the survivor is the one never ticked", left3 == [ids3[2]], left3)

# --- delete all still works ------------------------------------------
at4 = seeded(3)
at4.run()
[b for b in at4.get("button") if b.key == "arc_clear_all"][0].click().run()
check("14 delete all empties the archive",
      not sget(at4, archive.KEY), sget(at4, archive.KEY))

# --- the box is NOT touched by deleting -------------------------------
at5 = seeded(2)
at5.session_state["transcript_box"] = "work in progress"
at5.run()
ids5 = [r["id"] for r in at5.session_state[archive.KEY]]
[c for c in at5.checkbox if c.key == "arcsel_" + ids5[0]][0].check().run()
[b for b in at5.get("button") if b.key == "arc_del_sel"][0].click().run()
check("15 deleting never touches the box — tidying is not losing work",
      at5.session_state["transcript_box"] == "work in progress",
      at5.session_state["transcript_box"])

# --- a stale selection cannot outlive its item ------------------------
at6 = seeded(2)
at6.session_state["_t1_arc_sel"] = {"ghost_id_that_does_not_exist"}
at6.run()
check("16 a selection holding a dead id is swept, so the count cannot lie",
      "ghost_id_that_does_not_exist" not in at6.session_state["_t1_arc_sel"],
      at6.session_state["_t1_arc_sel"])

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
