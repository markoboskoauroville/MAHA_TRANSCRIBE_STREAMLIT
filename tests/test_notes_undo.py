"""UNDO FOR A DELETED NOTE.

Baba, 24.8.2026: "Let's put undo in notes."

A deleted note was the last unrecoverable act in the app. Notes are the
one thing here a person builds over days, and for a free user they live
only in their own browser — there is no Drive copy to fall back on.

    python3 tests/test_notes_undo.py

Sections 1-3 exercise ttt/notes.py directly, on a plain dict: the module
takes a `state` mapping and never touches Streamlit, so the ordering
rules can be checked without a page in the way. Section 4 drives the
real link on the real row.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ttt import notes as NOTES  # noqa: E402
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


def book(n=5):
    """A notebook of n notes, made through the module's own front door."""
    state = {}
    for i in range(n):
        NOTES.add(state, "note number %d, with words in it" % i)
    return state


def titles(state):
    return [NOTES.body_preview(x, 30)[:13] for x in NOTES.items(state)]


print("UNDO FOR A DELETED NOTE\n")

# --- 1. THE MECHANISM -------------------------------------------------
print("1 MECHANISM — one note, back where it was")
state = book(5)
before = [x["id"] for x in NOTES.items(state)]
third = before[2]
check("1a nothing to undo before anything is deleted",
      NOTES.undo_count(state) == 0)

NOTES.remove(state, third)
check("1b the note is gone", third not in [x["id"] for x in NOTES.items(state)])
check("1c and one is waiting to come back", NOTES.undo_count(state) == 1,
      NOTES.undo_count(state))

back = NOTES.undo_remove(state)
after = [x["id"] for x in NOTES.items(state)]
check("1d one went back", back == 1, back)
check("1e THE ORDER IS EXACTLY AS IT WAS", after == before,
      "%s vs %s" % (after[:4], before[:4]))
check("1f and the undo is spent", NOTES.undo_count(state) == 0)

# --- 2. THE REAL THING — a batch --------------------------------------
print("\n2 REAL — five deleted, five back")
state = book(8)
before = [x["id"] for x in NOTES.items(state)]
doomed = [before[1], before[3], before[4], before[6]]
gone = NOTES.remove_many(state, doomed)
check("2a four were deleted", gone == 4, gone)
check("2b four notes remain", len(NOTES.items(state)) == 4,
      len(NOTES.items(state)))
check("2c four are waiting", NOTES.undo_count(state) == 4,
      NOTES.undo_count(state))

back = NOTES.undo_remove(state)
after = [x["id"] for x in NOTES.items(state)]
check("2d four went back in ONE undo", back == 4, back)
check("2e AND THE WHOLE ORDER IS RESTORED", after == before,
      "%s\n            vs %s" % (after, before))

# --- 3. THE UGLY CASES ------------------------------------------------
print("\n3 UGLY")
state = book(3)
check("3a undo with nothing deleted does nothing, and does not raise",
      NOTES.undo_remove(state) == 0)

state = book(3)
ids = [x["id"] for x in NOTES.items(state)]
NOTES.remove(state, ids[0])
NOTES.undo_remove(state)
check("3b undo pressed twice does not make a duplicate",
      NOTES.undo_remove(state) == 0 and len(NOTES.items(state)) == 3,
      len(NOTES.items(state)))

# THE NOTE CAME BACK BY ANOTHER ROAD while the undo was still held.
#
# A Drive restore, or the browser's copy arriving late, can put the note
# back without spending the undo. Pressing undo then would insert a
# SECOND copy of a note that is already on screen.
#
# This case was written first as "undo pressed twice", which the undo
# slot being emptied already prevented — so the guard read as tested and
# was not. A mutation that removed it changed nothing. This is the check
# that actually reaches it.
state = book(3)
ids = [x["id"] for x in NOTES.items(state)]
NOTES.remove(state, ids[1])
state[NOTES.KEY].insert(1, dict(state[NOTES.UNDO_KEY]["notes"][0]["note"]))
check("3b2 undo does NOT duplicate a note that returned another way",
      NOTES.undo_remove(state) == 0 and len(NOTES.items(state)) == 3,
      [x["id"] for x in NOTES.items(state)])

# DELETE, UNDO, DELETE AGAIN — the held batch must not be stale.
state = book(4)
ids = [x["id"] for x in NOTES.items(state)]
NOTES.remove(state, ids[0])
NOTES.undo_remove(state)
NOTES.remove(state, ids[3])
check("3c a second delete holds the NEW note, not the old one",
      NOTES.undo_count(state) == 1, NOTES.undo_count(state))
NOTES.undo_remove(state)
check("3d and the right one comes back",
      [x["id"] for x in NOTES.items(state)] == ids,
      [x["id"] for x in NOTES.items(state)])

# THE LIST IS SHORTER THAN WHEN THE NOTE LEFT IT.
state = book(6)
ids = [x["id"] for x in NOTES.items(state)]
NOTES.remove(state, ids[5])          # the last one
for other in ids[:3]:                # now delete three more, losing the undo
    pass
state[NOTES.UNDO_KEY]["notes"][0]["at"] = 99   # a position past the end
check("3e a position past the end still restores, at the end",
      NOTES.undo_remove(state) == 1 and len(NOTES.items(state)) == 6,
      len(NOTES.items(state)))

# A DELETED NOTE MUST NOT BE SAVED ANYWHERE. The undo slot is its own
# key, outside the notebook, so it is never written to the browser or
# to Drive.
state = book(2)
ids = [x["id"] for x in NOTES.items(state)]
NOTES.remove(state, ids[0])
check("3f the held note is NOT inside the notebook that gets saved",
      NOTES.UNDO_KEY != NOTES.KEY
      and all(x["id"] != ids[0] for x in NOTES.items(state)))

# --- 4. THE LINK ON THE ROW -------------------------------------------
print("\n4 THE LINK, on the real row")


def app():
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=120)
    at.secrets["FREE_USER1"] = "emina"
    at.secrets["GROQ_API_KEYS"] = ["gsk_stub"]
    at.session_state["_authed"] = True
    at.session_state["_user"] = "emina"
    at.session_state["active_tab"] = "transcribe"
    return at


def link(at, prefix):
    for b in at.get("button"):
        if str(b.key or "").startswith(prefix):
            return b
    return None


state = book(4)
at = app()
at.session_state[NOTES.KEY] = state[NOTES.KEY]
at.run()
check("4a no undo link while nothing is deleted",
      link(at, "nact_undo_") is None)
check("4b and read is on the row", link(at, "nact_read_") is not None)

ids = [x["id"] for x in NOTES.items(state)]
at.session_state["_np_%s" % ids[1]] = True
at.run()
link(at, "nact_deln_").click().run()      # arms
link(at, "nact_deln2_").click().run()     # fires
check("4c the note is gone from the page",
      len(at.session_state[NOTES.KEY]) == 3,
      len(at.session_state[NOTES.KEY]))

u = link(at, "nact_undo_")
check("4d THE UNDO LINK IS THERE", u is not None)
check("4e and it says how many", u is not None and "1" in str(u.label),
      u.label if u else None)
if u:
    u.click().run()
    check("4f THE NOTE COMES BACK", len(at.session_state[NOTES.KEY]) == 4,
          len(at.session_state[NOTES.KEY]))
    check("4g in its old place",
          [x["id"] for x in at.session_state[NOTES.KEY]] == ids,
          [x["id"] for x in at.session_state[NOTES.KEY]])
    check("4h and the link is gone once spent",
          link(at, "nact_undo_") is None)
    check("4i read is back on the row", link(at, "nact_read_") is not None)

print("\n{} passed, {} failed".format(passed, failed))


def test_notes_undo():
    assert failed == 0, "%d of %d failed" % (failed, passed + failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
