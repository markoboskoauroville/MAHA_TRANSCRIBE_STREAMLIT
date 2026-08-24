import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from streamlit.testing.v1 import AppTest
ok=fail=0
def ck(n,c,d=""):
    global ok,fail
    if c: ok+=1; print("  ok   "+n)
    else: fail+=1; print("  FAIL "+n+("  — "+str(d) if d else ""))
def app(tier):
    at=AppTest.from_file(os.path.join(os.path.dirname(__file__),"..","app.py"),
                         default_timeout=90)
    at.session_state["_authed"]=True; at.session_state["_user"]="stub"
    at.session_state["active_tab"]="transcribe"
    # v186: THE TIER IS THE PERSON, NOT THE ROUTES.
    #
    # It used to be read off the engine, so this file set the routes and
    # that made it studio. Baba's tiers replaced that: "any studio user
    # is also free user, but it's not admin user", and the radio at the
    # top moves the person's tier, which moves the tools with it.
    #
    # So the person has to BE studio. `stub` is named in Secrets at the
    # tier under test, and the routes below are left in place because
    # they still say which providers that tier uses.
    at.secrets["GROQ_API_KEYS"]=["gsk_test"]
    if tier=="studio":
        at.secrets["STUDIO_USER1"]="stub"
    else:
        at.secrets["FREE_USER1"]="stub"
    # THE ROUTES, NOT THE STORED NAME. EN.current() derives the engine
    # from the routes every render — deliberately, so a hand-patched
    # crosspoint reads "mixed" instead of claiming an engine that is no
    # longer running. Setting _assigned_engine alone proves nothing.
    from ttt import engines as EN
    eng = EN.get(tier)
    for task, provider in eng.routes.items():
        at.session_state["route_%s" % task] = provider
    return at
def keys(at): return [b.key for b in at.get("button")]

print("THE TIER DECIDES WHAT THE COMMAND ROW OFFERS\n")
at=app("normal"); at.run()
k=keys(at)
ck("1 the free tier renders", not at.exception, at.exception)
ck("2 FREE HAS NO GRAMMAR", "tx_grammar" not in k, k)
ck("3 free has no reshape", "tx_reshape" not in k, k)
ck("4 free has no custom", "tx_custom" not in k, k)
# `clear` left the command row in v132 — it is under the box now, with
# copy, like every other box in the app. What the FREE tier still has in
# the row is `new`, and what it has under the box is copy and clear.
# `new` moved under the box with the rest (v139), so it needs text too.
# That is right: a new take with an empty box is a no-op.
# AN EMPTY BOX STILL OFFERS ONE THING (v147): `add to notes`, which
# now makes a BLANK note to speak into — what `new` used to do. copy
# and clear stay away, because there is nothing to copy or clear.
ck("5 an empty box offers add-to-notes and nothing else",
   "tx_tonote" in k and "bl_clear_tx" not in k, k)
# THE LINKS APPEAR ONLY WHEN THERE IS TEXT. An empty box has nothing to
# copy and nothing to clear, and a dead link is a question with no good
# answer — so this seeds the box first.
at1b = app("normal")
at1b.session_state["_t1_text"] = "nesto"
at1b.session_state["_t1_text_gen"] = 1
at1b.run()
_k1b = keys(at1b)
ck("5b and clear appears under the box once there is text",
   "bl_clear_tx" in _k1b, _k1b)
# `new` IS GONE (v147). Baba: "we do not need new — copy copies, clear
# clears for new transcription, add to notes if it is empty creates a
# new note." Two words for one act.
ck("5c and `new` is gone entirely", "tx_new" not in _k1b, _k1b)
ck("5d but NOT the studio tools — the tier still decides",
   "tx_grammar" not in _k1b and "tx_custom" not in _k1b, _k1b)

# EVERYTHING T DOES TO ITS TEXT IS UNDER THE BOX NOW (v139), so it
# needs text to be there — the same rule as copy and clear. An empty
# box has nothing to fix, nothing to reshape and nothing to keep.
at2=app("studio")
at2.session_state["_t1_text"]="nesto za popraviti"
at2.session_state["_t1_text_gen"]=1
at2.run()
k2=keys(at2)
ck("6 the studio tier renders", not at2.exception, at2.exception)
ck("7 STUDIO HAS GRAMMAR", "tx_grammar" in k2, k2)
ck("8 studio has reshape", "tx_reshape" in k2, k2)
ck("9 studio has custom", "tx_custom" in k2, k2)

# custom opens rather than sitting open
ck("10 the custom box is CLOSED until asked for",
   not [x for x in at2.text_input if x.key=="_tx_custom_ask"],
   [x.key for x in at2.text_input])
[b for b in at2.get("button") if b.key=="tx_custom"][0].click().run()
ck("11 pressing custom opens a box to say what you want",
   bool([x for x in at2.text_input if x.key=="_tx_custom_ask"]),
   [x.key for x in at2.text_input])
ck("12 with a way out", "tx_custom_no" in keys(at2), keys(at2))
print("\n%d passed, %d failed"%(ok,fail))
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
def test_tier():
    assert fail == 0, "%d of %d failed" % (fail, ok+fail)
