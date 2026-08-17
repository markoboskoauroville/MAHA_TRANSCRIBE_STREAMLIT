"""
Maha Transcribe — Streamlit / Groq edition.

Record → ffmpeg downsample to 16kHz mono FLAC (Groq's own documented
preprocessing target) → Whisper on Groq → optional re-check with the
more accurate model. Groq only, no other providers.
"""

import os
import hmac
import html
import time
import hashlib
import tempfile
import subprocess

import streamlit as st
from groq import Groq

import talk_engine as tk

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
    .stButton button { border-radius: 999px; }
    .st-key-correct_btn button { background-color: #4dd6e8; color: #0d0d0d; border-color: #4dd6e8; }
    .st-key-correct_btn button:hover { background-color: #6fe0ee; border-color: #6fe0ee; }
    </style>
    """,
    unsafe_allow_html=True,
)

APP_VERSION = "v1 (a)"

PRIMARY_MODEL = "whisper-large-v3-turbo"   # fast first pass
CORRECTION_MODEL = "whisper-large-v3"      # slower, more accurate — used by Correct


# ----------------------------------------------------------------------
# Password gate — as many passwords work as are listed in Secrets
# ----------------------------------------------------------------------
def app_passwords() -> list:
    pw = list(st.secrets.get("APP_PASSWORDS", []))
    single = st.secrets.get("APP_PASSWORD")   # older single-password secrets still work
    if single and single not in pw:
        pw.append(single)
    return [p for p in pw if p]


def check_password() -> bool:
    def _entered():
        entered = st.session_state.get("_pw_input", "")
        st.session_state["_authed"] = any(
            hmac.compare_digest(entered, p) for p in PASSWORDS
        )
        st.session_state["_pw_input"] = ""

    if st.session_state.get("_authed"):
        return True

    st.text_input("Password", type="password", key="_pw_input", on_change=_entered)
    if st.session_state.get("_authed") is False:
        st.error("Wrong password.")
    return False


PASSWORDS = app_passwords()
if not PASSWORDS:
    st.error("No password set in Secrets. Add APP_PASSWORDS (a list) in Streamlit Cloud → Settings → Secrets.")
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
# UI — two tabs. Transcribe: press, speak, press, copy. Talk: paste, read.
# ----------------------------------------------------------------------
st.caption(f"Maha Transcribe · {APP_VERSION}")

VOICE_LABELS = {"ukF": "Sonia", "ukM": "Ryan", "hrF": "Gabrijela", "hrM": "Srecko"}

tab_transcribe, tab_talk = st.tabs(["Transcribe", "Talk"])

with tab_transcribe:
    lang_label = st.segmented_control(
        "Language", ["English", "Croatian"], default="English", required=True,
        key="transcribe_lang",
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

        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("🔁 Correct", use_container_width=True, key="correct_btn",
                         help="Re-check with the accurate model"):
                try:
                    with st.spinner("Re-transcribing with whisper-large-v3…"):
                        corrected = transcribe(st.session_state["flac_path"], CORRECTION_MODEL, lang_code)
                    st.session_state["transcript_box"] = corrected
                    st.session_state["model_used"] = CORRECTION_MODEL
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with bcol2:
            if st.button("🔊 Read this", use_container_width=True, key="bridge_btn",
                         help="Send this transcript to the Talk tab"):
                st.session_state["talk_text"] = st.session_state.get("transcript_box", "")
                st.toast("Sent to the Talk tab.")

        if st.session_state.get("model_used"):
            st.caption(st.session_state["model_used"])

with tab_talk:
    voice_label = st.segmented_control(
        "Voice", ["Sonia", "Ryan", "Gabrijela", "Srecko"], default="Sonia",
        required=True, key="talk_voice",
    )
    vkey = {v: k for k, v in VOICE_LABELS.items()}[voice_label]

    st.text_area(
        "Text to read", key="talk_text", height=150, label_visibility="collapsed",
        placeholder="Paste text here, or send it from Transcribe with Read this",
    )

    rcol1, rcol2 = st.columns(2)
    read_clicked = rcol1.button("▶ Read", use_container_width=True, key="read_btn")
    rcol2.button("■ Stop", use_container_width=True, key="stop_btn",
                 help="Interrupts the reading in progress")

    doc_slot = st.empty()
    audio_slot = st.empty()

    if read_clicked:
        raw = (st.session_state.get("talk_text") or "").strip()
        sentences = tk.sentences_of(raw)
        if not sentences:
            st.info("Nothing to read yet.")
        else:
            for i, sent in enumerate(sentences):
                parts = []
                for j, s in enumerate(sentences):
                    safe = html.escape(s)
                    if j == i:
                        parts.append(
                            '<span style="background:#e0a340;color:#0d0d0d;'
                            'border-radius:4px;padding:1px 4px;">' + safe + "</span>"
                        )
                    else:
                        parts.append(safe)
                doc_slot.markdown(" ".join(parts), unsafe_allow_html=True)
                try:
                    audio_bytes, dur = tk.synth_sentence(sent, vkey)
                except Exception as e:
                    st.error(f"Could not read sentence {i + 1}: {e}")
                    break
                audio_slot.audio(audio_bytes, format="audio/mp3", autoplay=True)
                time.sleep(dur + 0.15)
            doc_slot.markdown(html.escape(raw))

