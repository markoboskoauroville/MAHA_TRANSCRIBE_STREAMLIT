# DELIVERY RECORD — TTT-LLL v177 — 24.8.2026

The SPA pill, the Braille status line, and the ETA that learns. Third
artefact through `MANTRA_MANIFEST/modules/delivery-gate.md`; the §15
report-back is at the bottom.

    VERSION    new: v177   previous: v176, in git history
    ARTEFACT   app.py 7784 lines, ttt/eta.py (new), ttt/sheet.py,
               apps_script/Code.gs 1138 lines, 2 new test files

## ⚠️ ONE THING ONLY BABA CAN DO

**The Apps Script MAIN needs a deploy.** `eta_put` and `eta_get` are new
branches; until they are deployed, `SHEET.put_timing` returns False, no
samples are ever stored, and the status line simply never shows a time.
Nothing else breaks — that is by design, but it also means a missing
deploy looks exactly like "the ETA doesn't work".

    Deploy -> Manage deployments -> ✏️ -> Version: NEW VERSION
    NEVER `New deployment` (HOW_WE_WORK, the rule that is never bent)

## WHAT CHANGED

1. **SPA pill.** The TR grid is HR ENG IT DE FR SPA. Spanish is a
   translation target and NOTHING else — no voice, no TRANSLATE_VKEY
   entry, not in LANGS5 (which also draws the login pills).
2. **The lock, as a test.** `tests/test_langs.py` enforces the rule Baba
   wrote into HOW_WE_WORK: hr and en for transcription and reading,
   anything for translation. It exists because the rule was broken
   within one session — a Spanish pill reached for a Spanish voice
   before anybody noticed the two are different offers.
3. **Quick Settings actually changes the voices.** Reported by Baba and
   real: the flip wrote `voice_engine`, the R tab's pills read the
   ROUTING, and nothing connected them. One `talking_engine()` now
   answers, and the flip writes both.
4. **The Braille status line.** Ten U+28xx frames, the engine named in
   parentheses, the estimate after it. It advances on each finished
   part rather than on a timer, because there is no loop to animate from
   and a frame that moves when something real happened beats one that
   spins while nothing does.
5. **The ETA.** Median wall-seconds-per-audio-second, per engine, over
   the last 40 samples, stored in the sheet's new `eta` tab.

## WHY A MEDIAN, AND WHY THE SHEET

The median is the whole reason the estimate improves instead of
drifting: one take that hit a rate limit and crawled is not a fact about
engine speed, and a mean would carry that limp into every later estimate
forever. Test 7 and 8 assert exactly this — 8 proves a mean WOULD have
been wrong, so the choice is measured rather than asserted.

The sheet rather than a text file because Streamlit Cloud wipes its disk
on every redeploy — a file loses the history at exactly the moment a
fresh estimate matters — and because a phone and a laptop then feed one
history. Baba chose the sheet when asked.

## GATES

    G1 PROVENANCE   pass    clean tree, v177 > v176, main, previous in
                            history
    G2 SECRETS      pass    staged diff 0 hits; 0 of 68 tracked files
                            carry a key shape; sandbox secrets.toml
                            confirmed NOT in the commit
    G3 ANALYSIS     pass    68 python files, pyflakes 0 findings;
                            Code.gs parses clean as JS
    G4 DEAD CODE    pass    12 new symbols, all referenced (lowest: 2).
                            The 13 unreferenced functions from v174
                            remain out of scope and remain
    G5 DEAD LOOPS   pass    2 new external waits (eta_put, eta_get),
                            both through _post with TIMEOUT=8s. The
                            spinner has no loop of its own — it is
                            advanced by the existing progress callback,
                            so it cannot spin forever on its own
    G6 STRESS       partial 68 mechanism checks green; suite 20 files
                            passed 0 failed; app boots 0 exceptions; TR
                            tab rendered and the six pills read
                            HR ENG IT DE FR SPA. MUTATED FOUR TIMES,
                            all four went red where predicted:
                            median->mean (5 red), MIN_SAMPLES 3->1
                            (3 red), Spanish given a voice (3 red),
                            Croatian Beatrice on the wrong model (v176)
    G7 BUDGETS      base+   app.py 7784 (was 7635), Code.gs 1138 (was
                            1067), +1 module 123 lines. 68 checks
                            (was 23)
    G8 UPGRADE      pass    the `eta` tab is CREATED ON FIRST WRITE, so
                            an existing sheet needs no migration; an
                            un-deployed script answers False and costs
                            an estimate, never a transcript; rolling
                            back to v176 leaves an orphan `eta` tab
                            that nothing reads and nothing breaks
    G9 RECORD       this document

## NOT TESTED — the part that matters

    NO PHONE, ANY OF IT   nobody has seen the Braille line spin, the
                          SPA pill, or the engine name in parentheses
                          on a real screen at 390px
    NO REAL SAMPLE        not one row has been written to the `eta`
                          tab. The estimator is tested against
                          synthetic samples only; the SHEET ROUND TRIP
                          IS UNTESTED and cannot be tested until the
                          MAIN deploy happens
    THE FIRST 3 TAKES     will show "learning how long this takes" and
                          no number. That is correct, not a fault
    THE ENGINE FIX        talking_engine() is verified by reading and
                          by boot; the actual Quick Settings flip
                          changing the visible pills is a phone check
    COPY/CLEAR RULE       written into HOW_WE_WORK this session and NOT
                          implemented — box_links() still returns early
                          on an empty box, which is the opposite of the
                          rule. Its own step
    STILL OPEN            AssemblyAI round trip, HR->ENG mid-recording,
                          single->multi mid-recording, Speechify "test
                          key" button, the v176 Speechify picker itself
    BROWSER SUITE         test_layout, test_reader, test_shake skipped
                          as always; 6 files need sheet/GAS config this
                          sandbox lacks and fail collection on
                          untouched v176 too

## KNOWN

- The spinner advances per finished PART. A single-part take shows one
  frame and does not animate — honest, but it will look static on short
  recordings. If that reads as frozen on a phone, say so and it becomes
  a timed rerun instead.
- The estimate is per engine and per SESSION cache; switching engines
  mid-session fetches that engine's history once, then reuses it.
- `eta` is capped at 500 rows, oldest deleted, so the sheet cannot grow
  without bound.

## WHAT WAS WRONG WITH THE GATE — §15, third report

**A stale `__pycache__` made a green test read as red.** After restoring
a mutated module, the suite still reported 3 failures until the bytecode
was cleared. The gate says "make each check fail on purpose, once" — it
does not say to clear caches before believing the restore. Two minutes
were spent suspecting correct code. The module should say: after a
mutation, clear caches before trusting the green.

**G6's mutation step has no place to record what was mutated.** Four
mutations were run this session and the record has nowhere structured to
put them, so they live in prose. A `MUTATED` line beside each gate would
make "the checks can fail" a claim with evidence rather than an
assertion.

**Still true from v176:** G8 has no row for a web app, and G2's history
scan silently degrades on a shallow clone.
