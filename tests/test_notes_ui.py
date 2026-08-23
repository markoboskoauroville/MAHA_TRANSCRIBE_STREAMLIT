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
        for x in seed: N.add(st,x)
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
# CARD KEYS CARRY THE POSITION NOW: "note_<index>_<id>", not "note_<id>".
# A duplicate id crashed the app outright, and the position makes the
# key unique whatever the ids say. These checks ask "is it a card",
# which is what they meant all along.
def is_card(k):
    return bool(k) and k.startswith("note_") and "_n" in k[4:]

cards=[b.key for b in at.get("button") if is_card(b.key)]
ck("5 one card per note", len(cards)==3, cards)

# search narrows
at2=app(["kruh i mlijeko","nazvati Kerstin","cekaj me u sumi"])
at2.run()
[x for x in at2.text_input if x.key=="notes_q"][0].set_value("kruh").run()
cards2=[b.key for b in at2.get("button") if is_card(b.key)]
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
   "tx_grammar" not in keys and "bl_clear_tx" not in keys, keys)
ck("10 the note has a close button", "note_close" in keys, keys)
ck("11 and a delete", "note_del" in keys, keys)
ck("12 the card list is not drawn under it",
   not [k for k in keys if is_card(k)], keys)

# closing brings it back
[b for b in at3.get("button") if b.key=="note_close"][0].click().run()
ck("13 closing returns the box",
   bool([a for a in at3.text_area if a.key.startswith("tx_area_")]),
   [a.key for a in at3.text_area])
ck("14 and the cards", bool([b.key for b in at3.get("button")
   if is_card(b.key)]))

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

# ── speaking while a note is open ────────────────────────────────────
#
# THE BUG THIS EXISTS FOR: the deck wrote to the box no matter what, and
# with a note open the box is not drawn — so the words went to a surface
# nobody could see. Not lost, INVISIBLE, which is worse: the app looked
# broken rather than wrong. Nothing tested WHERE the words went.
#
# A SOURCE CHECK, and here is why rather than a better one. deliver_text
# is reached only from the recorder, an opened file or the paste
# component — all three are components, and components return their
# default under AppTest, so not one of those doors can be opened from a
# test. Same limit as §73. Asserting on the source is worth more than a
# behavioural check that cannot reach the behaviour.
src = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
body = src.split("def deliver_text(", 1)[1].split("\ndef ", 1)[0]

ck("19 deliver_text asks whether a note is open",
   "OPEN_KEY" in body, body[:200])
ck("20 and when one is, it APPENDS THERE",
   "NOTES.append(st.session_state, open_id" in body, body[:200])
ck("21 and returns without touching the box — the box is not drawn, so "
   "writing to it is writing into the dark",
   "NOTES.append(st.session_state, open_id, new_text)\n        return" in body,
   body[:200])

# And the failure that used to be silent is now on the screen.
panel = src.split("def note_open_view(", 1)[1].split("\ndef ", 1)[0]
ck("22 a failed take inside a note is SHOWN, not swallowed",
   '_note_error' in panel and "st.error" in panel, panel[:200])

# --- the note's audio is kept too ------------------------------------
#
# Baba: "storage should work for both systems, recording and note."
#
# IT NEVER DID. transcribe_note_take made a FLAC, transcribed it and let
# it go — every word spoken into a note had its audio thrown away since
# notes gained a recorder in v101. The deck's takes were kept and the
# note's were not, and nothing said so, because failing to keep
# something you never promised to keep raises no error.
#
# SOURCE CHECKS: this path is reached only through a component, and a
# component returns its default under AppTest (§73). What can be
# asserted is the shape of the path.
note_take = src.split("def transcribe_note_take(", 1)[1].split("\ndef ", 1)[0]

ck("23 THE NOTE'S AUDIO IS KEPT, started alongside Whisper so it costs "
   "no waiting", "start_keeping(" in note_take, note_take[:200])
ck("24 and its transcript is written beside it, so a note's recording "
   "is as findable as any other and neither half can exist alone",
   "put_text(" in note_take, note_take[:200])
# ORDER IS NOT WHAT TEXT POSITION MEASURES HERE. `finish_keeping`
# appears TWICE — once in the failure path, which sits above the success
# path in the source, and once after the transcription. Comparing first
# occurrences said "wrong order" about code that is right, twice.
#
# What is worth asserting is that both halves exist and that the SUCCESS
# path finishes after the words arrive.
ck("25 the upload finishes in the success path, after the words have "
   "arrived — storage runs alongside them, never in front of them",
   # THREE, not two: the failure path, its guard, and the success
   # path. Counting them was me guessing at the shape of code I had
   # just written — what matters is that the LAST one comes after the
   # upload starts, which is the success path.
   note_take.rindex("finish_keeping(") > note_take.index("start_keeping("),
   note_take.count("finish_keeping("))
ck("26 A FAILED TAKE DOES NOT LEAVE AN ORPHAN. If transcription fails "
   "after the upload started, the recording is finished rather than "
   "abandoned half-written",
   "_orphan" in note_take, note_take[-400:])
ck("27 and storage can never cost the words: every part of it is "
   "wrapped", note_take.count("try:") >= 2, note_take.count("try:"))

print("\n%d passed, %d failed" % (ok,fail))


def test_notes_ui():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_notes_ui.py` is how it is meant to be read."""
    assert fail == 0, "{} of {} checks failed — see the output above".format(
        fail, ok + fail)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
