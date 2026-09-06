# BUILD THE CLEAN `secrets.toml` — brief for a Claude Code session

**You are running on Marko's Mac, in a folder he has prepared. Read this
file, then `docs/SECRETS_AUDIT.md` beside it, then do the job below.**

Written 6.9.2026 from the running app at v245, by auditing what the code
actually reads — not from memory and not from the old example file,
which is stale in three places.

---

## 1. THE JOB, IN ONE SENTENCE

In the folder you are started in there is a text file holding Marko's
API keys. **Turn it into one clean `secrets.toml` for Streamlit
Community Cloud, containing every name this version of the app reads
and nothing else.**

He will paste the result into **Settings → Secrets** on
`share.streamlit.io`. It never goes in the repository.

---

## 2. BEFORE YOU TOUCH ANYTHING

**The file in that folder is a secret file.** Everything in
`MANTRA_MANIFEST/modules/secrets.md` applies from your first command:

- **Do not print it.** Not to show its structure, not "redacted". A
  redaction built from known key shapes fails OPEN on a format it has
  not seen, and that is how a real key reached a transcript on
  20.8.2026. To understand the shape, print things DERIVED from it:
  `wc -l`, line lengths, four-character prefixes.
- **Never commit it.** Check `.gitignore` before your first `git add`,
  not after. And note the trap that bit this repo on 6.9.2026: the
  pattern `*_secrets*` is wide enough to silently swallow a FILE YOU
  MEANT TO KEEP, and `git add -A` says nothing when it ignores
  something.
- **Use by reference, never by value.** The key goes from the file into
  the process and nowhere else.
- **Scan the diff before every push:**
  `git diff --cached | grep -nE '(sk_|gsk_|AQ\.|ghp_|sk-ant-)[A-Za-z0-9_-]{20,}'`

**His Gemini keys begin `AQ.` and are 53 characters.** The older `AIza`
form is retired and no detector in this project looks for it. An
extractor that assumed the old prefix sliced three characters off all
twenty-one keys and made every one look invalid.

---

## 3. YOU DO NOT NEED TO WRITE A PARSER

One exists, it is ported from the Android Key Tester, and it was run
against these exact two files on 6.9.2026 with no false positives:

    ttt/keyparse.py        in markoboskoauroville/MAHA_TRANSCRIBE_STREAMLIT

    from ttt import keyparse as KP
    found = KP.extract(open("keys.txt").read())
    KP.by_provider(found)        # {"google": [...], "hume": [...]}

It carries three things you would otherwise have to rediscover:

- **whole-token matching**, so a tracking parameter inside a URL is not
  taken as a key (a naive splitter has genuinely tried to authenticate
  with the word *cafeteria*),
- **the label above each key is kept**, which is what turns "key 7 of
  21 is unpaid" into "kalabhumi is unpaid",
- **Hume is read from LABELS, not shape.** Its export is

      <account name>
      API key
      <api key>
      Secret key
      <secret key>

  and both halves are plain alphanumeric, so nothing about their shape
  says Hume. Parsed generically, seventeen accounts become thirty-four
  keys, half of them secrets that authenticate nothing.

---

## 4. WHAT THE CLEAN FILE MUST CONTAIN

**Audited against the code at v245.** Anything not on this list is not
read by this version and must not be carried forward.

### 4a. Who can get in — at least one of these, or nobody can log in

    ADMIN_USER1  = "..."      # ADMIN_USER without a digit also works
    STUDIO_USER1 = "..."
    FREE_USER1   = "..."      # FREE_USER2, FREE_USER3 ... any number

The pattern the code scans is `^(ADMIN|STUDIO|FREE)_USER\d*$`, so
adding `FREE_USER7` needs no code change.

    APP_PASSWORDS = ["...", "..."]   # the older shared-password door
    ADMIN_USER    = "..."            # which of them is the owner

`APP_PASSWORD` singular is still read for an older setup. Prefer the
list.

### 4b. The keys

    GOOGLE_API_KEYS     = ["AQ....", ...]   # free tier: TEN TTS
                                            # requests per account per
                                            # day, which is why it is a
                                            # list and not a key
    GROQ_API_KEYS       = ["gsk_...", ...]
    GROQ_API_KEY        = "gsk_..."         # older single form, still read
    ASSEMBLYAI_API_KEYS = ["...", ...]      # studio speech in
    SPEECHIFY_API_KEYS  = ["sk_...", ...]   # studio speech out
    ANTHROPIC_API_KEY   = "sk-ant-..."      # studio text

    [[HUME_ACCOUNTS]]                       # ONE BLOCK PER ACCOUNT
    name   = "kalabhumi"
    key    = "..."
    secret = "..."

    HUME_API_KEYS = ["...", ...]            # older form, no secrets

**`HUME_ACCOUNTS` is an array of tables and every entry needs all three
fields.** A key with no secret still does TTS, but only the pair proves
the account.

**QUOTAS ARE PER PROJECT, NOT PER KEY.** Two Google keys minted inside
one Cloud project share one budget — twenty keys can be one project's
allowance wearing twenty hats. One key per account.

### 4c. Options

    TABS_OFF        = ["vr", "looks"]    # tabs hidden from everybody
    REMEMBER_SECRET = "..."              # signs the remember-me cookie

`DRIVE_SECRET` is still accepted as an alias for `REMEMBER_SECRET` and
for nothing else now. If he has one, carry its VALUE over under the new
name rather than keeping both.

### 4d. DELETE THESE — they are read by nothing

    SHEETS_URL        the Apps Script deployment. The spreadsheet and
    SHEETS_TOKEN      ttt/accounts.py were removed in v237; grep the
                      repository and you will find no reader at all.
    DRIVE_SECRET      only as a duplicate of REMEMBER_SECRET, see above.

**They are still in `.streamlit/secrets.toml.example`,** which is stale.
Do not use that file as your list; use this section. Fixing the example
is a fair second task and a separate commit.

`AUTH_URL`, `AUTH_LOGIN_TOKEN` and `AUTH_ADMIN_TOKEN` ARE still read by
live functions. Keep them if he has them, drop them if he does not; they
are optional, not dead.

---

## 4e. THERE IS A SCRIPT. RUN IT RATHER THAN WRITING ONE.

    python3 tools/keys_to_toml.py ~/that-folder --dry-run
    python3 tools/keys_to_toml.py ~/that-folder -o secrets.toml

It reads every text file in the folder, finds the keys by shape and by
label, **tests every one against its provider**, and writes a
`secrets.toml` holding only the ones that can do work. Run `--dry-run`
first: it tests and reports and writes nothing.

**Baba, 6.9.2026: "He needs to test all the keys in the folder and then
not to write in secrets one which is not working."** That is what it
does, and the interesting part is what "not working" turns out to mean:

    working    -> written
    busy       -> WRITTEN. A throttled key is a healthy key having a
                  busy minute. Dropping it because the test caught it
                  mid-limit throws away an account that would have
                  worked a second later.
    unknown    -> RETRIED three times, and written even if it stays
                  unknown. This is not caution: on 6.9.2026 three of
                  twenty-one Google keys answered 503 on the first pass
                  and ALL THREE worked on the retry. One of them was
                  kalabhumi, the account every live test that day ran
                  through. A tool that dropped unknowns would have
                  deleted three live accounts.
    no credit  -> dropped, BY NAME, never silently. The account is alive
                  and needs paying, not deleting. `--keep-empty` puts
                  them back.
    refused    -> never written. 401/403 is the provider rejecting the
                  credential.

**MEASURED against Marko's two real files, 6.9.2026:** 38 credentials
found, 34 written, 4 left out — `community` refused, `caffeteria` and
`marko croatia` out of credit, `av.live.vmix`'s Hume pair refused. The
written file parsed as TOML with 18 Google keys and 16 Hume pairs.

It writes mode 0600 and **proves the file parses before you hand it
over**. It never prints a key.

**It does not invent the access lines** — `ADMIN_USER1`, `FREE_USER1`,
`APP_PASSWORDS`. No tool can know those. It writes them as commented
placeholders at the top and you fill them in with him.

---

## 5. THE ORDER TO WORK IN

0. **Run the script first** (§4e) and read its report. Everything below
   is what to do around it, and what to do if it finds nothing.
1. **Read the folder without printing it.** Count lines, lengths and
   prefixes. Say how many keys of each provider you believe are there.
2. **Extract with `KP.extract`.** Report counts and ACCOUNT NAMES only —
   never key material. A name is what makes a verdict actionable.
3. **Ask him which he wants carried over** if any provider has more keys
   than he expects, and tell him what the app last measured:
   on 6.9.2026, of twenty-one Google accounts, **eighteen working, two
   out of credit (`caffeteria`, `marko croatia`), one refused
   (`community`, 401)**; and of seventeen Hume pairs, **`av.live.vmix`
   answered 401 Invalid ApiKey — that pair is dead.**
4. **Write `secrets.toml`** with §4 as the specification.
5. **Verify it PARSES before he pastes it:**

       python3 -c "import tomllib;d=tomllib.load(open('secrets.toml','rb'));\
       print({k:(len(v) if isinstance(v,list) else 'set') for k,v in d.items()})"

   A block that Streamlit rejects fails at import with a message it
   REDACTS, so he would see a broken app and no reason.
6. **Count what you wrote, out loud**, per provider. "0 keys found" is
   the answer somebody needs; a silent success is not.
7. **Tell him what you did NOT carry over, by name**, and why.

---

## 6. THE TWO THINGS MOST LIKELY TO GO WRONG

**A pasted-but-unfilled template counts as keys.** The app now refuses
values containing `paste_your_` / `paste_the_`, but a half-filled block
is still the commonest way to end up with an engine that reports ready
and fails on its first real request.

**Streamlit Cloud caches imported modules.** After he pastes new
secrets, if anything behaves as though the old values are still in
force, the answer is **Manage app → Reboot app**, not a code change.
That cost an outage on 6.9.2026 and the app now says so itself.

---

## 7. WHAT TO READ IF YOU NEED MORE

    MANTRA_MANIFEST/modules/secrets.md     handling, arrival to shredding
    MANTRA_MANIFEST/modules/keyring.md     §2c-§2h, what a probe proves
    MANTRA_MANIFEST/modules/gemini-speech.md   the ten-a-day limit
    this repo, docs/SECRETS_AUDIT.md       the name-by-name audit
    this repo, ttt/keyparse.py             the parser, with its reasons

**Do not read the whole manifest.** It is large and most of it has
nothing to do with this job.
