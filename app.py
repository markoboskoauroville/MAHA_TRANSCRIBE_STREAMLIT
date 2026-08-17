"""
Maha Transcribe — Streamlit / Groq edition.

Transcribe: record → ffmpeg downsample to 16kHz mono FLAC (Groq's own
documented preprocessing target) → Whisper on Groq. Groq only.
Talk: paste text → read aloud live, sentence by sentence, with a subtitle line.
"""

import os
import json
import glob
import hmac
import html
import time
import hashlib
import tempfile
import subprocess

import streamlit as st
from groq import Groq

import streamlit.components.v1 as components

import talk_engine as tk
import help_text

# ----------------------------------------------------------------------
# Page setup — near-black + gold, no blur, no clutter
# ----------------------------------------------------------------------
st.set_page_config(page_title="TTT-LLL", page_icon="🎙️", layout="centered")

st.markdown(
    """
    <style>
    .stTextArea textarea { font-size: 1.15rem; line-height: 1.55; }
    .block-container { padding-top: 2.5rem; max-width: 640px; }
    div[data-testid="stAudioInput"] { margin-bottom: 0.6rem; }
    .stButton button { border-radius: 999px; }
    .st-key-correct_btn button { background-color: #4dd6e8; color: #0d0d0d; border-color: #4dd6e8; }
    .st-key-correct_btn button:hover { background-color: #6fe0ee; border-color: #6fe0ee; }
    .subtitle-box {
        border: 1px solid #3a3a3a; border-radius: 10px; padding: 16px 14px;
        min-height: 92px; font-size: 1.45rem; line-height: 1.45;
        color: #e8dcc0; background: #141414;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

APP_VERSION = "v8 (a)"

PRIMARY_MODEL = "whisper-large-v3-turbo"   # fast first pass
CORRECTION_MODEL = "whisper-large-v3"      # slower, more accurate — used by Correct

# Croatian first everywhere, English second.
VOICES_BY_LANG = {"hr": ["Gabrijela", "Srecko"], "en": ["Sonia", "Ryan"]}
VOICE_TO_VKEY = {"Gabrijela": "hrF", "Srecko": "hrM", "Sonia": "ukF", "Ryan": "ukM"}
VOICE_LANG = {"Gabrijela": "hr", "Srecko": "hr", "Sonia": "en", "Ryan": "en"}

# Translate tab + the login screen's language pills. European only, on
# purpose, in the order Baba asked for: Croatian first, English second.
LANGS5 = ["hr", "en", "it", "de", "fr"]
LANG_FULL = {"hr": "Croatian", "en": "English", "it": "Italian", "de": "German", "fr": "French"}
# One voice per language for the Translate tab's Read button — automatic,
# no picker, so this tab stays simple. Talk tab's own voice picker is
# untouched and does not gain these three languages, on purpose.
TRANSLATE_VKEY = {"hr": "hrF", "en": "ukF", "it": "itF", "de": "deF", "fr": "frF"}
TRANSLATE_MODEL = "openai/gpt-oss-120b"


# ----------------------------------------------------------------------
# Translation — the whole interface vocabulary lives here, so switching
# language is instant and needs no reload.
# ----------------------------------------------------------------------
STRINGS = {
    "tab_transcribe":     {"en": "Transcribe",       "hr": "Transkripcija"},
    "tab_talk":           {"en": "Talk",             "hr": "Čitanje"},
    "speech_lang_label":  {"en": "Speech language",  "hr": "Jezik govora"},
    "lang_en":            {"en": "English",          "hr": "Engleski"},
    "lang_hr":            {"en": "Croatian",         "hr": "Hrvatski"},
    "transcript_label":   {"en": "Transcript",       "hr": "Transkript"},
    "correct_btn":        {"en": "Correct",          "hr": "Ispravi"},
    "correct_help":       {"en": "Re-check with the accurate model", "hr": "Provjeri ponovno točnijim modelom"},
    "read_this_btn":      {"en": "Read this",        "hr": "Pročitaj ovo"},
    "read_this_help":     {"en": "Read this text aloud on the Talk tab", "hr": "Pročitaj ovaj tekst naglas na tabu Čitanje"},
    "voice_label":        {"en": "Voice",            "hr": "Glas"},
    "group_hr":           {"en": "HR",               "hr": "HR"},
    "group_en":           {"en": "ENG",              "hr": "ENG"},
    "talk_placeholder":   {"en": "Paste text here, or send it from Transcribe with Read this",
                            "hr": "Zalijepi tekst ovdje, ili ga pošalji s taba Transkripcija pomoću Pročitaj ovo"},
    "read_btn":           {"en": "Read",             "hr": "Čitaj"},
    "stop_btn":           {"en": "Stop",             "hr": "Zaustavi"},
    "stop_help":          {"en": "Interrupts the reading in progress", "hr": "Prekida čitanje u tijeku"},
    "nothing_to_read":    {"en": "Nothing to read yet.", "hr": "Još nema teksta za čitanje."},
    "read_fail":          {"en": "Could not read sentence", "hr": "Nije uspjelo čitanje rečenice"},
    "password_label":     {"en": "Password",         "hr": "Lozinka"},
    "wrong_password":     {"en": "Wrong password.",  "hr": "Pogrešna lozinka."},
    "remember_me":        {"en": "Remember me",      "hr": "Zapamti me"},
    "preparing_audio":    {"en": "Preparing audio…", "hr": "Priprema zvuka…"},
    "transcribing":       {"en": "Transcribing…",    "hr": "Transkribiranje…"},
    "settings_title":     {"en": "Settings",         "hr": "Postavke"},
    "settings_speech":    {"en": "Default speech language", "hr": "Zadani jezik govora"},
    "settings_voice":     {"en": "Default voice",    "hr": "Zadani glas"},
    "help_title":         {"en": "Help",             "hr": "Pomoć"},
    "forget_me":          {"en": "Forget me on this phone", "hr": "Zaboravi me na ovom telefonu"},
    "forgotten":          {"en": "Forgotten.",       "hr": "Zaboravljeno."},
    "no_password_secret": {"en": "No password set in Secrets. Add APP_PASSWORDS (a list) in Streamlit Cloud → Settings → Secrets.",
                            "hr": "Lozinka nije postavljena u Secrets. Dodaj APP_PASSWORDS (listu) u Streamlit Cloud → Settings → Secrets."},
    "no_groq_secret":     {"en": "No Groq key in Secrets. Add GROQ_API_KEYS (a list) in Streamlit Cloud → Settings → Secrets.",
                            "hr": "Nema Groq ključa u Secrets. Dodaj GROQ_API_KEYS (listu) u Streamlit Cloud → Settings → Secrets."},
    "tab_translate":      {"en": "Translate",        "hr": "Prevedi"},
    "translate_src_ph":   {"en": "Paste text to translate", "hr": "Zalijepi tekst za prijevod"},
    "translate_btn":      {"en": "Translate",         "hr": "Prevedi"},
    "translate_fail":     {"en": "Translation failed", "hr": "Prijevod nije uspio"},
    "swap_help":          {"en": "Swap languages",    "hr": "Zamijeni jezike"},
    "page_label":         {"en": "Page",             "hr": "Stranica"},
    "next_page":          {"en": "Next page",         "hr": "Sljedeća stranica"},
    "upload_label":       {"en": "Or pick an audio file", "hr": "Ili odaberi audio datoteku"},
    "chunk_progress":     {"en": "Transcribing part", "hr": "Transkribiram dio"},
    "method_direct":      {"en": "Uploaded as-is.",   "hr": "Poslano izravno."},
    "method_transcoded":  {"en": "Compressed to fit, then transcribed.",
                            "hr": "Sažeto da stane, pa transkribirano."},
    "method_chunked":     {"en": "File was large — split into parts, transcribed, and stitched back together.",
                            "hr": "Datoteka je velika — podijeljena na dijelove, transkribirana, pa spojena natrag."},
    "method_gap":         {"en": "Note: one or more parts could not be transcribed (marked […] in the text).",
                            "hr": "Napomena: jedan ili više dijelova nije transkribiran (označeno […] u tekstu)."},
}


def t(key: str) -> str:
    lang = st.session_state.get("ui_lang", "hr")
    entry = STRINGS.get(key, {})
    return entry.get(lang, entry.get("en", key))


def safe_text(name: str) -> str:
    """Pull a block of prose out of help_text for the current language.

    Deliberately forgiving: help is documentation, and missing documentation
    must never be able to take the app down (see HANDOVER.md, incident 1).
    """
    try:
        block = getattr(help_text, name, {}) or {}
        lang = st.session_state.get("ui_lang", "hr")
        return block.get(lang) or block.get("en") or ""
    except Exception:
        return ""


# ----------------------------------------------------------------------
# Secrets
# ----------------------------------------------------------------------
def app_passwords() -> list:
    pw = list(st.secrets.get("APP_PASSWORDS", []))
    single = st.secrets.get("APP_PASSWORD")   # older single-password secrets still work
    if single and single not in pw:
        pw.append(single)
    return [p for p in pw if p]


def groq_keys() -> list:
    keys = list(st.secrets.get("GROQ_API_KEYS", []))
    single = st.secrets.get("GROQ_API_KEY")
    if single and single not in keys:
        keys.append(single)
    return [k for k in keys if k]


PASSWORDS = app_passwords()
st.session_state.setdefault("ui_lang", "hr")
if not PASSWORDS:
    st.error(t("no_password_secret"))
    st.stop()


def _digest(pw: str) -> str:
    return hashlib.sha256(("maha|" + pw).encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------
# Browser storage bridge — read once per run, before the password gate,
# so "Remember me" can log someone in without them typing anything.
# ----------------------------------------------------------------------
AUTH_LS_KEY = "maha_auth"

# The bridge is declared HERE, in the entrypoint, on purpose. It used to live
# in its own module, and a backwards-incompatible change to its signature took
# the whole app down: Streamlit re-executes app.py on every run but keeps
# imported modules in sys.modules, so a warm process served the NEW app.py
# against the OLD module and every run died with TypeError. Glue this small
# stays with its caller, where it cannot go out of step. See HANDOVER.md.
_LS_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "ls_bridge_frontend")
try:
    _ls_component = components.declare_component("ls_bridge", path=_LS_FRONTEND)
except Exception:
    _ls_component = None


def ls_sync(writes=None, removes=None, stamp=0):
    """Read/write browser localStorage. Returns None if unavailable.

    Persistence is a convenience, never a dependency: if anything here fails
    the app must keep transcribing and reading, just without remembering
    settings. Nothing in this function is allowed to raise.
    """
    if _ls_component is None:
        return None
    try:
        return _ls_component(writes=writes or {}, removes=removes or [],
                             stamp=stamp, key="ls_sync", default=None)
    except Exception:
        return None


_pending = st.session_state.pop("_pending_ls", None)
if _pending:
    st.session_state["_ls_stamp"] = st.session_state.get("_ls_stamp", 0) + 1
    _ls = ls_sync(writes=_pending.get("writes"), removes=_pending.get("removes"),
                  stamp=st.session_state["_ls_stamp"])
else:
    _ls = ls_sync(stamp=st.session_state.get("_ls_stamp", 0))

LS_DATA = (_ls or {}).get("data") or {}
STORAGE_OK = _ls is not None


def queue_ls(writes=None, removes=None):
    """Queue a localStorage change for the next run of the bridge."""
    pend = st.session_state.get("_pending_ls") or {"writes": {}, "removes": []}
    pend["writes"].update(writes or {})
    pend["removes"].extend(removes or [])
    st.session_state["_pending_ls"] = pend


# ----------------------------------------------------------------------
# Password gate. The matched password also names the settings profile.
# ----------------------------------------------------------------------
def _try_remembered():
    token = LS_DATA.get(AUTH_LS_KEY)
    if not token:
        return
    for p in PASSWORDS:
        if hmac.compare_digest(token, _digest(p)):
            st.session_state["_authed"] = True
            st.session_state["_user"] = p
            return


if not st.session_state.get("_authed"):
    _try_remembered()


def check_password() -> bool:
    def _entered():
        entered = st.session_state.get("_pw_input", "")
        matched = next((p for p in PASSWORDS if hmac.compare_digest(entered, p)), None)
        st.session_state["_authed"] = matched is not None
        if matched is not None:
            st.session_state["_user"] = matched
            if st.session_state.get("_remember_me"):
                queue_ls(writes={AUTH_LS_KEY: _digest(matched)})
        st.session_state["_pw_input"] = ""

    def _set_login_lang(code):
        st.session_state["login_lang"] = code

    if st.session_state.get("_authed"):
        return True

    st.session_state.setdefault("login_lang", "hr")
    lcols = st.columns(len(LANGS5))
    for col, code in zip(lcols, LANGS5):
        col.button(
            code.upper(), key="login_pill_" + code, use_container_width=True,
            type="primary" if st.session_state["login_lang"] == code else "secondary",
            on_click=_set_login_lang, args=(code,),
        )

    ll = st.session_state["login_lang"]
    labels = help_text.LOGIN_LABELS.get(ll, help_text.LOGIN_LABELS["hr"])
    st.markdown(help_text.WELCOME.get(ll, help_text.WELCOME["hr"]))
    st.text_input(labels["password"], type="password", key="_pw_input", on_change=_entered)
    st.checkbox(labels["remember"], key="_remember_me", value=True)
    if st.session_state.get("_authed") is False:
        st.error(labels["wrong"])
    st.markdown("---")
    st.markdown(help_text.LOGIN_GUIDE.get(ll, help_text.LOGIN_GUIDE["hr"]))
    return False


if not check_password():
    st.stop()

USER = st.session_state.get("_user") or "shared"

KEYS = groq_keys()
if not KEYS:
    st.error(t("no_groq_secret"))
    st.stop()


# ----------------------------------------------------------------------
# Groq
# ----------------------------------------------------------------------
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


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """openai/gpt-oss-120b, chosen by testing against qwen/qwen3.6-27b (the
    other model Groq recommends for quality): gpt-oss-120b returned four
    clean translations with correct grammar including French subjunctive.
    qwen wrapped two of four in a visible multi-paragraph <think> block —
    once so long the reply was cut off before any translation appeared at
    all. See HANDOVER.md."""
    start = st.session_state.get("_key_idx", 0) % len(KEYS)
    last_err = None
    for offset in range(len(KEYS)):
        idx = (start + offset) % len(KEYS)
        client = Groq(api_key=KEYS[idx])
        try:
            resp = client.chat.completions.create(
                model=TRANSLATE_MODEL,
                messages=[{"role": "user", "content":
                    f"Translate the following {source_lang} text into {target_lang}. "
                    f"Output ONLY the translation, nothing else, no quotes, no notes.\n\n{text}"}],
                temperature=0.2,
            )
            st.session_state["_key_idx"] = idx
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All Groq keys failed ({last_err})")


def transcode_to_flac(in_path: str) -> str:
    """ffmpeg auto-detects input format from content, not extension, so this
    works on whatever a file picker hands it — mp3, m4a, ogg, wav, anything
    ffmpeg reads. Same 16kHz mono FLAC target Groq documents."""
    out_path = in_path + ".flac"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", in_path, "-ar", "16000", "-ac", "1",
             "-map", "0:a", "-c:a", "flac", out_path],
            check=True, capture_output=True, timeout=1800,
        )
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found on the server — check packages.txt.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed: {e.stderr.decode(errors='ignore')[-300:]}")
    return out_path


def to_flac16k(wav_bytes: bytes) -> str:
    """Downsample the browser recording to exactly what Whisper on Groq
    wants: 16kHz mono FLAC. This is Groq's own documented ffmpeg command."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        in_path = f.name
    try:
        return transcode_to_flac(in_path)
    finally:
        os.remove(in_path)


# ----------------------------------------------------------------------
# Big files: Groq's own hard limit is 25MB. Three tiers, in order, each
# only attempted if the one before didn't already produce something small
# enough — never all three unconditionally, and a failure in one tier falls
# through to the next rather than failing the whole job.
#   1. Already small enough — upload exactly as given, no transcoding cost.
#   2. Transcode to 16kHz mono FLAC (routinely 5-10x smaller than a raw
#      stereo recording) and try again.
#   3. Still too big — split the transcoded audio into fixed-length chunks
#      and transcribe each one. One chunk failing (even after that chunk's
#      own full Groq key rotation) leaves a marker and does not lose the
#      rest of the transcript.
# ----------------------------------------------------------------------
GROQ_MAX_MB = 25
SAFE_MB = 20                      # matches Baba's own safety margin
SAFE_BYTES = SAFE_MB * 1024 * 1024
CHUNK_SECONDS = 600               # 10 minutes; well under the size limit
                                   # even for dense speech at 16kHz mono FLAC


def split_into_chunks(flac_path: str, chunk_seconds: int = CHUNK_SECONDS) -> list:
    out_dir = tempfile.mkdtemp()
    pattern = os.path.join(out_dir, "chunk_%04d.flac")
    subprocess.run(
        ["ffmpeg", "-y", "-i", flac_path, "-f", "segment",
         "-segment_time", str(chunk_seconds), "-ar", "16000", "-ac", "1",
         "-c:a", "flac", pattern],
        check=True, capture_output=True, timeout=3600,
    )
    return sorted(glob.glob(os.path.join(out_dir, "chunk_*.flac")))


def transcribe_any_size(path: str, model: str, language: str, progress_cb=None):
    """Returns (text, method, reusable_path). reusable_path is whichever file
    actually got transcribed — the original for 'direct', the transcoded
    FLAC for 'transcoded' or 'chunked' — so a later Correct pass (a different
    model, not a different file) always has something valid to work from."""
    size = os.path.getsize(path)

    # Tier 1: small enough already.
    if size <= SAFE_BYTES:
        try:
            return transcribe(path, model, language), "direct", path
        except Exception:
            pass   # even a small file can fail to upload; fall through

    # Tier 2: transcode, then re-check.
    flac_path = transcode_to_flac(path)
    flac_size = os.path.getsize(flac_path)
    if flac_size <= SAFE_BYTES:
        try:
            return transcribe(flac_path, model, language), "transcoded", flac_path
        except Exception:
            pass   # fall through to chunking rather than give up

    # Tier 3: chunk and stitch. A chunk that fails leaves a gap marker
    # instead of aborting everything already transcribed successfully.
    chunk_paths = split_into_chunks(flac_path)
    parts, ok_count = [], 0
    for i, cp in enumerate(chunk_paths):
        if progress_cb:
            progress_cb(i, len(chunk_paths))
        try:
            parts.append(transcribe(cp, model, language))
            ok_count += 1
        except Exception:
            parts.append("[…]")
    if not ok_count:
        raise RuntimeError("Every chunk failed to transcribe — check the Groq keys.")
    return " ".join(p for p in parts if p), "chunked", flac_path


# ----------------------------------------------------------------------
# Per-user settings — session_state, then browser localStorage, then a
# server-side file. Streamlit Community Cloud doesn't guarantee disk across
# restarts, so the file is a same-instance convenience, not a durable store;
# localStorage is the one that really survives.
# ----------------------------------------------------------------------
DEFAULT_SETTINGS = {"ui_lang": "hr", "speech_lang": "hr", "voice": "Gabrijela"}
SETTINGS_LS_KEY = f"maha_settings_{USER}"


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
    """Seed session_state. Only safe before the matching widgets render."""
    for k in ("ui_lang", "speech_lang", "voice"):
        if values.get(k):
            st.session_state[k] = values[k]


if "_settings_bootstrapped" not in st.session_state:
    _apply_settings(DEFAULT_SETTINGS)
    _apply_settings(_load_server_settings(USER))
    st.session_state["_settings_bootstrapped"] = True

if LS_DATA.get(SETTINGS_LS_KEY) and not st.session_state.get("_ls_applied"):
    try:
        _apply_settings(json.loads(LS_DATA[SETTINGS_LS_KEY]))
    except Exception:
        pass
    st.session_state["_ls_applied"] = True


def persist_settings():
    values = {k: st.session_state.get(k) for k in ("ui_lang", "speech_lang", "voice")}
    _save_server_settings(USER, values)
    queue_ls(writes={SETTINGS_LS_KEY: json.dumps(values)})


def set_ui_lang(lang: str):
    st.session_state["ui_lang"] = lang
    persist_settings()


def set_speech_lang(lang: str):
    st.session_state["speech_lang"] = lang
    persist_settings()


def pick_voice(name: str):
    st.session_state["voice"] = name
    persist_settings()


def forget_me():
    queue_ls(removes=[AUTH_LS_KEY])
    st.session_state["_forgotten"] = True


def voice_picker(prefix: str):
    """Croatian group first, then English, each under its own label."""
    current = st.session_state.get("voice", "Gabrijela")
    for lang, label_key in (("hr", "group_hr"), ("en", "group_en")):
        st.caption(t(label_key))
        cols = st.columns(len(VOICES_BY_LANG[lang]))
        for col, name in zip(cols, VOICES_BY_LANG[lang]):
            col.button(
                name, key=f"{prefix}_{name}", use_container_width=True,
                type="primary" if name == current else "secondary",
                on_click=pick_voice, args=(name,),
            )


# ----------------------------------------------------------------------
# Gear — settings + help, upper right. Nothing else in the top bar.
# ----------------------------------------------------------------------
_, gear_col = st.columns([6, 1])
with gear_col:
    with st.popover("⚙️", use_container_width=False):
        lang_now = st.session_state.get("ui_lang", "hr")
        lcol1, lcol2 = st.columns(2)
        lcol1.button("[HR]", key="ui_hr", use_container_width=True,
                     type="primary" if lang_now == "hr" else "secondary",
                     on_click=set_ui_lang, args=("hr",))
        lcol2.button("[ENG]", key="ui_en", use_container_width=True,
                     type="primary" if lang_now == "en" else "secondary",
                     on_click=set_ui_lang, args=("en",))

        st.caption(t("settings_speech"))
        scol1, scol2 = st.columns(2)
        speech_now = st.session_state.get("speech_lang", "hr")
        scol1.button(t("lang_hr"), key="sp_hr", use_container_width=True,
                     type="primary" if speech_now == "hr" else "secondary",
                     on_click=set_speech_lang, args=("hr",))
        scol2.button(t("lang_en"), key="sp_en", use_container_width=True,
                     type="primary" if speech_now == "en" else "secondary",
                     on_click=set_speech_lang, args=("en",))

        st.caption(t("settings_voice"))
        voice_picker("setvoice")

        with st.expander(t("help_title")):
            st.markdown(safe_text("HELP"))

        st.button(t("forget_me"), key="forget_btn", use_container_width=True,
                  on_click=forget_me)
        if st.session_state.pop("_forgotten", False):
            st.caption(t("forgotten"))
        st.caption(APP_VERSION)


# ----------------------------------------------------------------------
# Tab bar. A segmented control rather than st.tabs, because st.tabs cannot
# be switched from Python — its session_state updates but the visible
# selection does not follow (verified in a browser), and Read this has to
# be able to move the user to the Talk tab by itself.
# ----------------------------------------------------------------------
st.session_state.setdefault("active_tab", "transcribe")
st.segmented_control(
    "nav", ["transcribe", "talk", "translate"], format_func=lambda k: t("tab_" + k),
    key="active_tab", required=True, label_visibility="collapsed",
)
active = st.session_state.get("active_tab") or "transcribe"


def do_correct():
    try:
        path = st.session_state.get("flac_path")
        lang = st.session_state.get("last_lang", "hr")
        if not path or not os.path.exists(path):
            raise RuntimeError("Original audio is no longer available.")
        corrected, method, reusable = transcribe_any_size(path, CORRECTION_MODEL, lang)
        st.session_state["transcript_box"] = corrected
        st.session_state["flac_path"] = reusable
        st.session_state["_transcribe_method"] = method
    except Exception as e:
        st.session_state["_correct_error"] = str(e)


def read_this():
    """Move to the Talk tab, carry the text over, pick the voice that matches
    the language just transcribed, and start reading — no popup, no extra tap."""
    st.session_state["talk_text"] = st.session_state.get("transcript_box", "")
    lang = st.session_state.get("last_lang", "hr")
    current = st.session_state.get("voice", "Gabrijela")
    if VOICE_LANG.get(current) != lang:
        st.session_state["voice"] = VOICES_BY_LANG[lang][0]
    st.session_state["active_tab"] = "talk"
    st.session_state["_auto_read"] = True


def _subtitle(text: str) -> str:
    return f'<div class="subtitle-box">{html.escape(text)}</div>'


def read_sentences_live(raw: str, vkey: str, doc_slot, sub_slot, audio_slot,
                        page_key: str, page_slot, force_page=False):
    """Shared by Talk and Translate: synthesize and play one sentence at a
    time, highlighting the current one in doc_slot and mirroring it alone in
    sub_slot (the NaturalReader-style subtitle box). No disk cache, no
    word-level timing — see HANDOVER.md for why.

    Long text is split into pages (tk.paginate) so one document never becomes
    one unbroken, uninterruptible reading session. A new page starts reading
    the instant Next page is pressed — no message, no waiting, no sense of
    having hit a limit."""
    try:
        sentences = tk.sentences_of(raw)
    except Exception as e:          # never let the engine take the page down
        sentences = []
        st.error(f"{t('read_fail')}: {e}")
    if not sentences:
        st.info(t("nothing_to_read"))
        return

    pages = tk.paginate(sentences)
    n_pages = len(pages)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    if st.session_state.get(page_key + "_digest") != digest:
        st.session_state[page_key] = 0
        st.session_state[page_key + "_digest"] = digest
    page_idx = min(max(st.session_state.get(page_key, 0), 0), n_pages - 1)
    page_sentences = pages[page_idx]

    if n_pages > 1:
        page_slot.caption(f"{t('page_label')} {page_idx + 1}/{n_pages}")

    for i, sent in enumerate(page_sentences):
        parts = []
        for j, s in enumerate(page_sentences):
            safe = html.escape(s)
            if j == i:
                parts.append(
                    '<span style="background:#e0a340;color:#0d0d0d;'
                    'border-radius:4px;padding:1px 4px;">' + safe + "</span>"
                )
            else:
                parts.append(safe)
        doc_slot.markdown(" ".join(parts), unsafe_allow_html=True)
        sub_slot.markdown(_subtitle(sent), unsafe_allow_html=True)
        try:
            audio_bytes, dur = tk.synth_sentence(sent, vkey)
        except Exception as e:
            st.error(f"{t('read_fail')} {i + 1}: {e}")
            break
        audio_slot.audio(audio_bytes, format="audio/mp3", autoplay=True)
        time.sleep(dur + 0.15)

    doc_slot.markdown(html.escape(" ".join(page_sentences)))
    sub_slot.markdown(_subtitle(""), unsafe_allow_html=True)

    if page_idx + 1 < n_pages:
        def _next_page():
            st.session_state[page_key] = page_idx + 1
            st.session_state[page_key + "_auto"] = True
        page_slot.button(
            f"▶ {t('next_page')} ({page_idx + 2}/{n_pages})",
            key=page_key + "_nextbtn", use_container_width=True,
            on_click=_next_page,
        )


def _set_translate_lang(which: str, code: str):
    st.session_state["translate_" + which] = code


def swap_translate_langs():
    src = st.session_state.get("translate_src", "hr")
    tgt = st.session_state.get("translate_tgt", "en")
    st.session_state["translate_src"] = tgt
    st.session_state["translate_tgt"] = src
    src_text = st.session_state.get("translate_src_text", "")
    out_text = st.session_state.get("translate_out", "")
    st.session_state["translate_src_text"] = out_text
    st.session_state["translate_out"] = src_text


def do_translate():
    text = (st.session_state.get("translate_src_text") or "").strip()
    if not text:
        return
    src = st.session_state.get("translate_src", "hr")
    tgt = st.session_state.get("translate_tgt", "en")
    try:
        st.session_state["translate_out"] = translate_text(text, LANG_FULL[src], LANG_FULL[tgt])
    except Exception as e:
        st.session_state["_translate_error"] = f"{t('translate_fail')}: {e}"


def lang_pills(prefix: str, which: str, current: str):
    cols = st.columns(len(LANGS5))
    for col, code in zip(cols, LANGS5):
        col.button(
            code.upper(), key=f"{prefix}_{code}", use_container_width=True,
            type="primary" if code == current else "secondary",
            on_click=_set_translate_lang, args=(which, code),
        )


# ----------------------------------------------------------------------
# Transcribe
# ----------------------------------------------------------------------
if active == "transcribe":
    speech_now = st.session_state.get("speech_lang", "hr")
    lcol1, lcol2 = st.columns(2)
    lcol1.button(t("lang_hr"), key="tr_hr", use_container_width=True,
                 type="primary" if speech_now == "hr" else "secondary",
                 on_click=set_speech_lang, args=("hr",))
    lcol2.button(t("lang_en"), key="tr_en", use_container_width=True,
                 type="primary" if speech_now == "en" else "secondary",
                 on_click=set_speech_lang, args=("en",))
    lang_code = speech_now

    audio = st.audio_input(t("tab_transcribe"), sample_rate=48000, label_visibility="collapsed")

    if audio is not None:
        digest = hashlib.md5(audio.getvalue()).hexdigest()
        if st.session_state.get("_digest") != digest:
            old_flac = st.session_state.get("flac_path")
            if old_flac and os.path.exists(old_flac):
                os.remove(old_flac)
            st.session_state["_digest"] = digest
            try:
                with st.spinner(t("preparing_audio")):
                    flac_path = to_flac16k(audio.getvalue())
                with st.spinner(t("transcribing")):
                    text = transcribe(flac_path, PRIMARY_MODEL, lang_code)
                st.session_state["transcript_box"] = text
                st.session_state["flac_path"] = flac_path
                st.session_state["last_lang"] = lang_code
                st.session_state["_transcribe_method"] = "direct"
            except Exception as e:
                st.error(str(e))

    uploaded = st.file_uploader(
        t("upload_label"),
        type=["mp3", "wav", "m4a", "flac", "ogg", "aac", "wma", "mp4", "webm", "mpga", "mpeg", "opus"],
        label_visibility="collapsed", key="audio_upload",
    )
    if uploaded is not None:
        file_digest = hashlib.md5(uploaded.getvalue()).hexdigest()
        if st.session_state.get("_file_digest") != file_digest:
            old_flac = st.session_state.get("flac_path")
            if old_flac and os.path.exists(old_flac):
                try:
                    os.remove(old_flac)
                except Exception:
                    pass
            st.session_state["_file_digest"] = file_digest
            suffix = "_" + "".join(c for c in uploaded.name if c.isalnum() or c in "._-")
            tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tmp.write(uploaded.getvalue())
            tmp.close()
            progress_bar = st.progress(0.0, text=t("preparing_audio"))
            try:
                def _cb(i, n):
                    progress_bar.progress((i + 1) / n, text=f"{t('chunk_progress')} {i + 1}/{n}")
                text, method, reusable = transcribe_any_size(tmp.name, PRIMARY_MODEL, lang_code, progress_cb=_cb)
                progress_bar.empty()
                st.session_state["transcript_box"] = text
                st.session_state["last_lang"] = lang_code
                st.session_state["flac_path"] = reusable
                st.session_state["_transcribe_method"] = method
            except Exception as e:
                progress_bar.empty()
                st.error(str(e))
                st.session_state["flac_path"] = None
            finally:
                # tmp.name itself is only still needed if tier 1 ('direct')
                # kept it as the reusable path; anything else made its own
                # transcoded/chunked files and the raw upload can go.
                if st.session_state.get("flac_path") != tmp.name and os.path.exists(tmp.name):
                    try:
                        os.remove(tmp.name)
                    except Exception:
                        pass

    if "transcript_box" in st.session_state:
        st.text_area(t("transcript_label"), key="transcript_box", height=200,
                     label_visibility="collapsed")

        bcol1, bcol2 = st.columns(2)
        bcol1.button(t("correct_btn"), use_container_width=True, key="correct_btn",
                     help=t("correct_help"), on_click=do_correct)
        bcol2.button(t("read_this_btn"), use_container_width=True, key="bridge_btn",
                     help=t("read_this_help"), on_click=read_this)

        if st.session_state.get("_correct_error"):
            st.error(st.session_state.pop("_correct_error"))

        method = st.session_state.get("_transcribe_method")
        if method and method != "direct":
            st.caption(t("method_" + method))
            if "[…]" in (st.session_state.get("transcript_box") or ""):
                st.caption(t("method_gap"))

# ----------------------------------------------------------------------
# Talk
# ----------------------------------------------------------------------
elif active == "talk":
    voice_picker("talkvoice")
    vkey = VOICE_TO_VKEY[st.session_state.get("voice", "Gabrijela")]

    st.text_area(t("tab_talk"), key="talk_text", height=150,
                 label_visibility="collapsed", placeholder=t("talk_placeholder"))

    rcol1, rcol2 = st.columns(2)
    read_clicked = rcol1.button(t("read_btn"), use_container_width=True, key="read_btn")
    rcol2.button(t("stop_btn"), use_container_width=True, key="stop_btn", help=t("stop_help"))

    doc_slot = st.empty()
    sub_slot = st.empty()
    audio_slot = st.empty()
    page_slot = st.empty()

    if read_clicked or st.session_state.pop("_auto_read", False) or st.session_state.pop("talk_page_auto", False):
        raw = (st.session_state.get("talk_text") or "").strip()
        read_sentences_live(raw, vkey, doc_slot, sub_slot, audio_slot, "talk_page", page_slot)
    else:
        sub_slot.markdown(_subtitle(""), unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Translate — Groq (openai/gpt-oss-120b) between five European languages,
# then an optional Read in the target language's own neural voice.
# ----------------------------------------------------------------------
else:
    st.session_state.setdefault("translate_src", "hr")
    st.session_state.setdefault("translate_tgt", "en")

    lang_pills("srcpill", "src", st.session_state["translate_src"])
    st.text_area("src", key="translate_src_text", height=120,
                 label_visibility="collapsed", placeholder=t("translate_src_ph"))

    _, swap_col, _ = st.columns([2.5, 1, 2.5])
    swap_col.button("⇄", key="swap_langs", use_container_width=True,
                     help=t("swap_help"), on_click=swap_translate_langs)

    lang_pills("tgtpill", "tgt", st.session_state["translate_tgt"])
    st.button(t("translate_btn"), key="do_translate_btn", use_container_width=True,
              on_click=do_translate)

    if st.session_state.get("_translate_error"):
        st.error(st.session_state.pop("_translate_error"))

    if "translate_out" in st.session_state:
        st.text_area("out", key="translate_out", height=150, label_visibility="collapsed")

        tr_col1, tr_col2 = st.columns(2)
        tread_clicked = tr_col1.button(t("read_btn"), use_container_width=True, key="tr_read_btn")
        tr_col2.button(t("stop_btn"), use_container_width=True, key="tr_stop_btn", help=t("stop_help"))

        tdoc_slot = st.empty()
        tsub_slot = st.empty()
        taudio_slot = st.empty()
        tpage_slot = st.empty()

        if tread_clicked or st.session_state.pop("translate_page_auto", False):
            raw = (st.session_state.get("translate_out") or "").strip()
            tgt = st.session_state.get("translate_tgt", "en")
            vkey = TRANSLATE_VKEY.get(tgt, "ukF")
            read_sentences_live(raw, vkey, tdoc_slot, tsub_slot, taudio_slot, "translate_page", tpage_slot)
        else:
            tsub_slot.markdown(_subtitle(""), unsafe_allow_html=True)
