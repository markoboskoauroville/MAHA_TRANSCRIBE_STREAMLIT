# LAST RUN — TTT-LLL — 24.8.2026, evening

Deployed and current: **v184**. Apps Script MAIN **deployed today**, same
URL, `k_hume` and `eta` tabs exist. Tree clean, HEAD = origin/main.

Read this file, then `docs/HOW_WE_WORK.md`. Per-version detail is in
`handoff/DELIVERY_RECORD_v176..v183.md`.

---

## ⚠️ THERE IS A LIVE BUG. START HERE.

**Transcription text does not reach the text box.** Baba records, the
audio goes, no words come back. Reported 24.8.2026 against v182–v184.

**DO NOT GUESS AT THIS.** Two diagnoses were made this session and both
were wrong:

1. "`stt` is undefined at line 7016, NameError." **FALSE.** `stt` is
   bound at module level at line 6835, and line 6839 already uses
   `stt.id`. A fix was written, tested, and reverted.
2. "The five bad Speechify keys are in the `k_speechify` sheet tab."
   **FALSE.** `persist_keys()` is browser-only by deliberate design —
   see its comment. That tab is empty and correct.

Both cost Baba an evening. Read the transcribe path properly. The
suspect set includes v177's additions to the deck path
(`braille_line`, `eta_seconds`, `remember_timing`, `audio_seconds`)
because they are new and sit in that exact flow — but VERIFY BY
EXECUTION, not by reading and pattern-matching.

**Nothing in this repo tests the recorder path.** No test makes a real
recording, which is why v177–v184 shipped through the gate with this
live. Whatever the cause turns out to be, the fix is incomplete without
a check that would have caught it.

---

## WHAT WAS BUILT THIS SESSION (v176 → v184)

    v176  Speechify voices per language; the Slavic four for Croatian
    v177  SPA pill, braille status line, ETA that learns (sheet-backed)
    v178  Notes: select, delete, read into R
    v179  Notes actions styled like the recordings actions
    v180  Disabled controls readable again (1.45:1 -> 5.41:1, measured)
    v181  TR cassette deck, polyglot — reads both boxes, female/male
    v182  VR tab — Hume AI, 24 voices, 18 emotions, 12s pacing
    v183  Hume pairs, sheet-backed keys, 21-account fallback
    v184  Hume key handling aligned with MANTRA_MANIFEST/apis/hume.md

## RULES BABA LOCKED THIS SESSION — in docs/HOW_WE_WORK.md

1. **Copy and clear, nailed to the wall.** Every text box has two action
   links beneath it, always, greyed when unavailable, NEVER absent.
   **WRITTEN BUT NOT IMPLEMENTED** — `box_links()` still returns early
   on an empty box, which is the opposite of the rule. Five call sites.
2. **Two languages, locked** — hr and en for transcription, reading in
   T and R, and the interface. **TR is exempt**: "translation tab is
   free, it's a free soul, he is multilingual polyglot." A language
   joining the TR grid must bring BOTH an Edge voice, female and male.
   Enforced by `tests/test_langs.py`.

## OPEN WORK, in Baba's priority order

1. **The transcription bug** (above).
2. **Key import.** Needs: a Replace / Add choice on import; a parser
   that imports NOTHING when a provider declares prefixes and no token
   matches; a way to DELETE a key; and imported keys persisting to the
   sheet the way Hume's now do.
   *Known fault:* five AssemblyAI 32-hex keys are in Baba's Speechify
   ring, rejected 401, because `import_keys`' generic fallback grabs any
   long alphanumeric token when no prefixed one is found.
3. **Tiers replace engines.** Remove the Engine row from the admin panel
   (`Edge / Groq` vs `Speechify / AssemblyAI / Claude`, and its `test`
   button). People get two tiers only: **free — Edge/Whisper** and
   **studio — all models**, labelled next to the radio buttons. No
   per-engine switching for people.
4. **Quick Settings labels are wrong.** Shows "transcribe: free" —
   transcription is Whisper, not free. Talk: Edge is correct.
5. **Test all keys**, with statistics, as `Key_Tester` does it — so keys
   need not be tested one at a time. Read that repo; do not re-derive.
6. **Interface size is missing its `default` link** (text size has one).
7. **Free ↔ studio must refresh the session.** Today Baba must log out,
   log in and reload before a tier change takes effect. Force it.
8. **Long login.** Typing name and password then pressing login waits a
   long time. Cause unknown, not investigated.
9. **Engine in parentheses under the recorder** after the audio is
   sent — the braille line was built for this in v177 and Baba reports
   not seeing it. Related to item 1; check together.
10. **Apps Script `eta_*` is deployed but unproven** — no timing row has
    ever been written. First real transcription should produce one.
11. **VR ships raw WAV** (~96 KB/second). Baba's own Hume brief says
    convert to Opus, 31x smaller. ffmpeg is available.

## SECRETS AND ACCOUNTS

- All 21 Hume accounts verified working, both as pairs (oauth2-cc) and
  as API keys. In the ring and in `k_hume`.
- Baba pasted his full Streamlit secrets and 21 Hume pairs into a chat.
  **He knows, and intends to rotate everything once development
  settles.** `DRIVE_ROOT_ID` is not a secret and needs no rotation.
- `APP_PASSWORDS` is the recovery door when the Google auth script is
  unreachable. Baba is reducing it from three people's passwords to one
  random owner key. He has TESTED that a recovery login gets admin
  rights. Never remove the working door before the replacement is
  proven.

## THE GATE — §15 findings from eight runs, for MANTRA_MANIFEST

Reported in the delivery records: G8 has no row for a web app; G2's
history scan degrades silently on a shallow clone; G6 cannot record what
was mutated; nothing catches VISUAL DRIFT (a control that looks wrong);
nothing catches a FAILURE PATH THAT DOES THE WRONG THING CONFIDENTLY
(403 was classified as a dead key and would have burned a 21-key ring);
harness failures masquerade as artefact failures; and — the big one from
today — **two mutations changed nothing and still read as passes**. A
mutation must be confirmed to change behaviour, or it certifies a check
that was never exercised.

**And the finding this session earned the hard way:** nine gates passed
on every version from v177 to v184 while the recorder was broken. The
gate cannot see a path no test executes. That is not a gap in the code.
It is a gap in the gate.
