# TTT-LLL — the administrator's guide

Written for Baba, who runs this for his family. Everything here assumes
a Mac, `clasp` already installed and logged in, and this repo cloned.

There are only **four places** anything lives. Once you can name them,
the rest of this document is detail.

| Where | What it holds | Who changes it |
|---|---|---|
| **This repo** | the app and the Apps Script source | you, in your editor |
| **The Apps Script project** | the running copy of `Code.gs` | `clasp push`, then Deploy |
| **The Google Sheet** | users, settings, API keys, the recording index | you, by hand |
| **Google Drive** | the audio and the transcripts | the app, mostly |

**Nothing syncs by itself.** clasp copies a file to Google. Streamlit's
secrets are pasted by hand. Google and Streamlit never talk to each
other — they only ever compare a password. That is the single most
confusing thing about this setup, and it is worth reading twice.

---

## PART 1 — Changing the script

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
clasp push
```

You should see `Pushed 2 files.` (`Code.gs` and `appsscript.json`.)

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

**Ignore the spinner. Look for the tabs.** If a function seems to hang
for more than thirty seconds, it is waiting for a dialog you cannot see.
Running from the TTT-LLL menu avoids that; running from the editor does
not. If the tab exists, the function did its job.

### 2.2 The tabs, and what each is for

| Tab | What it is |
|---|---|
| `users` | **username, password, engine, note** — the family |
| `settings` | `scope, key, value` — global switches and the AI prompts |
| `recordings` | the index of what is in Drive. **Do not edit by hand.** |
| `k_groq`, `k_speechify`, … | spare API keys, one per row |
| `u_<name>`, `Summary`, `Daily` | usage logs. Read-only in practice. |

---

## PART 3 — Managing users

This is the part you asked for, and it is deliberately simple: **the
`users` tab IS the user database.** Four columns.

```
username | password  | engine | note
---------|-----------|--------|---------------------------
baba     | kruh-more | studio | me
kerstin  | sunce-42  |        | uses the global engine
mama     | lipa-9    | free   | keep her on the free engine
```

### 3.1 Add a user

1. Open the `users` tab
2. Add a row: a username, a password
3. Leave `engine` blank unless you want to pin them to one
4. Tell them their username and password

That is all. **No deploy, no restart.** The app reads the sheet at login,
so the next time they open it, it works.

**Rules that matter:**

- **Username** is matched without caring about capitals. `Kerstin` and
  `kerstin` are the same person. It is stored lowercase.
- **Password** is matched **exactly**, including spaces. A trailing
  space you cannot see is a password they cannot type. If a login
  mysteriously fails, click the cell and check the end of the value.
- **Do not reuse a username.** It is the name of their Drive folder and
  their usage tab.
- Avoid spaces and punctuation in usernames — `ana-marija` is fine,
  `Ana Marija!` is asking for trouble.

### 3.2 Reset someone's password

Change the value in the `password` cell. Tell them the new one. Done.

They stay logged in on any device where they ticked *Remember me* until
that browser forgets — the old password does not lock them out
retroactively. If you need someone out **now**, change the password AND
tell them to press *Forget me* in Settings, or clear their browser data.

### 3.3 Delete a user

Delete their row. They can no longer log in.

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

Two ways, and they do the same thing:

- **In the app:** log in as yourself, amber gear, *Engine per user*.
  Every name has **Edge / Groq**, **Speechify / AssemblyAI / Claude**,
  and **global**.
- **In the sheet:** type `free`, `studio`, or leave the cell blank in
  their `engine` column.

**Blank means "use the global engine"** from the `settings` tab. It is
not an error and it is not "no engine".

The global engine is the row `global | engine | free` (or `studio`) in
`settings`. Changing an engine in the app as administrator writes that
row for you.

### 3.5 The emergency door — READ THIS ONE

Streamlit secrets still hold `APP_PASSWORDS`. Those passwords work
**even if the Sheet is unreachable, misconfigured, or empty.**

That is on purpose. A failure in the login screen locks out *everybody*,
including you, and there would be no way in to fix it. So:

> **Keep at least one password in `APP_PASSWORDS` that only you know,
> and do not delete it.** It is the key under the doormat. If the sheet
> ever breaks, you log in with that, with the username box empty.

To change it: Streamlit Cloud → Manage app → Settings → Secrets → edit
the line → Save. The app restarts itself.

### 3.6 About passwords in a spreadsheet — said plainly

The passwords sit in the sheet as ordinary text. Anyone you share that
spreadsheet with can read every password in it.

For a family of five, with a private sheet you own, that is a reasonable
trade — and it is what makes "she forgot her password" a ten-second fix
instead of a feature.

Two things follow, and they are not optional:

- **Never share that spreadsheet** with anyone who should not see every
  password. Not "view only" either — view is enough to read them.
- **Nobody should reuse a password they use anywhere else.** Make them
  up yourself: two Croatian words and a number is plenty.

The app itself never sends a password anywhere: the script is asked
"is this pair right" and answers yes or no. There is no way to get the
list of passwords out of the web app, only out of the spreadsheet.

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
| `bad token` | the script and Streamlit disagree | check `SHEETS_TOKEN` is spelled identically in both |
| `this session only` under the engine buttons | the deployed script is older than the repo | Deploy → Manage deployments → pencil → New version |
| `no users tab yet` | `setupUsers` has not been run, or is not deployed | run it from the TTT-LLL menu; deploy first if needed |
| someone cannot log in | password mismatch | check for a trailing space in the cell |
| nobody can log in | the sheet is unreachable | use your `APP_PASSWORDS` password with the username box empty |
| the app is completely white | usually a stale module after a deploy | Streamlit Cloud → Manage app → **Reboot**. A rerun is not enough. |
| `check engine` shows ✗ | a provider refused | the row names which one and why; usually an expired key |

**One habit worth having:** after any deploy, open the live app once and
log in. Local green is not production green.

---

## PART 6 — Could this all be in the app instead?

Some of it already is: assigning engines per person, and setting the
global engine, are both in the amber gear.

Adding, deleting and re-passwording people is **not** in the app yet. It
could be — the script would need `user_add`, `user_delete` and
`user_password` endpoints beside the ones that already exist, and a
panel behind the same admin gate.

It was not built yet for a reason worth understanding: **a bug in a user
panel can lock everybody out, including you.** The sheet cannot do that.
When it is built, the rule from §1 will still apply — `APP_PASSWORDS`
stays as the door that always opens.

Ask for it when you want it. For now, a spreadsheet you edit by hand is
not the crude version; it is the version that cannot break.
