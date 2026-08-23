# DELIVERY RECORD — TTT-LLL v174 — 23.8.2026

The first artefact in this account to go through
`MANTRA_MANIFEST/modules/delivery-gate.md`. §15 asks the first project
to come back and write what was wrong with the gate; that is at the
bottom.

    ARTEFACT   app.py 7318 lines, sha256 41d6ab08c54dd746…
               deployed by Streamlit Cloud from GitHub main
    VERSION    new: v174   previous: v173, still in git history

---

## GATES

    G1 PROVENANCE   pass    clean tree (0 dirty), HEAD == origin/main,
                            v174 > v173, branch main
    G2 SECRETS      pass    64 tracked python files scanned + every
                            tracked file: 0 hits on
                            (sk_|gsk_|AIza|ghp_|github_pat_|xox…)
                            WHOLE HISTORY scanned: 0 hits
    G3 ANALYSIS     pass    64 python files, pyflakes 0 findings,
                            0 unused imports; 6 frontends parse in node
    G4 DEAD CODE    pass    142 module functions examined, 18 reported,
                            1 false (used in tests), 17 confirmed
                            unreached. 4 DELETED this run — 141 lines
    G5 DEAD LOOPS   pass    2 unbounded loops examined, 2 now bounded
                            (1 fixed this run); 10 network waits, 10
                            with deadlines; 7 subprocess calls, 7 with
                            deadlines (60/300/1800s, read individually)
    G6 STRESS       partial 562 python checks + 142 script checks green;
                            app boots, all 4 tabs open on a 390px phone,
                            0 tracebacks, 0 JS errors. NO SOAK RUN
    G7 BUDGETS      base    no previous numbers exist. This sets them:
                            app.py 7318 lines, 704 total checks
    G8 UPGRADE      n/a     a web app: everyone gets the new version on
                            reload. See the note below
    G9 RECORD       this document

---

## WHAT THE GATE FOUND, that nothing else had

**G5 · one genuinely unbounded loop.** `ttt/notes.py` `_fresh_id` was
`while True`. It terminates in practice — `used` is finite — but the
source never said so, and JPL's rule 2 is explicit that a bound you can
only prove by reasoning is not a bound. Now `for _ in range(len(used) +
2)`, with a timestamp id if it ever falls out.

**G4 · four functions nothing reached**, all orphaned by my own changes
and left behind: `cmd_row` (v139), `size_controls` (v137), `copy_pill`
and `cp_row` (both superseded by `box_links`). 141 lines. Each confirmed
across the whole project — app, modules, tests, frontends, docs — not
merely within app.py.

**And the deletion immediately broke the build**, which is the gate
working. `FLASH_SECONDS` sat BETWEEN two of those functions and my
slice — "from this def to the next def" — swallowed it. pyflakes caught
it in the same breath. §6.2's "re-run: deleting dead code exposes more
dead code behind it" is right, and it also exposes LIVE code that was
standing behind it.

---

## NOT TESTED — the most valuable block, per §11

    NO SOAK           G6 asks for an hour of continuous use or a
                      thousand cycles, with heap, handles and time
                      measured at the end. Not run. This app records
                      audio and uploads it, which is exactly the shape
                      §13 says to soak before shipping
    NO MONKEY         no random-interaction run. `adb shell monkey` has
                      no equivalent here and none was improvised
    NO SABOTAGE LIST  §8.3: network dying mid-upload, a throttled
                      connection, a revoked key mid-session, 429 then
                      500, a full disk, the process killed. NONE of
                      these were injected
    NO REAL PROVIDER  every AssemblyAI check runs against rules and
                      source, never against AssemblyAI. THE SYNC PATH
                      HAS NEVER MADE A REAL CALL
    NO BROWSER SUITE  test_layout, test_reader, test_shake need a
                      served browser and were skipped, as always
    test_reader 8     red since v101 and still red
    NO BUDGETS        no cold-start, frame-time, memory or network
                      figures exist for any version, including this one
    G8 UNTESTED       nobody installed v173 and then v174. On a web app
                      the equivalent is a person with a live session and
                      saved settings reloading onto the new code, and
                      that was not tried

---

## KNOWN, and listed rather than hidden

- `st.components.v1.html` is past its stated removal date, at 6 call
  sites. requirements.txt now pins `<2.0.0`, which is a wall not a fix.
- `app.py` still holds its own Groq client and `transcribe()`,
  duplicating `ttt/providers/groq.py`. It has caused two shipped bugs.
- Notes live in the browser and in Drive; the two-system split in
  `docs/TWO_SYSTEMS.md` is designed and unbuilt.
- 13 more unreferenced functions remain after this run's 4.

---

## WHAT WAS WRONG WITH THE GATE ITSELF — §15's ask

**G8 does not fit a web app and says nothing about it.** There is no
install, no previous APK, no rollback by the person. The real question —
"what happens to somebody with a live session and saved settings when
the code under them changes mid-session" — is a genuine failure class
this app has hit (settings keys renamed, session state shapes changed)
and the gate has no gate for it. §15 lists the web books as
not-addressed; a Streamlit app is a third shape and needs its own row.

**G7 assumes a previous number exists and there is no cheap way to make
one.** "A budget without a previous number is a note, not a gate" is
correct, but for a one-person project the honest first step is a
BASELINE RECORD, and the module does not name what the minimum useful
baseline is. This record guesses: lines and check counts, which are
weak.

**G4's confidence tiers do not survive a project with tests.** Every
"unreferenced" finding had to be re-checked against tests/, frontends
and docs before it could be believed — 1 of 18 was false for exactly
that reason. The staged-deletion recipe in §6.2 should say "confirm
across the whole repository, not the file" as step 0.

**The cheapest-first ordering is right and it worked.** G2 and G3 took
seconds and G6 was where the time went, exactly as §1 predicts.
