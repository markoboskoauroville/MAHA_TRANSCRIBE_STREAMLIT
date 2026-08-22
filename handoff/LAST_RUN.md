# STEP: build the four accounts changes
STATUS: done and pushed. **Deploy the accounts script before using it.**

WHAT HAPPENED
- Two engines: `normal` and `studio`. The blank "follow the global row"
  state is gone. `free` still resolves everywhere, forever — old rows do
  not stop meaning something just because we renamed the word.
- A password you choose on create, optional, same 8-character floor.
  Empty still means "make me one".
- Must-change-on-first-login: a tenth column, set by create and by
  reset, cleared only by an actual password change. The screen it drives
  is the WHOLE screen — no tabs, no deck behind it.
- One message you can copy: name, username, password, and the sentence
  saying a change is coming. `st.code` puts the copy button in its
  corner. It carries a link only if you set `APP_URL`.

NUMBERS
- auth script (node)  ->  66 checks, was 46
- admin panel         ->  47 checks, was 39
- must-change (new)   ->  12 checks
- pytest tests/       ->  20 passed, 1 skipped (layout, no app served)
- pyflakes            ->  clean
- mutation-tested     ->  8 sabotages in the script, 5 in the app, all caught

WHAT BROKE, AND WHAT I UNDID
- Three real faults the tests found, all fixed, none of them in the part
  I was building:
  * `log_out` was defined 1,600 lines BELOW the new gate, which stops
    the script — so the way OFF that screen was a crash. Moved up.
  * A radio whose options change crashes on a stored value that is no
    longer one of them (`ValueError: '' is not in list`, thrown inside
    Streamlit) — a white panel. It now clears a stale value first.
  * The engine tick in the corner compared ids as strings, so a verdict
    recorded as `free` would have silently lost its tick.
- One of my own checks was worthless: it passed while the entire app
  rendered underneath the gate. Rewritten to measure against the real
  app, then re-mutated to prove it fails.
- Two sabotages ran against `app.py` and `auth_script/Code.gs` and were
  restored from copies held aside; `git status` is clean apart from the
  intended changes.

STILL UNSURE
- Nothing was tested against the REAL deployed script — the suites run a
  stub and a fake Apps Script runtime. The first real proof is you
  creating one person after deploying.
- The Croatian in the new screens is mine. Worth reading once: the
  message you will send to Emina and Marinko is in it.

FOR BABA
1. **Deploy the accounts script** — Manage deployments → pencil → New
   version. Until then: pressing `normal` fails loudly with "not an
   engine", a chosen password is ignored (the message still shows the
   one that works), and nobody is asked to change anything.
2. In the accounts editor, run `migrateEnginesPreview()`, read the log,
   then `migrateEnginesRun()`.
3. Make one test person and watch it end to end: the copy message, then
   log in as them in a private window and meet the change screen.
4. Then Emina and Marinko.
- Older queue, unchanged: `ADMIN_USER = "admin"`, `AUTH_ADMIN_TOKEN` in
  the Streamlit secrets, and step 1 of `SELF_UPGRADE.md` — the live
  Claude API check — is still unrun.
