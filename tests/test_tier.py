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
ck("5 but it still has new and clear",
   "tx_new" in k and "tx_clear" in k, k)

at2=app("studio"); at2.run()
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
