"""TEST 1 — THE MECHANISM ALONE.

No network, no audio, hand-picked inputs. Attacks the rules: the case each
is for, the case it must refuse, both sides of every boundary, two rules
colliding, and the same input twice.
"""
import sys
sys.path.insert(0, '/home/claude/repo')
from ttt import wordtimes as wt

P, F = 0, 0
def ck(name, got, want):
    global P, F
    ok = got == want
    if ok: P += 1
    else:
        F += 1
        print(f"  FAIL {name}\n       got  {got!r}\n       want {want!r}")
    return ok

def ckt(name, cond, note=''):
    global P, F
    if cond: P += 1
    else:
        F += 1
        print(f"  FAIL {name}  {note}")

H = lambda w, s, e: {"word": w, "start": s, "end": e}

# ---- normalise: the rule it is for, and what it must NOT collapse ----
ck("normalise lowercases", wt.normalise("Hello"), "hello")
ck("normalise strips punctuation", wt.normalise("said,"), "said")
ck("normalise spells small digits", wt.normalise("3"), "three")
ck("normalise spells 12", wt.normalise("12"), "twelve")
ck("normalise leaves 13+ as digits", wt.normalise("13"), "13")
ck("normalise leaves years alone", wt.normalise("1947"), "1947")
ck("normalise keeps unicode letters", wt.normalise("čovjeka"), "čovjeka")
ck("normalise of empty is empty", wt.normalise(""), "")
ck("normalise of pure punctuation is empty", wt.normalise("—"), "")
ckt("normalise does NOT collapse different words",
    wt.normalise("cat") != wt.normalise("dog"))

# ---- mapping: exact, reordered, missing, extra, merged ----
ck("exact match maps one to one",
   wt.map_heard_to_text([H("one",0,1),H("two",1,2)], ["one","two"]), [0,1])
ck("digit/word spelling still matches",
   wt.map_heard_to_text([H("1,",0,1),H("2,",1,2)], ["One","two"]), [0,1])
ck("a dropped word leaves a gap, others stay aligned",
   wt.map_heard_to_text([H("a",0,1),H("c",2,3)], ["a","b","c"]), [0,None,1])
ck("an extra heard word is skipped",
   wt.map_heard_to_text([H("a",0,1),H("x",1,2),H("b",2,3)], ["a","b"]), [0,2])
ck("prefix match ties merged tokens together",
   wt.map_heard_to_text([H("3,500",0,1),H("people",1,2)], ["3,500 people"]), [0])
ck("no heard words maps everything to None",
   wt.map_heard_to_text([], ["a","b"]), [None,None])
ck("no displayed words returns empty", wt.map_heard_to_text([H("a",0,1)], []), [])
ck("completely unrelated text still returns the right LENGTH",
   len(wt.map_heard_to_text([H("zzz",0,1)], ["a","b","c"])), 3)

# ---- times: ordering is the invariant a reader sees ----
t = wt.times_from_heard([H("a",0.0,0.5),H("b",0.5,1.0),H("c",1.0,1.5)],
                        ["a","b","c"], 1.5)
ck("starts come straight from heard", [round(x[0],3) for x in t], [0.0,0.5,1.0])
ck("each end meets the next start", [round(x[1],3) for x in t], [0.5,1.0,1.5])

t = wt.times_from_heard([H("a",0.0,0.5),H("d",1.5,2.0)], ["a","b","c","d"], 2.0)
ckt("unmatched middle words are interpolated, not left at zero",
    t[1][0] > 0.0 and t[2][0] > t[1][0], f"{t}")
ckt("interpolated words stay between their neighbours",
    t[0][0] <= t[1][0] <= t[2][0] <= t[3][0], f"{t}")

# out-of-order input must not produce a backwards highlight
t = wt.times_from_heard([H("a",1.0,1.5),H("b",0.2,0.4)], ["a","b"], 2.0)
ckt("non-monotonic input is forced monotonic", t[0][0] <= t[1][0], f"{t}")

# same input twice
h = [H("a",0.0,0.4),H("b",0.4,0.9)]
ck("same input twice gives the same answer",
   wt.times_from_heard(h,["a","b"],0.9), wt.times_from_heard(h,["a","b"],0.9))

ck("no heard words yields no times", wt.times_from_heard([], ["a"], 1.0), None)
ck("no displayed words yields no times", wt.times_from_heard([H("a",0,1)], [], 1.0), None)

# ---- proportional fallback ----
p = wt.proportional(["aa","bb"], 2.0)
ck("proportional splits evenly for equal lengths",
   [round(x[0],3) for x in p], [0.0,1.0])
ck("proportional of no words is empty", wt.proportional([], 5.0), [])
ck("proportional of no duration is empty", wt.proportional(["a"], 0), [])
ckt("proportional never exceeds the total",
    abs(wt.proportional(["a","bb","ccc"],3.0)[-1][1] - 3.0) < 1e-9)

# ---- the layered entry point ----
marks = [(0.0,1.0),(1.0,2.0)]
ck("engine marks are used when the count matches",
   wt.word_times(["a","b"], 2.0, engine_marks=marks), (marks,"engine"))
r, src = wt.word_times(["a","b","c"], 3.0, engine_marks=marks)
ck("engine marks with a WRONG count are refused", src, "proportional")
ck("no audio and no rotate falls through to proportional",
   wt.word_times(["a","b"], 2.0)[1], "proportional")
ck("empty words is handled", wt.word_times([], 1.0), ([], "none"))

# a rotate that explodes must not take the app down
def boom(fn): raise RuntimeError("key ring on fire")
ck("an exploding key ring degrades to proportional",
   wt.word_times(["a","b"], 2.0, audio_path="/nonexistent.wav",
                 rotate=boom)[1], "proportional")
# a rotate that returns nothing
ck("a key ring returning nothing degrades to proportional",
   wt.word_times(["a","b"], 2.0, audio_path="/nonexistent.wav",
                 rotate=lambda fn: None)[1], "proportional")
# a missing file must not raise
ck("a missing audio file returns None rather than raising",
   wt.fetch_word_times("/nonexistent.wav", "k"), None)


# ---- tokenize: offsets must index the ORIGINAL string ----
def spans_ok(text):
    return all(text[a:b] == w for w, a, b in wt.tokenize(text))
for txt in ["Wait — what? No, it's twenty-one.",
            "Zvuk je prvi element koji dopire.",
            "In 1947 the population reached 3,500 people.",
            "  leading and trailing  ",
            "one", "", "!!!", "a  b", "e-mail o'clock", "🎧 emoji here"]:
    ckt(f"offsets index the original: {txt[:24]!r}", spans_ok(txt))

ck("apostrophes stay inside the word",
   [w for w,_,_ in wt.tokenize("it's fine")], ["it's","fine"])
ck("hyphens stay inside the word",
   [w for w,_,_ in wt.tokenize("twenty-one")], ["twenty-one"])
# span ends at 4, so text[0:4] == "said" and the comma is left uncoloured
ck("trailing punctuation is NOT part of the span",
   wt.tokenize("said,")[0], ("said",0,4))
ckt("...and slicing with it really excludes the comma",
    "said,"[0:wt.tokenize("said,")[0][2]] == "said")
ck("em dash is not a word", [w for w,_,_ in wt.tokenize("a — b")], ["a","b"])
ck("digits are words", [w for w,_,_ in wt.tokenize("in 1947")], ["in","1947"])
ck("empty text has no tokens", wt.tokenize(""), [])
ck("punctuation-only text has no tokens", wt.tokenize("!?—"), [])
ck("None text has no tokens", wt.tokenize(None), [])

# ---- marks_for: refuses rather than guesses ----
ck("engine marks pass straight through",
   wt.marks_for("a b", b"x", 1.0, engine_marks=[{"start":0}]), [{"start":0}])
ck("no rotate means no marks", wt.marks_for("a b", b"x", 1.0), None)
ck("no audio means no marks",
   wt.marks_for("a b", None, 1.0, rotate=lambda f: None), None)
ck("no words means no marks",
   wt.marks_for("!!!", b"x", 1.0, rotate=lambda f: None), None)
ck("a failing rotate yields no marks",
   wt.marks_for("a b", b"x", 1.0, rotate=lambda f: (_ for _ in ()).throw(RuntimeError())), None)

# a rotate returning good heard data produces app-shaped marks
heard = [H("Wait",0.0,0.4), H("what",0.5,0.9), H("No",1.0,1.3)]
m = wt.marks_for("Wait — what? No,", b"x", 1.5, rotate=lambda f: heard)
ckt("marks come back in the app's shape",
    m and all({"start","end","start_time","end_time"} <= set(x) for x in m), f"{m}")
ckt("one mark per displayed word", m and len(m)==3, f"{m}")
ckt("mark spans point at real words",
    m and [ "Wait — what? No,"[x["start"]:x["end"]] for x in m ]==["Wait","what","No"], f"{m}")
ckt("mark times are non-decreasing",
    m and all(a["start_time"]<=b["start_time"] for a,b in zip(m,m[1:])))

print(f"\nTEST 1 (mechanism alone): {P} passed, {F} failed")
sys.exit(1 if F else 0)
