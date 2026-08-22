# SELF UPGRADE — the plan

A second Streamlit app, deployed from a `beta` branch, in which Baba
speaks a change, sees a diff, uses the result, and only then pushes it
to the family's app.

Written 22.8.2026. **Plan only — no code exists yet.**

---

## The shape, in one picture

    main branch    ──►  the family's app        amber, the real sheet, the real Drive
    beta branch    ──►  the beta app            cyan,  a beta sheet, a beta Drive folder

    speak → transcribe → Claude → diff → commit to beta → USE it → push to main

The rollback controls live in **beta**, so the thing that rescues the
app is never the thing that is broken.

---

## PART 1 — The three decisions asked for

### 1.1 Does beta need its own sheet and Drive folder?

**Yes. Both. This is the part that is not optional.**

The reason is not tidiness, it is that the app writes real things. A
beta test records audio into `USERS/<user>/<rec_id>/`, appends a row to
`recordings`, and writes a usage row. Those are the family's, and the
recordings are the only copy of somebody's voice. A convenience being
tested must not be able to touch them.

So beta gets:

| | main | beta |
|---|---|---|
| Spreadsheet | the real one | **File → Make a copy** |
| Drive folder | the real `DRIVE_ROOT_ID` | a new empty folder |
| Main Apps Script | the current deployment | **a second project**, same code, those two values changed |
| Accounts script | shared — see below | shared, login token ONLY |

**Two things to know about the copy.** It brings the `k_groq`,
`k_anthropic`, `k_speechify` and `k_assemblyai` tabs with it, which is
what lets beta transcribe and call Claude with no new secret — but it
also means the keys now live in two documents and a rotation has to
happen in both. And the copied `settings` tab is beta's own: changing
the global engine there does not touch the family.

**Accounts are the exception, deliberately.** Beta points `AUTH_URL` at
the SAME accounts script, with `AUTH_LOGIN_TOKEN` and **never**
`AUTH_ADMIN_TOKEN`. That token can only ask *"is this pair right"* — it
cannot create, rename, delete or reset anybody, so the worst a broken
beta can do to the family's accounts is fail to log in. This is what
makes "behind my admin password" real: the password is checked by the
accounts script, in constant time, at 1000 rounds, exactly as the real
login is.

Two residues, named rather than hidden: a *Remember me* ticked in beta
mints a real remember-token and each person has only five device slots;
and a password change made in beta is a real password change. Do
neither in beta, or accept them.

### 1.2 What the second Streamlit deployment needs from you

Eight things. Nothing here can be done from this repo.

1. A `beta` branch on GitHub — I can create and push that.
2. **Streamlit Cloud → New app**, same repo, **branch `beta`**, main file
   `app.py`. It gets its own URL. *(This is the one place "New app" is
   correct — the never-New-deployment rule is about Apps Script, where a
   second web app means a second URL nobody points at. Here the second
   URL is the entire point.)*
3. A copy of the Google Sheet — File → Make a copy. Note its id.
4. A new Drive folder for beta recordings. Note its id.
5. A second Apps Script project holding the same `apps_script/Code.gs`
   with `SHEET_ID` and `DRIVE_ROOT_ID` set to those two, and its own
   `SHEETS_TOKEN`. First deploy is a New deployment (it is a new
   script); every deploy after that is New version, as always.
6. Beta's secrets, pasted into the beta app only:

        APP_PASSWORDS      your own — the door that always opens
        ADMIN_USER         you
        SHEETS_URL         the BETA script's /exec URL
        SHEETS_TOKEN       the BETA script's token
        DRIVE_SECRET       the BETA script's
        AUTH_URL           the real accounts script
        AUTH_LOGIN_TOKEN   login token only — NOT the admin token
        GITHUB_TOKEN       see 7
        BETA               "1"      — turns the panel on and forces the colour

   No Anthropic key here: it comes from the beta sheet's `k_anthropic`
   tab through the existing key ring, like every other provider key.
7. A **fine-grained GitHub token**: this repository only, Contents
   read/write, an expiry date you are willing to renew. Nothing else —
   not Actions, not Administration.
8. Two answers from you: the beta colour (**cyan** is my recommendation
   — blue against amber is the pair that stays distinguishable for
   someone who does not see colour well; green against amber is not),
   and whether "Push to main" may push straight to `main` or should only
   move a `ready` branch you merge on GitHub.

### 1.3 What can still take main down, and how you recover

**Six ways it can still break, worst first.**

1. **A change that is green in beta and dead in main** — because beta
   has secrets main does not. Guarded by rule 1 below (the panel is
   inert without its secrets, exactly like the People panel) and by
   running the tests before any push.
2. **`requirements.txt` or `packages.txt`** — a bad pin does not raise a
   Python error, it fails the boot before your code runs, and the app is
   simply gone. **The tool must refuse to edit these**, along with
   `apps_script/**`, `auth_script/**`, `.streamlit/**` and its own
   module. If one of those needs changing, that is a normal session.
3. **Syntactically valid, semantically gutted.** `py_compile` proves
   nothing about meaning. That is why the test suite runs and why you
   must USE beta before the push is offered.
4. **A whole-file rewrite when a two-line edit was meant.** The diff is
   shown with its line counts, and a change over ~80 lines asks twice.
5. **A leaked GitHub token.** Fine-grained, one repo, contents only,
   with an expiry. It is never printed, never in `handoff/`, never in a
   diff.
6. **A rewritten history.** Pushes are fast-forward only. If main has
   moved underneath, the app stops and says so — it never force-pushes.

**Recovery, in the order to try it, all of it possible from a phone.**

1. **GitHub in the phone browser** — repo → Commits → the bad one →
   **Revert**. That makes a revert commit on `main` and Streamlit
   redeploys in about two minutes. This is the one to remember; it needs
   nothing but a browser and your GitHub login.
2. **The beta app's Roll back screen** — the last three commits of main,
   each with a button that pushes a revert of it. Beta is a separate
   deployment on a separate branch: main being dead does not touch it.
3. **Streamlit Cloud → Manage app → Reboot**, if the code is fine and
   the module is stale (§72's white screen).
4. **The `last-good` tag.** The push-to-main step moves it to main's tip
   *before* pushing, so there is always a named commit known to have
   run. From a phone: Streamlit Cloud → Settings → point the app at it.

**What cannot be lost, and is worth saying plainly.** None of this
touches recordings, transcripts or accounts — those are in Drive and in
the sheet, and a dead app is an outage, not a loss. `APP_PASSWORDS`
still opens the door the moment the app is back.

---

## PART 2 — The flow, screen by screen

All menus and buttons. Nothing to type.

1. **Gate.** The Upgrade module appears only when `BETA` is set, the
   secrets are present, and you have typed your own password — checked
   against the accounts script, not `is_admin()`.
2. **What to change.** Radio buttons over a curated map of the app —
   *the reader · the notes · the login screen · the deck · the archive ·
   the admin panel* — each naming one file. Not a file browser.
3. **Say it.** The existing recorder takes a voice note; the existing
   engine transcribes it; the text appears with **use this** / **say it
   again**.
4. **Claude reads the file and answers with the whole file back.**
   `claude-opus-5`, adaptive thinking, effort `high`. Roughly 25–30k
   input tokens for a large file and a few thousand out — **a few cents
   a request** at $5/$25 per million.
5. **The diff.** Unified, coloured, with "+12 −3" at the top. Buttons:
   **apply to beta** · **discard** · **say more and try again**.
6. **Apply** = compile-check → `pytest tests/ -x` → commit to `beta` →
   push. Beta redeploys itself. A failing check never commits; it shows
   the error and offers **try again** or **discard**.
7. **Use it.** The panel says *"not used since this change"* until beta
   has seen a real recording or a real reading. The push button is not
   drawn before that.
8. **Push to main** — its own screen, its own password prompt, showing
   what main will receive. Moves `last-good`, then fast-forwards `main`.
9. **Roll back** — the last three commits of beta and of main, each
   restored by a revert, never by a reset and never by a force-push.

---

## PART 3 — What is already here, and one thing that is broken

**Already here, and reusable:** the Anthropic provider
(`ttt/providers/anthropic.py`) with a live model list and a key ring fed
from the sheet, the recorder and the transcription path, `ACCOUNTS.login`
for the password check, and `theme.SCHEMES` for the colour.

**Broken for this purpose, and it must be fixed before step 4 can
work:** `Anthropic.complete()` always sends `temperature`, and every
current model — Opus 5, Opus 4.8, 4.7, Sonnet 5 — **rejects sampling
parameters with a 400**. Its `max_tokens` also defaults to 2048, which
cannot hold a returned file. So the self-upgrade needs its own call
(no `temperature`, `max_tokens` ~32k, streaming, adaptive thinking), and
`complete()`'s fallback model id (`claude-sonnet-4-5-20250929`) is old
enough to be worth replacing while we are there.

**Not decided yet, and better decided when the first version exists:**
whether the request should carry more than one file (a change often
touches `app.py` and a `ttt/` module together), and whether the diff
should be reviewable on a phone or only on the Mac.
