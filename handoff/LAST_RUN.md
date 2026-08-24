# LAST RUN — TTT-LLL — 24.8.2026, night

Deployed and current: **v186**. Apps Script MAIN deployed 24.8, same URL,
`k_hume` and `eta` tabs exist.

Read this file, then `docs/HOW_WE_WORK.md`. Detail is in
`handoff/DELIVERY_RECORD_v185.md` (the transcription bug and the door)
and `handoff/DELIVERY_RECORD_v186.md` (the tiers).

---

## FIRST THING, BEFORE ANYTHING ELSE

**Run `tests/test_recorder_stress.py`.** It is committed and it has
never completed — twice now. It holds the check that a dead key must NOT
be retried on every redraw, which is a real risk introduced by the
`_digest_done` change in v185. Two deliveries have gone out with G6 unrun.

    cd ~/Developer/MAHA_TRANSCRIBE_STREAMLIT && python3 tests/test_recorder_stress.py

## SECRETS — THE SHAPE CHANGED IN v186

    ADMIN_USER1  = "..."      ADMIN_USER, ADMIN_USER2 ... also work
    STUDIO_USER1 = "..."
    FREE_USER1   = "..."      FREE_USER2, FREE_USER3 ...
    GROQ_API_KEYS = ["...", ...]

The pattern is scanned, so any number of each works with no code change.
A value may be a list.

**A DUPLICATE KEY WILL NOT PARSE.** Baba first wrote `FREE_USER1` twice,
for two different people. TOML rejects that and the whole secrets file
fails to load. The second one must be `FREE_USER3`, or simply left out —
admin already grants free.

Baba pasted a full secrets file into chat and **intends to rotate
everything once development settles.** He has asked not to be reminded;
do not raise it unprompted.

`.streamlit/secrets.toml` is gitignored and stays that way.

## THE TIERS — v186

Three, and they NEST. A tier is a floor, not a slot.

    free     the app on the app's own keys: Edge and Whisper
    studio   everything free has, plus the paid models, plus Google
             storage for audio and notes
    admin    everything studio has, plus the owner's panel

**A repeated name merges to the highest tier.** Baba listed himself as
admin, studio and free at once — three true statements about one person,
and the answer is the largest. Order does not matter; checked.

**The radio sits above the tab bar** — free · studio · admin — and is
**drawn from the ACCOUNT, never the view.** Drawn from the view, dropping
to free would remove the control that gets you back. A free user holds
one tier, so no radio is drawn.

`is_admin()` follows the VIEW, so switching to free really removes the
gold tabs. `is_studio()` is a floor test, because admin is a studio user
too. The studio tools in the command row come from `is_studio()` now
rather than from the engine routes — **that is open item 3, "tiers
replace engines", done.**

**A fault found while writing the test, worth knowing:** a stale
`_view_tier` the account no longer grants crashed the whole page, because
`st.radio` reads session_state through its key before any clamp on read
can help. It is clamped before the widget is built now. Ignoring a bad
value and removing it are different acts.

## GOOGLE IS NOT A DOOR

Authentication through Google is gone for good. The door is a name from
Secrets and makes no network call. Google is storage only, and only for
studio and admin: `drive_store()` returns a disabled store below that
tier, so a free user's take is transcribed, handed back, and nothing of
theirs is kept in Baba's Drive.

The password-change form is unreachable — nothing sets `_via_accounts`.
`from ttt import gate` was removed (the throttle belonged to the password
door). **`ttt/gate.py` and `tests/gastest` are NOT deleted** — one import
from being useful again.

## THE v185 WORK, IN ONE PARAGRAPH

The transcription bug was the deck re-posting its take while Whisper was
still running. `ack=` is a prop read when the component renders, and the
component renders BEFORE the transcription, so the deck could not be
acknowledged until the run ended. Measured: re-post at t+2.6s, ack at
t+4.0s. Each re-post is a rerun; `RerunException` is a **BaseException**
and went straight through the `except Exception`, and `_digest` had
already been committed before the `try`. Fixed both ways: the deck is
acknowledged before the work, and `_digest_done` records STARTED rather
than DONE. `tests/test_recorder_path.py` failed 3 of 13 on v184 and
passes 13 of 13.

**Still unproven:** that Streamlit really interrupts an in-flight run on
a component post-back. AppTest is single-threaded and cannot show it.
**Baba recording once in a browser settles it, and he has not yet.**

## WHAT IS NOT DONE

1. **Nothing has been opened in a browser across three versions.** The L
   key's size, the radio's position, whether three tier words fit in a
   row on a phone — all unseen.
2. **G6 stress has never run.** See the top of this file.
3. **The note path has the same fault v185 fixed for the deck.**
   `transcribe_note_take()` POPS `_note_take` before the work, so an
   interrupted note take is gone rather than skipped. Worse than what
   was fixed. Not started.
4. **`tests/test_accounts.py` fails 12 checks**, all describing the door
   removed in v185. Retire them or restore the features — a decision,
   not a bug.
5. `test_engine_ui` and `test_engine_sheet` cannot collect;
   `test_reader.py` check 8 needs edge-tts. All verified identical on
   v184 — pre-existing.
6. **Storage was checked at `drive_store()`, not by watching a file
   arrive.** That a studio user's audio still reaches Drive and a free
   user's does not is inferred, not observed.

## OPEN WORK, in Baba's order

1. ~~The transcription bug~~ — fixed, needs one real recording.
2. **Key import.** A Replace / Add choice; a parser that imports NOTHING
   when a provider declares prefixes and no token matches; key deletion;
   imported keys persisting to the sheet as Hume's do.
   *Known fault:* five AssemblyAI 32-hex keys sit in the Speechify ring
   because `import_keys`' generic fallback grabs any long alphanumeric
   token when no prefixed one is found.
3. ~~Tiers replace engines~~ — done in v186. **The Engine row is still in
   the admin panel** and should now come out, with its `test` button.
4. **Quick Settings says "transcribe: free"** — transcription is Whisper.
5. **Test all keys**, with statistics, as `Key_Tester` does it. Read that
   repo; do not re-derive.
6. **Interface size is missing its `default` link** (text size has one).
7. **Free <-> studio must refresh the session.** The radio does this
   within a session now; check whether anything still needs a re-login.
8. ~~Long login~~ — the door makes no network call. **Confirm by timing.**
9. **Engine in parentheses under the recorder.** The braille line exists;
   with transcription fixed it should be visible. Check.
10. **Apps Script `eta_*` is deployed but unproven** — no timing row has
    ever been written. The first real transcription should produce one.
11. **VR ships raw WAV** (~96 KB/s). Convert to Opus, 31x smaller.
12. **The copy/clear rule Baba locked and I did not implement.**
    `box_links()` still returns early on an empty box, which is the
    opposite of the rule. Five call sites.

## THE GATE — §15 findings, for MANTRA_MANIFEST

**G6 has been skipped on two consecutive deliveries and nothing
escalated.** v185 buried it in NOT TESTED, v186 gave it a NOT RUN line.
Neither blocked. §12 says a gate with no consequence is advisory. **The
bug bar should name a check skipped twice as blocking.**

**Nothing distinguishes a test that BROKE from a test describing a
REMOVED feature.** Four files across two versions failed for the second
reason. In a pytest tally they look identical, and the difference is the
whole story.

**G3 paid for itself visibly:** it found `gate` imported and unused, which
was the only trace in the code that the brute-force throttle had gone out
with the old door.

**G5's pattern must name what it searched for.** In v185 it searched for
`requests.` on an app that uses `urllib` and returned "0 findings", which
read as a pass. Print the count AND the noun.

Carried forward: G8 has no row for a web app; G2's history scan degrades
silently on a shallow clone; G6 cannot record what was mutated; nothing
catches visual drift; nothing catches a failure path that does the wrong
thing confidently; harness failures masquerade as artefact failures; and
the gate cannot see a path no test executes.

## MUTATIONS — eight this session, all confirmed to change the file

    v185  remove the early ack           -> 3e red
          restore the old digest guard   -> 3b, 3c red
          let anybody through the door   -> 3a, 3b red
          put a title back on the door   -> 1e red
    v186  last-listed wins, not highest  -> 1b, 3a, 3b red
          is_admin follows the ACCOUNT   -> 4a, 5a red
          radio drawn from the VIEW      -> 4b, 4c red
          remove the clamp before radio  -> 5d red
