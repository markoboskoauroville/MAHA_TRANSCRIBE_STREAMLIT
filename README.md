# Maha Transcribe — Streamlit / Groq edition

Two tabs. **Transcribe** turns your voice into text with Whisper on Groq.
**Talk** turns text back into speech, read aloud live, sentence by sentence.

## Transcribe

Record → auto-transcribes with `whisper-large-v3-turbo`. If something looks
wrong, **Correct** re-runs the same audio through `whisper-large-v3` (slower,
more accurate). **Read this** sends the transcript straight to the Talk tab.

1. `st.audio_input(sample_rate=48000)` records at the highest quality the
   widget offers.
2. `ffmpeg` downsamples that to 16kHz mono FLAC — Groq's own documented
   preprocessing target for its speech-to-text models:
   ```
   ffmpeg -i <in> -ar 16000 -ac 1 -map 0:a -c:a flac <out>.flac
   ```
3. The FLAC goes to Groq's `/audio/transcriptions` endpoint with a
   `language` hint (`en` or `hr`).
4. Any number of Groq keys can be listed in secrets; the app rotates to the
   next one if a key is rate-limited or rejected.

## Talk

Paste text (or arrive via Read this), pick a voice, press Read. Each
sentence is spoken live with Microsoft's neural voices — Sonia, Ryan,
Gabrijela, Srecko — and the sentence currently playing is highlighted in the
text. Nothing is cached to disk: every read synthesizes fresh, in memory,
and is handed straight to the browser, the same shape as asking a page to
read itself aloud. There is no word-level timing, only sentence-level
highlight, on purpose — word timing drifts, sentence timing doesn't.

## Deploy on Streamlit Community Cloud

1. Push this repo (already public) — Streamlit Cloud reads it directly.
2. New app → pick this repo → main file `app.py`.
3. Advanced settings → Secrets → paste your `secrets.toml` content
   (`APP_PASSWORDS`, `GROQ_API_KEYS`). **Never commit that file** —
   `.streamlit/secrets.toml` is gitignored on purpose.
4. Deploy. `packages.txt` installs `ffmpeg` automatically on Streamlit
   Cloud's Debian build (needed for Transcribe); `requirements.txt` installs
   `streamlit`, `groq`, and `edge-tts`.

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
- No key is ever sent to the browser — Groq and edge-tts calls happen
  server-side only.
- `whisper-large-v3-turbo` vs `whisper-large-v3`: per Groq's guidance, turbo
  is the fast/cheap default, and large-v3 is the pick for error-sensitive
  re-checks — which is exactly what the Correct button is for.
- Talk reads with a blocking loop (`time.sleep` paced to each clip's real
  length); pressing Stop, or any other click, interrupts it, because
  Streamlit cancels an in-flight script run when a new interaction arrives.
