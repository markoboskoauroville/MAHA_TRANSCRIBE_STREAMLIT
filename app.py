"""
Maha Transcribe — Streamlit / Groq edition.

Record → ffmpeg downsample to 16kHz mono FLAC (Groq's own documented
preprocessing target) → Whisper on Groq → optional re-check with the
more accurate model. Groq only, no other providers.
"""

import os
import hmac
import hashlib
import tempfile
import subprocess

import streamlit as st
from groq import Groq

# ----------------------------------------------------------------------
# Page setup — near-black + gold, no blur, no clutter
# ----------------------------------------------------------------------
st.set_page_config(page_title="Maha Transcribe", page_icon="🎙️", layout="centered")

st.markdown(
    """
    <style>
    .stTextArea textarea { font-size: 1.15rem; line-height: 1.55; }
    .block-container { padding-top: 3rem; max-width: 640px; }
    div[data-testid="stAudioInput"] { margin-bottom: 0.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

PRIMARY_MODEL = "whisper-large-v3-turbo"   # fast first pass
CORRECTION_MODEL = "whisper-large-v3"      # slower, more accurate — used by Correct


# ----------------------------------------------------------------------
# Password gate
# ----------------------------------------------------------------------
def check_password() -> bool:
    def _entered():
        entered = st.session_state.get("_pw_input", "")
        correct = st.secrets.get("APP_PASSWORD", "")
        st.session_state["_authed"] = bool(correct) and hmac.compare_digest(entered, correct)
        st.session_state["_pw_input"] = ""

    if st.session_state.get("_authed"):
        return True

    st.text_input("Password", type="password", key="_pw_input", on_change=_entered)
    if st.session_state.get("_authed") is False:
        st.error("Wrong password.")
    return False


if "APP_PASSWORD" not in st.secrets:
    st.error("APP_PASSWORD is missing from Secrets. Streamlit Cloud → Settings → Secrets.")
    st.stop()

if not check_password():
    st.stop()


# ----------------------------------------------------------------------
# Groq key ring — tries each key in turn, remembers the last one that worked
# ----------------------------------------------------------------------
def groq_keys() -> list:
    keys = list(st.secrets.get("GROQ_API_KEYS", []))
    single = st.secrets.get("GROQ_API_KEY")
    if single and single not in keys:
        keys.append(single)
    return [k for k in keys if k]


KEYS = groq_keys()
if not KEYS:
    st.error("No Groq key in Secrets. Add GROQ_API_KEYS (a list) in Streamlit Cloud → Settings → Secrets.")
    st.stop()


def transcribe(path: str, model: str, language: str) -> str:
    start = st.session_state.get("_key_idx", 0) % len(KEYS)
    last_err = None
    for offset in range(len(KEYS)):
        idx = (start + offset) % len(KEYS)
        client = Groq(api_key=KEYS[idx])
        try:
            with open(path, "rb") as f:
                resp = client.audio.transcriptions.create(
                    file=(os.path.basename(path), f.read()),
                    model=model,
                    language=language,
                    response_format="text",
                    temperature=0.0,
                )
            st.session_state["_key_idx"] = idx
            text = resp if isinstance(resp, str) else getattr(resp, "text", str(resp))
            return text.strip()
        except Exception as e:  # bad key, rate limit, network — try the next key
            last_err = e
            continue
    raise RuntimeError(f"All Groq keys failed ({last_err})")


def to_flac16k(wav_bytes: bytes) -> str:
    """Downsample the browser recording to exactly what Whisper on Groq
    wants: 16kHz mono FLAC. This is Groq's own documented ffmpeg command."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        in_path = f.name
    out_path = in_path[:-4] + ".flac"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", in_path, "-ar", "16000", "-ac", "1",
             "-map", "0:a", "-c:a", "flac", out_path],
            check=True, capture_output=True, timeout=60,
        )
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found on the server — check packages.txt.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed: {e.stderr.decode(errors='ignore')[-300:]}")
    finally:
        os.remove(in_path)
    return out_path


# ----------------------------------------------------------------------
# UI — record, transcribe, correct. That's the whole workflow.
# ----------------------------------------------------------------------
st.caption("Maha Transcribe")

lang_label = st.segmented_control(
    "Language", ["English", "Croatian"], default="English", required=True
)
lang_code = "en" if lang_label == "English" else "hr"

audio = st.audio_input("Record", sample_rate=48000, label_visibility="collapsed")

if audio is not None:
    digest = hashlib.md5(audio.getvalue()).hexdigest()
    if st.session_state.get("_digest") != digest:
        old_flac = st.session_state.get("flac_path")
        if old_flac and os.path.exists(old_flac):
            os.remove(old_flac)
        st.session_state["_digest"] = digest
        st.session_state["model_used"] = None
        try:
            with st.spinner("Preparing audio…"):
                flac_path = to_flac16k(audio.getvalue())
            st.session_state["flac_path"] = flac_path
            with st.spinner("Transcribing…"):
                text = transcribe(flac_path, PRIMARY_MODEL, lang_code)
            st.session_state["transcript_box"] = text
            st.session_state["model_used"] = PRIMARY_MODEL
        except Exception as e:
            st.error(str(e))

if "transcript_box" in st.session_state:
    st.text_area("Transcript", key="transcript_box", height=200, label_visibility="collapsed")

    if st.button("🔁 Correct — re-check with the accurate model", use_container_width=True):
        try:
            with st.spinner("Re-transcribing with whisper-large-v3…"):
                corrected = transcribe(st.session_state["flac_path"], CORRECTION_MODEL, lang_code)
            st.session_state["transcript_box"] = corrected
            st.session_state["model_used"] = CORRECTION_MODEL
            st.rerun()
        except Exception as e:
            st.error(str(e))

    if st.session_state.get("model_used"):
        st.caption(st.session_state["model_used"])
