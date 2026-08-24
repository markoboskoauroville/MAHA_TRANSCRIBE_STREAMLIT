# DELIVERY RECORD — TTT-LLL v179 — 24.8.2026

The notes action row now looks like the recordings action row, because
it is styled by the same rule rather than a copy of it.

    VERSION    new: v179   previous: v178, in git history
    ARTEFACT   app.py 7936 lines, ttt/theme.py 1493 lines

## THE BUG, AND WHY IT HAPPENED

Baba, on a phone: "make the action links exactly the same look as in the
audio file storage — not yellow, grey underlined action links."

He was looking at `select all` and `read` rendered as outlined amber
pills while `delete` rendered correctly as a grey underlined link.

The cause was a KEY COLLISION, not a missing style. The new row used the
container key `noteacts_top`, and the stylesheet already had rules for
`[class*="st-key-noteacts"]` belonging to the OPEN NOTE's own action
row. So the row silently inherited a different panel's styling. Nothing
failed; it simply looked wrong, which is the failure shape this repo
keeps meeting.

## THE FIX

- The row's container is `nactrow_<where>` and its buttons are
  `nact_all_*`, `nact_read_*`, `nact_deln*` — a prefix that collides
  with neither the open note's `noteacts` nor the note cards' `note_`.
- Those selectors were ADDED TO THE RECORDINGS' EXISTING RULE, in the
  same selector list, rather than copied into a new one. Two rules for
  one look drift; this app has paid for that before.
- The same treatment for hover, for the disabled/greyed state, and for
  delete keeping its warning colour.
- `_np_` note rows now sit tight like `_rp_` recording rows.

## GATES

    G1 PROVENANCE   pass    clean tree, v179 > v178, main
    G2 SECRETS      pass    staged diff 0 hits; 0 of 69 files
    G3 ANALYSIS     pass    69 python files, pyflakes 0 findings
    G4 DEAD CODE    pass    nact_ 20 refs, nactrow_ 3, _np_ 7 — nothing
                            orphaned by the rename
    G5 DEAD LOOPS   pass    no new loops or waits; CSS and keys only
    G6 STRESS       partial 96 checks green (28 in notes, 4 new about
                            the styling); suite 21 files passed.
                            The six behaviours were RE-RUN after the
                            rename and all six still hold: select all
                            3/3, select none 0, delete arms then fires,
                            n2 survives, 0 stale ticks, read carries
                            "second note" to R with Sonia, read
                            disabled at two ticks.
                            MUTATED: pulled nact_ back out of the
                            shared rule -> test 24 red. Restored.
    G7 BUDGETS      same    app.py unchanged at 7936; theme.py +12
    G8 UPGRADE      pass    keys are session-scoped; nothing stored
                            changed; rollback to v178 loses nothing
    G9 RECORD       this document

## NOT TESTED

    NOT SEEN ON A PHONE   the whole point of this change is how it
                          LOOKS, and I cannot see it. The CSS is
                          asserted to be in the right rule; that the
                          rendered result matches the recordings panel
                          is Baba's check, not mine
    THE OPEN NOTE'S ROW   its read link is `nact_read_open`, so it now
                          takes the link styling too. That row is FOUR
                          columns on a narrow screen and has never been
                          seen at 390px
    STILL OPEN            copy/clear always-visible rule (written, not
                          implemented), Apps Script MAIN deploy for the
                          ETA, AssemblyAI round trip, HR->ENG and
                          single->multi mid-recording, Speechify
                          test-key button

## WHAT WAS WRONG WITH THE GATE — §15, fifth report

**No gate asks whether a new control LOOKS like the controls it sits
beside.** G4 finds code nothing reaches; nothing finds a control that
reaches the screen wearing the wrong clothes. It passed every gate at
v178 and was wrong the moment Baba looked at it. A cheap check exists
and is now in the suite: assert the new selector sits inside the
existing rule's selector list, not in a rule of its own. The module
should name this class — VISUAL DRIFT — beside UNREACHABLE,
UNREFERENCED and UNWIRED.

**Still true from v176-v178:** G8 has no web-app row, G2's history scan
degrades silently on a shallow clone, G6 has nowhere to record
mutations, and harness failures still masquerade as artefact failures.
