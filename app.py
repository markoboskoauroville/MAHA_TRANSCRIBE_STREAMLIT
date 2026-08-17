"""
Maha Transcribe — Streamlit / Groq edition.

Record → ffmpeg downsample to 16kHz mono FLAC (Groq's own documented
preprocessing target) → Whisper on Groq → optional re-check with the
more accurate model. Groq only, no other providers.
"""

import os
import json
import hmac
import html
import time
import hashlib
import tempfile
import subprocess

import streamlit as st
from groq import Groq

import talk_engine as tk
from ls_bridge import ls_bridge

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

APP_VERSION = "v2 (a)"

PRIMARY_MODEL = "whisper-large-v3-turbo"   # fast first pass
CORRECTION_MODEL = "whisper-large-v3"      # slower, more accurate — used by Correct
VOICE_LABELS = {"ukF": "Sonia", "ukM": "Ryan", "hrF": "Gabrijela", "hrM": "Srecko"}


# ----------------------------------------------------------------------
# Translation — interface chrome only. Speech language (what you're
# recognising) is a separate, existing setting and is not touched by this.
# ----------------------------------------------------------------------
STRINGS = {
    "tab_transcribe":     {"en": "Transcribe",      "hr": "Transkripcija"},
    "tab_talk":           {"en": "Talk",             "hr": "Čitanje"},
    "speech_lang_label":  {"en": "Speech language",  "hr": "Jezik govora"},
    "lang_en":            {"en": "English",          "hr": "Engleski"},
    "lang_hr":            {"en": "Croatian",         "hr": "Hrvatski"},
    "transcript_label":   {"en": "Transcript",       "hr": "Transkript"},
    "correct_btn":        {"en": "🔁 Correct",       "hr": "🔁 Ispravi"},
    "correct_help":       {"en": "Re-check with the accurate model", "hr": "Provjeri ponovno točnijim modelom"},
    "read_this_btn":      {"en": "🔊 Read this",     "hr": "🔊 Pročitaj ovo"},
    "read_this_help":     {"en": "Send this transcript to the Talk tab", "hr": "Pošalji transkript na tab Čitanje"},
    "read_this_toast":    {"en": "Sent to the Talk tab.", "hr": "Poslano na tab Čitanje."},
    "voice_label":        {"en": "Voice",            "hr": "Glas"},
    "talk_placeholder":   {"en": "Paste text here, or send it from Transcribe with Read this",
                            "hr": "Zalijepi tekst ovdje, ili ga pošalji s taba Transkripcija pomoću Pročitaj ovo"},
    "read_btn":           {"en": "▶ Read",           "hr": "▶ Čitaj"},
    "stop_btn":           {"en": "■ Stop",           "hr": "■ Zaustavi"},
    "stop_help":          {"en": "Interrupts the reading in progress", "hr": "Prekida čitanje u tijeku"},
    "nothing_to_read":    {"en": "Nothing to read yet.", "hr": "Još nema teksta za čitanje."},
    "read_fail":          {"en": "Could not read sentence", "hr": "Nije uspjelo čitanje rečenice"},
    "password_label":     {"en": "Password",         "hr": "Lozinka"},
    "wrong_password":     {"en": "Wrong password.",  "hr": "Pogrešna lozinka."},
    "preparing_audio":    {"en": "Preparing audio…", "hr": "Priprema zvuka…"},
    "transcribing":       {"en": "Transcribing…",    "hr": "Transkribiranje…"},
    "recorrecting":       {"en": "Re-transcribing with the accurate model…", "hr": "Ponovna transkripcija točnijim modelom…"},
    "settings_title":     {"en": "Settings",         "hr": "Postavke"},
    "settings_ui_lang":   {"en": "Interface language", "hr": "Jezik sučelja"},
    "settings_speech":    {"en": "Default speech language", "hr": "Zadani jezik govora"},
    "settings_voice":     {"en": "Default voice",    "hr": "Zadani glas"},
    "settings_saved":     {"en": "Saved.",           "hr": "Spremljeno."},
    "no_password_secret": {"en": "No password set in Secrets. Add APP_PASSWORDS (a list) in Streamlit Cloud → Settings → Secrets.",
                            "hr": "Lozinka nije postavljena u Secrets. Dodaj APP_PASSWORDS (listu) u Streamlit Cloud → Settings → Secrets."},
    "no_groq_secret":     {"en": "No Groq key in Secrets. Add GROQ_API_KEYS (a list) in Streamlit Cloud → Settings → Secrets.",
                            "hr": "Nema Groq ključa u Secrets. Dodaj GROQ_API_KEYS (listu) u Streamlit Cloud → Settings → Secrets."},
}


def t(key: str) -> str:
    lang = st.session_state.get("ui_lang", "hr")
    entry = STRINGS.get(key, {})
    return entry.get(lang, entry.get("en", key))


# ----------------------------------------------------------------------
# Password gate — as many passwords work as are listed in Secrets.
# The matched password also names the settings profile ("which user").
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
        matched = next((p for p in PASSWORDS if hmac.compare_digest(entered, p)), None)
        st.session_state["_authed"] = matched is not None
        if matched is not None:
            st.session_state["_user"] = matched
        st.session_state["_pw_input"] = ""

    if st.session_state.get("_authed"):
        return True

    # Pre-login screen is always Croatian by default — we don't know which
    # user (and therefore which UI-language preference) it is yet.
    st.session_state.setdefault("ui_lang", "hr")
    st.text_input(t("password_label"), type="password", key="_pw_input", on_change=_entered)
    if st.session_state.get("_authed") is False:
        st.error(t("wrong_password"))
    return False


PASSWORDS = app_passwords()
if not PASSWORDS:
    st.session_state.setdefault("ui_lang", "hr")
    st.error(t("no_password_secret"))
    st.stop()

if not check_password():
    st.stop()

USER = st.session_state.get("_user") or "shared"


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
    st.error(t("no_groq_secret"))
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
# Per-user settings — three layers, in priority order:
#   1. st.session_state (already loaded this session)
#   2. browser localStorage, via ls_bridge (survives restarts, per browser)
#   3. a small server-side JSON file (survives only within this container's
#      current lifetime — Streamlit Community Cloud does not guarantee disk
#      across restarts, so this is a same-instance convenience, not a
#      durable store; it exists so a second browser hitting the same
#      still-warm instance gets a reasonable starting point too)
# Whenever a setting changes, all three are written.
# ----------------------------------------------------------------------
DEFAULT_SETTINGS = {"ui_lang": "hr", "speech_lang": "Croatian", "voice": "Gabrijela"}
LS_KEY = f"maha_settings_{USER}"


def _settings_file(user: str) -> str:
    d = os.path.join(tempfile.gettempdir(), "maha_settings")
    os.makedirs(d, exist_ok=True)
    safe = "".join(c for c in user if c.isalnum()) or "user"
    return os.path.join(d, safe + ".json")


def _load_server_settings(user: str) -> dict:
    try:
        with open(_settings_file(user), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_server_settings(user: str, settings: dict) -> None:
    try:
        with open(_settings_file(user), "w", encoding="utf-8") as f:
            json.dump(settings, f)
    except Exception:
        pass


def _apply_settings(values: dict) -> None:
    """Seed session_state with settings values. Must only be called before
    any widget using these keys has been instantiated this run."""
    for k in ("ui_lang", "speech_lang", "voice"):
        if k in values and values[k]:
            st.session_state[k] = values[k]
            st.session_state["set_" + k] = values[k]


if "_settings_bootstrapped" not in st.session_state:
    _apply_settings(DEFAULT_SETTINGS)
    _apply_settings(_load_server_settings(USER))   # best-effort instant guess
    st.session_state["_settings_bootstrapped"] = True

# Fire (or re-fire) the localStorage bridge every run so Streamlit's
# component protocol can complete its round trip. If a write is pending
# from the settings popover, send it; otherwise this is a read-only poll.
_pending_write = st.session_state.pop("_pending_ls_write", None)
if _pending_write is not None:
    _ls_result = ls_bridge(write_key=LS_KEY, write_value=_pending_write, key="ls_sync")
else:
    _ls_result = ls_bridge(key="ls_sync")

if _ls_result and _ls_result.get("ok") and not st.session_state.get("_ls_applied"):
    raw = (_ls_result.get("data") or {}).get(LS_KEY)
    if raw:
        try:
            _apply_settings(json.loads(raw))
        except Exception:
            pass
    st.session_state["_ls_applied"] = True


def _save_settings_callback():
    values = {
        "ui_lang": st.session_state["set_ui_lang"],
        "speech_lang": st.session_state["set_speech_lang"],
        "voice": st.session_state["set_voice"],
    }
    _apply_settings(values)
    _save_server_settings(USER, values)
    st.session_state["_pending_ls_write"] = json.dumps(values)
    st.session_state["_settings_just_saved"] = True


# ----------------------------------------------------------------------
# Top bar: caption + gear settings popover, upper right
# ----------------------------------------------------------------------
top_l, top_r = st.columns([6, 1])
with top_l:
    st.caption(f"Maha Transcribe · {APP_VERSION}")
with top_r:
    with st.popover("⚙️", use_container_width=False):
        st.caption(t("settings_title"))
        st.radio(
            t("settings_ui_lang"), ["hr", "en"],
            format_func=lambda v: "Hrvatski" if v == "hr" else "English",
            key="set_ui_lang", on_change=_save_settings_callback,
        )
        st.radio(
            t("settings_speech"), ["Croatian", "English"],
            format_func=lambda v: t("lang_hr") if v == "Croatian" else t("lang_en"),
            key="set_speech_lang", on_change=_save_settings_callback,
        )
        st.radio(
            t("settings_voice"), ["Sonia", "Ryan", "Gabrijela", "Srecko"],
            key="set_voice", on_change=_save_settings_callback,
        )
        if st.session_state.pop("_settings_just_saved", False):
            st.caption(t("settings_saved"))


# ----------------------------------------------------------------------
# UI — two tabs. Transcribe: press, speak, press, copy. Talk: paste, read.
# ----------------------------------------------------------------------
tab_transcribe, tab_talk = st.tabs([t("tab_transcribe"), t("tab_talk")])

with tab_transcribe:
    lang_label = st.segmented_control(
        t("speech_lang_label"), [t("lang_en"), t("lang_hr")],
        default=t("lang_hr") if st.session_state.get("speech_lang", "Croatian") == "Croatian" else t("lang_en"),
        required=True, key="transcribe_lang_display",
    )
    lang_code = "hr" if lang_label == t("lang_hr") else "en"

    audio = st.audio_input(t("tab_transcribe"), sample_rate=48000, label_visibility="collapsed")

    if audio is not None:
        digest = hashlib.md5(audio.getvalue()).hexdigest()
        if st.session_state.get("_digest") != digest:
            old_flac = st.session_state.get("flac_path")
            if old_flac and os.path.exists(old_flac):
                os.remove(old_flac)
            st.session_state["_digest"] = digest
            st.session_state["model_used"] = None
            try:
                with st.spinner(t("preparing_audio")):
                    flac_path = to_flac16k(audio.getvalue())
                st.session_state["flac_path"] = flac_path
                with st.spinner(t("transcribing")):
                    text = transcribe(flac_path, PRIMARY_MODEL, lang_code)
                st.session_state["transcript_box"] = text
                st.session_state["model_used"] = PRIMARY_MODEL
            except Exception as e:
                st.error(str(e))

    if "transcript_box" in st.session_state:
        st.text_area(t("transcript_label"), key="transcript_box", height=200, label_visibility="collapsed")

        def _do_correct():
            try:
                corrected = transcribe(st.session_state["flac_path"], CORRECTION_MODEL, lang_code)
                st.session_state["transcript_box"] = corrected
                st.session_state["model_used"] = CORRECTION_MODEL
            except Exception as e:
                st.session_state["_correct_error"] = str(e)

        def _do_bridge():
            st.session_state["talk_text"] = st.session_state.get("transcript_box", "")
            st.session_state["_bridge_sent"] = True

        bcol1, bcol2 = st.columns(2)
        with bcol1:
            st.button(t("correct_btn"), use_container_width=True, key="correct_btn",
                      help=t("correct_help"), on_click=_do_correct)
        with bcol2:
            st.button(t("read_this_btn"), use_container_width=True, key="bridge_btn",
                      help=t("read_this_help"), on_click=_do_bridge)

        if st.session_state.get("_correct_error"):
            st.error(st.session_state.pop("_correct_error"))
        if st.session_state.pop("_bridge_sent", False):
            st.toast(t("read_this_toast"))

        if st.session_state.get("model_used"):
            st.caption(st.session_state["model_used"])

with tab_talk:
    voice_label = st.segmented_control(
        t("voice_label"), ["Sonia", "Ryan", "Gabrijela", "Srecko"],
        default=st.session_state.get("voice", "Gabrijela"),
        required=True, key="talk_voice",
    )
    vkey = {v: k for k, v in VOICE_LABELS.items()}[voice_label]

    st.text_area(
        t("tab_talk"), key="talk_text", height=150, label_visibility="collapsed",
        placeholder=t("talk_placeholder"),
    )

    rcol1, rcol2 = st.columns(2)
    read_clicked = rcol1.button(t("read_btn"), use_container_width=True, key="read_btn")
    rcol2.button(t("stop_btn"), use_container_width=True, key="stop_btn", help=t("stop_help"))

    doc_slot = st.empty()
    audio_slot = st.empty()

    if read_clicked:
        raw = (st.session_state.get("talk_text") or "").strip()
        sentences = tk.sentences_of(raw)
        if not sentences:
            st.info(t("nothing_to_read"))
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
                    st.error(f"{t('read_fail')} {i + 1}: {e}")
                    break
                audio_slot.audio(audio_bytes, format="audio/mp3", autoplay=True)
                time.sleep(dur + 0.15)
            doc_slot.markdown(html.escape(raw))
