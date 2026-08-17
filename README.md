# Maha Transcribe — Streamlit / Groq edition

Record your voice in the browser, get it transcribed by Whisper on Groq.
Groq only — no other providers.

**Workflow:** press, speak, press, copy. Recording auto-transcribes with
`whisper-large-v3-turbo`. If something looks wrong, **Correct** re-runs the
same audio through `whisper-large-v3` (slower, more accurate).

## How it works

1. `st.audio_input(sample_rate=48000)` records at the highest quality the
   widget offers.
2. `ffmpeg` downsamples that to 16kHz mono FLAC — this is
   [Groq's own documented preprocessing target](https://console.groq.com/docs/speech-to-text#audio-preprocessing)
   for its speech-to-text models:
   ```
   ffmpeg -i <in> -ar 16000 -ac 1 -map 0:a -c:a flac <out>.flac
   ```
3. The FLAC is sent to Groq's `/audio/transcriptions` endpoint with a
   `language` hint (`en` or `hr`) set from the toggle in the UI.
4. Multiple Groq keys can be listed in secrets; the app rotates to the next
   one if a key is rate-limited or rejected.

## Deploy on Streamlit Community Cloud

1. Push this repo (already public) — Streamlit Cloud reads it directly.
2. New app → pick this repo → main file `app.py`.
3. Advanced settings → Secrets → paste your `secrets.toml` content
   (`APP_PASSWORDS`, `GROQ_API_KEYS`). **Never commit that file** —
   `.streamlit/secrets.toml` is gitignored on purpose.
4. Deploy. `packages.txt` installs `ffmpeg` automatically on Streamlit
   Cloud's Debian build; `requirements.txt` installs `streamlit` and `groq`.

## Local development

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # fill in real values
pip install -r requirements.txt
streamlit run app.py
```

## Notes

- Password gate accepts any password listed in `APP_PASSWORDS` (a list — share
  the app with as many people as you like, one password each), checked with
  a constant-time comparison.
- No key is ever sent to the browser — Groq calls happen server-side only.
- `whisper-large-v3-turbo` vs `whisper-large-v3`: per Groq's guidance, turbo
  is the fast/cheap default, and large-v3 is the pick for error-sensitive
  re-checks — which is exactly what the Correct button is for.
