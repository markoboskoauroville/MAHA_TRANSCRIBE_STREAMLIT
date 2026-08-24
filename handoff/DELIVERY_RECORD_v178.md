# DELIVERY RECORD — TTT-LLL v178 — 24.8.2026

Notes get the recordings panel's selection and delete, and an open note
can send itself to R and play. Fourth artefact through the delivery gate.

    VERSION    new: v178   previous: v177, in git history
    ARTEFACT   app.py 7936 lines (was 7784), tests/test_notes_select.py

## WHAT CHANGED

1. **A tick beside every note**, the same control the recordings list
   uses, and an action row above: **select all · read · delete**.
2. **Select all doubles as select none**, exactly as recordings does.
3. **Delete arms before it fires** — one press says "delete 2 — sure?",
   the second carries it out. It works on many notes; that is the one
   act that genuinely means the same thing repeated.
4. **Read is one note only** and greys out for many, for the same reason
   `play` does in the recordings row.
5. **An open note has a `read` action link** in its own foot row, beside
   date, delete and close.
6. **read_note()** carries the note's text to R, picks a voice matching
   the note's language, closes the note, and starts playing — the same
   handoff `read_this` does from T.

## THE ONE REFACTOR, AND WHY IT WAS NECESSARY

`read_this` carried the Speechify-vs-Edge voice logic inline. Copying it
into `read_note` would have made two copies of the thing that CHANGED AT
v176 when the Speechify seats were reorganised — the exact shape that
put two shipped bugs in app.py before. It is now `_match_voice_to()`,
defined above both callers, used by both, and asserted single by test 20.

## MEASURED IN A RUNNING APP, not by reading

    select all              3 of 3 ticked
    press again             0 ticked
    delete, first press     armed, 3 notes still present — nothing lost
    delete, confirmed       n1 and n3 gone, n2 remains, 0 stale ticks
    read (English note)     tab -> talk, text -> "second note",
                            voice -> Sonia (English, matched), and
                            _auto_read consumed by R, which is the
                            reading having STARTED
    two notes ticked        read link disabled: True

## GATES

    G1 PROVENANCE   pass    clean tree, v178 > v177, main
    G2 SECRETS      pass    staged diff 0 hits; 0 of 69 tracked files
                            carry a key shape
    G3 ANALYSIS     pass    69 python files, pyflakes 0 findings
    G4 DEAD CODE    pass    7 new symbols, all referenced (lowest: 2)
    G5 DEAD LOOPS   pass    9 loop constructs in the diff, all bounded
                            by the notes list; 0 new external waits
    G6 STRESS       partial 91 mechanism checks green (23 new);
                            suite 21 files passed 0 failed; six
                            behaviours exercised in a running app.
                            MUTATED TWICE, both red where predicted:
                            select-all reading the whole notebook
                            instead of the filtered list (test 6),
                            delete forgetting to clear its tick (test 8)
    G7 BUDGETS      base+   app.py 7936 (was 7784). 91 checks (was 68)
    G8 UPGRADE      pass    no stored shape changed. Ticks live in
                            session only (`_np_<id>`), so an existing
                            notebook needs no migration and a rollback
                            to v177 loses nothing
    G9 RECORD       this document

## NOT TESTED

    NO PHONE            nobody has seen the tick, the row, or the read
                        link at 390px. THE ROW IS FOUR COLUMNS NOW in
                        the open note (was three) — that is the most
                        likely thing to wrap badly on a narrow screen
                        and it is exactly what I cannot check here
    THE PLAYER ITSELF   `_auto_read` is consumed by R, which is the
                        right signal, but no audio was generated or
                        heard. Whether the note actually SOUNDS is a
                        phone check
    LONG NOTES          read_note sends the whole note. A very long one
                        goes through R's own part-splitting, which is
                        untested here
    SEARCH + SELECT     select-all is asserted to use the filtered list
                        by reading and by test 6; typing a search and
                        then pressing select-all was NOT exercised in a
                        running app
    NO SOAK             as ever
    STILL OPEN          copy/clear always-visible rule (written, not
                        implemented), Apps Script MAIN deploy for the
                        ETA, AssemblyAI round trip, HR->ENG mid-record,
                        single->multi mid-record, Speechify test-key
                        button, the v176 Speechify picker on a phone

## KNOWN

- The notes list is inside a fold. The action row is inside it too, so
  it is reached by opening the fold — consistent with the search field,
  which already lives there.
- Read on an open EMPTY note is disabled rather than hidden, per the
  rule Baba locked this session.
- Ticks are per session. Reloading the page clears them, which is right:
  a stale selection is how somebody deletes the wrong thing.

## WHAT WAS WRONG WITH THE GATE — §15, fourth report

**Two harness failures cost more time than any code failure.** A stale
`__pycache__` made restored code read as broken (v177), and this session
`AppTest.from_file("app.py")` resolved against the CALLER's directory,
not the app's — a FileNotFoundError that looks like the app failing to
boot. Neither is in the module. G6 should say: when a check fails,
confirm the harness before suspecting the artefact, and clear caches
after any mutation.

**G4's count is honest but shallow.** "7 new symbols, all referenced"
counts references; it cannot see that a control is referenced only from
code no interface reaches — the UNWIRED class the module names as the
dangerous one. Here it was closed by clicking the buttons in AppTest,
which is not what G4 asks for. The module should say plainly that G4's
grep does not close UNWIRED and name the click-through as the thing that
does.

**Still true from v176 and v177:** G8 has no row for a web app, G2's
history scan degrades silently on a shallow clone, and G6 has nowhere
structured to record what was mutated.
