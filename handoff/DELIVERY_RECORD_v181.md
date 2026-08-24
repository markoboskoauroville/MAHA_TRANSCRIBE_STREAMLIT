# DELIVERY RECORD — TTT-LLL v181 — 24.8.2026

The TR tab gets its cassette deck, and it is a polyglot.

    VERSION    new: v181   previous: v180 (readability), v179, v178
    ARTEFACT   app.py, talk_engine.py, docs/HOW_WE_WORK.md, 2 tests

## THE RULE WAS AMENDED, NOT BROKEN

Baba locked "two languages for transcription and reading" this morning.
This change needed Spanish to speak, which that rule forbade. Rather
than quietly rewriting it, it was put to him, and he amended it:

  *"That language rule only applies to other tabs. Translation tab is
  free. It's a free soul. He can speak any. He is multilingual
  polyglot."*

So HOW_WE_WORK now reads:

    TRANSCRIPTION      hr, en. Locked
    READING IN T AND R hr, en. Locked — voices, pickers, engines
    INTERFACE          hr, en. Locked
    TRANSLATION        anything. TR translates it AND reads it aloud

And a new obligation: a language joining the TR grid must bring BOTH an
Edge voice, female and male — the deck offers exactly two buttons, and a
language that answers only one is a control that does nothing half the
time. tests/test_langs.py enforces it.

## WHAT WAS BUILT

- **The deck at the top of TR**, the same wave transport R has. Always
  drawn, whether anything is loaded or not.
- **One setting under it: female / male.** Baba: "user does not choose a
  voice by name, only female or male — we don't want to overburden them,
  they are old people." The ten Edge voices are now an implementation
  detail behind `tk.vkey_for(lang, gender)`.
- **A read link under EACH box.** The upper box speaks the UPPER row's
  language, the lower box the LOWER row's.
- **Spanish gained Elvira and Alvaro** (es-ES, Castilian), both
  confirmed live in Edge's catalogue.
- **Whole text in one piece**, unlike R, which splits into parts for
  pasted articles. A translation box holds a paragraph; one piece means
  no part-handoff and none of the seam bugs that machinery prevents.

## MEASURED

    every pairing        hr/en/it/de/fr/es x F/M -> the right voice,
                         9 cases checked, 9 correct
    english is british   every en voice is en-GB; "en-US" appears
                         nowhere in the voice table
    TR tab renders       deck, both gender pills, both read links,
                         six target pills HR ENG IT DE FR SPA,
                         0 exceptions
    empty boxes          both read links disabled, and now READABLY so
                         (v180: 5.41:1 rather than 1.45:1)

## GATES

    G1 PROVENANCE   pass    clean tree, v181 > v180, main
    G2 SECRETS      pass    diff 0 hits, 69 files 0 hits
    G3 ANALYSIS     pass    69 files, pyflakes 0 findings
    G4 DEAD CODE    pass    6 new symbols, all referenced (lowest: 2)
    G5 DEAD LOOPS   pass    tr_make_audio loops over plan_blocks, a
                            bounded list, and the text is capped at
                            TR_DECK_CAP=4000 chars before it starts.
                            Synthesis uses tk.synth_sentence, which
                            already carries R's deadlines
    G6 STRESS       partial 105 checks green; suite 21 files passed.
                            MUTATED THREE TIMES: lower box wired to the
                            source row (SLIPPED THROUGH the first
                            version of check 15 — the check was
                            rewritten to read inside tr_read, and then
                            caught it), Spanish given only a female
                            voice (red), en-US sneaking in (red)
    G7 BUDGETS      base+   105 checks (was 96)
    G8 UPGRADE      pass    `tr_gender` defaults to F; no stored shape
                            changed; rollback to v180 leaves an unused
                            session key and nothing else
    G9 RECORD       this document

## NOT TESTED — and one of these matters more than usual

    NO AUDIO WAS EVER PLAYED. tr_make_audio has NOT been run against
    edge-tts in this session — this sandbox cannot reach it. The voice
    LOOKUP is proven for all 12 combinations; whether the joined MP3
    plays cleanly in the wave component is unproven and is the first
    thing to check on the phone.

    MP3 JOINING          blocks are synthesised separately and joined
                         end to end. R relies on the same thing inside
                         a part, but TR joins across whole blocks. If a
                         click or a gap is audible at the seams, say so
    NO PHONE             the deck's look on TR at 390px, the two gender
                         pills, the read links' placement
    LONG TEXT            capped at 4000 chars, silently truncated —
                         nothing tells the person yet
    THE v180 GREY        the readability fix is measured but not seen
    STILL OPEN           copy/clear always-visible rule (written, not
                         implemented), Apps Script MAIN deploy for the
                         ETA, AssemblyAI round trip, HR->ENG and
                         single->multi mid-recording, Speechify
                         test-key button

## WHAT WAS WRONG WITH THE GATE — §15, sixth report

**A check that passes its mutation is worse than no check.** Check 15
asserted both language keys appeared in app.py — they do, all over the
tab — so wiring the lower box to the upper row passed cleanly. It was
only caught because the mutation was actually run. The module says to
mutate every new check; this session is the evidence for WHY, and the
rule deserves a stronger wording: a check must be mutated against the
specific failure it claims to prevent, not against any failure.

**Still true from v176-v179:** G8 has no web-app row, G2's history scan
degrades on a shallow clone, G6 cannot record mutations, harness
failures masquerade as artefact failures, and nothing catches visual
drift.
