# LAST RUN — TTT-LLL — 25.8.2026, later

Deployed and current: **v188**. Apps Script MAIN deployed 24.8, same URL.

## THIS RUN

**Two tests were run first, before any fix, as asked.**

`tests/live_check.py` — **NOT RUN. It cannot run in a sandbox.** It needs
`.streamlit/secrets.toml` (gitignored, so not in a clone) and
`/home/claude/real_take.webm`. Neither exists off Baba's Mac. **The live
health of v187/v188 against real keys is UNPROVEN.** Run it on the Mac.

`tests/test_recorder_stress.py` — **RAN, and the reason it never
completes is now known.** ~9.5 min wall clock.

- SABOTAGE 1, every key dead: **both checks RED.** No error rendered;
  **whisper called 6 times over 8 redraws.** The v185 record's claim
  that a real error is loud and not retried is **confirmed wrong.**
  This is open item 7, now measured rather than argued.
- SABOTAGE 2, line 125: `at.run()` **times out after 300s** and raises
  `RuntimeError: AppTest script run timed out`. The process ends there.
  **SOAK, ENORMOUS, EMPTY and MALFORMED have never executed once.**
  Cause: `_Tx.create` raises `RerunException`; a rerun from inside the
  script body ends the run with no widget deltas, so AppTest waits the
  full `default_timeout=300`. The check also cannot tell "handled the
  interruption" from "rendered nothing" — **it needs rewriting before
  its result can be believed.**

**FIXED — fault 1, the TR crash.** `plan_blocks` returns tuples;
`tr_make_audio` read each block as "a str or a list of str". R's reader
at app.py:8027 was the caller that was RIGHT (`ss, char_off = parts[i]`
— it needs the offset for word timings). TR does not need the offset.
`ttt/speech.py:block_texts()` now unpacks once and returns `list[str]`;
TR asks for that.

**New check: `tests/test_tr_blocks.py`, 16 checks, no Streamlit.**
Mutations, both moving BEHAVIOUR: isinstance guess restored -> 14/16 and
the TypeError reproduced live; `block_texts` returning raw tuples ->
9/16. The first draft of check 2b THREW on the mutation instead of going
red, which stopped the file and hid checks 3 and 4 — hardened.

**Regression sweep:** test1_wordtimes 65/0, test_langs 22/0, test_undo
19/0, test_notes 53/0, test_reader ok. `test_box.py` is red — **and it
was already fully red on unchanged v187**, checked by stashing and
re-running, so it is pre-existing, not this change. pyflakes 0.

**NOT TESTED:** anything in a browser. That the TR play button reaches
`tr_make_audio`, and that the joined MP3 sounds like speech. Check 4 of
the new file is a grep of the function body and says so.

**NEXT:** fault 2, VR. Blocked on one decision — one Hume key, or the
~twenty pairs from the older file. The deep ring needs that file
uploaded.

---

## THE BRIEF THAT STARTED THIS (v187 state)

`k_hume` and `eta` tabs exist.

Read this, then `docs/HOW_WE_WORK.md`. History: DELIVERY_RECORD_v185.md
(the transcription bug and the door), v186 (the tiers).

---

## BABA USED THE APP ON HIS PHONE. FIVE FAULTS. START HERE.

Three versions shipped without anyone opening a browser. He opened one at
03:20 and found five things in six minutes. **Nothing below was caught by
the suite. Every fix needs a check that would have caught it.**

### 1 · TR CRASHES. A red Python wall instead of the app. **WORST.**

`TypeError` at `app.py:6773`, in `tr_make_audio`:

    for block in SPEECH.plan_blocks(tk.sentences_of(body)):
        piece = block if isinstance(block, str) else " ".join(block)

**`plan_blocks` returns `[(sentences, char_offset)]` — TUPLES.** Its
docstring says so. So `" ".join(block)` tries to join a list and an int.

REPRODUCED, exactly, no Streamlit needed:

    python3 -c "import sys; sys.path.insert(0,'.')
    from ttt import speech
    print(speech.plan_blocks(['One.','Two.','Three.']))
    ' '.join(speech.plan_blocks(['One.','Two.'])[0])"
    -> [(['One.'], 0), (['Two.','Three.'], 5)]
    -> TypeError: sequence item 0: expected str instance, list found

The fix is `sentences, _offset = block` then join `sentences`. **Check
the other callers of plan_blocks first** — R's reader uses it too and may
have the same assumption or may be the one that is right.

### 2 · VR IS DEAD. Play does nothing.

**Hume keys are read from the SHEET (`k_hume`), never from Secrets.**
`hume_speak()` takes a `ring`, and the ring is filled by
`hume_keys_from_sheet()` at app.py:8125. Baba's `k_hume` tab is empty, so
`ring["keys"]` is empty and `hume_speak` returns `t("vr_no_key")` — which
apparently shows as nothing at all.

**Baba wants:** `HUME_API_KEYS` in Secrets as a list, a fallback so
Secrets fills the ring when the sheet is empty, **and VR available to
FREE users.** He has one key ready; about twenty more key/secret pairs
exist in an older file if a deeper ring is wanted. `VR.pick_rested()`
already rotates on rest, and the comment says 21 accounts cost 0s of
waiting against 171s on one.

Also open from before: **VR ships raw WAV**, ~96 KB/s. The Hume notes say
Opus at 24 kbit mono is 31x smaller and clear for speech.

### 3 · THE LINK ROWS ARE NOT ONE LINE.

In TR, `read` sits on its own line BELOW `copy · clear`. Baba: "In the
Translate, Read should be Copy, Clear, Read. All in one line on the same
side. Not separate button." It is a `box_links` `extra`, so this is
about where TR calls it, not about the helper.

### 4 · PLAY NEEDS TWO PRESSES.

Every reader deck. First press does nothing; second starts it. Baba:
"Why?" Unknown, never investigated. **If it cannot be solved, he asked
for a line reading "press play to read" UNDER THE PLAYER** — he was
explicit that it goes under the player, not under the text box.

### 5 · ALIGNMENT. `transcribe · free` is not on the right margin.

`tab_signature()` is meant to sit right-aligned like a signature. In his
screenshot it is left of centre. Baba: "Alignment is very important for
beauty of this app."

### AND: THE UNDO HE COULD NOT FIND

v187's undo appears only once something has been LOST — record into an
empty box and nothing was overwritten, so no link. He looked for it and
it was not there. **It fails the only test that matters.** Consider
showing it whenever the box has text, or whenever history exists.

**What DOES work, from his own screenshots:** the door, the transcript in
the box, `add to notes`, "your notes · 1", and the free tier's session-only
behaviour. He said: "First up, it's nicely appearing... That's good."

---

## SECRETS — THE SHAPE

    ADMIN_USER1  = "..."      ADMIN_USER, ADMIN_USER2 ... also work
    STUDIO_USER1 = "..."
    FREE_USER1   = "..."      FREE_USER2, FREE_USER3 ...
    SHEETS_URL / SHEETS_TOKEN / DRIVE_SECRET / DRIVE_ROOT_ID
    GROQ_API_KEYS = ["...", ...]      all five verified 200 on 24.8
    HUME_API_KEYS = ["..."]           NOT READ BY THE APP YET — item 2

The pattern `^(ADMIN|STUDIO|FREE)_USER\d*$` is scanned, so any number of
each works with no code change. A value may be a list.

**A DUPLICATE KEY WILL NOT PARSE.** Baba twice wrote `FREE_USER1` for two
different people; TOML rejects it and the whole file fails to load.

`AUTH_URL`, `AUTH_LOGIN_TOKEN`, `AUTH_ADMIN_TOKEN` are no longer read.

Baba pasted full secrets into chat and **intends to rotate once
development settles. He has asked not to be reminded. Do not raise it.**

## THE TIERS — v186

Three, and they NEST; a tier is a floor, not a slot.

    free     the app on the app's own keys: Edge and Whisper
    studio   plus the paid models, plus Google storage for audio+notes
    admin    plus the owner's panel

A repeated name merges to the HIGHEST tier; order does not matter. The
radio above the tab bar is drawn from the ACCOUNT, never the view —
drawn from the view, dropping to free would remove the way back.
`is_admin()` follows the VIEW; `is_studio()` is a floor test.

**Free is session-only by observation:** transcript yes, `rec_id` None,
nothing in Drive. Notes persist in the person's own BROWSER
(localStorage), not Drive. The `.flac` is deleted when the NEXT take
starts, not when the text lands.

## PROVEN AGAINST THE REAL ENDPOINT — 24.8

`tests/live_check.py` (not in the suite; it spends money). Real Secrets,
real Groq, real speech through the deck's own webm/opus:

    box: "This is a test of the transcription app. One, two, three."
    11 of 11 spoken words, 2.3s, 57 chars, _last_run agreed

**The v185 transcription bug is fixed and proven live.** All five Groq
keys answered 200.

## STILL OPEN FROM BEFORE

1. **G6 stress has NEVER completed** — three deliveries running.
   `tests/test_recorder_stress.py`. It went red on its first check the
   one time it ran: with every key dead, the app **retried 6 times over
   8 redraws and showed NOTHING on screen.** The v185 record claims a
   real error is loud and not retried; **that claim is wrong.** The fix
   is a bounded retry — count attempts per digest, allow one, then stop
   and say so. Baba has not yet chosen it.
2. **The note path still POPS `_note_take` before the work**, so an
   interrupted note take is gone rather than skipped. Same fault v185
   fixed for the deck, worse outcome.
3. `tests/test_accounts.py` fails 12 checks describing the removed door.
   Retire them or restore the features — a decision, not a bug.
4. `test_engine_ui`, `test_engine_sheet` cannot collect;
   `test_reader.py` check 8 needs edge-tts. Verified identical on v184.
5. **The Engine row is still in the admin panel** and should come out
   now that tiers replaced engines.
6. Key import: Replace/Add choice; a parser that imports NOTHING when a
   provider declares prefixes and none match; key deletion; imported
   keys persisting to the sheet as Hume's do. *Known fault:* five
   AssemblyAI 32-hex keys sit in the Speechify ring because
   `import_keys`' generic fallback grabs any long alphanumeric token.
7. Test-all-keys with statistics, as `Key_Tester` does it — read that
   repo, do not re-derive.
8. Interface size is missing its `default` link.
9. Quick Settings says "transcribe: free"; transcription is Whisper.
10. Apps Script `eta_*` deployed but no timing row has ever been written.
11. `box_links()` returns early on an empty box — the opposite of the
    rule Baba locked. Five call sites.
12. Undo for the R and TR boxes: they share `box_links`' clear and
    neither can be undone. A refactor, not an addition.

## THE GATE — §15

**Three deliveries shipped without a browser and a user found five faults
in six minutes.** No gate asks "has a person looked at it". G6 has been
skipped three times running with no escalation — **a check skipped twice
should be blocking.** Nothing distinguishes a test that BROKE from one
describing a REMOVED feature. G5's pattern must name what it searched for
(it searched `requests.` on a `urllib` app and read "0 findings" as a
pass). G3 earned its keep: it found `gate` imported and unused, the only
trace that the throttle went out with the old door.

## MUTATIONS

Every mutation asserts the file changed AND that behaviour moved. **In
v187 one did not:** removing the duplicate guard in `undo_remove` left
26/26 passing, because "undo pressed twice" was already prevented by the
undo slot emptying itself. Check `3b2` was added — a note that returned
by another road while the undo was still held — and the same mutation now
shows `n2` twice. **This is the trap: a mutation that changes the file
and not the behaviour reads as a pass.**
