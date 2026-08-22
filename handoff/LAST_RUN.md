# STEP: decisions recorded · fix the Claude call · the eight-step checklist
STATUS: done, except the live API check — that one needs you (step 1)

WHAT HAPPENED
- Decisions written into `docs/SELF_UPGRADE.md`: beta is CYAN, Push to
  main goes straight to `main`, one file per request, and the diff must
  be readable on a phone.
- Fixed `ttt/providers/anthropic.py`: no `temperature` unless a caller
  passes one on purpose, `max_tokens` 2048 -> 16000, timeout 120s ->
  300s, and the fallback model id is now `claude-opus-5` instead of a
  dated year-old one. Both call sites (translation, the AI text box)
  relied on the old 0.2 default and neither passes one, so nothing else
  changes shape.
- New `tests/test_anthropic_call.py`: 8 checks on what actually goes on
  the wire, through a fake transport.
- `§1.2` rewritten as your checklist, easiest first. The `beta` branch
  now exists on GitHub, identical to main (undo: `git push origin
  --delete beta`).

NUMBERS
- pytest tests/     ->  18 passed, 1 skipped (layout — no app served)
- the new file      ->  8 passed offline, 1 skipped (live call, no key)
- pyflakes          ->  clean
- app.py measured   ->  5,015 lines, ~66,000 tokens

WHAT BROKE, AND WHAT I UNDID
- My own test was wrong first: the fake `fetch` threw away the reply, so
  two checks failed for a reason that had nothing to do with the code.
  Fixed the fake, not the checks.
- Sabotage, then undone: I restored the old always-send-temperature line
  and watched check 2 go red, so the check is known to catch the real
  bug and not just to pass.

STILL UNSURE
- **The fix is verified against my reading of the API, not against the
  API.** This machine has no Anthropic key — they live in the sheet's
  `k_anthropic` tab — so the ninth check, the real call, did not run.
  Until you run step 1 below, that is an assertion, not a result.
- Whether translations change character now that no `temperature` is
  sent. Current models ignore it either way; an older one would now run
  at its own default rather than 0.2. Worth one look at a translation
  you know well.

FOR BABA
- Step 1 of the checklist, one paste, and it keeps the key off the
  screen and out of your history:

      cd ~/Developer/MAHA_TRANSCRIBE_STREAMLIT && read -s "ANTHROPIC_API_KEY?paste the key, then Enter: " && export ANTHROPIC_API_KEY && python3 tests/test_anthropic_call.py

  Nine checks instead of eight is the answer you want.
- The other seven steps are in `docs/SELF_UPGRADE.md` §1.2, one at a
  time, easiest first.
- Older queue, unchanged: deploy the AUTH script, add
  `AUTH_ADMIN_TOKEN` to the Streamlit Cloud secrets, and check whether
  `migrateRun()` ever ran on the live sheet.
