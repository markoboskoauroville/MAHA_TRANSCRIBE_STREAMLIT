# NEXT-CHAT PROMPT — migrate MAHA_TRANSCRIBE_STREAMLIT off Streamlit Cloud

*Paste everything below into a fresh chat. It is written for a reader with no memory of any previous
conversation. Written 3. 9. 2026.*

---

## 1. WHO AND WHAT

I am Baba (Marko Boško), a video editor at Nova TV Zagreb. GitHub account
**`markoboskoauroville`**.

The app is **`MAHA_TRANSCRIBE_STREAMLIT`** — public repo, branch `main`, Python, Streamlit, about
**35,000 lines**. It is a transcription and reading tool used by my family, not a toy. It currently
runs on **Streamlit Community Cloud**, which puts it to sleep and wakes it slowly, and it stores
things in Google Drive.

**Read `MANTRA_MANIFEST/START_HERE.md` first** (private repo, same account), then this app's own
`HANDOVER.md` and `DELIVERY_RECORD.md`. The manifest is the governing specification for everything
I build — four tests, delivery gate, secrets in a vault, versioning, design language.

## 2. WHAT I WANT

Move it to hosting that is **free, always on, and not dependent on Google**, and replace the Google
Drive storage with something I own.

Concretely:

- The app answers immediately, always. No sleeping, no 50-second wake.
- User settings, and a **history of transcriptions**, persist between sessions.
- A user can **delete their own history**, and delete must really delete.
- A free address, ideally a real domain later.
- **Streamlit Cloud is kept alive during the migration.** Fork or branch — the family's working copy
  must not break while this is built. Only switch when the new one is proven.

## 3. THE ANSWER TO THE QUESTION I ALREADY ASKED — DO NOT REDO THIS RESEARCH

I asked whether this could run on Cloudflare. It was researched properly on 3. 9. 2026 and the
answer is **no**. Do not re-investigate it; spend the time on the build.

**Cloudflare Workers and Pages cannot run this.** They execute JavaScript/WASM in isolates with
10 ms CPU per request and no persistent process. This app calls **ffmpeg 60 times**, declares
**8 custom Streamlit components** with server-side session state, and uses `st.session_state` 748
times in `app.py` alone. Streamlit is a long-lived Python server holding a WebSocket. There is no
version of it that runs on Workers.

**Cloudflare Containers could run the Docker image but there is no free tier.** It requires the
Workers Paid plan at $5/month, and the included allowance is **375 vCPU-minutes per month** against
the 43,200 minutes in a month. Always-on would cost roughly **$50–60/month**.

**The chosen target is an Oracle Cloud Always Free ARM VM.** It is the only 2026 free tier that runs
real workloads: **2 OCPU / 12 GB RAM, always on, free forever, no sleep at all** — so the cold-start
problem disappears rather than being minimised. ffmpeg, Streamlit and the custom components all run
unchanged.

Three things to expect, none of them blockers:

- Oracle **halved** this allowance in June 2026, from 4 OCPU/24 GB to 2 OCPU/12 GB. Any guide quoting
  four cores is out of date. 12 GB is ample here.
- Capacity in popular regions sells out. Expect "out of capacity" errors and retry, possibly in a
  different region.
- Signup asks for a card even though nothing is charged.

**Rejected, with the reason, so nobody re-litigates:** Google Cloud `e2-micro` is the other
always-free box but has **1 GB RAM**, too tight for ffmpeg plus audio buffers, and it reintroduces
the Google dependency I am trying to remove. Fly.io and Render either sleep or no longer have a real
free tier. Hugging Face Spaces sleeps after 48 hours.

## 4. STORAGE — AND A CORRECTION TO MY OWN IDEA

I originally wanted user settings and history written as text files into a GitHub repo. **Do not
build that as the primary store.** It is a commit per write, a 5,000/hour rate limit, and concurrent
writes conflict.

**On a VM there is a filesystem. Use SQLite on local disk as the live store** — instant, no limits,
no conflicts — and push a periodic backup to a **private** repo or object storage. GitHub becomes
durable backup, not the database.

**Transcription history is personal data.** Whatever holds it must be private, and "delete my
history" has to actually remove the rows, not leave them recoverable in git history. If backups go
to git, deletion has to be handled deliberately rather than by writing a new commit that leaves the
old blob in place.

## 5. WHAT THE APP ACTUALLY NEEDS FROM A HOST

Measured from the repository, not assumed:

| Need | Detail |
|---|---|
| `ffmpeg` | `packages.txt` requests it; called 60 times, `ffprobe` 5 times |
| Long-lived process | Streamlit server plus WebSocket; 748 `st.session_state` uses |
| Custom components | 8 `declare_component` sites across 6 `*_frontend` folders |
| Python deps | small and portable: `streamlit>=1.61,<2`, `groq`, `edge-tts` |
| Providers | groq, anthropic, assemblyai, hume, speechify, edge — all HTTP, all fine |
| Writable disk | `ttt/audio.py`, `ttt/speech.py`, `ttt/drive.py` all write files at runtime |

**The Streamlit ceiling is load-bearing.** `requirements.txt` pins `streamlit<2.0.0` with a long
comment explaining why: `st.components.v1.html` was announced for removal after 2026-06-01, that date
has passed, and there are six call sites plus six `declare_component` calls. **Do not raise or remove
that pin** without moving the components to `st.iframe` first. Removing it takes the app down for a
family who changed nothing.

## 6. THE WORK, IN ORDER, WITH THE REASON FOR THE ORDER

1. **Fork or branch first.** Streamlit Cloud keeps serving from `main` untouched for the whole
   migration. Nothing below may break the live copy.
2. **Get the Oracle VM.** Do this early — capacity errors may cost days, and everything else is
   pointless if the box never appears. ARM Ampere, Ubuntu, 2 OCPU / 12 GB.
3. **Dockerfile.** `python:3.12-slim`, `apt install ffmpeg`, requirements, the app. Build it on ARM,
   because an x86 image will not run and finding that out late wastes a session.
4. **Storage layer.** SQLite schema for users, settings and transcription history, behind a small
   module so the call sites do not care what is underneath. Include the delete path from the start —
   retrofitting deletion is how it ends up incomplete.
5. **Prove it locally**, then on the VM, against the four tests.
6. **HTTPS and a domain.** Caddy in front for automatic certificates.
7. **Only then** point the family at it, and only after it has been up untouched for a few days.

## 7. WHAT IS OPEN AND UNDECIDED

- **Whether Google Drive comes out entirely or stays as an optional export.** `ttt/drive.py` exists
  and works; I have not decided whether to delete it or keep it behind a switch.
- **What the domain will be.** Nothing chosen. A free `*.pages.dev` cannot front the app, since it
  serves static files only — the VM needs its own DNS.
- **Whether multi-user auth stays as it is.** There is a password door in `app.py` and a three-tier
  scheme; I have not decided if that survives the move.
- **Whether I want a VM-creator assistant script** the way `cf-publish.sh` scripts Cloudflare. I
  raised it and did not decide. If Oracle's setup turns out to be many manual steps, it is probably
  worth it.

## 8. WHAT HAS NEVER BEEN TESTED — CARRY THIS FORWARD

- The app has **never run on ARM.** Everything to date is x86 Streamlit Cloud.
- The custom components have **never been served from anything but Streamlit Cloud.**
- **No load test, ever.** Nobody knows what two simultaneous transcriptions do to memory.
- **Nothing has ever been restored from a backup.** A backup that has not been restored is a guess.
- iOS and Safari are **out of scope** by my decision. Do not spend time there.

## 9. WORKING RULES

- **Secrets:** keys arrive as `.txt` uploads. Extract by shape into `~/.secret`, never open the file,
  never print a value, counts only. The vault does not survive a session — rebuild it from the
  uploads folder each time. See `MANTRA_MANIFEST/modules/secrets.md`.
- **Cloudflare specifically:** `MANTRA_MANIFEST/apis/cloudflare.md`, and
  `scripts/cf-publish.sh` publishes any folder to `pages.dev` in one command. My account id and
  token are already stored as encrypted GitHub Actions secrets on `NOVA_TV_777`.
- **Four tests before anything ships**, including the sabotage test. `modules/four-tests.md`.
- **Verify, do not assert.** Measure it, print the number, and if a check passes suspect the check.
  `modules/checking-the-checks.md`.
- **Build, verify, push, wait for CI, report with the link.**
- **Update the handoff per step, not at the end of the session.**

## 10. HOW I WORK

I am usually **on a phone**, dictating. Expect voice-to-text mangling — treat "Noah TV" as "Nova TV".
Screenshots are how I show you things; a pasted screenshot with no words means *look at this and fix
it*. Give me the exact taps when I am in someone else's dashboard, because I cannot see what you can.
Croatian for anything my colleagues or family read, English to me.

**Tell me when I am wrong.** The GitHub-as-database idea in §4 was mine and it was worse than the
alternative; saying so saved me building it.
