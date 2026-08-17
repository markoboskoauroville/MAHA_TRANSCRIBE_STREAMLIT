# TTT-LLL — HANDOVER

Live: https://ttt-lll.streamlit.app
Repo: https://github.com/markoboskoauroville/MAHA_TRANSCRIBE_STREAMLIT
Entrypoint: `app.py` · Version: see `APP_VERSION` in `app.py`

**TTT** = Talk To Type (speech → text). **LLL** = Look, Listen, Learn
(text → speech, seen and heard at once).

---

## 1. INCIDENT: the red TypeError screen (17.8.2026)

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

**Translate.** A third tab, added for Emina and Marinko — they like
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

