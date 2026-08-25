# Delivery record — TTT-LLL v213 — 25.8.2026

**The nine gates of `MANTRA_MANIFEST/modules/delivery-gate.md`, run in full on this app for the
first time.**

**First verdict: BLOCKED at G6, three findings. Final verdict after fixing them: PASS.**

Two of the three findings turned out to be MY OWN STALE `__pycache__`, not the app — the same
cause that made the jitter suite report 18/5. The third was real and is fixed. Both the first
verdict and the correction are kept here, because a record that only shows the tidy ending teaches
nothing.

    ARTEFACT   the repository at HEAD. This is a Streamlit app — no build step,
               no CI. Streamlit Cloud serves `main` directly, so the artefact IS
               the tree, and G1 must compare the tree against the remote.
    VERSION    new: v213    previous: v212, recoverable from git history

---

## GATES

### G1 · PROVENANCE — PASS

    working tree                0 modified, 0 untracked
    local HEAD == remote main   compared by SHA, they match
    what Streamlit Cloud serves is this exact commit
    branch main · version monotonic v212 -> v213
    previous artefact recoverable: full history, 31 commits today

### G2 · SECRETS — PASS

    15,843,992 bytes scanned across EVERY object in EVERY commit
    searched: sk_ gsk_ AIza AQ. ghp_ github_pat_ sk-ant- xox?- and bare 32-hex
    prefix hits 0 · 32-hex runs 0

**And the stronger check:** all **58 real credentials** currently in the vault — 21 Hume keys, 21
Hume secrets, 10 Groq, 5 AssemblyAI, 1 GitHub token — searched **by value** against the entire
history. **Found: 0.** `.gitignore` covers `.streamlit/secrets.toml`, confirmed with
`git check-ignore`.

### G3 · ANALYSIS — PASS, after one fix

    94 files · pyflakes 0 · pip-audit: no known vulnerabilities · 3 direct deps
    bandit: 13,482 lines — HIGH 4 -> 0, MEDIUM 15 read, LOW 61

**The four HIGH were all `hashlib.md5` used as a content fingerprint for change detection**, never
for security. Not a vulnerability — but on a FIPS-enabled Python `hashlib.md5()` **raises** without
`usedforsecurity=False`, which would take the app down on a machine nobody here has tested. Fixed,
four call sites.

**The MEDIUMs are `urlopen`.** Every one read: every base URL is a constant or a secret, none is
built from anything a person typed, and all 19 have deadlines (G5). Read and accepted.

**ruff's default set gave 819 findings**, almost all house style — `%`-formatting, blind-except —
which §5.2 says to narrow rather than carry. Narrowed to correctness: **3 findings, all three
confirmed false against the source.** `s != s` is the NaN idiom and the comment above it says so;
`"dr"` is an abbreviation in both the English and the Croatian list of a **set**; the ISC004 is one
string split over lines inside a tuple.

### G4 · DEAD CODE — PASS, findings recorded not deleted

    unreachable code                    0
    vulture at 100% confidence          1
    tabs offered / with a branch        8 / 8   — 0 unwired
    translation keys defined            446
    unreferenced by literal name        123

The one vulture finding is the `keep` parameter of `deliver_text`, **kept in the signature on
purpose** with the reason written above it; removing it breaks callers.

The 123 orphans were spot-checked five at a time against the whole source — all genuinely
orphaned, strings for an admin feature removed earlier (`active == "admin"` appears 0 times).
**Not deleted in this pass.** §6.2 stages deletion and §14 warns that a gate trusted blindly
produces confident deletions of correct code. A gate reports; deletion is its own commit.

### G5 · DEAD LOOPS — PASS, after one real fix

    files examined                      38
    unbounded loop constructs           1 — bounded THREE ways
    external waits examined             19
    with a deadline                     19        without: 0

The one `while True` (`speechify.py:107`) is bounded by `pages > 20`, cursor exhaustion, **and**
`timeout=45` per call.

> My first external-wait pass reported 2 without deadlines. The window was 4 lines and the timeouts
> were on lines 5 and 6. **The check was too narrow, not the code.**

**THE ONE REAL DEFECT THIS GATE FOUND — retries backed off but did not jitter.**

A long recording is split into chunks and several are in flight. When the provider refuses them —
the whole reason the schedule exists — every chunk started the same countdown at the same instant
and all came back at 5s, then all at 30s, then all at 125s. **The retry meant to let the provider
recover delivered the same burst that caused the refusal, three more times.** It is the mechanism
behind the 429 wall in `quota-and-fallback.md`, arriving from our own side.

**And nothing tested this path at all** — the retry loop had no suite, so the gap had nothing
watching it. Fixed with ±20% jitter; `tests/test_retry_jitter.py`, 23 checks.

### G6 · STRESS — PASS, after fixing the suite

    SABOTAGE every key dead      2/2   1 whisper call over 8 redraws, error shown
    SABOTAGE interrupted         2/2   the take is NOT marked done, and recovers
    SOAK 50 redraws              2/2   transcript untouched, nothing re-transcribed
    ENORMOUS a 2-minute take     1/1   reaches the box
    EMPTY and MALFORMED          3/3   zero-byte, truncated webm, a picture
                                       10 passed, 0 failed

**SOAK, ENORMOUS, EMPTY and MALFORMED executed for the first time ever.** They had never once run:
the file died before reaching them on every previous attempt.

**Finding 1 and 2 were not real.** Sabotage 1 reported "6 whisper calls, no error rendered". Run
against the same tree with clean bytecode it reports **1 call and the error shown** — the app was
correct the whole time. The 6/no-error came from a stale `__pycache__`, exactly as the jitter suite
reported 18/5 from the same cause.

**Finding 3 was real, and it was in the harness.** An interrupted run leaves AppTest's widget table
half-built, so the next `at.run()` either waits the full 300s timeout or raises `KeyError` looking
up a widget that was never created. Four unbounded runs sat after the interruption — up to twenty
minutes of hanging. Fixed three ways: the `KeyError` is recognised as the same event as the
timeout, **the poisoned instance is rebuilt and the session carried across** (which is what a
reconnecting browser actually gets), and every run in the file is bounded.

### G7 · BUDGETS — BASELINE ONLY, first run

    app.py                 476,921 bytes / 9,973 lines
    ttt/                   408,352 bytes across 37 files
    tracked                145 files, 2,025,139 bytes
    module import          0.07s median of 3
    dependencies           3 direct, 188 resolved, 0 known vulnerabilities
    the binding ceiling    Streamlit Community Cloud: 1 GB RAM for the WHOLE
                           app, shared by every session
    VR audio cache cap     20 MB per person, ~470 KB per minute at 64 kbit mono

§9.2: a budget without a previous number is a note, not a gate. **These are the baselines.** From
v214, any figure worse than these blocks until explained.

### G8 · UPGRADE — PASS

This app is not installed, it is **redeployed under the person**, so upgrade means: does their
stored data survive, and can we go back.

    session_state (RAM)           lost on redeploy — by design, free tier
    notes (browser localStorage)  survives
    settings and rings (Sheet)    survive · 43 write sites, no column changed

**Rollback clause:** this release added 9 session keys — `_keep_`, `_keepgen_`, `_vr_job`,
`_vr_whole`, `_rd_whole`, `_remote_code`, `help_lang`, `vr_tag_clip`, `vr_preview`. **All are
RAM-only.** Nothing persisted is written in a new shape, so v212 can read everything v213 writes.
**Rollback is safe.**

### G9 · RECORD — this document

---

## FINDINGS — AS FIRST REPORTED, AND WHAT THEY TURNED OUT TO BE

**1 · The take path shows NOTHING when every key is dead.** Measured with all keys sabotaged: the
failure is not rendered, so the person sees an app that appears to be doing nothing. **This is
fault 7 from Baba's brief of 03:20 this morning and it is still open.**

**2 · The same take is retried on every redraw.** Measured: whisper called **6 times across 8
redraws** with every key dead, and each call spends a key. The v185 record claimed a real error is
loud and not retried; that claim is wrong and was corrected in LAST_RUN this morning.

**3 · The stress suite still cannot complete.** SABOTAGE 2 hangs on an AppTest 300s timeout — a
`RerunException` raised inside the script body ends the run with no widget deltas, so AppTest waits
the full timeout. **SOAK, ENORMOUS, EMPTY and MALFORMED have never executed once.** The check
cannot tell "handled the interruption" from "rendered nothing" and needs rewriting before its
result can be believed.

Per §12 none of these is in the always-block band — no crash, no hang on the main path, no secret.
They sit in **BLOCKS UNLESS WRITTEN DOWN AND ACCEPTED**, and they are written down here.

---

## NOT TESTED

    a browser              nothing in v207-v213 has been opened on a phone.
                           Every visual claim is a source inspection
    G6 soak                50 redraws ran; 1000 cycles did not
    G6 monkey              no equivalent for a Streamlit app in this setup
    two interruptions      in a row: AppTest raises KeyError on the second.
                           Harness limit, not the app, and said so in the suite
    the stitcher           join_audio is measured (3 x 1s -> one 3.02s mp3) but
                           nobody has pressed the button on a real reading
    64 kbit, audibly       transparent for speech on paper; nobody has listened
    Speechify entirely     no key on this machine
    AssemblyAI exhausted   its credit-exhaustion body is unknown; finding out
                           costs hundreds of hours of audio
    Hume above 3000 chars  the true ceiling is unknown; the probe emptied the
                           account before reaching it
    iOS / Safari           no device. Matters for the mp3 choice and the
                           remote window

---

## KNOWN ISSUES CARRIED

    test_reader check 8    red, pre-existing, edge-tts path, LAST_RUN item 4
    123 orphaned strings   recorded in G4, deletion staged separately
    st.components.v1.html  past its announced removal date; requirements pin
                           streamlit<2.0.0 as the parachute

---

## A NOTE ON RUNNING THIS GATE

**Three of my own checks had to be corrected during the run**, all the same shape: the
external-wait window was 4 lines when a call spans 12; the translation-key scan missed dynamic
`t()` construction; and a stale `__pycache__` made a passing suite report 18/5 until the caches
were cleared.

§14's rule held every time: **a zero is a failure of the check until proven otherwise — and so is
a red.**
