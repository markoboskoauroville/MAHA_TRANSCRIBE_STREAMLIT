"""ABSOLUTE PRECISION OR NOTHING — one sentence, one file, one highlight.

    python3 tests/test_sentence_highlight.py

Baba, 5.9.2026: "The engines which do not support precise timings, like
Speechify — Edge also doesn't support, it kind of supports but it's not
precise, so we can also remove that part. WE WANT ABSOLUTE PRECISION OR
NOTHING, otherwise it's confusing. Generate each sentence in a separate
file and play each sentence as a file. But you need to buffer 3 in
memory, 3 sentences, so the transition is without any delay. And then
you highlight the sentence you are playing."

WHY THIS IS EXACT AND NOT MERELY FINER. Every highlight until now was a
CLAIM about where the voice had got to, made from timings of three
different honesties: Speechify's are real, Edge's word boundaries are
close but drift on Croatian, and Gemini publishes none at all. A mark
that is nearly right is worse than none — it teaches the eye to distrust
the page.

A sentence per file removes the claim. There is no clock: the file that
is sounding IS the sentence that is lit, so it cannot drift, and it
looks the same on every engine — a reader should not be able to tell
which engine is running by watching the page.

WHAT THIS CANNOT CATCH: whether a hand-off is audible. Three sentences
of buffer is a judgement about network latency on a phone, and only a
phone can settle it.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import speech as S  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

src = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))

print("1 ONE SENTENCE IS ONE BLOCK")
ss = ["One.", "Two is longer.", "Three."]
plan = S.plan_sentences(ss)
check("1a a block per sentence", len(plan) == len(ss), len(plan))
check("1b and never more than one in a block",
      all(len(b) == 1 for b, _ in plan), [len(b) for b, _ in plan])
check("1c in order, nothing lost",
      [b[0] for b, _ in plan] == ss, [b[0] for b, _ in plan])
joined = " ".join(ss)
check("1d every offset lands on its OWN sentence — the highlighter has "
      "nothing to drift against, but the offset still has to be true",
      all(joined[o:o + len(b[0])] == b[0] for b, o in plan),
      [(o, joined[o:o + 5]) for b, o in plan])
check("1e the first offset is zero", plan[0][1] == 0)

print("\n1b THE UGLY CASES")
check("1f nothing in, nothing out", S.plan_sentences([]) == [])
check("1g a blank is not a block", S.plan_sentences(["", "  ", "A."])
      == [(["A."], 4)], S.plan_sentences(["", "  ", "A."]))
long_one = "x" * 3000 + "."
big = S.plan_sentences([long_one])
check("1h a sentence past the provider's ceiling is SPLIT — a request "
      "that comes back 413 is a sentence that never plays",
      len(big) > 1, len(big))
check("1i and every piece fits", all(len(b[0]) <= 1500 for b, _ in big),
      [len(b[0]) for b, _ in big])
check("1j the pieces stay SEPARATE blocks rather than being merged back, "
      "so what is lit is always exactly what is sounding",
      all(len(b) == 1 for b, _ in big))
check("1k Croatian survives", [b[0] for b, _ in
      S.plan_sentences(["Čuo sam.", "Đavo."])] == ["Čuo sam.", "Đavo."])

print("\n2 THREE IN THE BUFFER")
check("2a the depth is three", S.BUFFER_AHEAD == 3, S.BUFFER_AHEAD)
check("2b and the reader uses it rather than the old two",
      "SPEECH.BUFFER_AHEAD" in code and "PREFETCH_AHEAD, len(parts)" not in code,
      "the reader still prefetches with PREFETCH_AHEAD")
check("2c which is deeper than the block-shaped default, because a "
      "single sentence buys two or three seconds of cover where a block "
      "of four bought fifteen",
      S.BUFFER_AHEAD > 2)

print("\n3 THE READER PLANS BY SENTENCE")
check("3a it calls plan_sentences", "SPEECH.plan_sentences(sentences)" in code)
check("3b and no longer plan_even, which lit four sentences at once",
      "SPEECH.plan_even(sentences" not in code,
      "plan_even is still the reader's planner")
check("3c plan_even is KEPT for engines metered by the CALL — Google's "
      "free tier is ten TTS requests per account per day, so a "
      "sentence-per-file paragraph would spend an account",
      "def plan_even" in open(os.path.join(
          os.path.dirname(__file__), "..", "ttt", "speech.py"),
          encoding="utf-8").read())

print("\n4 THE WHOLE SENTENCE IS LIT, NOT A WORD")
check("4a the current sentence carries the mark",
      "class='rdnow'" in code)
check("4b and it is the whole sentence, escaped, with no span inside it",
      "% html.escape(s))" in code
      and "_highlight_span(s, word_start, word_end)" not in code,
      "a word span is still being rendered")
check("4c the arguments that no longer mean anything are named rather "
      "than silently ignored", "del word_start, word_end" in code)
check("4d and they stay in the signature, so every caller keeps working",
      "word_start: int = None, word_end: int = None" in code)
check("4e the lit sentence is still the scroll anchor",
      "id='rdhere'" in code)
from ttt import theme  # noqa: E402
check("4f and it is visibly lit", ".rdnow" in theme.css("amber", "mono", 1.0))

print("\n5 IT LOOKS THE SAME ON EVERY ENGINE")
# The other half of what he asked for: a reader should not be able to
# tell which engine is running by watching the page.
check("5a nothing in the renderer asks which engine is playing",
      not any(w in code[code.find("def _render_page"):
                        code.find("def read_picture")]
              for w in ("edge", "speechify", "google", "engine")),
      "the renderer knows a vendor's name")

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
