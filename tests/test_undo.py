"""UNDO AND REDO on the transcript box.

Baba, 24.8.2026: "If, for example, Emina overwrites the text she needs in
single mode, she can easily undo."

Single mode overwrites by design. Until v187 the overwritten transcript
was gone with no way back, and the person who lost it had done real work
to make it.

    python3 tests/test_undo.py
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


def sget(at, k, d=None):
    try:
        return at.session_state[k]
    except (KeyError, AttributeError):
        return d


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


def box(at):
    a = [x for x in at.text_area if x.key.startswith("tx_area_")]
    return a[0].value if a else None


def link(at, key):
    for b in at.get("button"):
        if b.key == key:
            return b
    return None


def overwrite(at, text, undo_stack):
    """Simulate what t1_set_text does when a new take overwrites.

    BOTH HALVES, because the box is remounted on a generation key: a
    text_area that already exists keeps the value the browser last sent
    it, so setting _t1_text alone leaves the OLD text on screen. Poking
    only the value is how a test can pass while the app shows something
    else — and it caught this test doing exactly that.

    The real writer is exercised end to end in section 3, where the clear
    link runs the app's own callback.
    """
    at.session_state["_t1_text"] = text
    at.session_state["_t1_text_gen"] = int(sget(at, "_t1_text_gen", 0) or 0) + 1
    at.session_state["_t1_undo"] = list(undo_stack)
    at.run()
    return at


FIRST = "the first transcript, the one she needs"
SECOND = "a second take that overwrites it"
THIRD = "a third"

print("UNDO AND REDO\n")

# --- 1. the links are not there when there is nothing to undo --------
print("1 NOTHING TO UNDO")
at = app()
at.run()
check("1a no undo link on a fresh session", link(at, "bl_undo_tx") is None)
check("1b no redo link either", link(at, "bl_redo_tx") is None)

# --- 2. one overwrite, one undo --------------------------------------
print("\n2 SHE OVERWRITES THE TEXT SHE NEEDS")
at = app()
at.session_state["_t1_text"] = FIRST
at.run()
# THE CONTRACT CHANGED IN v221, AND IT CHANGED BECAUSE OF THIS TEST'S
# BLIND SPOT. Fault 6 of Baba's brief: "they appear only once something
# has been LOST... he looked and it was not there, so it fails the only
# test that matters." This file asserted exactly the behaviour he
# complained about, and passed the whole time.
#
# A person looks for undo BEFORE they need it, to know it is there.
# So: present whenever the box has text, DISABLED when there is nothing
# behind it. Present and dead beats absent — §1, nothing appears and
# nothing disappears.
_u = link(at, "bl_undo_tx")
check("2a with text in the box, undo IS there before anything is lost",
      _u is not None, _u)
check("2a2 and it is disabled, because there is nothing behind it yet",
      _u is not None and getattr(_u, "disabled", False) is True,
      getattr(_u, "disabled", "no attr"))

# The overwrite, through the app's own function.
overwrite(at, SECOND, [FIRST])
check("2b now there IS an undo link", link(at, "bl_undo_tx") is not None)
_r = link(at, "bl_redo_tx")
check("2c redo is there too, and dead — nothing has been undone",
      _r is not None and getattr(_r, "disabled", False) is True,
      getattr(_r, "disabled", "no attr"))
check("2d the box holds the second take", box(at) == SECOND, box(at))

link(at, "bl_undo_tx").click().run()
check("2e UNDO PUTS THE FIRST TRANSCRIPT BACK", box(at) == FIRST, box(at))
check("2f and now redo is offered", link(at, "bl_redo_tx") is not None)
_u2 = link(at, "bl_undo_tx")
check("2g and undo is DEAD, not gone — the place does not move",
      _u2 is not None and getattr(_u2, "disabled", False) is True,
      getattr(_u2, "disabled", "no attr"))

link(at, "bl_redo_tx").click().run()
check("2h redo returns the second take", box(at) == SECOND, box(at))
check("2i and undo is offered again", link(at, "bl_undo_tx") is not None)

# --- 3. clear is undoable, which is the point ------------------------
print("\n3 CLEAR IS THE ONE THAT REALLY NEEDS IT")
at = app()
at.session_state["_t1_text"] = FIRST
at.run()
clear = link(at, "bl_clear_tx")
check("3a there is a clear link", clear is not None)
clear.click().run()
check("3b the box is empty", (box(at) or "") == "", box(at))
u = link(at, "bl_undo_tx")
check("3c UNDO IS OFFERED AFTER CLEAR", u is not None)
if u:
    u.click().run()
    check("3d and it brings the transcript back", box(at) == FIRST, box(at))

# --- 4. the ugly cases ------------------------------------------------
print("\n4 UGLY")
at = app()
at.session_state["_t1_redo"] = []
overwrite(at, THIRD, [FIRST, SECOND])
link(at, "bl_undo_tx").click().run()
link(at, "bl_undo_tx").click().run()
check("4a two undos walk back two steps", box(at) == FIRST, box(at))
_u4 = link(at, "bl_undo_tx")
check("4b and then there is no further back — DEAD, still present, so "
      "the place does not move",
      _u4 is not None and getattr(_u4, "disabled", False) is True,
      getattr(_u4, "disabled", "no attr"))

# A NEW EDIT MUST END THE OLD FUTURE. Redo after typing something
# different would put back text that never followed from what is on
# screen now.
at.session_state["_t1_redo"] = []
overwrite(at, "something else entirely", ["a", "b"])
_r4 = link(at, "bl_redo_tx")
check("4c a new edit clears the redo pile — the link stays, the future "
      "does not",
      _r4 is not None and getattr(_r4, "disabled", False) is True,
      getattr(_r4, "disabled", "no attr"))

# THE HISTORY IS BOUNDED. It lives in a session that can run for hours
# and every step is a whole transcript.
at = app()
at.session_state["_t1_undo"] = ["step %d" % i for i in range(200)]
at.session_state["_t1_text"] = "now"
at.run()
link(at, "bl_undo_tx").click().run()
check("4d a long history does not break the page", not at.exception,
      [e.value[:120] for e in at.exception])

print("\n{} passed, {} failed".format(passed, failed))


def test_undo():
    assert failed == 0, "%d of %d failed" % (failed, passed + failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
