# STEP: the toggle actually routes

STATUS: done, pushed as v172. No deploy needed.

## ⚑ REMEMBER THIS — THE DELIVERY GATE ⚑

**Baba, 23.8.2026: "after the last step we need to go through this
process. Reading the manifest — modules/delivery-gate.md. Testing with
these principles."**

`MANTRA_MANIFEST/modules/delivery-gate.md`, written by him that day. It
is NOT the four tests. The four tests ask "does this change work"; the
gate asks **"may this artefact ship"** — nine checks, cheapest first,
each able to fail alone, each printing a COUNT rather than an adjective.

    G1 provenance   G2 secrets    G3 analysis
    G4 dead code    G5 dead loops G6 stress
    G7 budgets      G8 upgrade    G9 the record

**It names two of our own bugs by name.** G5 is "the transcription
failure where audio reaches the destination and the text never does: a
step skipped because the step before it ran out of time and nobody was
watching the clock" — that is v154. G4's UNWIRED class is "reachable,
correct, and nothing in the interface leads to it. It compiles. It
passes review. It does nothing" — that was `aai_on` between v171 and
this version.

**What it asks OF THE AI, by name:** G4 and G5. Reading every loop in
the project and asking "what bounds this", and every external wait and
asking "where is the deadline". Print the count examined, not only the
findings.

**The first project to run it should come back and write what was
wrong** — §15 says nothing in the account has been through it yet.

---

## What this step did

- v171 saved `aai_on` and NOTHING READ IT. That is precisely the gate's
  UNWIRED class, and it lasted exactly one version.
- `current_routes()` now honours it: toggle on AND a key present routes
  transcription to AssemblyAI; anything else leaves the free engine
  exactly as it was.
- A KEY IS REQUIRED WITH THE TOGGLE. A toggle on with no key would send
  work to a provider that cannot answer, failing later and further away
  than refusing here.

## Two bad tests, and what replaced them

1. I checked that the string `aai_on` appeared in the source. `if (False
   and ...aai_on...)` satisfies that perfectly — THE MUTATION SURVIVED
   and the check was a rumour, which is the gate's §14 exactly.
2. I then tried to rewrite the function's source with string
   replacement and exec it. It broke on an apostrophe in its own
   docstring. Clever, brittle, worse than what it replaced.
3. What is there now states the RULE independently and asserts the
   source still expresses it, including the exact `if (` shape. Both
   mutations now bite: disabling the toggle fails 1, removing the
   override fails 2.

## Numbers

- aai sync 34 (was 28) · engines 28 · engine sheet 28 · box 16 — green
- pyflakes clean

## Still open

- `PROVIDERS.all()` does not exist and I wrote it anyway; pyflakes
  cannot catch a missing module method. Caught by reading, not tooling.
- The sync path from v167 is still not called: the ENGLISH ≤118s fast
  route needs wiring into the AssemblyAI provider's transcribe.
