import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import notes as N
ok=fail=0
def ck(n,c,d=""):
    global ok,fail
    if c: ok+=1; print("  ok   "+n)
    else: fail+=1; print("  FAIL "+n+("  — "+str(d) if d else ""))

s={}
ck("1 None text makes nothing", N.add(s, None) is None)
ck("2 only punctuation still makes a note", bool(N.add(s, "...")))
ck("3 and its heading is not empty", N.heading(N.items(s)[0]) != "")

huge = "riječ " * 60000
hid = N.add(s, huge)
ck("4 a 300,000-character note is kept", bool(hid))
ck("5 its heading is still short", len(N.heading(N.get(s,hid))) < 60,
   len(N.heading(N.get(s,hid))))
ck("6 its preview is still short", len(N.body_preview(N.get(s,hid))) <= 121,
   len(N.body_preview(N.get(s,hid))))

import time
t0=time.time(); N.search(s, "riječ"); dt=time.time()-t0
ck("7 searching a huge note is not slow", dt < 1.0, "%.3fs" % dt)

ck("8 a hostile query does not crash", isinstance(N.search(s, "((("), list))
ck("9 a query of only spaces returns everything",
   len(N.search(s, "     ")) == len(N.items(s)))
ck("10 a 5000-word query does not crash",
   isinstance(N.search(s, "x "*5000), list))

ck("11 get on a missing id is None", N.get(s, "nope") is None)
ck("12 update on a missing id is False", N.update(s, "nope", text="x") is False)
ck("13 heading of a note with no text key", N.heading({}) == "—")
ck("14 preview of a note with no text key", N.body_preview({}) == "")

bad = {"_t1_notes": "not a list"}
ck("15 a corrupted store is replaced, not fatal", bool(N.add(bad, "x")))

s2={}
a=N.add(s2,"one")
N.update(s2,a,title="   ")
ck("16 a whitespace title falls back to the words",
   N.heading(N.get(s2,a)) == "one", N.heading(N.get(s2,a)))

s3={}
b=N.add(s3,"x")
for i in range(200): N.append(s3,b,"line %d"%i)
ck("17 two hundred appends do not corrupt it",
   N.get(s3,b)["text"].count("line ")==200)

s4={}
N.add(s4,"čćžšđ ČĆŽŠĐ")
ck("18 diacritics survive storage", "čćžšđ" in N.items(s4)[0]["text"])
ck("19 and are findable folded", len(N.search(s4,"cczsd"))==1)
print("\n%d passed, %d failed" % (ok,fail))
sys.exit(1 if fail else 0)
