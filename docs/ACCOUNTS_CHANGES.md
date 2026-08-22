# FOUR CHANGES TO THE ACCOUNTS SYSTEM — the plan

Asked for 22.8.2026. **Plan only — no code written.**

Two engines instead of three · a password I choose · a forced change on
first login · one message I can copy.

---

## The short answer to "what must I deploy"

| | Deploy? |
|---|---|
| **The accounts script** (`auth_script/Code.gs`) | **YES** — Manage deployments → pencil → New version. Changes 1, 2 and 3 live here. |
| **The main script** (`apps_script/Code.gs`) | **No.** Checked, not assumed — see §5. |
| **The Streamlit app** | Nothing to press. A push to `main` redeploys it. |
| **One editor run, once** | `migrateEnginesRun()` — the new function that rewrites the old engine values. |

And the honest part: **the app and the script will not land at the same
minute**, so §6 says exactly what each order does. Neither order locks
anybody out — that was the first thing I checked.

---

## 1. TWO ENGINES: `normal` and `studio`

Today the engine cell holds `free`, `studio`, or **blank meaning "follow
the global row"**. That third state goes.

**The stored word becomes `normal`, and `free` is accepted forever on
read.** Not for tidiness: nothing in this system updates atomically, so
every value already written has to keep meaning something. A row that
says `free` is a person who is on the free engine, whichever deployment
reads it.

- `ttt/engines.py` — the engine's id becomes `normal`; an alias table
  maps `free` → `normal` inside `EN.get()`, so every old row, the old
  global settings row, and any half-deployed corner keep resolving.
  `DEFAULT` becomes `normal`.
- `auth_script/Code.gs` `userEngine_` — accepts `normal` and `studio`,
  maps `free` → `normal` on write, and **keeps accepting an empty
  string** by storing `normal`. That last part is not sloppiness: the
  currently deployed panel sends `""` for its "global" button, and if
  the script is deployed before the app is pushed, that press must not
  become an error. It becomes the new meaning instead.
- `userCreate_` — writes `normal` rather than the blank it writes today.
- The panel — the radio loses its third option and shows
  **normal · studio**.

**The global settings row stays.** It is not per-person state; it is
what somebody logging in through `APP_PASSWORDS` runs, since they have
no row on the users tab at all. Its value should become `normal` too,
and the alias means `free` there keeps working until it does.

**The migration, run once from the editor**, in the preview/run pair
this script already uses:

    migrateEnginesPreview()   logs what it WOULD do, changes nothing
    migrateEnginesRun()       does it

It rewrites `free` → `normal`, and fills every blank cell. **A blank
cell is the one that needs a decision from you**, because blank meant
"whatever the global row says": if the global row is `free`, blank
becomes `normal` and nobody moves; if it is `studio`, those people are
on studio today and writing `normal` would quietly demote them. The
preview prints the global row's current value and the list of blank
people before anything is written.

---

## 2. A PASSWORD I CHOOSE, WHEN I CHOOSE ONE

`userCreate_` accepts `body.password`. Empty or absent → it generates
one, exactly as now. Non-empty → it uses it, after the same
`MIN_PASSWORD` (8) check the change-password endpoint already applies.
It is hashed on arrival like any other and never written to a log.

- `ttt/accounts.py user_create()` gains an optional `password`.
- The panel's create form gains one optional box: *leave empty and I
  will make one for you*.

**One rule that decides whether this is safe: the panel shows the
password from the SCRIPT'S REPLY, never the one you typed.** The reply
already carries it, and the panel already reads it from there. Against
an undeployed script — which ignores the new field and generates its own
— that is the difference between a message showing a password that
works and a message showing the one you meant.

---

## 3. MUST CHANGE ON FIRST LOGIN

A tenth column, `must_change`, beside `remember`.

- Written **true** by `userCreate_` and by `userPassword_` (a reset) —
  including when you chose the password yourself. The person should end
  up owning a password nobody else has ever seen.
- Returned by `login_` **and by `rememberLogin_`**, or a remembered
  phone would walk straight past the gate.
- Cleared by `passwordChange_` on success. One place, the same place
  that already proves the current password.
- `N_COLS` 9 → 10 and the header list gains it, so the column appears on
  its own the next time the sheet is touched. Old sheets read as empty,
  which is `false`, which is right.

**In the app**, the gate sits immediately after the login gate, before
the tabs: when the flag is set, the ONLY thing on screen is *set a new
password*, and it clears on success.

**This screen belongs to the family, not to the owner** — so hard rule 6
governs it completely (44px targets, generous type, nothing clipped at
250%), and none of the density that `docs/HOW_WE_WORK.md` allows behind
the amber gear applies here. It is also the first screen a new person
ever sees.

**Two guards against the one way this could trap somebody:** the app
remembers within the session that a change already succeeded, so a stale
reply cannot ask twice; and *log out* stays reachable on that screen.

---

## 4. ONE MESSAGE I CAN COPY

After a create, a `st.code(...)` block — Streamlit puts a copy button in
its corner, so it is one tap on a phone — holding a finished sentence:

> Emina, your account is ready. Username: **emina**. Password:
> **xxxxx**. The first time you log in it will ask you to choose your
> own password.

Built from the reply (§2), in whichever language the gear is set to, so
it arrives in Croatian when the app is in Croatian. The *I have written
it down* button stays: the message vanishes with it, and it cannot be
fetched again.

If an `APP_URL` secret is set, the message opens with the link. If it is
not set, the sentence simply does not mention one — no placeholder, no
guess.

---

## 5. WHY THE MAIN SCRIPT DOES NOT NEED A DEPLOY

Checked in the code, because "probably fine" is how the last deploy debt
started:

- The panel writes engines through the **accounts** script
  (`app.py:2103` → `ACCOUNTS.user_engine`). The main script's own
  `setUserEngine_`, which validates `free`/`studio` and would reject
  `normal`, is reached only by `ttt/sheet.py:set_user_engine`, and
  nothing outside `tests/test_users.py` calls that any more.
- The global engine row is written through `putSetting_`, which stores
  the string and **validates no engine names at all**, so `normal` lands
  there without a deploy.
- The main script reads only the first four columns of the users tab, so
  a tenth column is invisible to it.
- Re-running *Set up users tab* from the TTT-LLL menu is still safe: it
  only creates the tab when it is missing and only ever styles columns
  1–4.

**One thing that will need updating and is not a deploy:**
`tests/test_users.py` still asserts the main script's old engine rules
(`free`, blank, and `banana` refused), and `tests/test_admin_users.py`
asserts the three-option radio. Both change with the code.

---

## 6. WHAT BREAKS IF YOU DO NOT DEPLOY

The app redeploys itself when I push; the script waits for you. So the
realistic gap is **app new, script old**, and that column matters most.

| | App new, script OLD | Script new, app OLD |
|---|---|---|
| **1. Two engines** | Pressing **normal** fails **loudly**: the old script answers `not an engine: normal`. Nobody is moved by accident, and studio still works. | Nothing breaks — the old panel's "global" press is accepted and stored as `normal`, which is what it now means. |
| **2. Chosen password** | Your typed password is **ignored** and one is generated. The message shows the generated one, because it is built from the reply — so what you send is always what works. | Nothing; the old panel never sends the field. |
| **3. Must change** | The flag is never set and never returned; the app treats a missing field as false. **The feature is simply absent** — nobody is forced, nobody is locked out. | The flag is set and returned, and the old app ignores it. Inert until the push. |
| **4. The message** | Works — it is entirely app-side. | Unchanged. |

**Nothing in either column can lock a person out**, which is the only
question that really matters here. The worst case is a refused engine
press with a clear reason on the screen.

And `APP_PASSWORDS` is untouched by all of it: a person coming through
that door has no users row, no engine of their own, and no flag.

---

## 7. THE ORDER I WOULD DO IT IN

1. Build all four, on `beta` if you want to see them first, on `main` if
   you would rather have them now.
2. **Deploy the accounts script** — New version, never New deployment.
3. Run `migrateEnginesPreview()`, read the log, then
   `migrateEnginesRun()`.
4. Create one person to watch it end to end: the copy message, then log
   in as them in a private window and meet the change-password screen.
5. Only then create Emina and Marinko.

**Open, and worth a word from you before step 1:** whether the forced
change should also apply to **you** the first time, given your own
account predates the flag. My answer is no — you set your password
yourself and nobody else has seen it — but the column will be empty for
you either way, which means no.
