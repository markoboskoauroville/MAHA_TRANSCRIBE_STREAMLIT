"""THE OWNER'S GOLD EDGE, and who counts as the owner.

    python3 tests/test_owner_edge.py
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


def app(user):
    at = AppTest.from_file(
        os.path.join(os.path.dirname(__file__), "..", "app.py"),
        default_timeout=90)
    # v186: WHO THE OWNER IS COMES FROM SECRETS, BY NAME.
    #
    # This file used to rely on admin_user() falling back to
    # APP_PASSWORDS[0], which happened to be "stub". That fallback is
    # what the tiers replaced — the owner is ADMIN_USER1 now — so the
    # test has to say who it means instead of inheriting it.
    at.secrets["ADMIN_USER1"] = "stub"
    at.secrets["FREE_USER1"] = "emina"
    at.secrets["GROQ_API_KEYS"] = ["gsk_test"]
    at.session_state["_authed"] = True
    at.session_state["_user"] = user
    at.session_state["active_tab"] = "transcribe"
    return at


RULE = "border-color:var(--amber)"


def edge(at):
    """The one rule owner_edge() emits, or ''.

    Matching on "block-container" alone found the MAIN stylesheet, which
    styles that class too — so every check passed for everybody, and the
    mutation that gave the edge to everyone changed nothing. Match the
    exact rule instead.
    """
    return " ".join(m.value for m in at.markdown
                    if RULE in (m.value or ""))


print("THE OWNER'S EDGE\n")

# The fixture sets ADMIN_USER = stub, so "stub" is the owner here.
at = app("stub")
at.run()
check("1 the app runs for the owner", not at.exception, at.exception)
check("2 THE OWNER GETS A GOLD EDGE",
      "border-color:var(--amber)" in edge(at), edge(at)[:90])

at2 = app("emina")
at2.run()
check("3 a normal user does NOT get it", not edge(at2), edge(at2)[:90])
check("4 and the app still runs for them", not at2.exception, at2.exception)

# THE POINT OF THE TOKEN. The signature line at the foot is var(--amber)
# too, so the edge and the word `admin` are one colour by construction.
# A hex copied into the rule would drift the day a scheme changes, and
# then the two marks that mean "you are the owner" would disagree.
check("5 it uses the SAME token as the signature, not a copied hex",
      "var(--amber)" in edge(at) and "#" not in edge(at), edge(at)[:90])

print("\n{} passed, {} failed".format(passed, failed))

if __name__ == "__main__":
    sys.exit(1 if failed else 0)


def test_owner_edge():
    assert failed == 0, "%d of %d checks failed" % (failed, passed + failed)
