# DELIVERY RECORD — TTT-LLL v185 — 24.8.2026

    ARTEFACT   the repository at main, which is what Streamlit Cloud runs.
               There is no binary. app.py, 72 python files, 117 tracked.
    VERSION    new: v185   previous: v184, still in git history

Two pieces of work, both asked for in one session.

1. **The live transcription bug is fixed** — the one that shipped through
   nine gates on eight versions.
2. **The door was replaced** — one box, one key marked L, names in
   Secrets. Baba's request, and it removes several things on purpose.

---

## 1 · THE TRANSCRIPTION BUG

**Symptom.** Baba records, the audio reaches Drive, no words come back,
nothing red on the screen. Reported against v182–v184.

**Two diagnoses last session were wrong** (`stt` undefined; bad keys in
the sheet) and both were re-read before starting. Neither was reused.

### What it actually was, established by execution

The deck holds its blob until Python echoes the stamp, and re-posts after
**2, 4, 8, 15, 25 seconds**. `ack=` is a PROP, read from session_state
when the component renders — and the component renders at the TOP of the
module, before the transcription. So on the run that receives a take the
deck is told `ack=None`, and it cannot learn otherwise until the run
ENDS, which is after Whisper has answered.

Measured on a three-second transcription:

    t+0.6s   deck rendered, ack=None — its retry timer starts here
    t+2.6s   THE DECK RE-POSTS THE TAKE
    t+4.0s   deck rendered again, ack=<stamp> — acknowledged, too late

Every re-post is a `setComponentValue`, which is a rerun, which kills the
run that is transcribing. And:

- `RerunException` and `StopException` inherit from **BaseException**, so
  they pass straight through the `except Exception` guarding the block
  and print nothing at all.
- `st.session_state["_digest"] = digest` was committed **before** the
  `try:`.

So the run died mid-transcription, the digest already said the take was
handled, the audio stayed held, and every render afterwards skipped the
block. Silent, permanent, and the deck — acknowledged on the new run —
stopped spinning and looked like it had succeeded.

### The fix, in two parts

**A · The deck is acknowledged before the work.** On a new take the run
now stores it and returns immediately. The next render hands the deck its
stamp in milliseconds, it stops its retry timer, and the transcription
runs with nothing waiting on it. One extra rerun per take. It is the
shape `transcribe_note_take()` already used, and its docstring says why.

**B · The digest records STARTED, not DONE.** `_digest_done` is False
while the work runs and True at the end of the try and inside the except
— **never in a `finally`**, because a finally runs on the interruption
too and would put the hole straight back. A take found started-but-not-
finished is picked up again on the next render.

A alone would leave the same silence if any other rerun landed
mid-transcription. B alone would let a killed run be killed again, up to
five times, spending a key each time.

---

## 2 · THE DOOR

Baba, 24.8.2026: *"First screen of an app doesn't have anything, only one
entry box. There is no title, no text, zero."*

`check_password()` was 272 lines; it is 74. The screen is one unlabelled
text box and one button marked **L**. Names come from `ADMIN_USER` and
`NORMAL_USER1..3` in Secrets, through one function, `_named_people()`,
used by both the start-up check and the door.

`is_admin()` is untouched — it still compares the signed-in name to
`admin_user()`, which still reads `ADMIN_USER`. The gold edge and the two
owner tabs work as before; checked.

The start-up guard no longer REQUIRES `APP_PASSWORDS`; it accepts a name
instead. `APP_PASSWORDS` is still read and still works if set.

### WHAT THIS REMOVED — read this part

The old door did five things this one does not:

    the password, and the username box above it
    the APP_PASSWORDS emergency door, ADMIN.md §3.5
    the brute-force throttle in ttt/gate.py
    Remember me, and the token minted for it
    login through the Google accounts script

The accounts system itself still exists and the admin tab still manages
it — nothing now uses it to let anybody IN. `_try_remembered()` is left
in place, unused, one line from being restored.

**The username is now the entire credential.** There is nothing behind
it. That is why `tests/test_door.py` uses invented names and the real
ones live only in Streamlit Cloud Settings.

---

## GATES

    G1 provenance  pass   1 file changed in app.py + 6 test files;
                          branch main; APP_VERSION reads v185
    G2 secrets     pass   117 tracked files scanned, 0 hits.
                          staged diff scanned: 0 key shapes, 0 auth
                          tokens, 0 real usernames, secrets.toml not
                          tracked (confirmed by git check-ignore)
    G3 analysis    pass   72 files, pyflakes 0 findings, 72 compile
    G4 dead code   pass   vulture ≥90%: 1 finding, pre-existing
                          (`keep` in deliver_text, kept deliberately —
                          its own comment explains why)
    G5 dead loops  pass   12 urlopen waits examined, 12 with a deadline;
                          0 `while True`.
                          NOTE: the first pattern searched for
                          `requests.` and returned 0 of 0 — a check that
                          ran nothing and read as a pass. The app uses
                          urllib. Caught only by treating the zero as a
                          failure. §15 finding below
    G6 stress      PARTIAL tests/test_recorder_stress.py is written and
                          did not finish inside the session's time limit.
                          NOT a pass — see NOT TESTED
    G7 budgets     pass   app.py 8,518 → 8,417 lines, measured. The door
                          lost 198 lines; the two fixes and their
                          comments added ~97 back. One extra rerun per
                          take, which is a page redraw, not a network
                          call — and the door no longer makes a network
                          call at all, which should make login faster
    G8 upgrade     pass   test 4 of test_recorder_path: a session
                          carrying v184's `_digest` and a stale
                          `flac_path` still transcribes a new take.
                          A live session mid-upgrade sees the new door;
                          nobody is signed out who was signed in
    G9 record      this document

### The mutations, and that they CHANGED something

Last session two mutations changed nothing and read as passes. Every
mutation below asserted the file actually changed before the run.

    remove fix A (the early ack)        → 3e goes red, 12/13
    restore the old digest guard        → 3b and 3c go red, 11/13
    let anybody through the door        → 3a and 3b go red, 19/21
    put a title back on the door        → 1e goes red, 20/21

Four mutations, four different checks red, each fix load-bearing.

And the order that proves a fix: `test_recorder_path.py` was written
first and run against **unfixed v184**, where it failed 3 of 13 — exactly
3b, 3c and 3e. Then the fix, then 13 of 13.

---

## NOT TESTED

    THE BROWSER            nothing was opened in one. The deck, the box
                           and the door are all AppTest only. The L key's
                           SIZE and the greyed states are code, unseen
    THE RE-POST ITSELF     that Streamlit's ScriptRunner really does
                           interrupt an in-flight run when a component
                           posts back. AppTest is single-threaded and
                           cannot reproduce it. Everything either side of
                           that link is measured; the link is inferred
    G6 STRESS              the file exists and is committed, and it did
                           not finish. The dead-key-must-not-retry check
                           inside it guards a real risk that fix B
                           introduces and it has NOT been run
    A REAL WHISPER CALL    no Groq key in the sandbox. Every transcription
                           check stubs the Groq SDK at `from groq import
                           Groq`, which is the seam app.py uses
    tests/test_reader.py   check 8 needs edge-tts and this sandbox blocks
                           its TLS. Fails identically on v184 and v185
    test_owner_edge        2 of 5 checks fail. Verified identical on v184
                           — pre-existing, not this change
    test_engine_ui,        cannot collect here. Verified identical on
    test_engine_sheet      v184 — pre-existing
    test_accounts          12 checks now fail because they describe the
                           door that was removed: the APP_PASSWORDS
                           emergency door, the throttle, remember-me, and
                           accounts-script login. Its helper was
                           repointed at the L key; the checks themselves
                           were NOT rewritten
    THE NOTE PATH          `transcribe_note_take()` POPS `_note_take`
                           before doing the work, so an interrupted note
                           take is not skipped — it is gone. Same class
                           of fault, worse outcome. NOT fixed

Suite: 25 passed, 1 failed (test_owner_edge, pre-existing) across the
files that collect.

---

## §15 — WHAT WAS WRONG WITH THE GATE

**G5's first pattern matched nothing and read as a pass.** It searched
for `requests.` on an app that uses `urllib`. "0 calls, 0 without a
deadline" is indistinguishable from "12 calls, all fine" from outside.
The module already says print the count and treat a zero as a failure
until proven; it should also say **print what was SEARCHED FOR**, because
the count was of the wrong noun.

**G6 has no way to say PARTIAL.** A check that was written, committed and
not run is neither a pass nor a fail, and the record format has no shape
for it. It went in NOT TESTED, where it is easy to miss, when it should
be visible on the gate line itself.

**The gate still cannot see a path no test executes.** Last session's
finding stands and is now demonstrated in the other direction: the moment
one test drove the recorder, the bug was found in three runs. The gate
needs a check that asks *which entry points has nothing ever called* —
a coverage question, not a correctness one.

**A test that describes a removed feature fails and looks like a
regression.** `test_accounts`' 12 failures are a deliberate product
decision, and nothing in the record format distinguishes "this broke"
from "this was removed on purpose". They need different words.
