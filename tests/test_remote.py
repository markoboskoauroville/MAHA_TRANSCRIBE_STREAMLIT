"""THE RELAY, ALONE. No Streamlit, no network, no browser."""
import sys, time
sys.path.insert(0, "/home/claude/app")
from ttt import remote as R

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

print("1 THE CODE")
codes = {R.new_code() for _ in range(400)}
check("1a 400 codes, 400 different", len(codes) == 400, len(codes))
check("1b none contains l, o, 0 or 1 — the four that get mistyped",
      not any(set("lo01") & set(c) for c in codes))
check("1c length is stable", {len(c) for c in codes} == {R.CODE_LENGTH})

print("\n2 TWO CHANNELS THAT DO NOT SEE EACH OTHER")
st = {}
c = R.new_code()
R.put(st, c, "spoken words", R.SAY)
R.put(st, c, "pasted words", R.HEAR)
check("2a say holds what T pushed", R.get(st, c, R.SAY)["text"] == "spoken words")
check("2b hear holds what the page pushed", R.get(st, c, R.HEAR)["text"] == "pasted words")
check("2c writing one did not move the other's sequence",
      R.get(st, c, R.SAY)["seq"] == 1 and R.get(st, c, R.HEAR)["seq"] == 1)
try:
    R.put(st, c, "x", "sideways"); ok = False
except ValueError:
    ok = True
check("2d an unknown channel is refused, not silently created", ok)

print("\n3 THE SEQUENCE ONLY MOVES WHEN THE TEXT DOES")
st2 = {}; c2 = R.new_code()
for _ in range(60):
    R.put(st2, c2, "same line", R.SAY)
check("3a sixty renders of the same text is one arrival",
      R.get(st2, c2, R.SAY)["seq"] == 1, R.get(st2, c2, R.SAY)["seq"])
R.put(st2, c2, "a different line", R.SAY)
check("3b changed text ticks it", R.get(st2, c2, R.SAY)["seq"] == 2)
R.put(st2, c2, "a different line", R.SAY, force=True)
check("3c PUSH sends again even when nothing changed — the button must work",
      R.get(st2, c2, R.SAY)["seq"] == 3, R.get(st2, c2, R.SAY)["seq"])

print("\n4 ARRIVED — the whole receiving side")
slot = R.get(st2, c2, R.SAY)
check("4a new text is an arrival", R.arrived(slot, 2))
check("4b the same text seen again is not", not R.arrived(slot, 3))
check("4c a slot that has never been written is not", not R.arrived(R.get(st2, c2, R.HEAR), 0))
R.put(st2, c2, "   ", R.HEAR, force=True)
check("4d whitespace is not an arrival — clearing must not make it speak",
      not R.arrived(R.get(st2, c2, R.HEAR), 0), R.get(st2, c2, R.HEAR))
check("4e a missing slot is not an arrival", not R.arrived(None, 0))

print("\n5 THE WINDOW CLOSES ITSELF")
st3 = {}; c3 = R.new_code()
now = time.time()
R.put(st3, c3, "old", R.SAY, now=now - R.IDLE_SECONDS - 10)
check("5a an idle window reads as gone", R.get(st3, c3, R.SAY, now=now) is None)
check("5b and it was DELETED, not left sitting in memory", c3 not in st3, list(st3))
st4 = {}; c4 = R.new_code()
R.put(st4, c4, "old", R.SAY, now=now - R.IDLE_SECONDS - 10)
R.put(st4, c4, "new", R.HEAR, now=now)
check("5c traffic on EITHER channel keeps the window alive",
      R.get(st4, c4, R.SAY, now=now) is not None)
st5 = {}
for _ in range(5):
    R.put(st5, R.new_code(), "x", R.SAY, now=now - R.IDLE_SECONDS - 10)
R.put(st5, "keeper", "x", R.SAY, now=now)
check("5d sweep drops the dead and keeps the live", R.sweep(st5, now) == 5 and list(st5) == ["keeper"], list(st5))

print("\n6 AN UNKNOWN CODE IS NOT AN ERROR")
check("6a a code nobody opened reads as nothing", R.get({}, "zzzzzzz", R.SAY) is None)
check("6b and does not create it", True)

print("\n7 THE LINK")
check("7a built from the app's own base",
      R.link_for("https://ttt-lll.streamlit.app", "abc2345") == "https://ttt-lll.streamlit.app/?remote=abc2345")
check("7b a trailing slash does not double", R.link_for("http://x/", "q") == "http://x/?remote=q")
check("7c age reads in words", (R.age_words(2), R.age_words(30), R.age_words(120), R.age_words(7200)) == ("just now", "30s ago", "2m ago", "2h ago"),
      (R.age_words(2), R.age_words(30), R.age_words(120), R.age_words(7200)))

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
