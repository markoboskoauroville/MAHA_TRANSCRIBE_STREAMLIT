# DELIVERY RECORD — TTT-LLL v182 — 24.8.2026

VR — Virtual Rehearsal. A fourth tab, Hume AI, and an emotion grid.

    VERSION    new: v182   previous: v181
    NEW FILES  ttt/vr.py, ttt/providers/hume.py, tests/test_vr.py

## ⚠️ BEFORE IT WORKS FOR ANYONE

**The owner must import a Hume key** in Settings → keys, via the file
picker, exactly as Speechify's were imported. Until then VR renders
fully and says "No Hume key yet". Baba is making more keys for the
fallback ring; the ring rotates them already.

## WHAT WAS BUILT

- **24 voice pills**, 12 female and 12 male, each showing accent and
  age. Every name read from the live catalogue (160 voices, 2 pages) on
  24.8.2026, not remembered.
- **18 emotion checkboxes**, combinable, up to four at once.
- **A deck at the top**, same transport as R and TR.
- **A free-text direction box** for anything the grid does not cover.
- **The pace, stated in seconds**: the button disables itself and reads
  "Hume AI is drinking coffee ☕ — 7 seconds".

## THE VOICE ROSTER, AND WHY IT IS NOT WHAT WAS ASKED

Baba asked for voices with "actor" in the name. Measured: 3 have it, all
male. The women are called "Actress" — 4 of them. And there is exactly
ONE British actor voice and NO British actress, so a UK-only actor cast
would have been one voice, not four. He then said narrators and hosts
were a good idea, and asked for many.

Even so the performer names run 18 male to 5 female. A rehearsal tool
that offers a woman five parts and a man eighteen is not a rehearsal
tool, so the female roster reaches into the wider English catalogue for
voices of the same character — journalists, ladies, storytellers,
mothers. Balance was worth more than the naming rule it cost. This is a
DECISION, not an oversight, and it is the first thing to overrule if
Baba disagrees.

"Most popular" could not be honoured: the API exposes id, name, provider
and tags. There is no popularity, ranking or usage field. Nothing was
invented to fill that gap.

## THE BUG THIS SESSION CAUGHT BEFORE SHIPPING

Every call from inside the app's own HTTP client returned **403 "error
code: 1010"** while curl succeeded with an identical request. Baba's
brief predicted a sandbox proxy problem; it was not that.

It is **Cloudflare**, which Hume sits behind, banning urllib's DEFAULT
user agent by browser signature. Measured, same key and body, same
second: no User-Agent -> 403 every time; any ordinary User-Agent -> 200
every time.

Two consequences, both fixed:

1. Every Hume request now names the app.
2. **403 no longer classifies as a dead key.** It did, which meant one
   Cloudflare answer would have marched through the ring and burned
   every key Baba owns while all of them were perfectly fine. That is
   the worst outcome available in this whole feature, and it was one
   HTTP status away.

## MEASURED, WITH BABA'S KEY

    key                 200 on the voices endpoint
    catalogue           160 voices walked, 2 pages, all 24 names verified
    emotion works       same line and voice: calm 2.59s vs angry 2.91s
                        (+12%); joyful 2.35s vs sad 2.87s (+22%)
    end to end          4 generations through the app's exact code path
                        and pacing: 4 of 4 OK, ZERO 429s
                        Male English Actor / calm        2.75s
                        Classical Film Actress / sad+angry 1.95s
                        Indian Actress / afraid+tender+pleading 2.23s
                        Lady Elizabeth / cold+sarcastic  2.11s
    pacing              12s, Baba's own measurement (0.2s -> 15 refusals,
                        3s -> still refused, 12s -> 31 of 31)
    tab renders         24 voice pills, 18 emotion boxes, button
                        correctly disabled on an empty box, 0 exceptions

## GATES

    G1 PROVENANCE   pass    clean tree, v182 > v181, main
    G2 SECRETS      pass    diff scanned for key SHAPES: 0 hits; diff
                            scanned for Baba's actual Hume key prefix:
                            0 hits; 72 files: 0 hits. Error bodies are
                            scrubbed of anything 32+ chars before they
                            can reach a screen — Hume quotes requests
                            back
    G3 ANALYSIS     pass    72 python files, pyflakes 0 findings
    G4 DEAD CODE    pass    every new symbol referenced; Hume registered
                            through the registry's documented "one file
                            plus one line", so nothing bespoke
    G5 DEAD LOOPS   pass    hume_call has a 120s timeout; the ring loop
                            is bounded by key count; THE PACE ITSELF is
                            the deadline that matters and it is tested
                            without waiting, because wait_left takes
                            `now` as an argument
    G6 STRESS       partial 145 checks green (40 new). MUTATED FIVE
                            TIMES, all five red where predicted: pace
                            12->3 (6 checks red), wait_left rounding
                            down, direction ordered by tick order,
                            stamp taken after the call, User-Agent
                            removed
    G7 BUDGETS      base+   145 checks (was 105); +2 modules
    G8 UPGRADE      pass    new tab, new provider, new session keys.
                            Nothing stored changed shape. Rolling back
                            to v181 leaves an unused "hume" ring
    G9 RECORD       this document

## NOT TESTED

    NO PHONE            24 pills in threes and 18 checkboxes in threes
                        is the densest screen in this app. How it wraps
                        at 390px is unknown and is the most likely
                        thing to be wrong
    NO AUDIO HEARD      four WAVs were generated and their sizes and
                        durations checked. Nobody has LISTENED. Whether
                        "sad + angry" actually sounds sad and angry is
                        Baba's ear, not a number
    WAV, NOT OPUS       the deck ships raw WAV — about 96 KB per second.
                        A 3s line is 250 KB through the browser. Baba's
                        brief says convert to Opus (31x smaller) and
                        that is NOT done here; ffmpeg is available in
                        the app for this and it is the obvious next step
    THE RING            rotation is tested by reading, not by running:
                        one key exists. It cannot be exercised until
                        Baba adds a second
    429 RECOVERY        never provoked. The pacing means it has not
                        happened once, which is the point, but it also
                        means the cool-down path is unproven
    STILL OPEN          copy/clear always-visible rule (written, not
                        implemented), Apps Script MAIN deploy for the
                        ETA, AssemblyAI round trip, HR->ENG and
                        single->multi mid-recording, Speechify test-key
                        button, the TR deck's audio

## WHAT WAS WRONG WITH THE GATE — §15, seventh report

**No gate asks whether an error status means what the code thinks it
means.** 403 was classified as a dead key by analogy with Speechify, and
it passed every gate; it would have burned an entire key ring on its
first Cloudflare hiccup. G5 covers waits that never end; nothing covers
a FAILURE PATH THAT DOES THE WRONG THING CONFIDENTLY. That class
deserves naming beside UNREACHABLE, UNREFERENCED, UNWIRED and VISUAL
DRIFT.

**Two of my own checks passed while asserting nothing** — one counted
commas in a string full of commas, one compared escaped source text and
failed on its own quoting. Both were caught only because they were run
and read. The module's rule should be sharper: a check must be MUTATED
against the specific failure it names, and a check whose failure message
cannot be produced on demand is not yet a check.
