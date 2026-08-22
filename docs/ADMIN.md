# TTT-LLL — the administrator's guide

Written for Baba, who runs this for his family. Everything here assumes
a Mac, `clasp` already installed and logged in, and this repo cloned.

There are only **five places** anything lives. Once you can name them,
the rest of this document is detail.

| Where | What it holds | Who changes it |
|---|---|---|
| **This repo** | the app and both Apps Script sources | you, in your editor |
| **The main script** | the running copy of `apps_script/Code.gs` | `clasp push`, then Deploy |
| **The accounts script** | the running copy of `auth_script/Code.gs` — logins and passwords | `clasp push`, then Deploy |
| **The Google Sheet** | users, settings, API keys, the recording index | the accounts script, and you for settings |
| **Google Drive** | the audio and the transcripts | the app, mostly |

**Nothing syncs by itself.** clasp copies a file to Google. Streamlit's
secrets are pasted by hand. Google and Streamlit never talk to each
other — they only ever compare a password. That is the single most
confusing thing about this setup, and it is worth reading twice.

---

## PART 1 — Changing the script

### 1.0 There are TWO scripts — and which token is whose

They are separate Apps Script projects, with separate deployments and
separate tokens. Confusing them is the most expensive mistake available
here, so name them once:

| | **The main script** | **The accounts script** |
|---|---|---|
| In this repo | `apps_script/Code.gs` | `auth_script/Code.gs` |
| Does | recordings, Drive, settings, usage | logins, passwords, who exists |
| Its token | `SHEETS_TOKEN` | `AUTH_LOGIN_TOKEN` **and** `AUTH_ADMIN_TOKEN` |
| Its address in secrets | `SHEETS_URL` | `AUTH_URL` |
| Deploy | Deploy → Manage deployments → pencil → **New version** | the same, in its own project |

**They share one spreadsheet and nothing else.** The accounts script
owns the `users` tab; the main script reads the four left-hand columns
of it and never writes a password.

**The accounts script has two tokens, and the difference is the point:**

- **`AUTH_LOGIN_TOKEN`** may ask *"is this pair right"*, hand back a
  remembered session, and change a password **when the current one is
  supplied**. It cannot make, rename or delete anybody. Every phone in
  the house is effectively carrying this one.
- **`AUTH_ADMIN_TOKEN`** may change people. The app reads it in exactly
  one place — the People panel — and the script wants your own password
  on top of it before it will delete, rename or reset (§3.2).

Both are pasted into Streamlit secrets, and both are *also* set in the
accounts project's **Project Settings → Script Properties**, where they
are compared. Three more properties live there and **nowhere else**:

```
AUTH_PEPPER       the secret that makes a leaked spreadsheet useless (§3.6)
AUTH_ADMIN_USER   the one username allowed to prove itself as administrator
AUTH_SETUP_PASSWORD   temporary — setupAdmin() uses it once and deletes it
```

`AUTH_PEPPER` is **not** in the sheet and **not** in Streamlit. If you
ever change it, every existing password stops working and every account
needs a reset. Leave it alone.

One more name, on the app's side: **`ADMIN_USER`** in Streamlit secrets
decides who sees the amber gear. It should be the same person as
`AUTH_ADMIN_USER` in the accounts project — if they disagree, the gear
opens for somebody whose password the script will not accept as proof.

### 1.1 The one trap, before anything else

`apps_script/Code.gs` in this repo has **placeholders** at the top:

```javascript
var SHEETS_TOKEN  = 'CHANGE_ME_to_a_long_random_string';
var DRIVE_SECRET  = 'CHANGE_ME_to_a_different_long_random_string';
var DRIVE_ROOT_ID = 'PUT_YOUR_FOLDER_ID_HERE';
```

Your local copy has your **real** values. If you ever `git pull` and let
those placeholders overwrite your file, then push, everything answers
`bad token` and it looks like the app broke.

Protect your filled-in file once:

```bash
cd ~/path/to/MAHA_TRANSCRIBE_STREAMLIT
git update-index --assume-unchanged apps_script/Code.gs
```

That tells git to stop tracking your changes to that one file, so
`git add -A` can never publish your token by accident.

**Only the main script needs this.** `auth_script/Code.gs` keeps its
secrets in Script Properties rather than in the file, so there is
nothing in it to protect and `git pull` updates it normally.

**But it also means `git pull` will not update that file.** So when I
tell you the script has changed, the routine is:

```bash
# 1. let git see the file again
git update-index --no-assume-unchanged apps_script/Code.gs

# 2. keep your own copy safe
cp apps_script/Code.gs ~/Desktop/Code.gs.MINE

# 3. take the new version
git stash                 # park your edits
git pull
git stash drop            # you do not want the old edits back

# 4. put your three values back into the NEW file
#    open apps_script/Code.gs, copy the three lines from
#    ~/Desktop/Code.gs.MINE into it — ONLY the three values

# 5. hide it again
git update-index --assume-unchanged apps_script/Code.gs
```

Only the **value** moves between the two files. `Code.gs` uses
`'single'` quotes and Streamlit's TOML uses `"double"` — the quotes stay
where they are. Copying the quotes across makes the value literally
contain apostrophes, which is a very confusing hour.

### 1.2 Push it

```bash
cd ~/path/to/MAHA_TRANSCRIBE_STREAMLIT
clasp push                      # the MAIN script
```

You should see `Pushed 2 files.` (`Code.gs` and `appsscript.json`.)

**The accounts script is pushed from its own folder**, because that is
where its `.clasp.json` — and therefore its project id — lives:

```bash
cd ~/path/to/MAHA_TRANSCRIBE_STREAMLIT/auth_script
clasp push                      # the ACCOUNTS script
```

Push from the wrong folder and you send one script's code to the other
project. If that happens, push the right file from the right folder and
deploy again; nothing is lost.

If it fails with something unhelpful, the usual cause is the Apps Script
API being off. Turn it on at
`script.google.com/home/usersettings`, then push again.

### 1.3 PUSH IS NOT DEPLOY

This is the step everyone forgets, including me. `clasp push` updates the
source. The web app keeps serving the **old** version until you deploy.

On the Google side, in the Apps Script editor:

**Deploy → Manage deployments → the pencil ✏️ → Version: New version →
Deploy**

> **Never use "New deployment" after the first time.** It creates a
> SECOND web app at a DIFFERENT URL, while your Streamlit `SHEETS_URL`
> still points at the first one. The old code keeps answering and
> nothing appears to change. If you have already done this, the fix is
> to go back to Manage deployments and update the original.

**Both projects deploy the same way, separately.** Changing the accounts
script and deploying the main one leaves the login exactly as it was —
the two have nothing to do with each other, and `AUTH_URL` points at the
accounts deployment, not this one.

### 1.4 How to tell it worked

Open the app, log in as yourself, go to the amber gear, press
**check engine**. If it answers, the script is alive.

For the newer features specifically: choose an engine and look at the
line under the buttons. `saved to the sheet for everyone` means the new
script is deployed. `this session only` means it is not.

---

## PART 2 — The Sheet

### 2.1 First-time setup, or after a big change

Open the spreadsheet itself (not the script editor). There is a
**TTT-LLL** menu next to Help. If you do not see it, reload the page —
the menu is built when the sheet opens.

Run these in order:

1. **First-time setup** — makes `Summary`, `Daily`, and a `u_<name>` tab per user
2. **Set up settings and keys tabs** — makes `settings`, `k_groq`, `k_speechify`, `k_anthropic`, `k_assemblyai`
3. **Set up Drive storage** — makes `recordings` and checks it can see your Drive folder
4. **Set up users tab** — makes `users`

Then, **once**, in the **accounts** project's editor (§1.0): set
`AUTH_PEPPER`, `AUTH_LOGIN_TOKEN`, `AUTH_ADMIN_TOKEN` and
`AUTH_ADMIN_USER` in Script Properties and run **`setupAdmin()`**. It
makes your own account and prints the password to the log **once**.
Write it down there and then — §3.6 explains why nothing can print it
again. If a `users` tab already exists it adds the columns it needs
rather than replacing anything.

**Ignore the spinner. Look for the tabs.** If a function seems to hang
for more than thirty seconds, it is waiting for a dialog you cannot see.
Running from the TTT-LLL menu avoids that; running from the editor does
not. If the tab exists, the function did its job.

### 2.2 The tabs, and what each is for

| Tab | What it is |
|---|---|
| `users` | the family — **username, engine, note**, and the hashes beside them (§3.6). Owned by the accounts script; use the People panel. |
| `settings` | `scope, key, value` — global switches and the AI prompts |
| `recordings` | the index of what is in Drive. **Do not edit by hand.** |
| `k_groq`, `k_speechify`, … | spare API keys, one per row |
| `u_<name>`, `Summary`, `Daily` | usage logs. Read-only in practice. |

---

## PART 3 — Managing users

This is the part you asked for, and it is now **in the app**: amber gear
→ **People**. Everything in this Part is done from that panel, and the
`users` tab is what it writes.

The tab still has the four columns the main script reads, plus the ones
the accounts script added on the right:

```
username | password | engine | note     | salt | hash | rounds | folder | remember
---------|----------|--------|----------|------|------|--------|--------|----------
baba     |          | studio | me       | 7f…  | Qk…  | 1000   | baba   | a9…
kerstin  |          |        | …        | 2c…  | Lm…  | 1000   | kerstin|
mama     |          | free   | …        | e1…  | Zx…  | 1000   | mama   |
```

**The `password` column is empty and stays empty.** It is what the old
plaintext login used; the accounts script emptied it at migration and
never writes it again. See §3.6.

**Do not add or delete rows by hand.** A person made in the panel gets a
salt, a hash and a frozen folder name in one locked write; a row typed
into the sheet has none of those and cannot log in.

### 3.1 Add a user

1. Amber gear → **People**
2. Type the username (and a note, if you want one)
3. **Optionally** type a password. Leave it empty and one is made for
   you — that is what it did before this box existed.
4. **Add**
5. A **whole message** appears at the top of the panel, ready to send:
   their name, their username, the password, and the sentence saying
   they will be asked to change it. One tap on the corner of that block
   copies it.

**The password is shown once.** If you close the panel before copying
it, reset it (§3.2); there is no way to look it up — §3.6 explains why.

**It is a temporary password either way**, whether you chose it or the
script made it. By the time they have it, it has been typed into a
panel and sent through a chat app, so the first thing the app asks them
is to choose their own. You do not have to explain that: the message
says it, and the app enforces it.

**Rules that matter:**

- **Username** is matched without caring about capitals. `Kerstin` and
  `kerstin` are the same person. It is stored lowercase.
- **Do not reuse a username.** It is the name of their Drive folder and
  their usage tab.
- Avoid spaces and punctuation in usernames — `ana-marija` is fine,
  `Ana Marija!` is refused.
- The panel needs `AUTH_URL` and `AUTH_ADMIN_TOKEN` in Streamlit
  secrets. If either is missing it says so and does nothing — it never
  takes the app down with it.

### 3.2 Reset someone's password

**In the app, not in the sheet.** Amber gear → **People** → their row →
**Reset**. A strip opens under that person and asks for **your own
password** — not the token, yours. Type it, confirm, and the new
password appears once at the top of the panel. Copy it before you leave
that screen.

**Why it asks for your password as well as the admin token:** the token
is a string sitting in Streamlit's secrets, and a string can leak or be
left on a screen. A reset is not the gentle one of the three actions —
it locks a person out of their own account — so the script wants the
person, not just the string. It checks the name you are logged in as
against `AUTH_ADMIN_USER` in its own Script Properties, so holding the
token is not enough to nominate yourself administrator.

Three things happen on a reset, all of them deliberate:

- The old password stops working **immediately**.
- **Every remembered device is signed out.** A reset is how you get
  somebody *out* as much as how you let them back *in*, and leaving
  their old phone logged in would defeat half of that. This is the
  answer to "I need them out now" — there is nothing else to do.
- The row is re-hashed at today's cost, not the cost it was made at.
- **They must choose their own password the next time they log in.** The
  one you hand over is temporary by design: it has been read aloud and
  sent through a chat app by the time they have it. The app asks for a
  new one before it shows them anything else, and nothing you or I can
  press skips that screen for them.

If **you** are the one who forgot: nobody can reset the administrator
from inside the app. Log in with your `APP_PASSWORDS` password and the
username box empty (§3.5), then use the panel.

### 3.3 Delete a user

Amber gear → **People** → their row → **Delete**, and confirm with your
own password, the same as a reset. They can no longer log in.

Renaming is in the panel too, but the button is **deliberately
disabled**, with the reason on its tooltip: the accounts script freezes
a folder name at creation, and the main script still builds
`USERS/<username>/` out of the login name. A rename today would walk
away from that person's recordings. When the main script reads the
`folder` column, the button loses `disabled` and nothing else changes.

**Their recordings are NOT deleted.** Drive still holds
`USERS/<username>/…` and `recordings` still has their rows. That is
deliberate — losing a person's audio because you tidied a spreadsheet
would be the wrong direction to fail in.

To remove their recordings too:

1. In Drive, open your `USERS` folder, find `<username>`, delete it
2. In the `recordings` tab, delete their rows

Do those two together, or the app's list will point at audio that is not
there.

### 3.4 Give someone a different engine

Amber gear → **People**. Pick the person, then the engine: **normal**
or **studio**. One press, no confirmation — an engine is the one thing
here that can be put back by pressing the other button, so it does not
ask for your password.

**Two engines, not three.** `normal` is Edge / Groq — the app's own
keys, free. `studio` is Speechify / AssemblyAI / Claude, on your keys.
There used to be a third choice, a blank cell meaning "follow the global
row", and it is gone: a person's engine is now theirs outright.

**Old sheets keep working.** A cell still saying `free` is read as
`normal` everywhere, and a blank one lands on `normal` too. To tidy them
up in one go, open the ACCOUNTS script's editor and run
`migrateEnginesPreview()` — it prints what it would change and writes
nothing — then `migrateEnginesRun()`.

The global engine row in `settings` stays, and it is what somebody
logging in through `APP_PASSWORDS` runs, since they have no row on the
users tab at all.

**Blank means "use the global engine"** from the `settings` tab. It is
not an error and it is not "no engine".

The global engine is the row `global | engine | free` (or `studio`) in
`settings`. Changing an engine in the app as administrator writes that
row for you.

### 3.5 The emergency door — READ THIS ONE

Streamlit secrets still hold `APP_PASSWORDS`, and **real accounts did
not replace it.** Those passwords work **even if the accounts script is
unreachable, half-deployed, misconfigured, or the Sheet is empty.**

That is on purpose, and it matters more now than it did with passwords
in a spreadsheet: the login screen is a second web app that can be down
on its own. A failure there locks out *everybody*, including you, and
there would be no way in to fix it. So:

> **Keep at least one password in `APP_PASSWORDS` that only you know,
> and do not delete it.** It is the key under the doormat. If the
> accounts script ever breaks — or you forget the administrator
> password — you log in with that, with the username box empty.

Logging in this way makes you the administrator (`ADMIN_USER`, or the
first entry in `APP_PASSWORDS`), so the amber gear and the People panel
are there. The panel still needs the accounts script to be answering:
if the door you came through is the one that broke, fix that first.

To change it: Streamlit Cloud → Manage app → Settings → Secrets → edit
the line → Save. The app restarts itself.

### 3.6 About passwords — said plainly

**There are no passwords in the spreadsheet any more.** The `password`
column is empty. What is stored is three cells per person:

```
salt    a long random string, different for every person
hash    the password put through a one-way mill
rounds  how many times it went through — 1000 today
```

The mill is HMAC-SHA256, keyed with a **pepper**, run `rounds` times.
The salt goes in so that two people who happen to choose the same
password still get different hashes. The repetition is the cost: about
**half a second** on Google's servers, measured, not guessed. You wait
it once when you log in; somebody guessing waits it for every guess.

**The pepper is the part that matters.** It lives in the accounts
project's **Script Properties** — not in the sheet, not in Streamlit,
not in this repo, not in any file you can open. Without it, the hashes
in the spreadsheet cannot be attacked offline at all. That is what makes
a leaked sheet a leak of *usernames*, not of passwords.

Now the plain part, and it is the whole point of the change:

> **You cannot read anyone's password. Not from the sheet, not from the
> app, not from the script, not by asking me.** A hash cannot be turned
> back. When someone forgets theirs, the only thing anybody can do —
> including you — is **reset** it (§3.2) and hand them a new one.

That includes your own. There is no copy of it anywhere.

So "she forgot her password" is no longer a ten-second look-up; it is a
ten-second reset that also signs her old devices out. That is the better
trade, and it is why the plaintext column went.

What still follows:

- **Do not share that spreadsheet** with people who should not see it.
  The hashes are useless without the pepper, but the sheet also lists
  who exists, their notes, their engines and their recordings.
- **Nobody should reuse a password they use anywhere else.** The script
  makes them up now, which handles this by itself — let it.
- The app still never sees a stored password. It asks the script *"is
  this pair right"* and gets yes or no, and the login costs the same
  half second for a name that does not exist as for one that does, so
  the family list cannot be read off the login screen.

---

## PART 4 — Google Drive

### 4.1 The shape

```
USERS/                          ← the folder whose id is DRIVE_ROOT_ID
    baba/
        20260819-094352-c7062f8c/
            part_0000.flac      ← the audio, 16 kHz mono, 10-minute parts
            text.txt            ← the transcript of that recording
    kerstin/
        …
```

One folder per person, one folder per recording, and **the audio and the
transcript always live together.** That is why deleting a recording in
the app removes both — it trashes the folder.

### 4.2 What you can safely do by hand

- **Look at anything.** Reading changes nothing.
- **Delete a whole recording folder** — then delete its row in
  `recordings` so the index matches.
- **Delete a whole person's folder** when they leave.

### 4.3 What NOT to do by hand

- **Do not rename folders.** The name is the id the app looks up.
- **Do not move recordings between people's folders.**
- **Do not edit `text.txt` in Drive** expecting the app to notice — it
  will read your edit next time it pulls, but the `chars` count in the
  sheet will be wrong until the app writes it again.
- **Do not edit the `recordings` tab by hand** except to delete a row
  you have just deleted in Drive.

### 4.4 It fills up

Drive files count against **your** Google quota, because the script runs
as you. Roughly **1 MB per minute** of speech. An hour a day for a year
is about 20 GB.

Nothing expires on its own — that was deliberate, so no recording
disappears without you choosing it. Deleting old recordings is
housekeeping you do when you feel like it.

---

## PART 5 — When something is wrong

| What you see | What it means | What to do |
|---|---|---|
| `bad token` | a script and Streamlit disagree | check *which* script (§1.0): `SHEETS_TOKEN` for the main one, `AUTH_LOGIN_TOKEN` / `AUTH_ADMIN_TOKEN` for accounts |
| `this session only` under the engine buttons | the deployed main script is older than the repo | Deploy → Manage deployments → pencil → New version |
| `admin token required` | the panel is using the login token | `AUTH_ADMIN_TOKEN` missing or wrong in Streamlit secrets |
| `administrator password required` | the password you typed to confirm was wrong, or you are not `AUTH_ADMIN_USER` | check `ADMIN_USER` and `AUTH_ADMIN_USER` name the same person (§1.0) |
| the People panel says it cannot connect | `AUTH_URL` or `AUTH_ADMIN_TOKEN` is missing | paste both into Streamlit secrets |
| the People panel lists nobody | the accounts script answered, and there is nobody | expected only before `setupAdmin()` has run |
| someone cannot log in | wrong password, or their row has no hash | reset them (§3.2); a row typed in by hand has no hash and never works |
| nobody can log in | the accounts script is unreachable | use your `APP_PASSWORDS` password with the username box empty |
| the app is completely white | usually a stale module after a deploy | Streamlit Cloud → Manage app → **Reboot**. A rerun is not enough. |
| `check engine` shows ✗ | a provider refused | the row names which one and why; usually an expired key |

**One habit worth having:** after any deploy, open the live app once and
log in. Local green is not production green.

---

## PART 6 — It IS in the app now

This Part used to say the user panel was not built. It is built, it is
deployed, and it is the thing you asked for at the very start: *"I want
in this panel to have list of all users and assign them engines."*

Amber gear → **People**. Five things, all of them live:

| | What it does | What it asks for |
|---|---|---|
| **Add** | makes the account, generates the password, shows it once | nothing |
| **Reset** | new password, old devices signed out | **your own password** |
| **Delete** | the account goes, the recordings stay | **your own password** |
| **Engine** | Edge / Groq, Speechify / AssemblyAI / Claude, or global | nothing |
| **Rename** | disabled on purpose — see §3.3 | — |

It talks to the **accounts** script, not the main one (§1.0). That is
why it works while the main script is mid-deploy: the old version of
this panel asked the main script and said *"no users tab yet"* whenever
that script was behind, which was true about the deployment and a lie
about the tab.

**The worry that delayed it has not gone away, it has been designed
against.** A bug in a user panel can lock everybody out, including you.
So:

- Every call in it **returns** rather than raises. An unreachable script
  is a sentence on the screen, not a crash.
- A missing `AUTH_ADMIN_TOKEN` is not an error — the panel says so and
  does nothing.
- The two destructive actions need your password as well as the token,
  and the script checks the name against its own `AUTH_ADMIN_USER`.
- **`APP_PASSWORDS` is untouched by all of it** and stays the door that
  always opens (§3.5). Nothing in this panel can close it.

What is left for the spreadsheet: settings, API keys, the recording
index, and reading things. Not people — do those here.
