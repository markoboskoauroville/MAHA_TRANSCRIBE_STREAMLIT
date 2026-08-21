import os, sys
sys.path.insert(0, ".")
from streamlit.testing.v1 import AppTest
from ttt import notes as N

def sget(at,k,d=None):
    try: return at.session_state[k]
    except (KeyError, AttributeError): return d

def clean():
    import tempfile
    p=os.path.join(tempfile.gettempdir(),"maha_settings","stub.json")
    try: os.remove(p)
    except OSError: pass

ok=fail=0
def ck(n,c,d=""):
    global ok,fail
    if c: ok+=1; print("  ok   "+n)
    else: fail+=1; print("  FAIL "+n+("  — "+str(d) if d else ""))

def app(seed=None, open_id=None):
    clean()
    at=AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "app.py"), default_timeout=90)
    at.session_state["_authed"]=True; at.session_state["_user"]="stub"
    at.session_state["active_tab"]="transcribe"
    if seed:
        st={}
        ids=[N.add(st,x) for x in seed]
        at.session_state[N.KEY]=st[N.KEY]
        at.session_state["_notes_adopted"]=True
        if open_id is not None:
            at.session_state["_open_note"]=st[N.KEY][open_id]["id"]
    return at

print("NOTES IN THE APP\n")

at=app()
at.run()
ck("1 T renders with no notes", not at.exception, at.exception)
ck("2 no search box when there is nothing to search",
   not [x for x in at.text_input if x.key=="notes_q"])

at=app(["kruh i mlijeko","nazvati Kerstin","cekaj me u sumi"])
at.run()
ck("3 T renders with notes", not at.exception, at.exception)
ck("4 the search box is there",
   bool([x for x in at.text_input if x.key=="notes_q"]))
cards=[b.key for b in at.get("button") if b.key.startswith("note_n")]
ck("5 one card per note", len(cards)==3, cards)

# search narrows
at2=app(["kruh i mlijeko","nazvati Kerstin","cekaj me u sumi"])
at2.run()
[x for x in at2.text_input if x.key=="notes_q"][0].set_value("kruh").run()
cards2=[b.key for b in at2.get("button") if b.key.startswith("note_n")]
ck("6 searching narrows the cards", len(cards2)==1, cards2)

# opening one takes over
at3=app(["prva biljeska","druga"], open_id=0)
at3.run()
ck("7 the open note renders", not at3.exception, at3.exception)
keys=[b.key for b in at3.get("button")]
ck("8 THE MAIN BOX IS NOT DRAWN while a note is open",
   not [a for a in at3.text_area if a.key.startswith("tx_area_")],
   [a.key for a in at3.text_area])
ck("9 the command row is not drawn either",
   "tx_grammar" not in keys and "tx_clear" not in keys, keys)
ck("10 the note has a close button", "note_close" in keys, keys)
ck("11 and a delete", "note_del" in keys, keys)
ck("12 the card list is not drawn under it",
   not [k for k in keys if k.startswith("note_n") and k[5:].isdigit()], keys)

# closing brings it back
[b for b in at3.get("button") if b.key=="note_close"][0].click().run()
ck("13 closing returns the box",
   bool([a for a in at3.text_area if a.key.startswith("tx_area_")]),
   [a.key for a in at3.text_area])
ck("14 and the cards", bool([b.key for b in at3.get("button")
   if b.key.startswith("note_n")]))

# delete needs two presses
at4=app(["jedna","druga"], open_id=0)
at4.run()
before=len(sget(at4,N.KEY,[]))
[b for b in at4.get("button") if b.key=="note_del"][0].click().run()
ck("15 ONE press does not delete — it arms",
   len(sget(at4,N.KEY,[]))==before, len(sget(at4,N.KEY,[])))
ck("16 and the button now asks to be sure",
   "note_del2" in [b.key for b in at4.get("button")],
   [b.key for b in at4.get("button")])
[b for b in at4.get("button") if b.key=="note_del2"][0].click().run()
ck("17 the second press deletes", len(sget(at4,N.KEY,[]))==before-1,
   len(sget(at4,N.KEY,[])))
ck("18 and the note closes", sget(at4,"_open_note") is None)

print("\n%d passed, %d failed" % (ok,fail))
sys.exit(1 if fail else 0)
