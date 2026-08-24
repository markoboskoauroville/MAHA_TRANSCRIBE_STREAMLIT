# DELIVERY RECORD — TTT-LLL v176 — 24.8.2026

Speechify voices per language: the Slavic four for Croatian, the British
four for English, the model stored beside every seat. Second artefact in
this account through `MANTRA_MANIFEST/modules/delivery-gate.md`; the
§15 report-back is at the bottom.

    ARTEFACT   app.py (7635 lines) + ttt/providers/speechify.py +
               tests/test_sp_voices.py, deployed by Streamlit Cloud
               from GitHub main (sha256 of app.py in the commit note)
    VERSION    new: v176   previous: v175, still in git history

---

## WHAT CHANGED

- `SP_VOICES_BY_LANG`: hr = Lesya, Beatrice, Dominika, Daria on
  simba-multilingual; en = Beatrice, Imogen, Edmund, Hugh on simba-3.2.
  The model travels with the seat because beatrice_32 sits in BOTH rows
  with DIFFERENT models — a suffix rule cannot know that.
- The Speechify picker is two grouped rows mirroring the Edge picker
  (tag, then four names), the lit seat decided by the (voice, model)
  pair so the two Beatrices never light together.
- `pick_sp_voice` stores the model; `sp_model` is a persisted setting
  with an upgrade-safe default (every pick v175 could store was _32,
  and simba-3.2 is right for all of them).
- "Read this" now aligns the Speechify voice to the transcribed
  language, as it always did for Edge.
- Deleted as dead in the same run: the flat `SP_CURATED` list and a
  helper this very session wrote and nothing called.

## MEASURED LIVE, 24.8.2026, with Baba's own test ring (21 keys)

    key probe          HTTP 200 on api.speechify.ai AND api.sws.speechify.com
                       — the older host still answers; left unchanged
    catalogue          988 voices, 5 pages, cursor walked to the end
    ids                all 8 seats found; lesya uk-UA, dominika pl-PL,
                       daria ru-RU exist ONLY on simba-multilingual /
                       simba-3.0; no plain "beatrice" id exists — the
                       Croatian Beatrice is beatrice_32 on multilingual
    croatian           still no hr-HR voice on any model
    synthesis          3 calls, one per model path incl. Croatian
                       diacritics: all 200, billed == sent (3, 10, 11),
                       word marks on every path
    fallback           a real key with 4 chars changed -> HTTP 401,
                       which the ring maps to dead and rotates past

## GATES

    G1 PROVENANCE   pass    clean tree after commit, HEAD == origin/main,
                            v176 > v175, branch main, previous version in
                            git history
    G2 SECRETS      pass    staged diff: 0 hits; all 65 tracked python
                            files + every tracked file: 0 hits on
                            (sk_|gsk_|AIza|ghp_|github_pat_|xox…);
                            sandbox secrets.toml confirmed gitignored and
                            NOT in the commit. History: HEAD only — the
                            sandbox clone is shallow; v174's record
                            scanned the whole history and found 0
    G3 ANALYSIS     pass    65 python files, pyflakes 0 findings
                            (frontends untouched, not re-parsed)
    G4 DEAD CODE    pass    every symbol this change added is referenced
                            (SP_VOICES_BY_LANG 14, SP_VOICE_HELP 2,
                            sp_default_voice 2); 2 symbols DELETED, both
                            confirmed 0 references repo-wide — one of
                            them written and orphaned by this same
                            session, caught at the gate. The 13
                            unreferenced functions v174 listed remain
                            out of scope and remain
    G5 DEAD LOOPS   pass    18 loop constructs added by the diff, 18
                            bounded by fixed 4-seat collections; 0 new
                            external waits (synthesis reuses the
                            existing 90s-deadline call)
    G6 STRESS       partial 23 mechanism checks green and mutated once
                            to prove red; suite 18 files passed 0
                            failed; app boots with 0 exceptions.
                            NO SOAK, NO BROWSER SUITE (as v174)
    G7 BUDGETS      base+   app.py 7635 lines (v174 baseline 7318; v175
                            sat between with no recorded number). 727
                            total checks vs 704 at v174
    G8 UPGRADE      pass    simulated honestly: a v175 settings file
                            (sp_voice stored, sp_model absent) booted
                            into v176 keeps the pick and defaults the
                            model correctly. Rollback: v175 reading a
                            v176 file ignores the extra key — but see
                            KNOWN for the Slavic-voice rollback caveat
    G9 RECORD       this document

## NOT TESTED — per §11, the most valuable block

    NO PHONE           nobody has pressed the new buttons on a real
                       phone. The two-row layout is AppTest + code
                       inspection; it lives in a browser at 390px and
                       must be seen there
    NO END-TO-END READ a full text read aloud through the new picker in
                       the running app — the live synth calls were made
                       from the harness, not from the button
    NO SOAK            same hole as v174, same shape of app
    BROWSER SUITE      test_layout, test_reader, test_shake skipped, as
                       always; test_reader 8 red since v101 stands
    HISTORY SCAN       shallow clone: G2's history pass covers HEAD only
    ENVIRONMENT        6 test files need the sheet/GAS config this
                       sandbox lacks and were excluded; they also fail
                       collection on untouched v175 here, so nothing is
                       attributed to this change
    STILL OPEN FROM    AssemblyAI round trip, HR->ENG mid-recording,
    STEP 5             single->multi mid-recording, and the Speechify
                       "test key" BUTTON (the endpoint is proven live
                       now, the button press is not)

## KNOWN, listed rather than hidden

- ROLLBACK CAVEAT: store a Slavic voice (lesya/dominika/daria), then
  roll back to v175, and the old code derives simba-english for it —
  Speechify will refuse and show its error until a voice v175 knows is
  picked. Visible failure, no data loss, accepted here.
- SP_VOICE_HELP tooltips are English-only; the picker tags are already
  bilingual through t(). Localise if Baba wants it.
- app.py still carries its own Speechify client beside
  ttt/providers/speechify.py; both were updated in step this run. The
  merge remains its own scheduled session.
- st.components.v1.html at 6 call sites and the <2.0.0 pin: unchanged.

## WHAT WAS WRONG WITH THE GATE — §15's ask, second report

**G8 still has no row for a web app, and the v174 report already said
so.** This run had to invent its own upgrade simulation (a previous
version's settings file, a fresh boot on top) and its own rollback
question (old code reading new stored data). Both belong in the module
as the Streamlit shape of G8, or the next project invents them a third
time, differently.

**G2's history scan silently degrades on a shallow clone.** The command
succeeds and reports 0 on HEAD-only history, which reads exactly like a
full-history pass. The module should say: print the depth beside the
count, and a shallow scan is a partial, never a pass.

**The gate caught a real one cheaply again**: G4 flagged a helper this
same session had written and nothing called — dead on arrival, deleted
before it could lie to the next session. The cheap gates continue to
pay for themselves.
