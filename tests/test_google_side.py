"""SWITCHING THE GOOGLE SIDE (female / male) STARTS THE READING AGAIN AT
ONCE (Marko, 7.9.2026). The side change picks the first voice of the new
side, calls the pick (which sets _auto_read) and RERUNS — before this, the
pick was made but nothing reran, so the reading stopped until the next
press.

    python3 tests/test_google_side.py

1  the mechanism: the side-change block of google_voice_row, read off the
   source — set the voice, tell the pick, set the widget's key, rerun, in
   that order, all inside the guard that makes it a single rerun
2  the running function: with a male voice in force and the radio on F,
   the body moves the voice to the first female one, calls on_pick, and
   asks for a rerun (st.rerun raised as Streamlit's own exception)
3  ugly: a voice already on the chosen side changes nothing and reruns
   nothing; no on_pick is fine
4  upgrade: the mutation — without the rerun the old behaviour returns:
   the pick is made, the voice moves, and nothing reruns
"""
import os
import re
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RAW = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
CODE = re.sub(r'"""(?:.|\n)*?"""', "", "\n".join(l for l in RAW.splitlines() if not l.lstrip().startswith("#")))

print("1 THE MECHANISM, ALONE")
fn = CODE[CODE.find("def google_voice_row("):CODE.find("def do_correct(")]
block = re.search(r"if current not in names and names:\n((?:        .*\n|\n)+?)(?=        if current:)", fn)
check("the side-change block is there", block is not None)
body = block.group(1) if block else ""
order = [body.find(x) for x in ('st.session_state["google_voice"] = current', "on_pick()",
                                "st.session_state[vkey] = current", "st.rerun()")]
check("voice set, pick told, widget key set, rerun — in that order, all inside the guard",
      all(i >= 0 for i in order) and order == sorted(order), order)
check("the rerun is the last thing in the block", body.rstrip().endswith("st.rerun()"), body[-60:])


# A SMALL STREAMLIT STAND-IN: the function only needs session_state, radio,
# selectbox, container and rerun; the real ones need a running script.
class Rerun(Exception):
    pass


def make_st(state):
    st = types.SimpleNamespace()
    st.session_state = state

    class _C:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    st.container = lambda **k: _C()
    st.radio = lambda *a, **k: None
    st.selectbox = lambda *a, **k: None

    def rerun():
        raise Rerun()
    st.rerun = rerun
    return st


def run_row(state, on_pick=None):
    """google_voice_row in isolation: its own source, executed against the stand-in."""
    src = RAW[RAW.find("def google_voice_row("):RAW.find("def do_correct(")]
    ns = {"st": make_st(state), "GOOGLE_P": GP, "t": lambda k: k}
    exec(compile(src, "google_voice_row", "exec"), ns)
    try:
        return ns["google_voice_row"]("talkg", on_pick), False
    except Rerun:
        return None, True


from ttt.providers import google as GP                             # noqa: E402  (what app.py calls GOOGLE_P)
female = [n for n, _t in GP.top_voices("F", 10)]
male = [n for n, _t in GP.top_voices("M", 10)]
check("there are female and male voices to switch between", female and male, (female[:2], male[:2]))

print("2 THE FUNCTION, RUN")
picked = []
state = {"google_voice": male[0], "talkg_gender": "F"}
_v, rerun = run_row(state, on_pick=lambda: picked.append(1))
check("a male voice in force with the radio on F moves to the first female voice",
      state["google_voice"] == female[0], state.get("google_voice"))
check("the pick is told once", picked == [1], picked)
check("the widget's key is set to the same voice", state.get("talkg_voice") == female[0])
check("and the page is asked to run again", rerun)

print("3 THE UGLY CASES")
picked = []
state = {"google_voice": female[1], "talkg_gender": "F"}
_v, rerun = run_row(state, on_pick=lambda: picked.append(1))
check("a voice already on the side stays", state["google_voice"] == female[1])
check("nothing is picked", picked == [])
check("and nothing reruns — no loop", not rerun)
state = {"google_voice": male[0], "talkg_gender": "F"}
_v, rerun = run_row(state, on_pick=None)
check("no on_pick: the move still happens and reruns", state["google_voice"] == female[0] and rerun)

print("4 THE MUTATION: without the rerun, the old behaviour is back")
src = RAW[RAW.find("def google_voice_row("):RAW.find("def do_correct(")]
mutant = src.replace("            st.rerun()\n", "")
check("the mutation removed exactly the rerun", mutant != src and mutant.count("st.rerun()") == src.count("st.rerun()") - 1)
ns = {"st": make_st({"google_voice": male[0], "talkg_gender": "F"}), "GOOGLE_P": GP, "t": lambda k: k}
exec(compile(mutant, "mutant", "exec"), ns)
picked = []
try:
    ns["google_voice_row"]("talkg", lambda: picked.append(1))
    rerun = False
except Rerun:
    rerun = True
check("the mutant still picks", picked == [1])
check("but never reruns — which is the fault Marko saw", not rerun)

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
