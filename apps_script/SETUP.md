# The Apps Script — setup

**There is ONE file: `Code.gs`.** Not three, not a base plus additions.
Earlier there were three and they had to be pasted together in the right
order with two edits made by hand; pasting them wrongly is exactly what
left the Drive functions unreachable and scored 15 out of 40 on the
tests. One file cannot be assembled wrongly.

If you ever see a second `.gs` in this folder, something has gone wrong.
Everything belongs in `Code.gs`.

---

## What you fill in

All of it is in ONE block near the top of `Code.gs`, between two thick
boxes ending with `END OF THE PART YOU EDIT`. Nothing below that block
ever needs touching.

| in `Code.gs` | in Streamlit secrets | what it is |
|---|---|---|
| `SHEETS_TOKEN` | `SHEETS_TOKEN` | must match exactly |
| `DRIVE_SECRET` | `DRIVE_SECRET` | must match, and differ from the token |
| `DRIVE_ROOT_ID` | — | your Drive folder id, audio storage only |
| `KNOWN_USERS` | — | who gets a tab on day one |
| `KEY_PROVIDERS` | — | which `k_` key tabs get made |

Make the two secrets yourself. In Terminal:

```
openssl rand -base64 33
```

Run it twice, once for each. **Never paste a secret into a chat, an
email or a screenshot** — a message cannot be unsent. If one ever lands
in a message, replace it rather than hope.

There are **no API keys in `Code.gs`**. Groq, Speechify, Anthropic and
AssemblyAI keys live in the `k_` tabs of the spreadsheet.

---

# clasp — editing the script on your Mac

Without this, updating the script means copying the whole file and
pasting it into a browser. With it, you edit the file on your Mac and
one command sends it to Google.

**This is new, so here is every step. Nothing is assumed.**

## Once, to set it up

**Step 1 — install it.** In Terminal:

```
npm install -g @google/clasp
```

If `npm` is not found, install Node first: `brew install node`.

**Step 2 — let it into your Google account.**

```
clasp login
```

A browser window opens. Sign in with the account that owns the
spreadsheet, and allow it. It saves permission in your home folder and
you will not be asked again.

**Step 3 — turn on the Apps Script API. ONE TIME, and it is easy to
miss.** Open:

https://script.google.com/home/usersettings

Switch **Google Apps Script API** to **ON**. Without this every push
fails with a permission error that does not explain itself.

**Step 4 — find your script id.** Open the spreadsheet, then
Extensions → Apps Script. Look at the address:

```
https://script.google.com/.../projects/THIS_LONG_PART/edit
```

`THIS_LONG_PART` is the script id.

**Step 5 — make your `.clasp.json`.** In the repo folder:

```
cp apps_script/.clasp.json.example .clasp.json
```

Open `.clasp.json` and paste your script id where it says
`PASTE_YOUR_SCRIPT_ID_HERE`. It is gitignored, because it is yours.

## Every time after that

Edit `apps_script/Code.gs` in your editor, then:

```
clasp push
```

That is the whole thing. It replaces the script in Google with your file.

To have it push by itself on every save:

```
clasp push --watch
```

Leave it running in a Terminal window while you work.

## THE STEP CLASP DOES NOT DO

**`clasp push` does not deploy.** It updates the code; the running web
app keeps answering with the old version until you publish a new one.

In the Apps Script editor: **Deploy → Manage deployments → the pencil →
Version: New version → Deploy.**

Skip it and it looks exactly as though your changes did nothing. This is
the single most common way to lose an hour here.

## After the first push

Run these once each, from the Apps Script editor's Run menu:

1. `setup()` — user tabs, Summary, Daily
2. `setupConfig()` — the settings tab and the `k_` key tabs
3. `setupDrive()` — the recordings tab. It checks your folder id and
   refuses if your two secrets are the same. Skip it if you are not
   using audio storage yet.

Then paste `SHEETS_URL` (the `/exec` address), `SHEETS_TOKEN` and
`DRIVE_SECRET` into Streamlit secrets.

## If something goes wrong

| what you see | what it means |
|---|---|
| `User has not enabled the Apps Script API` | Step 3 |
| `bad token` from the app | `SHEETS_TOKEN` differs between `Code.gs` and Streamlit secrets |
| `bad signature` on audio | `DRIVE_SECRET` differs between the two |
| changes seem to do nothing | you pushed but did not deploy a New version |
| `setupDrive()` refuses | your two secrets are identical, or the folder id is wrong |

## Pulling, if you edit in the browser

If you change something in Google's editor, bring it back before you
edit locally, or your next push overwrites it:

```
clasp pull
```

Then commit it. **The file in this repo and the script in Google should
never disagree** — that is the whole point of using clasp.
