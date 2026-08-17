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

---

## 4. FILES

```
app.py                      entrypoint: gate, settings, both tabs, LS bridge
talk_engine.py              sentence splitting + live edge-tts synthesis
help_text.py                HELP and LOGIN_GUIDE prose, hr + en
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
