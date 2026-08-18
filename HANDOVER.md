# TTT-LLL — HANDOVER

Live: https://ttt-lll.streamlit.app
Repo: https://github.com/markoboskoauroville/MAHA_TRANSCRIBE_STREAMLIT
Entrypoint: `app.py` · Version: see `APP_VERSION` in `app.py`

**TTT** = Talk To Type (speech → text). **LLL** = Look, Listen, Learn
(text → speech, seen and heard at once).

---

## 0. HARD RULES — read before touching anything

These are Baba's standing instructions. Breaking one has already cost real
work at least once, which is why each is written down here rather than
remembered.

**1. Multiple repos with the same app name -> ASK, never guess.**
Baba has several repos that look like the same application at different
ages. Picking by name, by guess, or by "looks most complete" is forbidden.
If more than one candidate exists, stop and ask which is authoritative
BEFORE reading or porting anything from it. This rule exists because MA
Reader was ported from `mareader` — an old, superseded port — when the real
one was `ma-reader-thermux`. Known case, settled: **MA Reader means
`markoboskoauroville/ma-reader-thermux`, and nothing else.** Its
`1md_ma_reader_handover_[ENG].md` is the source of truth; read that first.

**2. MODULARITY IS THE ARCHITECTURE — everything, always.**
Baba's standing philosophy for every app built in this line of work:
*modularity, flexibility, adaptability. Anything can go anywhere.* Build
modules, then wire them together; never a monolith with features welded
into it.

What this means concretely here:
- Anything that talks to an outside service is a **provider** behind a
  common interface, registered in `ttt/providers/`. Adding Anthropic,
  Deepgram, ElevenLabs later is dropping in one file and registering it —
  never editing the tabs, the reader, or the settings screen.
- A capability (speech-to-text, text-to-speech, translation) is asked for
  by name from the registry. Calling code must never import a specific
  vendor or branch on `if provider == "groq"`. If a tab knows a vendor's
  name, that's a bug.
- Shared machinery lives in its own module and is used by everyone: the
  key ring, the storage layer, the audio/ffmpeg helpers, the reading loop,
  the UI atoms. None of them may import a specific provider.
- The reading loop takes a *function* that makes audio, not an engine
  name. That's why word-level highlighting worked the moment Speechify
  arrived without touching the loop.
- Every module must be liftable into another app with its imports and
  nothing else. If a module needs `app.py` to work, it isn't a module.

Caveat that has already bitten once (see incident 1): Streamlit keeps
imported modules in `sys.modules` while re-running the entrypoint, so a
warm process can hold an old module against new calling code. Changing a
module's function signature therefore needs a full restart, not a rerun.
Keep signatures additive with defaults wherever possible.

**3. The handover is part of the work, not paperwork after it.**
Workflow on every change, in order: build -> test -> push -> THEN update
this file. It must always describe the newest feature. If this file
disagrees with the code, the code is right and this file is a bug.

**4. TEST EVERY FEATURE FOUR TIMES.**
Superseded the earlier "three times" on 18.8.2026. Four passes, and each
must be able to FAIL while the other three PASS — before writing one, ask
what could be true that would make this test pass and the feature still be
broken. (1) the mechanism alone, outside the app, no network or UI;
(2) inside the running app with real data and real dependencies, looking
for a number an outside party confirms; (3) the ugly cases — empty,
enormous, malformed, hostile, twice, out of order, absent, and NEVER
ANSWERS; (4) the upgrade from the version before. After each passes, break
it on purpose and confirm it goes red: a test never seen fail is a rumour,
and roughly half of all failures are in the test, not the code. If two
tests cannot fail independently, that is three tests and a duplicate.
  1. the logic alone, in plain Python, no Streamlit, no network
  2. the running app in a real browser at phone width
  3. the awkward case — reload, empty input, a dead key, a second user
A test that has never failed has not been shown to work. When something
passes on the first try, assume the test is wrong before assuming the code
is right; several "bugs" in this project turned out to be broken
assertions (a hex colour that the browser serialises as rgb(), an expander
whose contents are not in the DOM until it is opened, a timeout shorter
than the audio it was waiting for).

**5. API KEYS: Marko lends, Claude shreds — at the END of the session.**
Amended 18.8.2026. The original wording was "every time", and it was read
as shredding after the first test and asking again, which wasted a whole
session in re-uploads. The agreement now: keys are uploaded once, held for
the WHOLE of that conversation, and die with the sandbox when it ends —
which is a real end, not a promise, because the sandbox does not persist
between conversations. Never print them, always redact them from command
output, scan every staged diff for key material before committing, and say
plainly that the scan came back clean. Baba rotates them when the app is
finished. What has NOT changed: they never enter the repo, never enter the
chat, and are never assumed to survive into a new conversation.
The working agreement, stated by Baba and to be honoured exactly:
*"Marko is giving you the keys when you need it for testing and you throw
them into fire."*
  * Ask when a real key would genuinely prove something a fake one cannot.
  * Use it only for that test.
  * Never write a key into a file, a commit, a log, or the deployed
    secrets. Never print one in full — mask to first 4 characters.
  * Shred immediately afterwards: delete every artifact the test created
    (server-side key stores under the temp dir, scratch files), then grep
    the working tree and the staged diff to prove it is clean, and say so.
  * Assume no key is still lying around from a previous turn. If one is
    needed again, ask again.

**6. THIS IS AN ACCESSIBILITY APP. Build like it.**
Baba: *"this app will be used by old people who don't see well... it is
actually accessibility app for people who cannot see, who cannot read.
App is doing the service to this planet."*

That makes accessibility the product, not a setting. Anything that breaks
at a large text size is a bug of the same seriousness as losing someone's
recording. The standards, not taste, decide what counts as done —
`ttt/a11y.py` implements and names each one:

  1.4.4  Resize text        usable at 200%. We go to 250%, because 200 is
                            a floor, not a target.
  1.4.10 Reflow             no two-direction scrolling at 320 CSS px.
                            Nothing goes in a fixed-width box, ever.
  1.4.12 Text spacing       line height, letter and paragraph spacing
                            scale WITH the text. Enlarged text on cramped
                            leading is harder to read than small text —
                            the usual failure of a naive zoom.
  2.5.5  Target size        44x44 CSS px for anything pressable. WCAG
                            2.2's AA floor of 24px is NOT enough for a
                            shaking hand; use the AAA figure.
  1.4.6  Contrast           7:1. Near-black and gold already clear it.

Rules that follow from this and must not be undone:
  * `rem`, never `px`, for anything textual. A fixed pixel size ignores
    the reader's own OS and browser font setting — the first thing a
    person with low vision will already have turned up.
  * The text-size control sits ABOVE each reading surface, never only in
    Settings. Someone who cannot read the screen must not have to
    navigate a menu they cannot read in order to make it readable.
  * Wrapping uses `overflow-wrap: break-word`, not `word-break`, so
    ordinary prose keeps its shape and only genuinely oversized words are
    broken.
  * Respect `prefers-reduced-motion`, and keep a visible focus ring.

KNOWN LIMITATION, measured not guessed: `hyphens: auto` does nothing
useful here because Streamlit sets `<html lang="en">` and the browser
therefore applies English hyphenation to Croatian words and declines to
break them. Word wrapping falls back to `overflow-wrap: break-word`,
which still prevents overflow — a very long word breaks without a hyphen
rather than pushing the layout sideways. Fixing it properly needs the
document's `lang` to follow the interface language, which Streamlit does
not expose. Revisit if it ever does.

**7. Aesthetics are a requirement, not a finishing touch.**
Think like a visual designer, every time. Concretely and permanently: a
button is the size of its text, never the width of the page. Small pills,
arranged in tidy rows that wrap. Streamlit's default (`use_container_width`
plus columns that stack below ~640px) turns every small choice into a
column of full-width slabs on a phone — that is a bug, not a default to
accept. The CSS at the top of `app.py` overrides both; keep it. Main
actions (Read, Translate, Correct) may stay wide; choosers (languages,
voices, engines) must not.

## 1. INCIDENT: stale-module crashes (THREE times — 17.8.2026) — NOW FIXED AT THE CAUSE

**Fixed properly in v33.** app.py drops every `ttt.*` module (plus
`talk_engine` and `help_text`) from `sys.modules` whenever the build stamp
changes, BEFORE importing them. The stamp is `APP_VERSION`, which is
bumped on every change anyway, so the two cannot drift. One re-import per
deploy, nothing per rerun.

Guarding individual call sites did NOT scale: the login screen was
hardened after the second occurrence, and the third crash simply landed
somewhere else (`copybtn.cp_html`). Remove the cause, not the symptom.

Verified by simulating it: deleted a function from a loaded module, showed
a plain re-import keeps the stale copy (the crash), then showed the guard
produces a fresh one — and that an unchanged stamp does NOT reload.

**It happened again, and that is the important part.** The first time was
`ls_bridge` (below). The second was `help_text.MORE_LABEL`: the login
screen was rewritten to use a new constant, both files were pushed
together and correct on GitHub, every local test passed — and the
deployed app died with `AttributeError` on the login screen, locking
everyone out of the entire app.

Same mechanism both times, and the reason local testing CANNOT catch it:
a local run is always a cold start, so the module is always fresh. Only a
warm production process runs new `app.py` against an old module.

**The rule that follows, now enforced in code:** anything `app.py` reads
from a local module must survive that module being one version behind.
Never a bare `module.CONSTANT` on a path that runs before login — an
AttributeError there is total, because nobody can get past it to reach
anything else. Login-screen access now goes through `_ht()`, which falls
back through: module absent -> table absent -> language absent ->
Croatian absent, and returns something usable at every step. Verified by
deleting `MORE_LABEL` outright and confirming the app still loads and
logs in.

**Recovery when it does happen:** reboot the app from Manage app. A
rerun is not enough; the process must actually restart.

---

## 1a. The original incident (ls_bridge)

**Symptom.** Every page load died with
`TypeError: This app has encountered an error`, traceback pointing at
`_ls = ls_bridge(stamp=st.session_state...)`. The app was completely
unusable — no transcribing, no reading.

**Root cause.** A backwards-incompatible signature change to a local module,
across two commits:

```
f594f68   def ls_bridge(write_key=None, write_value=None, key=None)      # deployed
0f6a6d6   def ls_bridge(writes=None, removes=None, stamp=0, key=...)     # new
```

Streamlit re-executes `app.py` on every rerun, but **imported modules stay
cached in `sys.modules` for the life of the process.** After the redeploy the
warm process was running the NEW `app.py` against the OLD `ls_bridge` module.
The new caller passed `stamp=`, which the old function had never heard of:

```
TypeError: ls_bridge() got an unexpected keyword argument 'stamp'
```

Reproduced exactly before fixing. This is version skew inside one process.

**Why it was fatal rather than annoying.** The call sat at module scope,
before the password gate, with no error handling. So a failure in *settings
persistence* — a pure convenience — killed *transcription and reading*, the
entire product. That is the worse half of the bug.

**Fix, three layers:**

1. **Removed the skew surface.** `ls_bridge.py` is deleted. The bridge is
   declared inside `app.py`, which is re-executed every run and therefore can
   never be stale relative to its caller. Small glue lives with its caller.
2. **Made it non-fatal.** `ls_sync()` cannot raise. If the component is
   missing, broken, or unavailable, it returns `None` and the app runs
   normally without remembering settings.
3. **Made the data modules defensive.** Help text goes through `safe_text()`,
   sentence splitting is wrapped. Missing documentation or an engine hiccup
   shows a message; it never white-screens the app.

**Verified by deliberately breaking things:** a booby-trapped stale
`ls_bridge.py` planted on `PYTHONPATH` (app loads clean), and the entire
component frontend directory deleted (app fully usable, just without
persistence).

### Rules that follow from this — do not break them

- **Never change a local module's function signature incompatibly.** Add new
  parameters with defaults, keep old ones accepted. A warm process may be
  running old modules against new callers.
- **Prefer keeping small glue in the entrypoint** over a module that can go
  out of step for the sake of tidiness.
- **A non-essential feature must never be able to crash the app.** Storage,
  analytics, help text, telemetry: all wrapped, all degradable. Ask of every
  new dependency: "if this fails at 4am, does the app still transcribe?"
- **Never blanket-`except` while debugging.** During this fix a
  `try/except Exception` around `declare_component` hid the real cause and
  cost a diagnostic cycle. Log the exception while investigating; silence it
  only once the failure mode is understood and deliberate.
- **After any redeploy, load the live URL once before declaring done.**
  Local green is not production green.

---

## 2. WHAT THE APP IS

Two halves under one password.

**Transcribe (TTT).** `st.audio_input(sample_rate=48000)` records at high
quality → `ffmpeg` downsamples to 16kHz mono FLAC, which is Groq's own
documented preprocessing target → Groq Whisper.
`whisper-large-v3-turbo` is the automatic first pass; **Correct** re-runs the
same audio through `whisper-large-v3` (slower, more accurate).
**Read this** jumps to the Talk tab, picks a voice matching the language just
transcribed, and starts reading.

**Talk (LLL).** Paste text, press Read. Each sentence is synthesized live by
`edge-tts` straight to memory and played with `st.audio(autoplay=True)`.
The sentence being spoken is highlighted in gold, and repeated alone in a
large **subtitle box** below (the NaturalReader idea).

**Translate.** A third tab, added for the other two users — they like
languages. Two boxes and pill-button language switches, From and Croatian
first / English / Italian / German / French, a swap (⇄) that exchanges both
the languages and the text, and a **Translate** button that calls Groq
(`openai/gpt-oss-120b`, see §3). Under the result, the same **Read** +
subtitle-box mechanism as the Talk tab, reused via the shared
`read_sentences_live()` — not a second copy of it — reading in a neural
voice picked for whichever language was translated into.

---

## 3. DESIGN DECISIONS WORTH KNOWING

**No audio cache, no word timing.** An earlier version ported the full
per-sentence mp3 cache and waveform-alignment engine from
`ma-reader-thermux` (pinned commit `be376fd`) — `refine_tokens`,
`measure_silence`, two-band envelope, DP anchor matching. It worked, and it
was deleted on purpose: Streamlit Cloud has no durable disk and cannot serve
per-sentence audio routes, and word-level highlight drifts. Sentence-level
highlight does not drift. `talk_engine.py` went 586 lines → ~100.
**Do not reintroduce the cache.**

**The tab bar is a `segmented_control`, not `st.tabs`.** `st.tabs` cannot be
driven from Python: its `session_state` value updates but the visible
selection does not follow (verified in a real browser). **Read this** must be
able to move the user to the Talk tab, so the tab bar has to be a widget
Python actually controls. Do not "tidy" this back into `st.tabs`.

**localStorage needs a real custom component.** `st.components.v1.html()` is
sandboxed without `allow-top-navigation`, so a script inside it cannot
navigate to carry a value back (`Unsafe attempt to initiate navigation`). A
`declare_component` frontend talks over `postMessage`, which the sandbox
permits. That is why `ls_bridge_frontend/index.html` exists — one file,
no npm, no build step.

**Settings persistence, three layers, in priority order:**
1. `st.session_state` — this session.
2. Browser localStorage — survives restarts, per browser. The real one.
3. A server-side JSON file in `tempfile.gettempdir()` — same-instance
   convenience only. Streamlit Cloud does not guarantee disk across
   restarts; never treat this as durable.

**Identity is the password.** Whichever password matched names the settings
profile, so each person gets their own preferences. **Remember me** stores a
salted SHA-256 of the password, never the password itself, per browser.
**Forget me** in Settings undoes it (needed for a shared phone).

**Translation model: `openai/gpt-oss-120b`, chosen by testing, not by
reputation.** Compared against `llama-3.3-70b-versatile`, `gpt-oss-20b`, and
`qwen/qwen3.6-27b` on real Croatian/English/Italian/German/French sentences
with an idiom and a formal register in them. `gpt-oss-120b` handled both
correctly (kept "Poštovani" as "Cher Monsieur", not just "Monsieur"; used
the natural idiom, not a literal one). **`qwen3.6-27b` is disqualified**:
despite an explicit "reply with ONLY the translation" instruction, it wrapped
its answer in a full visible `<think>...</think>` block — sometimes several
paragraphs — which is both wrong output and wasted latency. `gpt-oss-20b`'s
smaller size showed: idioms translated literally instead of naturally
("piove come da un tubo" instead of "piove a dirotto"). If Groq adds a
stronger model later, retest with this same method before switching —
parameter count alone is not the signal, output was.

**Five languages, European only, this exact order:** Croatian, English,
Italian, German, French. Baba's explicit instruction — not Indian, African,
Chinese, or Philippine languages, on purpose. Croatian first everywhere,
matching the rest of the app.

**New neural voices, Translate tab only, one per language, no picker.**
Italian/German/French use the exact same voices already hand-picked and
vetted in Baba's own `ma-reader-thermux` app (its `LANGS` table) — reused
rather than guessed fresh, so the quality bar matches Sonia/Ryan/Gabrijela/
Srecko: `it-IT-ElsaNeural`, `de-DE-KatjaNeural`, `fr-FR-DeniseNeural`. These
live in `talk_engine.VOICES` alongside the original four (now also holding
Diego/Conrad/Henri as the unused male half of each pair, kept for
completeness) but the **Talk tab's own picker is untouched** —
`VOICES_BY_LANG` / `VOICE_TO_VKEY` in `app.py` still only ever show the
original four. Don't let Talk's UI grow past that by pointing it at the
fuller `VOICES` table.

**The login screen's language pills are not decorative — the checkbox
label moves with them.** `LOGIN_LABELS` in `help_text.py` gives Password /
Remember me / Wrong password in all five languages, keyed by
`session_state["login_lang"]`, and `check_password()` renders the actual
widgets from that dict — never hardcode a label there again, or the guide
text (which says e.g. "tick the box marked X") will describe a box that
says something else. `LOGIN_GUIDE` itself was translated once via this same
Groq model, then proofread by asking the model to critique its own output
as a strict native speaker (caught a German word-order slip: "So die App
steht" → "So steht die App"), then hand-verified against the actual UI
layout before being baked in as static text — the login screen must never
depend on a live API call to render.

---

## 4. FILES

```
app.py                      entrypoint: gate, settings, three tabs, LS bridge
talk_engine.py              sentence splitting + live edge-tts synthesis
                             (VOICES: 4 Talk voices + 6 Translate-tab extras)
help_text.py                HELP (hr/en) + LOGIN_GUIDE + LOGIN_LABELS (all 5)
ls_bridge_frontend/         one-file vanilla-JS custom component
requirements.txt            streamlit, groq, edge-tts
packages.txt                ffmpeg (apt, needed by Transcribe)
```

Secrets live ONLY in Streamlit Cloud → Settings → Secrets. Never committed:

```toml
APP_PASSWORDS = ["...", "..."]
GROQ_API_KEYS = ["gsk_...", "gsk_..."]
```

Any number of passwords and any number of Groq keys work; keys rotate on
failure.

---

## 5. CONVENTIONS

- Near-black surfaces, gold `#e0a340`, cyan `#4dd6e8` for contrast.
  **No blur, no backdrop-filter, no dimming overlay, anywhere.**
- Version appears in Settings only, never on the main screen.
- Bump `APP_VERSION` on every change, with the account suffix, e.g. `v4 (a)`.
- Interface is Croatian by default; **Croatian always listed before English**,
  in voices, language toggles, everywhere.
- The whole interface vocabulary lives in `STRINGS` in `app.py`, so switching
  language is instant with no reload. Any new user-facing string goes there —
  never hardcode English into the UI.

---

## 6. TESTING

Local run needs `.streamlit/secrets.toml` (gitignored):

```bash
pip install -r requirements.txt
streamlit run app.py
```

`streamlit.testing.v1.AppTest` covers logic. Note it mishandles `format_func`
radios and has no `.get` on `session_state` — use `at.session_state["k"]`.
Anything involving the browser (localStorage, tab switching, autoplay,
subtitles) must be tested in a real headless browser; AppTest cannot see it.

**Before shipping, deliberately break things and confirm graceful
degradation:** delete `ls_bridge_frontend/`, plant a stale module, cut the
network. The app must survive all three.

---

## 7. PROVIDER KEYS — Speechify (and the pattern for anything after it)

Bring-your-own-key, ported from Baba's `MA_READER_SPEECHIFY` and
`Key_Tester` repos, storage adapted since this app cannot rely on local
disk (see §incident 1 above). Each provider's ring is its own blob under
`maha_keys_{user}`, same session_state -> localStorage -> server-file path
as `SETTINGS_LS_KEY`, parallel to it rather than merged in — keys are
bigger and more sensitive than the small settings blob.

**Generic ring** (`new_ring`, `ring_pick`, `ring_import`, `mask_key`,
`persist_keys`/`load_keys`, `render_key_list`) is provider-agnostic and
meant to be reused as-is for the next provider. State machine per key:
`new -> ok -> dead` on 401/402/403 (buried, never retried), `-> cool` on
429 (rests 120s, comes back on its own), network/5xx changes nothing.

**`ring_import` is line-aware**, matching Key_Tester's KeyParser exactly:
processes the raw text line by line, and whichever key-shaped tokens it
finds get the file line *directly above* them (verbatim, blank/absent ->
none) as a `label` — a username or account note, not the key. Prefixed
tokens (`sk_`, `sws_`, etc. for Speechify) are taken first and exactly; if
none carry a known prefix, falls back to any long mixed letter+digit run
(AssemblyAI's 32-hex keys have no distinctive prefix, so they only ever
hit the fallback path — expected, not a bug).

**Settings UI**: each key gets its own row — icon + label + first 4
characters + its own Test button, not one global test-all. This was a
deliberate Baba correction mid-build; don't regress it to a single button.

**Speechify model, corrected 17.8.2026** — `sp_model_for(voice_id)` picks
`simba-3.2` for the curated `_32` voices and `simba-english` for everything
else. The older `SPEECHIFY_API_GUIDE.md` recommends 3.2 generally; MA
Reader v3's handover records that 3.2 answers HTTP 400 for any voice whose
id does not end `_32`, which is almost the whole catalogue. Re-verified
live against the API here: voice `alec` + `simba-3.2` -> 400 "the selected
voice is not available for simba-3.2", the same voice + `simba-english` ->
success. Baba's newer notes beat the older guide; when two of his documents
disagree, check the dates and trust the newer, then verify against the API.

**Speechify specifics** (`sp_call`, `sp_request`, `sp_synthesize`): base
URL `https://api.speechify.ai`, `Authorization: Bearer <key>` on every
call. `sp_synthesize` returns `(audio_bytes, seconds, marks)` — marks is a
flattened, time-sorted list of `{start, end, start_time, end_time}` from
`speech_marks` (start/end are *character offsets into the text sent*,
start_time/end_time in seconds). Confirmed against a real synthesis call,
not just the docs: root is a `type: sentence` chunk, `chunks` holds
`type: word` entries, punctuation-only entries are skipped.

**Word-level highlight**: `read_sentences_live`'s `synth_fn(text)` may
return a 2-tuple `(audio, seconds)` or a 3-tuple with marks. Marks present
-> step the highlight through each word's own measured window, in both
the main document view and the subtitle box (`_highlight_span`,
`_render_page`, `_subtitle` all take optional `start`/`end` char bounds).
Marks absent (Edge, or Speechify without marks for some reason) -> the
original whole-sentence highlight. **Do not build this for Edge** — its
own word-boundary events run on a separate clock and drift out of sync
over the course of a sentence; that's specifically why sentence-level was
the rule before Speechify's *exact, not inferred* offsets made word-level
worth doing at all. The distinction is the data quality, not a preference.

**Talk tab engine toggle**: Edge/Speechify, shown once any key isn't dead.
Swaps the *entire* voice picker (4 named Edge voices, or the 8 curated
Speechify voices) — never shows both at once. Persisted like every other
setting (`voice_engine`, `sp_voice` are in `SETTINGS_KEYS` now).

**Tested with real keys once, then shredded** (17.8.2026) — Baba supplied
real Speechify and AssemblyAI keys explicitly for a one-time test, to be
deleted after. Confirmed real API shapes match this document, confirmed
`ring_import` on two genuinely messy real key files, confirmed the full
browser flow (import -> per-key test -> engine switch -> word highlight
visibly advancing in both views), then deleted every trace: the
server-side settings file the browser test created, one scratch file.
Nothing was committed, nothing added to deployed secrets. If real keys are
needed again, ask — don't assume any are still lying around.



---

## 8. THE MODULE MAP (read this before adding anything)

`app.py` is the entrypoint and should stay thin: page setup, the auth
gate, the tab chain, and wiring. Everything reusable lives in `ttt/`.

    ttt/keyring.py     multi-key ring, vendor-agnostic. rotate(ring,
                       attempt) is the ONE place rotation policy lives:
                       dead buries permanently, cool rests 120s and
                       revives itself, soft blames nobody and stops rather
                       than burning the ring. import_keys() is line-aware —
                       the file line above a key becomes its label — and
                       NEVER drops a key for its shape.
    ttt/store.py       per-user storage over a namespace: session ->
                       localStorage -> server file. Imports no Streamlit,
                       so it is testable without it. Cloud disk is not
                       durable; localStorage is the real layer.
    ttt/audio.py       ffmpeg + the 3-tier big-file strategy. Takes a
                       transcribe_fn, so it serves any STT. Returns its
                       temp paths; call cleanup() with them.
    ttt/reader.py      the reading loop. Takes synth(text) and a frame
                       callback, draws nothing, touches no session_state.
    ttt/read_tab.py    archive + progress line for the Read tab.
    ttt/providers/     base.py = the three capability shapes and one HTTP
                       helper; one file per vendor; __init__.py = registry.

### Adding a provider

One file in `ttt/providers/`, one line in `REGISTRY`. Nothing else. The
Settings screen renders key sections from `keyed_providers()`, engine
pickers list `with_capability("tts")` / `("stt")`, and the reader takes
whatever `synth` it is handed. If you find yourself editing a tab to add a
vendor, stop — the registry is not being used properly.

**Never** import a vendor module outside `ttt/providers/`, and never
branch on `if provider == "groq"` in calling code.

### Ring access

`get_ring(provider_id)` is the only way to obtain a ring. It always
attaches to the stored dict. The old pattern
`load_keys().get(x) or new_ring()` silently detached and lost every state
change; do not reintroduce it. Call `save_rings()` after anything that
could change a key's state — including after a read, since keys die
mid-read.

## 9. AUDIT, 17.8.2026

Bugs found by reading rather than by anything failing visibly:

  * **Detached rings** (5 sites) — state changes thrown away whenever a
    provider had no keys yet. Fixed structurally via `get_ring()`.
  * **Dead keys resurrecting** — the read loop never persisted the ring,
    so a key buried mid-session returned on reload and wasted a request
    every time. Fixed with `save_rings()` at the end of every read.
  * **Temp file leak** — a transcoded FLAC and a chunk directory per large
    upload, never removed, on long-lived shared containers. `ttt/audio.py`
    now returns its temps and `cleanup()` takes them.
  * **Translate was a bare `else:`** — which is why no tab could follow it.
    Now an explicit `elif`.
  * **Speechify model hardcoded** to simba-3.2, which 400s for any voice
    not ending `_32`. Now per-voice via `model_for()`.

## 10. WHAT MA READER HAS THAT THIS DOES NOT

Recorded so nobody re-litigates it from scratch. See the top of
`ttt/read_tab.py` for the full reasoning.

    media / lock-screen keys      needs an Android privileged shell
    true full screen              Streamlit owns its own chrome; a
                                  half-hidden UI would break the rule
                                  rather than meet it
    clipboard auto-read           the API can hang forever; a textarea is
                                  the honest equivalent
    word pause inside silence     needs a per-clip ffmpeg silence map;
                                  possible later, not faked now
    per-sentence offline export   possible (zip of mp3 + json), not built
    waveform re-pinning for Edge  MA Reader decodes every Edge clip and
                                  re-pins each word to the real waveform.
                                  Until that is ported, Edge returns no
                                  marks and highlights by sentence, which
                                  is honest and never wrong.

---

## 11. PLANNED: bulletproof transcription (spec, not yet built)

Baba's requirement, recorded 17.8.2026 to be built when its turn comes.
**Nothing is ever lost, and no limit is ever hit.** Not the 25MB request
limit, not a rate limit, not a five-hour sitting, not a twenty-two hour
upload. Groq is free, so the answer is never "too big" — it is *feed it
spoon by spoon*.

### The two cases

**Live recording, hours long.** Someone sits and talks. The app must slice
continuously while they are still speaking, transcribe each slice in the
background, and keep recording throughout. Slices are cut well below the
limit, never at it. The transcript grows in front of them as they talk.
Stopping is just the last slice — there is no big upload at the end and
nothing to wait for.

**Uploads, arbitrarily long.** A 22-hour file is fine. Same machinery:
split, feed, stitch. The existing `ttt/audio.py` tiers already do the
splitting; what is missing is doing it *incrementally and visibly* rather
than as one blocking job.

### Key rotation is the engine

Five Groq keys. When one says "you talk too much" (429), it goes to sleep
and the next one takes over immediately — the rested key rejoins later on
its own. `ttt/keyring.py` already implements exactly this policy
(`rotate()`, `cool` for 120s, `dead` only for auth failures); the work is
routing Groq's own app-owned keys through that ring instead of the simple
loop in `ttt/providers/groq.py`, so a rate limit becomes a hand-off rather
than an error.

Chunks must be retried across keys, not abandoned: a chunk that fails on
key 3 tries key 4 before it is allowed to leave a gap. Today the gap marker
appears too eagerly for that reason.

### What the person sees — this part matters as much as the engine

Not a spinner. The work, happening:

- how much audio is still waiting ("14 min left to transcribe"), counting
  down as portions complete
- each portion appearing in the transcript the moment it lands, in order
- which portion is in flight, and that another key took over when it did
- an estimate of time remaining, honest, based on how fast portions have
  actually been coming back

Baba's words: *"everything happening in front of their eyes automatically,
and they are watching the miracle."* The visible progress is a feature, not
instrumentation.

### THE STEPS (one at a time, each build-then-test-three-times)

    1. Groq's own keys through the key ring          DONE (v20)
       so a 429 is a hand-off, not an error
    2. Per-chunk retry across keys before any gap    DONE (v21)
    3. Silence-aware cut points                      <- NEXT
    4. Portions land visibly, with a countdown
    5. Resume after a reload
    6. Slice while still recording

Step 1 is the engine of all the rest: until Groq rotates properly, a long
job dies at the first rate limit no matter how well it is chunked.

### Rules for whoever builds it

- **Never drop audio.** A failed chunk retries on other keys first; only
  after every live key has refused does it leave a marked gap, and the gap
  must say which minutes are missing so it can be re-run.
- **Never block the recorder.** Transcription runs behind the recording;
  slicing must not pause capture.
- **Order is sacred.** Portions land out of order; the transcript must
  still read in sequence.
- **Cut on silence where possible.** Splitting mid-word costs accuracy at
  every seam. ffmpeg can find a quiet moment near the target boundary.
- **Resume after a reload.** A long session must survive the browser
  reloading; completed portions belong in storage, not only in memory.
- **Test with genuinely long audio**, not a 75-second clip. The bugs live
  in hour three.

---

## 12. PLANNED: one key, one entry — merging sources and deleting keys

Recorded 17.8.2026, to build when its turn comes.

### Two doors, one key ring

A key can arrive two ways:

  * **added** — file picker or paste in Settings, stored in the user's own
    key ring (localStorage).
  * **secret** — `APP_PASSWORDS` / `GROQ_API_KEYS` / any future
    `*_API_KEYS` in Streamlit Cloud secrets, owned by the deployment.

The same key is often in BOTH. It must appear as ONE entry, never two.
Deduplicate on the SHA-256 fingerprint that `keyring.fingerprint()` already
computes — never on the raw string, so the comparison never needs the key
in the clear. When a key exists in both places, keep one entry and record
both origins on it (`origins: ["secret", "added"]`), because that changes
what deleting it can mean.

Rotation, testing and counting all operate on the merged ring, so a key
present twice can never be tried twice, rested twice, or double-counted.

### Deleting a key — what is actually possible

**Answer to Baba's question:** Streamlit secrets are READ-ONLY at runtime.
`st.secrets` is loaded from the Cloud dashboard (or a local
`.streamlit/secrets.toml`) and there is no API to write or delete an entry
from inside a running app. So:

  * **added key -> real deletion.** Remove it from the ring and it is
    gone from the browser store. Nothing left behind.
  * **secret key -> suppression only.** The app can put its fingerprint on
    an ignore list so it is skipped by rotation, by testing and by the
    counts — it behaves as if absent. But it still exists in secrets, and
    it comes back the moment the ignore list is cleared. Truly removing it
    means editing it in the Streamlit dashboard: *Manage app -> Settings ->
    Secrets*, delete the line, save. The app restarts itself.
  * **key in both -> deleting removes the added copy and suppresses the
    secret one**, and the UI must say exactly that rather than implying it
    vanished everywhere.

### Rules for the UI

  * Show each key ONCE, with a small mark for where it came from
    (secret / added / both).
  * Delete is honest about the outcome: "removed" for added keys,
    "ignored — still in secrets, remove it there to delete it properly"
    for secrets keys, with the dashboard path spelled out.
  * The ignore list is per deployment, not per user: one person ignoring
    a shared app key must not silently change it for everyone else.
    Store it beside the app's own settings, not in a user's localStorage.
  * An ignored key stays visible and un-ignorable with one press, or it
    becomes a key nobody can find again.

---

## 13. THE SPOON LIST (agreed with Baba, eat one at a time)

Each is built alone, tested three ways, pushed, then the handover is
updated. Nothing is started before the one before it is finished.

### Unlimited transcription (the elephant, §11)
    1. Groq keys through the ring                    DONE v20
    2. Per-chunk retry before any gap                DONE v21
    3. Silence-aware cut points                      NEXT
    4. Portions land visibly, with a countdown
    5. Resume after a reload
    6. Slice while still recording

### Accessibility (hard rule 6)
    A1. Text size control on every surface           DONE v22
    A2. Copy pills with live state                DONE v24
        (paste is V2 — a different mechanism,
         see §14; it is NOT the same button)
    A3. Hover, press and disabled states          DONE v23

### Vision (read what is in a picture)
    V1. Groq vision: picture -> text             DONE v32
    V2. Paste a screenshot straight into the app.
        RESEARCH DONE, see §14 — the route is the
        native paste EVENT, not the clipboard API.

### Login and permissions
    L1. QUIET LOGIN SCREEN                        DONE v25
        First screen shows ONE
        box — password — plus Remember me, and
        nothing else. Baba: "there is so much text,
        people get confused. What do I need to
        read? Do I need to enter password?"
        Under the box, a single triangle. Pressing
        it unfolds the whole thing: welcome, the
        TTT-LLL explanation, the five languages,
        the home-screen guide. A quiet Easter egg —
        whoever can see it may open it; whoever
        cannot simply sees one box and knows
        exactly what to do.
        The triangle must be a real 44px target and
        must say what it is to a screen reader; the
        folded content must still be reachable by
        keyboard.

    L2. ADMIN CONTROLS WHAT OTHERS SEE.
        the owner (whoever ADMIN_USER names) is the owner. He gets
        a panel listing every other user with
        switches for what each of them may see:
        their own API keys, the patch bay, the
        model pickers, the voice catalogue.
        Everything already exists — this is only
        showing and hiding. Default for a normal
        user is everything hidden: they get a clean
        app that just works, and a capability
        appears only when Baba turns it on, e.g.
        because they paid for their own key and
        want better quality.

        THE ONE HARD PART, and it must be solved
        first: WHERE THE SWITCHES LIVE. Per-user
        settings currently live in that user's own
        browser (localStorage), which Baba's
        browser cannot write to. A shared, durable
        store is required or the panel cannot work
        at all. Streamlit Cloud disk is not durable
        and secrets are read-only at runtime, so
        neither is an option.
        The natural answer is the store we already
        have: the Apps Script web app behind the
        usage sheet (§ apps_script/). Add a tab
        holding one row per user with their
        permission flags, plus a doGet that returns
        them; the app reads it at login and Baba's
        panel writes it back. Same shared secret,
        no new service, and Baba can also just edit
        the sheet by hand — which he will like.
        Alternative if that is ever unwanted: a
        small JSON in a private GitHub repo via the
        API. Decide before building.

### Keys (§12)
    K1. Merge the two key sources into one ring
        entry by fingerprint.
    K2. Delete a key: real removal for added keys,
        suppression for secrets keys, and the UI
        says which happened.


---

## 14. CLIPBOARD: what is actually possible, measured

Probed against a real Streamlit component iframe rather than assumed,
because this decides whether a button can exist at all.

**The component iframe's Permissions Policy** (read off the live
`allow` attribute) includes `clipboard-write` and does NOT include
`clipboard-read`.

    COPY   navigator.clipboard.writeText  -> WORKS.
           clipboard-write is granted to the iframe, so a copy button
           driven by a user's press is fine.

    PASTE  navigator.clipboard.readText   -> BLOCKED in a real browser.
           clipboard-read is absent from the allow list, so Permissions
           Policy refuses it however the user answers a prompt. Headless
           Chromium CAN be told to grant it, and it then succeeds — that
           is an automation artifact and must not be mistaken for proof.
           Do not ship a paste button built on readText.

    PASTE  the native `paste` EVENT       -> WORKS, with NO permission.
           Verified with permissions explicitly withheld: the event
           fires, `clipboardData` carries `text/plain`, AND a pasted
           screenshot arrives as a real image File (`file:image/png`,
           correct byte length). This is the route for V2 — the person
           presses Ctrl+V (or long-press → Paste), the browser hands the
           data over because THEY initiated it, and no permission is
           involved.

So: copy via the clipboard API, paste via the paste event. Anything else
is a button that looks like it works and does not.

---

## 15. PLANNED: the sheet as two-way storage (not just a log)

Baba's idea, recorded 17.8.2026. The Apps Script web app already accepts
writes; adding a `doGet` that RETURNS rows makes the same sheet a small
per-user database. That is worth doing because it is the only durable,
shared store this deployment has — Cloud disk is not durable, secrets are
read-only, and localStorage is trapped in one browser.

**First use, and the one to build first: custom prompts.** GRAMMAR and
RE-SHAPE currently run fixed instructions from `ttt/transform.py`. A
`settings` tab in the sheet, one row per user, would let each person have
their own wording — and Baba can edit it by hand in the sheet, which is
the real appeal.

    user        key              value
    user1       prompt_grammar   Ispravi pravopis, ne diraj stil.
    user2       prompt_reshape   Skrati na natuknice.

**Then, as wanted:** saved texts (the Read archive, which is
browser-only today and dies with a cleared browser), per-user voice and
engine choices, and anything else that should follow a person between
devices.

### Rules for whoever builds it

  * **The sheet is a convenience, never a dependency.** If it is
    unreachable the app must behave exactly as it does today, with the
    built-in defaults. Same rule as the usage log: read with a short
    timeout, swallow every error.
  * **Cache per session.** A read on every rerun would mean several
    fetches a second.
  * **Still no content in the log tabs.** Saved texts, if added, go in
    their own tab that the owner can see is private data, not mixed into
    usage rows.
  * **Write through the same shared token.** No second auth path.
  * **A prompt from the sheet is untrusted text.** It goes into an LLM
    instruction, so keep the fencing that `transform.build_prompt`
    already applies to the material, and cap the length.

---

## 16. NEXT: the cassette deck, and fixing Edge's drift

Baba's brief of 18.8.2026, recorded in full because it is a session's work
and was NOT attempted in one pass. Doing it badly would have been worse
than leaving it clearly written down.

The role model is his own TTT Mini keyboard: dark ground, soft-cornered
keys, one accent, everything on a grid, nothing decorative.

### D1. The transport deck
Replace `st.audio_input` with a custom component: four square buttons in
one row — **record, pause, stop, eject** — in the manner of a 1980s
Technics cassette deck. Eject opens the file picker. Under them a THIN
oscilloscope line, a few pixels tall, that dances while signal is
present, and a running timer.

This needs a real recorder component (MediaRecorder + AnalyserNode in
the iframe, posting the blob back). `st.audio_input` cannot be restyled
into this; do not try.

### D2. The recording archive
Every recording in a session is kept, as pasted text already is. A small
square with a dropdown holding ONE text action: **retranscribe**. The
reason is concrete — someone picks the wrong language, and the audio must
not be lost with the mistake.

### D3. One interface across phases
**A rule, not a preference:** the interface must not change shape between
idle, recording and reading. The player is always present, greyed when
inactive. Reading does not rearrange the screen; it only fills in what
was already there.

Reading mode: the same box, text enlarged, no jumping. When stopped, the
whole text returns at normal size.

### D4. Word highlighting that does not shake — AND FIXING THE TIMINGS
Edge returns no word marks, and the proportional guess in
`speech.fill_missing_times` drifts badly over a long block. Baba's
solution is right and should be built:

  * ~~Analyse the AMPLITUDE ENVELOPE to find the silences between
    words.~~ **DISPROVED 18.8.2026, and this is why a year of tuning went
    nowhere.** Measured against Speechify's exact marks: 236 of 238
    inter-word intervals are EXACTLY ZERO SECONDS. Speech does not stop
    between words — 'the elements' has no gap in it, the tongue simply
    moves. Envelope detection finds stop-consonant closures instead: ten
    "pauses" in a sentence that had four. There is nothing there to find.
  * ~~The gaps ARE the word boundaries.~~ They are not. What IS wrong
    with a proportional guess is PAUSES at punctuation being spread
    across every word, so the error accumulates down the line. Weighting
    by syllables instead of characters changes nothing at all: 232 ms
    against 231 ms.
  * **SOLVED INSTEAD by Whisper word timestamps** — see §20 and
    docs/WORD_TIMINGS.md. Median 47 ms against 119 ms.
  * Then highlight by CHANGING THE WORD'S COLOUR, not by wrapping it in
    a box — a background or bold changes the text's metrics and the line
    reflows, which is the shaking. Colour alone keeps every glyph exactly
    where it was.
  * Verify by measuring: capture the bounding box of a fixed word before
    and during highlighting; if x or y moves by even a pixel, the
    approach is wrong.

### D6. Server-side audio for fast retranscribe (Baba, 18.8.2026)

Upload anything — any audio container, or a VIDEO, since `-map 0:a`
lifts the audio track out and discards the pictures. Convert once to
Whisper's native 16 kHz mono, LEVELLED (done in v48, see LOUDNORM in
ttt/audio.py), and keep that file for the session so a retranscribe is
server-to-server and near-instant instead of a re-upload.

The conversion and levelling are done. What is NOT done is the KEEPING:
Streamlit Cloud's disk is not durable and files must not outlive the
session. Needs a decision on where — the same shared store as §15, or a
short-lived bucket — plus a cleanup path so nothing lingers.

### D7. Audio storage moves to Google Drive (Baba, 18.8.2026)

Once the rest is proven, converted audio goes to GOOGLE DRIVE through the
same Apps Script web app as §15 — Baba will supply the folder. Drive
keeps each user's audio until he chooses to delete it, which solves the
problem Cloud disk cannot: durability without a new service or a second
auth path.

Then retranscribe is server-to-server: the levelled 16 kHz file is
already there, so changing the language costs one API call and no upload.

Rules when building it: the same shared token, no audio in the usage
tabs, a per-user folder, and the app must still work unchanged when Drive
is unreachable — storage is a convenience, never a dependency, exactly
like the usage log.

### D5. Two settings, done (v47)
Grey ◐ = how the app looks, for everyone. Amber ⚙ = engines and keys,
owner only. Colour carries the distinction so neither needs a word.

---

## 17. THE SHEET AND THE DRIVE AS THE APP'S BACKEND

Baba's design, 18.8.2026. The Google Sheet stops being a log and becomes
the app's dashboard and configuration; the Drive folder becomes its audio
store. Both are reached through the SAME Apps Script web app that already
exists, which is what makes this cheap.

### THE PERMISSION QUESTION, ANSWERED

Baba asked: *"if I authenticate all these links, will the user have right
to use it?"*

**The users never authenticate, and never need a Google account.** An
Apps Script web app deployed as **"Execute as: Me"** and **"Who has
access: Anyone"** runs every request under BABA'S OWN Google identity.
The Streamlit app calls a URL with the shared token; the script does the
Drive and Sheet work as him and returns a result. Emina's browser never
touches Google at all.

Three consequences worth being clear about:

  * The shared token IS the security. Anyone with the URL and the token
    can write. Keep it in Streamlit secrets, never in the repo.
  * Files land in HIS Drive and count against HIS quota. That is the
    intent — it is his app.
  * "Anyone" means anyone with the URL, not anyone signed in. It does
    NOT make the Drive folder public; the folder can stay private,
    because the script is what reaches it.

### THE AUDIO ROUND TRIP

    upload → Streamlit → ffmpeg (levelled, 16 kHz mono)
           → Apps Script → Drive /<user>/<id>.flac
           → Whisper reads it back through the script

Retranscribe then costs no upload: the prepared file is already there, so
changing the language is one call. The script creates a per-user folder on
first write — `DriveApp.getFolderById(ROOT).createFolder(user)` if it does
not exist.

### THE SHEET AS CONFIGURATION

Tabs beyond the existing per-user and Summary/Daily ones:

  * **settings** — one row per setting, `scope | key | value`, where
    scope is `global` or a username. TRUE/FALSE for switches, text for
    prompts. A user row wins over the global row; if the user has none,
    global applies. First two settings to carry: `prompt_grammar` and
    `prompt_reshape`, so the AI wording is editable by hand without a
    deploy.
  * **assemblyai**, **anthropic**, one per provider — keys that are NOT
    in Streamlit secrets are read from here as a fallback. This is what
    lets a key be added without a redeploy.

### RULES FOR WHOEVER BUILDS IT

  * **Never a dependency.** If the sheet or Drive is unreachable the app
    behaves exactly as it does today, on built-in defaults. Short
    timeout, swallow everything, same as the usage log.
  * **Cache per session.** A settings read on every rerun is several
    fetches a second.
  * **A prompt from the sheet is untrusted text.** It goes into an LLM
    instruction, so keep transform.py's existing fencing and cap the
    length.
  * **Keys read from the sheet are still keys.** They go into the same
    ring, get the same rotation and the same shredding, and are never
    written to a browser.
  * **No text in the sheet, still.** Settings and keys, never content.


---

## 18. AUDIT AGAINST THE SOURCE — 18.8.2026

Checked file by file rather than assumed. The handover had drifted from
the code in three ways, all now recorded truthfully rather than tidied
away.

### The real file map

    app.py                  entrypoint, tabs, all UI
    help_text.py            HELP + login strings (hr/en)
    talk_engine.py          Edge TTS: synth_sentence, sentences_of

    ttt/a11y.py             text scale, reading CSS, WCAG rules
    ttt/audio.py            ffmpeg: loudnorm + 16k mono, tiering, retry
    ttt/copybtn.py          copy component (circle and word forms)
    ttt/gate.py             login throttle ladder
    ttt/keyring.py          key ring + thread-safe rotate()
    ttt/read_tab.py         archive (add/remove/save/load pieces)
    ttt/routing.py          patch bay model (hidden in UI, still used)
    ttt/sheet.py            settings + spare keys from the Google Sheet
    ttt/speech.py           blocks, per-part build, sentence marks
    ttt/store.py            3-layer storage (local_only for content)
    ttt/theme.py            design tokens, schemes, fonts, all CSS
    ttt/transform.py        AI text transforms
    ttt/usage.py            usage logging to the sheet
    ttt/vision.py           Groq vision: picture -> text
    ttt/providers/          base, edge, speechify, assemblyai, groq, anthropic

    paste_frontend/         paste component (NOT used - paste removed v49)
    player_frontend/        part player (audio + subtitle + ended signal)
    ls_bridge_frontend/     localStorage bridge
    apps_script/Code.gs             deployed script (logging + config)
    apps_script/config_addition.gs  the config half, already pasted in
    apps_script/SETUP.md            setup guide

### DEAD CODE, found by AST, not by reading

Fourteen top-level functions in app.py are never referenced. They are
leftovers from features that were replaced rather than removed, and
several are still DESCRIBED in this document as if live:

    split_into_chunks   mask_key         ring_import       provider_models
    handles_big_files   cp_row           copy_pill         sp_test_one
    aai_test_one        aai_transcribe   forget_me         do_correct
    read_this           read_sentences_live

`ttt/reader.py` is likewise no longer imported — the reading path is
speech.py plus player_frontend now. `paste_frontend/` is unused since
paste was removed.

**Do not delete these blind.** Some are genuinely obsolete (cp_row,
copy_pill, read_sentences_live, read_this — all replaced by cmd_row and
the block player). Others may be wanted again: do_correct is
retranscribe-with-a-better-model, which is close to the retranscribe
feature still queued, and sp_test_one/aai_test_one are the per-key Test
buttons that the simplified Settings stopped rendering.

### What this means for the next session

Clearing this is worth one focused pass with the four tests applied, not
a casual tidy — `read_sentences_live` and `do_correct` in particular
touch paths that still half-exist.

---

## 19. DRIVE AUDIO STORAGE (v52)

Half-built: the Apps Script and the client are written and tested against
each other; NOTHING IS WIRED INTO app.py YET, and none of it has run
against the real deployment. Test 2 is outstanding and needs Baba to
redeploy first.

### What was measured, not assumed

**The platform refuses a request body over 52,428,800 bytes (50 MiB).**
Exactly. 50 MiB passes; one KB more is HTTP 400. Measured against the live
deployment by posting padded bodies with a DELIBERATELY WRONG token, so
the script rejected them before writing anything and the sheet was never
touched. Stable across three repeats.

**16-bit 16 kHz FLAC runs ~17,200 bytes per second of speech.** So one
10-minute part is ~10.3 MB, ~13.7 MB as base64 — about a quarter of the
envelope. That is why parts are 10 minutes, and why there is no chunked
upload protocol: one part is one request, in both directions, and there is
no reassembly logic to get wrong.

**Groq CAN fetch audio from a `url` instead of an upload**, and it is the
documented route above 25 MB. Verified: Groq fetched a 2 MB file from S3
and returned a transcript byte-identical to uploading the same file, and a
dead URL failed in 0.2s rather than hanging. WE DO NOT USE IT. Two
reasons: ContentService cannot serve binary at all (see below), and a
URL Groq can reach is a URL anyone can reach, which would have meant
flipping Drive files to link-public and revoking them afterwards — a
revocation that fails leaves the audio public forever.

### THE BIT DEPTH BUG (fixed in v52, was live since v48)

`loudnorm` works internally in floating point, so adding it to Groq's
documented ffmpeg command silently changed the FLAC encoder's output from
16-bit to **24-bit**. Groq's own command has no filter, which is why the
docs never show this and why it went unnoticed. Every stored and uploaded
file was **48% larger than necessary** for a transcript Groq returns
BYTE-IDENTICAL either way (verified against the real API, 398 chars both
ways). Fixed with `-sample_fmt s16` in BOTH `to_flac16k` and
`split_into_chunks` — the second one matters, because without it a
re-encode would reintroduce 24-bit in the parts actually sent to Drive.
Verified across stereo/mp3/m4a/mp4-video/silent/0.08s/already-16k inputs:
all seven produce 16000,1,16.

### Architecture

Audio goes: ffmpeg (levelled, 16 kHz mono, 16-bit) -> split into
10-minute parts -> Drive, one part per request. Coming back it is
Drive -> Streamlit -> Whisper as bytes.

**ContentService can only serve text.** There is no way to return raw
bytes from an Apps Script web app; this was checked in the docs before
building, not discovered afterwards. So a part comes back as base64 inside
JSON and this process decodes it and hands the bytes to Whisper. The
phone still only ever uploads once — everything after is datacentre to
datacentre, which was the actual point of storing it.

**Two secrets, on purpose.** `SHARED_TOKEN` unlocks `doGet`, which returns
the settings AND the API keys. Download links are the part most likely to
end up in a log, so they carry a short-lived HMAC signature made with a
SEPARATE `DOWNLOAD_SECRET` (`DRIVE_SECRET` in Streamlit secrets). The
audio branch sits ABOVE the token check in `doGet` for exactly this
reason. Losing the download secret must never cost the keys, and there are
tests both ways: `SHARED_TOKEN` cannot open audio, `DOWNLOAD_SECRET`
cannot read config.

### Traps found while building, both by a test failing

**The signature covers the SANITISED rec_id.** `safeName_` lowercases and
strips punctuation, so a client that signs the RAW id gets "bad signature"
for a recording that plainly exists — which reads exactly like a broken
secret and is not. `safe_name()` in `ttt/drive.py` must match `safeName_`
character for character; there is a test that runs both over 25 inputs
including traversal, unicode, emoji and the 60-char cap. `new_rec_id()`
also mints ids that are already lowercase hex so the two cannot diverge in
practice.

**GAS hands back SIGNED bytes** from `computeHmacSha256Signature` (-128 to
127). Without `& 0xFF` the hex conversion emits literal `-` characters and
every signature is wrong. Proven: the naive port produces
`7c71057f5459803f4929631f-52e4a-a`.

### Failure directions, chosen deliberately

* Registration happens AFTER every part uploads. A half-stored recording
  leaves orphan Drive files and no archive row — the harmless direction.
  A row with missing audio would not be.
* `fetch()` returns [] rather than a partial list. A partial list
  transcribes to a fluent transcript with a hole in the middle and nothing
  in the result would show anything was missing.
* Re-uploading a part REPLACES it, so a retry after a timeout cannot
  double the storage. Re-registering updates the row. Both are idempotent.
* Every wait has a deadline (15s small calls, 180s per part), because a
  call that neither answers nor refuses reaches no catch handler.
* `DriveStore` never raises and is never a dependency: storage failing
  must not cost anyone their transcript.

### Test status

* **Test 1, mechanism alone: 41 passed, 0 failed.** The real Apps Script
  source executed under a fake GAS runtime (`gastest/`) — our code runs
  untouched, only Google's services are faked. Seven deliberate mutations
  of the source were each caught: audio branch moved below the token
  check, `& 0xFF` dropped, expiry check removed, duplicate-part trashing
  removed, signature comparison forced true, dispatch removed from
  doPost, per-user folder collapsed.
* Interop: `safe_name` 25/25 agree with `safeName_`; `sign_part` 4/4 agree
  with `signPart_`. Both shown to fail under mutation.
* **NOT TESTED, and cannot be until Baba redeploys:** whether Apps Script
  can base64-decode and Drive-write a real ~14 MB part inside its 6-minute
  execution and memory limits. The 50 MiB figure is the TRANSPORT limit —
  the probe was rejected at the token check, before any decode. This is
  the first thing the redeploy must prove.
* Tests 2, 3 and 4 are outstanding. Nothing is wired into `app.py`.

---

## 20. WORD TIMINGS (v53, live in v54)

Edge returns no word marks. It now gets them anyway, from the audio it
just rendered. Full method, every failed approach with its numbers, and
the rendering rule: **docs/WORD_TIMINGS.md**. Point other projects at that
file; it is written to be portable.

### The finding that matters

**Speech has no silence between words.** 236 of 238 inter-word intervals
in Speechify's own marks are exactly zero. Every silence-detection
approach to word boundaries is looking for something that is not in the
signal. If §16 D4 sent you hunting for gaps, stop — that section is now
corrected in place.

### What ships

`ttt/wordtimes.py`, three layers, degrading in order:

1. **engine marks** — Speechify already reports them, exactly
2. **Whisper word timestamps** — one Groq call on the rendered audio,
   `verbose_json` + `timestamp_granularities[]=word`, then the words it
   HEARD are mapped onto the words being DISPLAYED with Needleman-Wunsch
   over normalised tokens
3. **proportional** — what it always did, always available

Held out on unseen sentences and a voice never used in development:

| | mean | median | <50 ms | <100 ms |
|---|---|---|---|---|
| proportional (was) | 138 ms | 119 ms | 26% | 45% |
| **Whisper words** | **71 ms** | **47 ms** | **53%** | **80%** |

Under ~50 ms a highlight reads as simultaneous with the voice. The median
is inside that band.

### The part that is easy to get wrong

Not the timing — the MAPPING. Whisper returns the words it heard, which
are not the words on screen: `12%` for '12 percent', `1,` for 'One',
`3,500 people` merged into one token, and sometimes a word simply missing.
Without sequence alignment one numeral throws the rest of the sentence out
of step. Unmatched words are interpolated between their neighbours,
because a highlight that stops moving is worse than one slightly early.

### Wiring

`_derive_marks()` in app.py, called from `read_sentences_live` ONLY when
the engine returned no marks — Speechify never pays for the call. It costs
~0.4 s before a sentence starts. Every failure path returns None and the
reader behaves exactly as it did before, sentence at a time.

### What was built and deliberately NOT shipped

A complete DSP aligner: energy envelope, spectral flux, adaptive pause
segmentation, DP for assigning words to phrases and DP again for placing
boundaries inside them. Fitted duration prior, punctuation cues, digit
handling. It reached 200 ms on the corpus its prior was fitted to and
**195 ms on held-out data — worse than the 138 ms proportional method it
was meant to beat.** Refining Whisper's anchors with the same DSP gave
88 ms against 89 ms unrefined across nine settings: no gain, which follows
directly from there being no acoustic gap to snap to. It is not in the
repo. Do not rebuild it.

What that work DID earn, if a no-network fallback is ever needed:
punctuation predicts pauses (cut the worst sentence from 608 ms to
322 ms); digits are spoken far longer than they look (`1947` has no vowel
but takes 1.3 s, ~1.3 syllables per digit); and fit the duration prior
rather than guessing it (0.168 s + 0.155 s/syllable, against a guess of
0.055 + 0.180 that was 25% low on one-syllable words).

### Test status

Four tests: **65, 10, 21, 15 passed, 0 failed.** Test 3 found a real crash
on API entries missing `start`, now fixed. Test 4 found a bug of my own —
I had referenced a session key `read_lang` that does not exist anywhere,
which would have silently cost Whisper its language hint on every
Croatian sentence; the real key is `speech_lang`. Mutations were run
against every suite and each was caught.

**NOT TESTED:** anything on Edge audio. The sandbox cannot reach
speech.platform.bing.com, so all validation used Speechify audio. Whisper
should not care what made the sound, but that is inference, not
measurement — the first Edge reading is the real test.

---

## 21. THE STEADY HIGHLIGHT (v55)

The other half of §16 D4, and it became urgent the moment the timing half
shipped: with real word timings the highlight moves two or three times a
second instead of once a sentence, so a defect that used to fire per
sentence now fires per word.

### One property, measured

`padding:1px 4px` on the highlighted word moved **every following word
8 px sideways** and displaced **89 word-positions** while stepping a
single 29-word sentence at a 320 px column. Measured in real Chromium,
reading real geometry — not a judgement that it looked fine.

`background`, `color` and `border-radius` are PAINTED. They never
participate in the box model and cannot move anything. Padding was the
only offender, so the amber fill the design language calls for costs
nothing and stays. Dark-on-amber contrast is 9.06:1, above WCAG AAA.

Note this corrects a slight over-statement in §16 D4, which said "never a
background or bold: those change the text's metrics". Bold does. A
background does not. Padding does. The instinct was right, the reason was
half right, and the difference matters because it means the amber fill
never had to be given up.

### THE SECOND DEFINITION — the trap in §0, caught again

`ttt/reader.py:highlight()` held its own copy of the same span and would
have kept shaking in the LLL reader view while the Talk view was clean.
That reads as an intermittent bug rather than a style one, which is far
harder to chase. **When fixing a style, grep for another rule doing the
same job before believing it is done.**

### tests/test_shake.py

Runs headless Chromium at a phone width, steps the highlight across a
sentence and measures the bounding box of EVERY OTHER word at every step.
Anything that is not the highlighted word must not move at all.

It reads the shipped styles out of `app.py` and `ttt/reader.py` by regex
rather than holding its own copy — a test with its own copy of the style
passes forever while the real style drifts back to padding. Both arms
were verified to go red when padding is reintroduced.

Requires `playwright` and a chromium download, so it is a local test, not
a Cloud one. Run it after ANY change to either highlight span.

---

## 22. THE CASSETTE DECK (v56)

Replaces `st.audio_input` in the transcribe tab with a real recorder
component: rec / pause / stop / eject as a transport row, a live
oscilloscope, and a running timer.

### Format — measured, not chosen

**MediaRecorder cannot produce WAV in any browser.** The API emits
webm/opus, ogg/opus or mp4/aac only; WAV would mean capturing raw PCM
through an AudioWorklet and writing the header in JS. It would also not
survive the trip: WAV is 5.8 MB a minute and 345 MB an hour, against
1 MB a minute for opus at 128k, and that blob crosses the websocket
base64'd.

Opus at 128k is transparent for this purpose. Through the app's own
ffmpeg chain to 16 kHz FLAC, Whisper returned the same words as a WAV
reference. **32k was NOT transparent** — "Sound" came back as "Bound" —
so the floor is real. 64k was already clean; 128k is for the headroom,
because the test material was clean studio TTS and a phone in a room is
harder to encode.

Note the fake device reports **stereo** even when the constraint asks for
mono. ffmpeg's `-ac 1` handles it, but do not assume the constraint is
honoured.

### The scope must not be able to lie

It reads the live signal through an AnalyserNode. It is auto-gained,
because speech sits near -20 dBFS and at a fixed scale moved **two pixels
on a 46 px window** — technically correct and useless to look at. Gain
rises fast and falls slowly so it does not pump between syllables.

Auto-gain WITHOUT a floor would amplify the noise of a disconnected
microphone into a convincing dance, which is the one lie this display must
never tell. Hence `FLOOR`. Measured in real Chromium:

    real speech        trace fills 43 px of 46, varying 14-43 with the voice
    dead microphone    1 px, flat

**If the scope is flat, the microphone is genuinely not receiving.** That
is the single most useful thing a recorder can say before someone talks
for ten minutes into nothing.

### Recording is chunked every second

`rec.start(1000)`. A crash or a killed tab loses one second, not the take.

### Test status

Test 2, real Chromium with a fake microphone at `--use-file-for-fake-
audio-capture`: **18 passed, 1 failed**, and the one failure was the
test's own metric (lit-pixel count cannot tell a flat line from a
waveform; vertical extent can). componentReady, transport state
transitions, the clock freezing under pause, the blob posting back once,
the byte count matching, and **ffprobe as an outside party confirming the
blob is real opus audio**.

The mic needs a SECURE CONTEXT. `page.set_content()` fails with
"microphone refused" — serve the component over `http://127.0.0.1` to
test it.

---

## 23. LEVELLING ON THE TRANSCRIBE PATH (v56)

`app.py:transcode_to_flac` — the function the microphone and the file
picker actually use — was Groq's raw command with **no levelling at all**.
`ttt/audio.py:to_flac16k` had it; this one never did. THERE ARE TWO
TRANSCODE FUNCTIONS AND TWO `split_into_chunks`. That duplication is a
live hazard: the v52 bit-depth fix only ever touched one half of it.

Levelling now runs before transcoding. Measured word error rate:

    very quiet (-32dB), clean      2.9%  ->  0.0%
    quiet with heavy room noise    7.2%  ->  2.9%
    quiet with light room noise    0.0%  ->  2.9%
    loud and clean                 0.0%  ->  0.0%

It rescues the two cases that actually fail in the field and costs a
little on one that was already perfect.

`-sample_fmt s16` went in at the same time and MUST NOT be separated from
it: loudnorm works in floating point and silently promotes FLAC output to
24-bit, making every file ~48% larger for an identical transcript. See
§19.

---

## 24. TWO DEAD FEATURES FOUND BY pyflakes

`python3 -m pyflakes app.py` finds names that are used but never defined.
These compile fine and crash at runtime, so nothing catches them until a
person presses the button. **Run it before every push.**

**FIXED — the sheet prompts.** `SHEET` was used in three places and
`ttt.sheet` was never imported into app.py, so `sheet_prompt()` raised
NameError inside a try/except. Grammar and reshape showed an error instead
of using the wording from the sheet. One missing import line.

**STILL BROKEN — reading text out of a picture.** `read_picture` is
called at the image branch of the file picker but does not exist. Commit
`92c4cbb` ("Terminal command rows everywhere", 17.8.2026) deleted it along
with `vision_model` and `http_json_groq_models` while leaving the caller
behind. Image OCR has been dead since then.

It is NOT restored here, deliberately. The originals are recoverable from
`git show d94bd60:app.py`, but `vision_model` was written against a
model-listing helper that no longer exists — the provider API is now
`provider.models(task, fetch)` — so a faithful restore means rewriting it,
and that cannot be tested without a running Streamlit. A half-restored
chain that compiles and fails differently is worse than a known gap.
`ttt.vision` currently shows as an unused import, which is the second
independent sign the whole path is dead.
