"""READ, COPY, CLEAR — one row, and 1,4,4 as the reading plan.

    python3 tests/test_tr_row.py

Baba, 25.8.2026: "Read should be together with copy and clear. Read,
copy, clear, same position in the screen."

This is fault 3 from his FIRST brief, on 25.8.2026 at 03:20, and it
survived eleven versions: `read` had its own container under the row,
left-aligned, while copy and clear sat right-aligned above it. Two rows
for three links, and the odd one out looked like a different kind of
thing.

WHAT THIS CANNOT CATCH: whether the three now LOOK like one row at
390px. copy is a component in an iframe and its neighbours are Streamlit
buttons, which is the whole subject of HOW_WE_WORK's "why a component
never quite matches the page" — two stylesheets cannot be kept in step
by reasoning about them.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import speech as S  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
tr = app[app.index('elif active == "translate":'):app.index('elif active == "vr":')]

print("1 READ IS IN THE ROW, NOT UNDER IT")
print("       searched the translate tab, %d chars" % len(tr))
check("1a the source box's read is an extra on box_links",
      'extra=([(t("tr_read_src")' in tr and "nact_read_trsrc" in tr)
check("1b so is the output box's",
      "nact_read_trout" in tr and tr.count('extra=([(t("tr_read_src")') == 2,
      tr.count('extra=([(t("tr_read_src")'))
check("1c neither has its own container any more",
      'key="nact_trsrc"' not in tr and 'key="nact_trout"' not in tr,
      [x for x in ("nact_trsrc", "nact_trout") if 'key="%s"' % x in tr])
check("1d there are exactly two box_links calls in TR",
      tr.count("box_links(") == 2, tr.count("box_links("))

print("\n1b THE ORDER IS COPY, CLEAR, READ")
# box_links appends extras after copy and clear, which is the order he
# asked for in the first brief: "Read should be Copy, Clear, Read."
bl = app[app.index("def box_links("):]
bl = bl[:bl.index("\ndef tab_signature")]
check("1e copy is added first", bl.index('items.append(("copy"')
      < bl.index('items.append(("clear"'))
check("1f clear second", bl.index('items.append(("clear"')
      < bl.index("items += list(extra or [])"))
check("1g extras last, so read lands third",
      "items += list(extra or [])" in bl)
check("1h and they share ONE row of equal columns",
      "cols = st.columns([1] * len(items))" in bl)

print("\n1c A READ LINK OVER AN EMPTY BOX WOULD BE A DEAD LINK")
# box_links renders the row whenever a module offers an extra, so the
# extra is passed only when there is text. Otherwise `read` would stand
# alone over an empty box with nothing to read.
check("1i the source extra is conditional on the box having text",
      "_trsrc_body else None" in tr)
check("1j and so is the output's", "_trout_body else None" in tr)
check("1k both read the box they belong to, not each other's",
      'translate_src_text" or ""' in tr.replace("get(", "")
      or "_trsrc_body = " in tr)

print("\n1d EACH BOX READS ITS OWN LANGUAGE")
# The upper box speaks the UPPER row's language. Getting this backwards
# would read a translation in the language it came from.
check("1l the source link calls tr_read('src')",
      'tr_read("src")' in tr)
check("1m the output link calls tr_read('out')",
      'tr_read("out")' in tr)
check("1n they are not the same call twice",
      tr.count('tr_read("src")') == 1 and tr.count('tr_read("out")') == 1)

print("\n2 THE READING PLAN IS 1, 4, 4")
check("2a the reader asks for a one-sentence first block",
      "SPEECH.plan_even(sentences, first=1)" in app)
sizes = [len(b) for b, _ in S.plan_even(["S."] * 25, first=1)]
print("       25 sentences -> %s" % sizes)
check("2b the first block is ONE sentence — sound starts at once",
      sizes[0] == 1, sizes)
check("2c and every full block after it is four",
      set(sizes[1:-1]) == {4}, sizes)
check("2d nothing is lost",
      sum(sizes) == 25, sum(sizes))
check("2e a single-sentence text is still one block",
      [len(b) for b, _ in S.plan_even(["Only."], first=1)] == [1])
check("2f the offsets still land on their own first sentence",
      all(" ".join(["S%d." % i for i in range(9)])[o:o + len(b[0])] == b[0]
          for b, o in S.plan_even(["S%d." % i for i in range(9)], first=1)))

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
