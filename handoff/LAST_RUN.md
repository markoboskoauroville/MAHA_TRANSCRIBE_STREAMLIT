# STEP: two models, and what they cost
STATUS: done, pushed as v168. No deploy needed.
**The key/credit PANEL is still not built — the arithmetic under it is.**

WHAT BABA GAVE ME
- Universal-3.5 Pro, pre-recorded (async): $0.21/hr → ~238 hours
- Universal-Streaming, real-time: $0.15/hr → ~333 hours
- "We're going to use only these 2 models. You need to restrict on
  these 2 models only."

THE NUMBERS CHECK OUT, and that matters
- 50 / 0.21 = 238.1 and 50 / 0.15 = 333.3, both matching the hours he
  quoted against the $50 a new account starts with. Two independent
  figures agreeing is why these are written down as FACT rather than
  left as an editable box.
- THAT BOX WAS ME HEDGING. I had found three different prices on the web
  ($0.15, $0.21, $0.37) and planned a settings field so somebody else
  could resolve it. He has the real ones, so the hedge is gone: one
  place holds the rates, and the picker note, the hours-left figure and
  the cost-so-far all follow it.

RESTRICTED TO TWO
- `universal-3-pro` and plain `universal` were in the picker and are
  gone. A picker offering a model nobody has priced can produce a bill
  nobody expected, and the whole point of an hours-left figure is that
  every path has a known rate.

THE ONE THING I COULD NOT VERIFY, AND SAID SO IN THE CODE
- Which of the two rates the SYNC endpoint bills at. It sends Universal
  3.5 Pro — read from TTT mini's header, not assumed — so cost_of is
  called with the model actually sent, and a real invoice should be
  checked against it once. Guessing quietly would put a wrong number
  under "hours left", which is the number he asked for.
- And an unknown model falls back to the DEARER rate, so a mistake
  over-estimates the cost rather than under-estimating it.

NUMBERS
- aai sync 17 (was 11) · engines 28 · engine sheet 28 — green
- mutations: a third model in the picker fails 1, swapped rates fail 4
- pyflakes clean

STILL TO BUILD
- The panel itself: paste, test, delete, the free/paid toggle, hours
  left, cost per hour, and the link to pay. Settings keys are reserved
  (aai_key, aai_on, aai_rate, aai_credit, aai_spent_s) — `aai_rate` can
  go now that the rates are known.
