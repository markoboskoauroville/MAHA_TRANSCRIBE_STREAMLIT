"""NOTES — the model alone, then the app wiring.

    python3 tests/test_notes.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ttt import archive  # noqa: E402
from ttt import notes as N  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


print("NOTES — the model\n")

# --- making them ------------------------------------------------------
s = {}
a = N.add(s, "Prva bilješka o nečemu važnom")
check("1 a note is made", bool(a))
check("2 and is the only one", N.count(s) == 1)

b = N.add(s, "Druga bilješka")
check("3 the newest is first", N.items(s)[0]["id"] == b, N.items(s)[0])

check("4 empty text makes nothing", N.add(s, "   ") is None)
check("5 the same text twice in a row is not kept twice",
      N.add(s, "Druga bilješka") == b and N.count(s) == 2)

# --- headings ---------------------------------------------------------
check("6 an untitled note is headed by its first words",
      N.heading(N.get(s, a)) == "Prva bilješka o nečemu važnom",
      N.heading(N.get(s, a)))

long_id = N.add(s, "jedan dva tri četiri pet šest sedam osam")
check("7 a long note's heading is cut at a word, with an ellipsis",
      N.heading(N.get(s, long_id)) == "jedan dva tri četiri pet…",
      N.heading(N.get(s, long_id)))

N.update(s, a, title="Moj naslov")
check("8 a title, once given, wins", N.heading(N.get(s, a)) == "Moj naslov")

# --- editing ----------------------------------------------------------
N.update(s, a, text="promijenjeno")
check("9 the text can be changed", N.get(s, a)["text"] == "promijenjeno")
check("10 and the note remembers it was edited", bool(N.get(s, a)["edited"]))

# A FRESH LIST, and a note that is NOT already at the top.
#
# The first version of this check measured `pos_before` AFTER an earlier
# update in the same test had already run — so under a mutation that
# reorders on edit, the note had moved BEFORE the baseline was taken and
# the check compared the mutated order against itself. It could not fail.
# Caught by mutating the code and watching it stay green.
s_ord = {}
first = N.add(s_ord, "prva")
middle = N.add(s_ord, "druga")
last = N.add(s_ord, "treca")
expected = [last, middle, first]          # newest first, and it must stay
check("11a the starting order is newest first",
      [n["id"] for n in N.items(s_ord)] == expected,
      [n["id"] for n in N.items(s_ord)])

N.update(s_ord, first, text="prva, promijenjena")
check("11 EDITING DOES NOT REORDER THE LIST — the list must not reshuffle "
      "under someone's hand",
      [n["id"] for n in N.items(s_ord)] == expected,
      [n["id"] for n in N.items(s_ord)])

N.append(s_ord, middle, "jos nesto")
check("11b APPENDING does not reorder it either",
      [n["id"] for n in N.items(s_ord)] == expected,
      [n["id"] for n in N.items(s_ord)])

# --- the search cache must not be able to go stale --------------------
#
# Nothing tested this and a mutation that removed the invalidation stayed
# green. The cache is an optimisation; a stale one is a wrong answer.
s_cache = {}
c1 = N.add(s_cache, "zebra u zoo")
N.search(s_cache, "zebra")                       # warm the cache
N.update(s_cache, c1, text="slon u dzungli")
check("11c after editing, the OLD word is no longer found",
      N.search(s_cache, "zebra") == [], N.search(s_cache, "zebra"))
check("11d and the NEW word is", len(N.search(s_cache, "slon")) == 1)

N.append(s_cache, c1, "i jos jedna rijec: tigar")
check("11e after appending, the appended word is found",
      len(N.search(s_cache, "tigar")) == 1)

N.update(s_cache, c1, title="Naslov Zirafa")
check("11f a changed TITLE is searchable too",
      len(N.search(s_cache, "zirafa")) == 1, N.search(s_cache, "zirafa"))

# --- talking into a note ---------------------------------------------
N.update(s, a, text="prvi red")
N.append(s, a, "drugi red")
check("12 speaking again ADDS to the note", "prvi red" in N.get(s, a)["text"]
      and "drugi red" in N.get(s, a)["text"], N.get(s, a)["text"])
check("13 with a blank line between, so passes stay separable",
      N.get(s, a)["text"] == "prvi red\n\ndrugi red",
      repr(N.get(s, a)["text"]))
check("14 appending nothing changes nothing", N.append(s, a, "   ") is False)
check("15 appending to a note that is gone is refused, not a crash",
      N.append(s, "nope", "x") is False)

# --- speaking AT THE CURSOR -------------------------------------------
#
# Baba: "it does not insert when I put my cursor — it just appends
# normally, it ignores my cursor and puts a line at the end." That made
# a note a log rather than a document: you could add to the bottom and
# nowhere else.
s_cur = {}
c = N.add(s_cur, "prvi red\n\ntreci red")
N.append(s_cur, c, "drugi red", at=8)          # just after "prvi red"
check("15a A TAKE LANDS WHERE THE CURSOR WAS, not at the end",
      N.get(s_cur, c)["text"] == "prvi red\n\ndrugi red\n\ntreci red",
      repr(N.get(s_cur, c)["text"]))

s_end = {}
e = N.add(s_end, "sam")
N.append(s_end, e, "poslije")                  # no caret at all
check("15b NO CURSOR MEANS THE END — which is what a take from the deck "
      "gets, since the deck has no cursor to report",
      N.get(s_end, e)["text"] == "sam\n\nposlije",
      repr(N.get(s_end, e)["text"]))

s_far = {}
f = N.add(s_far, "kratko")
N.append(s_far, f, "iza", at=9999)
check("15c A CARET PAST THE END IS CLAMPED, not sliced past — a stale "
      "caret from a previous render must not drop the tail",
      N.get(s_far, f)["text"] == "kratko\n\niza",
      repr(N.get(s_far, f)["text"]))

s_top = {}
tp = N.add(s_top, "bilo sto")
N.append(s_top, tp, "na vrhu", at=0)
check("15d and a caret at 0 puts it at the top",
      N.get(s_top, tp)["text"].startswith("na vrhu"),
      repr(N.get(s_top, tp)["text"]))

# --- search -----------------------------------------------------------
s2 = {}
N.add(s2, "Kupiti kruh i mlijeko")
N.add(s2, "Nazvati Kerstin o putovanju")
N.add(s2, "Čekaj me u šumi kod potoka")
N.add(s2, "kruh za doručak")

check("16 search finds by word", len(N.search(s2, "kruh")) == 2,
      [N.heading(x) for x in N.search(s2, "kruh")])
check("17 search ignores capitals", len(N.search(s2, "KRUH")) == 2)
check("18 EVERY word must match, not any — narrowing must narrow",
      len(N.search(s2, "kruh doručak")) == 1,
      [N.heading(x) for x in N.search(s2, "kruh doručak")])
check("19 no diacritic needed — 'cekaj' finds 'Čekaj'",
      len(N.search(s2, "cekaj")) == 1,
      [N.heading(x) for x in N.search(s2, "cekaj")])
check("20 'sumi' finds 'šumi' too", len(N.search(s2, "sumi")) == 1)
check("21 an empty query returns everything", len(N.search(s2, "  ")) == 4)
check("22 nonsense returns nothing", N.search(s2, "zzzz") == [])

# --- deleting ---------------------------------------------------------
s3 = {}
x = N.add(s3, "jedan")
y = N.add(s3, "dva")
check("23 one can be removed", N.remove(s3, x) is True and N.count(s3) == 1)
check("24 the other survives", N.get(s3, y) is not None)
check("25 removing a ghost is False, not a crash", N.remove(s3, "no") is False)
N.clear(s3)
check("26 clear empties it", N.count(s3) == 0)

# --- the archive becomes notes ---------------------------------------
s4 = {}
archive.add(s4, "stara jedan")
archive.add(s4, "stara dva")
took = N.adopt_archive(s4)
check("27 old archive items become notes", took == 2 and N.count(s4) == 2,
      (took, N.count(s4)))
check("28 the newest archive item is the newest note",
      N.get(s4, N.items(s4)[0]["id"])["text"] == "stara dva",
      N.items(s4)[0]["text"])
check("29 ADOPTION RUNS ONCE — a second pass must not resurrect notes "
      "the person has since deleted",
      N.adopt_archive(s4) == 0 and N.count(s4) == 2)

s5 = {}
check("30 nothing to adopt is not an error", N.adopt_archive(s5) == 0)

# --- the limit --------------------------------------------------------
s6 = {}
for i in range(N.LIMIT + 20):
    N.add(s6, "note number %d" % i)
check("31 the list is capped", N.count(s6) == N.LIMIT, N.count(s6))
check("32 and it is the OLDEST that fall off",
      "note number %d" % (N.LIMIT + 19) == N.items(s6)[0]["text"],
      N.items(s6)[0]["text"])

# --- ids --------------------------------------------------------------
s7 = {}
ids = [N.add(s7, "x%d" % i) for i in range(5)]
check("33 every id is different — a counter, not a clock",
      len(set(ids)) == 5, ids)

print("\n{} passed, {} failed".format(passed, failed))


def test_notes():
    """The verdict, in the one form pytest can report. The checks
    themselves run above, at import, because this file is a script
    first — `python3 tests/test_notes.py` is how it is meant to be read."""
    assert failed == 0, "{} of {} checks failed — see the output above".format(
        failed, passed + failed)


# THE EXIT BELONGS TO THE SCRIPT, NOT TO THE IMPORT. At module level it
# fired during pytest's collection, which aborts the whole run with
# INTERNALERROR before one test is reported.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
