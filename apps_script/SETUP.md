# Connecting the usage sheet — step by step

Ten minutes, once. After this it runs by itself and you never touch it
again.

## What you end up with

A Google Sheet that fills itself in as people use the app.

- **Summary** — one line per user: how many uses, audio minutes,
  characters, hours in the app, first and last use.
- **Daily** — per user, per day: how many uses and how much. This is the
  "how hard are they hammering it" view.
- **u_user1**, **u_user2**, **u_user3**, … — one tab per person,
  every single use as its own row, so you can build any calculation you
  like yourself.

## What it never contains

No text. Ever. Not what was transcribed, not what was translated, not
what was read. The signal the app sends has no field for content, so none
can be sent even by mistake. What it does send: which user, what kind of
action, how big (seconds of audio, or number of characters), which engine,
and when.

---

## Step 1 — make the sheet

1. Go to **sheets.new** (that makes a fresh empty spreadsheet).
2. Name it something like **TTT-LLL usage**.

## Step 2 — paste the script

1. In that sheet: menu **Extensions → Apps Script**.
2. Delete whatever is in the editor (usually a stub called `myFunction`).
3. Paste the whole of **Code.gs** in.
4. Near the top, change this line:

   ```js
   var SHARED_TOKEN = 'CHANGE_ME_to_a_long_random_string';
   ```

   Put any long random string between the quotes — 20+ characters, letters
   and numbers, no spaces. This is what stops strangers writing into your
   sheet. Keep it; you need it again in step 5.

5. Check the user list on the next line is right:

   ```js
   var KNOWN_USERS = ['user1', 'user2', 'user3'];
   ```

   Anyone missing still gets a tab automatically the first time they use
   the app — this list just means you do not stare at an empty sheet on
   day one.

6. Save (the disk icon, or Ctrl+S).

## Step 3 — run setup once

1. In the toolbar, make sure the function dropdown says **setup**.
2. Press **Run**.
3. Google asks for permission the first time. Choose your account, then
   **Advanced → Go to (project name)** → **Allow**. This is Google warning
   you about your own script; it is expected.
4. You get a popup saying it is ready, and the tabs appear in the sheet.

## Step 4 — publish it

1. Top right: **Deploy → New deployment**.
2. Click the gear next to "Select type" and choose **Web app**.
3. Set:
   - **Execute as**: *Me*
   - **Who has access**: **Anyone**
4. Press **Deploy**, approve if asked.
5. Copy the **Web app URL**. It looks like
   `https://script.google.com/macros/s/AKfy...long.../exec`

> "Anyone" sounds alarming but is correct here: the app has to be able to
> reach it without a Google login. The `SHARED_TOKEN` is what actually
> protects it — without the token the script refuses to write anything.

**Check it works:** paste that URL into a browser. You should see
something like `{"ok":true,"service":"TTT-LLL logging","users":3}`.

## Step 5 — tell the app

In Streamlit: **Manage app → Settings → Secrets**, and add these two lines
to what is already there:

```toml
SHEETS_URL = "https://script.google.com/macros/s/AKfy...long.../exec"
SHEETS_TOKEN = "the same long random string from step 2"
```

Save. The app restarts by itself. Done.

---

## Afterwards

- New user added to the app's passwords? They get a tab automatically the
  first time they use it. Then in the sheet use the **TTT-LLL → Refresh
  statistics** menu so Summary and Daily pick them up.
- Changed the script? You must **Deploy → Manage deployments → edit
  (pencil) → New version → Deploy**, or your change is not live. This is
  the single most common thing to trip over.
- Want a different calculation? The per-user tabs hold the raw rows, so
  build whatever you like beside them. Nothing in the app depends on the
  Summary or Daily tabs, so you cannot break logging by editing them.

## If nothing arrives

1. Open the web app URL in a browser — if that fails, the deployment is
   wrong, not the app.
2. Check the token matches exactly in both places.
3. In the Apps Script editor, **Executions** (left sidebar) shows every
   incoming call and any error.
4. The app is built so a logging failure is silent and harmless — it will
   keep working perfectly with the sheet disconnected. So "the app is
   fine but the sheet is empty" points at steps 4 or 5, never at the app.
