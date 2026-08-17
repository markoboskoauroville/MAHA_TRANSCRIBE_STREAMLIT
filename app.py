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

from ttt import keyring as kr
from ttt import providers as PROVIDERS
from ttt.store import Store
from ttt.usage import UsageLog, UNIT_SECONDS, UNIT_CHARS
from ttt import transform as TR
from ttt import routing as RO
from ttt import audio as ttt_audio
from ttt import a11y
from ttt import theme
from ttt import gate
from ttt import copybtn

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

    /* --- PILL ROWS -------------------------------------------------
       Streamlit stacks columns vertically below ~640px, which turned
       every small choice (HR/EN/IT/DE/FR, voices, engines) into a
       column of full-width slabs on a phone. Keep those rows
       horizontal and let them wrap, and size each button to its own
       text rather than the container. Small pills, in a row. */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0.4rem !important;
        align-items: center;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        width: auto !important;
        flex: 0 0 auto !important;
        min-width: 0 !important;
    }
    div[data-testid="stColumn"] div[data-testid="stVerticalBlock"] { gap: 0.4rem; }

    /* --- PATCH BAY -------------------------------------------------
       The pill rules above deliberately let columns size to their own
       content, which is right everywhere else and WRONG here: a patch
       bay whose columns do not line up between rows is not a grid, it is
       jumbled text. Inside the bay, restore equal columns that never
       wrap, so every crosspoint sits under its own heading. */
    .st-key-patchbay div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 0.2rem !important;
    }
    /* Must out-specify the global pill rule above, which is
       div[stHorizontalBlock] > div[stColumn] — a child combinator of two
       attribute selectors. !important alone does NOT win that; the
       selector has to be at least as specific, hence the full path. */
    .st-key-patchbay div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        flex: 1 1 0 !important;
        width: auto !important;
        min-width: 0 !important;
    }
    /* The jack itself. The stButton wrapper is auto-width by the pill
       rule above, so widening only the <button> leaves it a sliver — both
       have to be told. Round, centred, and sized like something you press
       with a finger, not a sliver of a pill. */
    .st-key-patchbay div[data-testid="stButton"] {
        width: 100% !important;
        display: flex;
        justify-content: center;
    }
    .st-key-patchbay .stButton button {
        width: 38px !important;
        height: 38px !important;
        min-width: 38px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        font-size: 0.95rem;
        line-height: 1;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    /* Column headings and engine names centred over their own column so
       the eye can run straight down a column and along a row. */
    .st-key-patchbay div[data-testid="stCaptionContainer"] {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 38px;
    }
    .st-key-patchbay div[data-testid="stColumn"]:first-child
        div[data-testid="stCaptionContainer"] { justify-content: flex-start; }
    .st-key-patchbay div[data-testid="stCaptionContainer"] p {
        font-size: 0.72rem;
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .stButton button {
        border-radius: 999px;
        width: auto;
        min-width: 0;
        padding: 0.3rem 1.05rem;
        white-space: nowrap;
    }
    /* Buttons that genuinely are the main action of their row keep
       their full width — only the small choosers are shrunk. */
    .stButton button[kind="primaryFormSubmit"],
    .stButton button[kind="secondaryFormSubmit"] { width: 100%; }

    .st-key-correct_btn button { background-color: #fbbf24; color: #0b0d10; border-color: #fbbf24; }
    .st-key-correct_btn button:hover { background-color: #6fe0ee; border-color: #6fe0ee; }
    .subtitle-box {
        border: 1px solid #23303d; border-radius: 10px; padding: 16px 14px;
        min-height: 92px; font-size: 1.45rem; line-height: 1.45;
        color: #f2ddb4; background: #141a21;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# The visual language first (colour, border, radius, spacing), then the
# reading stylesheet on top (size, line height, targets). That order
# matters: a11y must be able to override anything theme sets about text,
# because the reader's chosen size outranks the design.
st.markdown(theme.css(), unsafe_allow_html=True)

# The reading stylesheet, regenerated from the person's own text size on
# every run. Injected AFTER the base sheet so it wins, and kept separate
# so the base sheet stays about layout while this one is only about
# readability. See ttt/a11y.py for which WCAG criteria each rule serves.
st.markdown(a11y.css(st.session_state.get("text_scale", a11y.DEFAULT_SCALE)),
            unsafe_allow_html=True)

APP_VERSION = "v31 (a)"

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
    "tab_read":           {"en": "Read",             "hr": "Čitaonica"},
    "read_paste_ph":      {"en": "Paste a text here and press Read",
                            "hr": "Zalijepi tekst ovdje i pritisni Čitaj"},
    "read_start":         {"en": "Read",             "hr": "Čitaj"},
    "read_save":          {"en": "Keep",             "hr": "Sačuvaj"},
    "read_archive":       {"en": "Archive",          "hr": "Arhiva"},
    "read_open":          {"en": "Open",             "hr": "Otvori"},
    "read_delete":        {"en": "Delete",           "hr": "Obriši"},
    "read_empty":         {"en": "Nothing kept yet.", "hr": "Još ništa nije sačuvano."},
    "read_saved":         {"en": "Kept.",            "hr": "Sačuvano."},
    "read_speed":         {"en": "Speed",            "hr": "Brzina"},
    "read_gap":           {"en": "Pause between sentences", "hr": "Pauza između rečenica"},
    "read_autosave":      {"en": "Keep texts automatically", "hr": "Automatski čuvaj tekstove"},
    "ai_ask":             {"en": "Tell the AI what to do with this text",
                            "hr": "Reci AI-u što da napravi s ovim tekstom"},
    "ai_apply":           {"en": "Apply",             "hr": "Primijeni"},
    "ai_undo":            {"en": "Undo",              "hr": "Vrati"},
    "ai_working":         {"en": "Working…",          "hr": "Radim…"},
    "ai_fail":            {"en": "The AI could not do that",
                            "hr": "AI to nije mogao napraviti"},
    "routing_title":      {"en": "Which engine does what", "hr": "Koji pogon što radi"},
    "model_label":        {"en": "Model",             "hr": "Model"},
    "model_refresh":      {"en": "Refresh model list", "hr": "Osvježi popis modela"},
    "model_live":         {"en": "from the provider",  "hr": "s poslužitelja"},
    "model_static":       {"en": "built-in list (this provider has no model list)",
                            "hr": "ugrađen popis (ovaj pogon nema popis modela)"},
    "routing_nokey":      {"en": "No working key for this engine yet",
                            "hr": "Još nema ispravnog ključa za ovaj pogon"},
    "routing_none":       {"en": "no engine available", "hr": "nema dostupnog pogona"},
    "admin_title":        {"en": "Owner — usage logging", "hr": "Vlasnik — zapis korištenja"},
    "admin_on":           {"en": "Connected to the sheet", "hr": "Spojeno na tablicu"},
    "admin_off":          {"en": "Not connected. See apps_script/SETUP.md.",
                            "hr": "Nije spojeno. Vidi apps_script/SETUP.md."},
    "admin_sent":         {"en": "Signals sent this session", "hr": "Poslano ovu sesiju"},
    "admin_failed":       {"en": "Failed",              "hr": "Neuspjelo"},
    "admin_session":      {"en": "Session length (min)", "hr": "Trajanje sesije (min)"},
    "admin_users":        {"en": "Users who can log in", "hr": "Korisnici koji se mogu prijaviti"},
    "admin_test":         {"en": "Send a test signal",  "hr": "Pošalji probni signal"},
    "admin_test_sent":    {"en": "Test signal sent — check the sheet.",
                            "hr": "Probni signal poslan — provjeri tablicu."},
    "read_storage_note":  {"en": "Texts are kept in this browser only, never the audio. Clearing browser data removes them.",
                            "hr": "Tekstovi se čuvaju samo u ovom pregledniku, nikad zvuk. Brisanje podataka preglednika ih uklanja."},
    "translate_src_ph":   {"en": "Paste text to translate", "hr": "Zalijepi tekst za prijevod"},
    "translate_btn":      {"en": "Translate",         "hr": "Prevedi"},
    "translate_fail":     {"en": "Translation failed", "hr": "Prijevod nije uspio"},
    "swap_help":          {"en": "Swap languages",    "hr": "Zamijeni jezike"},
    "page_label":         {"en": "Page",             "hr": "Stranica"},
    "next_page":          {"en": "Next page",         "hr": "Sljedeća stranica"},
    "upload_label":       {"en": "Or pick an audio file", "hr": "Ili odaberi audio datoteku"},
    "chunk_waiting":      {"en": "Keys are resting — waiting {s}s and trying part {i} again",
                            "hr": "Ključevi se odmaraju — čekam {s}s i ponovno pokušavam dio {i}"},
    "chunk_progress":     {"en": "Transcribing part", "hr": "Transkribiram dio"},
    "method_direct":      {"en": "Uploaded as-is.",   "hr": "Poslano izravno."},
    "method_transcoded":  {"en": "Compressed to fit, then transcribed.",
                            "hr": "Sažeto da stane, pa transkribirano."},
    "method_chunked":     {"en": "File was large — split into parts, transcribed, and stitched back together.",
                            "hr": "Datoteka je velika — podijeljena na dijelove, transkribirana, pa spojena natrag."},
    "method_gap":         {"en": "Note: one or more parts could not be transcribed (marked […] in the text).",
                            "hr": "Napomena: jedan ili više dijelova nije transkribiran (označeno […] u tekstu)."},
    "speechify_title":    {"en": "Speechify (premium voices)", "hr": "Speechify (premium glasovi)"},
    "key_file_label":     {"en": "Or pick a key file",  "hr": "Ili odaberi datoteku s ključem"},
    "key_paste_label":    {"en": "Paste key(s)",        "hr": "Zalijepi ključ(eve)"},
    "key_paste_ph":       {"en": "Paste one or more keys, any messy text is fine",
                            "hr": "Zalijepi jedan ili više ključeva, može i neuredan tekst"},
    "import_keys_btn":    {"en": "Import keys",         "hr": "Uvezi ključeve"},
    "test_keys_btn":      {"en": "Test keys",           "hr": "Testiraj ključeve"},
    "no_keys_found":      {"en": "No key found in that.", "hr": "Nije pronađen nijedan ključ."},
    "keys_added":         {"en": "New keys added",      "hr": "Novih ključeva dodano"},
    "keys_good":          {"en": "working",             "hr": "rade"},
    "keys_bad":           {"en": "rejected",            "hr": "odbijeno"},
    "gate_wait":          {"en": "Please wait {s} before trying again.",
                            "hr": "Pričekaj {s} prije novog pokušaja."},
    "gate_min":           {"en": "min",               "hr": "min"},
    "gate_sec":           {"en": "s",                 "hr": "s"},
    "clear_btn":          {"en": "clear",             "hr": "obriši"},
    "grammar_btn":        {"en": "GRAMMAR",           "hr": "GRAMATIKA"},
    "reshape_btn":        {"en": "RE-SHAPE",          "hr": "PREOBLIKUJ"},
    "copy_idle":          {"en": "Copy",              "hr": "Kopiraj"},
    "copy_busy":          {"en": "Copying…",          "hr": "Kopiram…"},
    "copy_done":          {"en": "Copied ✓",          "hr": "Kopirano ✓"},
    "copy_done_short":    {"en": "OK",                "hr": "OK"},
    "copy_failed":        {"en": "Could not copy",    "hr": "Nije uspjelo"},
    "text_smaller":       {"en": "Smaller text",      "hr": "Manje slovo"},
    "text_bigger":        {"en": "Bigger text",       "hr": "Veće slovo"},
    "text_size":          {"en": "Text size",         "hr": "Veličina slova"},
    "vc_title":           {"en": "All Speechify voices", "hr": "Svi Speechify glasovi"},
    "vc_load":            {"en": "Load voice list",   "hr": "Učitaj popis glasova"},
    "vc_loading":         {"en": "Loading…",          "hr": "Učitavam…"},
    "vc_search":          {"en": "Search by name",    "hr": "Traži po imenu"},
    "vc_any":             {"en": "Any",               "hr": "Sve"},
    "vc_count":           {"en": "voices",            "hr": "glasova"},
    "vc_current":         {"en": "Current voice",     "hr": "Trenutni glas"},
    "vc_pick":            {"en": "Use",               "hr": "Koristi"},
    "vc_note":            {"en": "Any voice can read any language. Croatian in an English voice works and stays in time.",
                            "hr": "Svaki glas može čitati bilo koji jezik. Hrvatski engleskim glasom radi i ostaje u ritmu."},
    "voice_engine":       {"en": "Voice engine",        "hr": "Glasovni pogon"},
    "engine_edge":        {"en": "Standard",            "hr": "Standardni"},
    "engine_speechify":   {"en": "Speechify",           "hr": "Speechify"},
    "no_label":           {"en": "(no label)",          "hr": "(bez oznake)"},
    "test_btn":           {"en": "Test",                "hr": "Testiraj"},
    "assemblyai_title":   {"en": "AssemblyAI (accurate transcription)", "hr": "AssemblyAI (točnija transkripcija)"},
    "engine_groq":        {"en": "Groq (free)",         "hr": "Groq (besplatno)"},
    "engine_assemblyai":  {"en": "AssemblyAI",          "hr": "AssemblyAI"},
    "transcribe_engine":  {"en": "Transcription engine", "hr": "Pogon za transkripciju"},
    "aai_stage_upload":   {"en": "Uploading to AssemblyAI…", "hr": "Šaljem na AssemblyAI…"},
    "aai_stage_queue":    {"en": "Queued…",              "hr": "U redu čekanja…"},
    "aai_stage_process":  {"en": "Transcribing…",        "hr": "Transkribiram…"},
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


def admin_user() -> str:
    """Who owns this deployment.

    ADMIN_USER in secrets if set; otherwise the FIRST entry in
    APP_PASSWORDS. Deliberately not a hardcoded name — the app should no
    more contain a specific person's name than it should contain a
    password, and an owner who renames themselves should not need a code
    change.
    """
    named = str(st.secrets.get("ADMIN_USER", "") or "").strip().lower()
    if named:
        return named
    pw = app_passwords()
    return pw[0].strip().lower() if pw else ""


def is_admin() -> bool:
    return bool(USER) and USER.strip().lower() == admin_user()


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


# Small constants that app.py needs are read through a guard, NEVER
# straight off the module. Streamlit re-executes app.py on every rerun but
# keeps imported modules cached in sys.modules for the life of the
# process, so a warm process can run NEW app.py against an OLD help_text
# — and a plain attribute access then dies with AttributeError on the
# login screen, locking everyone out of the whole app.
#
# This has now happened twice (HANDOVER §1 was the same shape with
# ls_bridge). The lesson was written down and then repeated anyway, so it
# is worth stating as a rule: anything app.py reads from a local module
# must survive that module being one version behind. A fallback here costs
# nothing; an AttributeError costs the entire app.
_LOGIN_FALLBACK = {
    "MORE_LABEL": {"hr": "Što je ovo?", "en": "What is this?",
                   "it": "Che cos'è?", "de": "Was ist das?",
                   "fr": "Qu'est-ce que c'est ?"},
    "LOGIN_LABELS": {"hr": {"password": "Lozinka", "remember": "Zapamti me",
                            "wrong": "Pogrešna lozinka."}},
    "WELCOME": {"hr": ""},
    "LOGIN_GUIDE": {"hr": ""},
}


def _ht(name: str, lang: str):
    """A value from help_text that cannot bring the app down.

    Falls back to the module being absent, the table being absent, the
    language being absent, and Croatian being absent — in that order. Any
    of those is a cosmetic loss; an AttributeError on the login screen is
    total, because nobody can get past it to reach anything else.
    """
    table = getattr(help_text, name, None)
    if not isinstance(table, dict) or not table:
        table = _LOGIN_FALLBACK.get(name, {})
    if lang in table:
        return table[lang]
    if "hr" in table:
        return table["hr"]
    fb = _LOGIN_FALLBACK.get(name, {})
    return fb.get(lang) or fb.get("hr") or ""


def _more_label(lang: str) -> str:
    return _ht("MORE_LABEL", lang) or _LOGIN_FALLBACK["MORE_LABEL"]["hr"]


def check_password() -> bool:
    def _entered():
        entered = st.session_state.get("_pw_input", "")
        st.session_state["_pw_input"] = ""

        # Refuse to even compare while the throttle is running, so a
        # guesser gains nothing by hammering. See ttt/gate.py for what
        # this does and does not protect against.
        tstate = st.session_state.setdefault("_gate", {})
        allowed, wait = gate.check(tstate, time.time())
        if not allowed:
            st.session_state["_authed"] = False
            st.session_state["_gate_wait"] = wait
            return

        matched = next((p for p in PASSWORDS if hmac.compare_digest(entered, p)), None)
        st.session_state["_authed"] = matched is not None
        if matched is not None:
            gate.record_success(tstate)
            st.session_state.pop("_gate_wait", None)
            st.session_state["_user"] = matched
            if st.session_state.get("_remember_me"):
                queue_ls(writes={AUTH_LS_KEY: _digest(matched)})
        else:
            gate.record_failure(tstate, time.time())
            _, wait = gate.check(tstate, time.time())
            st.session_state["_gate_wait"] = wait

    def _set_login_lang(code):
        st.session_state["login_lang"] = code
        # Picking a language happens INSIDE the fold-out, and Streamlit
        # collapses an expander on every rerun unless told otherwise.
        # Without this, choosing your language slams the panel shut in
        # your face — and the welcome text you were about to read
        # disappears.
        st.session_state["_login_open"] = True

    if st.session_state.get("_authed"):
        return True

    st.session_state.setdefault("login_lang", "hr")
    ll = st.session_state["login_lang"]
    labels = _ht("LOGIN_LABELS", ll)

    # ONE BOX, and nothing else.
    #
    # The old screen led with five language pills, a welcome, an
    # explanation of the name and a home-screen guide, and only then the
    # password. Baba: "there is so much text, people get confused. What
    # do I need to read? Do I need to enter password?" For someone who
    # struggles to read a screen, a wall of text before the one field
    # that matters is not generosity, it is an obstacle.
    #
    # So: password, Remember me, and a single fold-out underneath. Whoever
    # can see it may open the whole thing; whoever cannot sees one box and
    # already knows what to do. Nothing is removed — only folded.
    st.text_input(labels["password"], type="password", key="_pw_input", on_change=_entered)
    st.checkbox(labels["remember"], key="_remember_me", value=True)
    if st.session_state.get("_authed") is False:
        wait = st.session_state.get("_gate_wait", 0)
        if wait and wait > 0:
            pretty = gate.humanise(wait, t("gate_min"), t("gate_sec"))
            st.error(f"{labels['wrong']} {t('gate_wait').format(s=pretty)}")
        else:
            st.error(labels["wrong"])

    # st.expander gives a real disclosure widget: a proper button with the
    # right ARIA state, keyboard reachable, and the content stays in the
    # page for a screen reader rather than being hidden from it.
    with st.expander(_more_label(ll),
                     expanded=st.session_state.get("_login_open", False)):
        lcols = st.columns(len(LANGS5))
        for col, code in zip(lcols, LANGS5):
            col.button(
                code.upper(), key="login_pill_" + code,
                type="primary" if st.session_state["login_lang"] == code else "secondary",
                on_click=_set_login_lang, args=(code,),
            )
        st.markdown(_ht("WELCOME", ll))
        st.markdown("---")
        st.markdown(_ht("LOGIN_GUIDE", ll))
    return False


if not check_password():
    st.stop()

USER = st.session_state.get("_user") or "shared"

# Usage logging to the Google Sheet. Created once per session so the
# session timer is meaningful, and inert unless both secrets are present —
# the app behaves identically with the sheet disconnected.
if "_usage" not in st.session_state:
    st.session_state["_usage"] = UsageLog(
        url=st.secrets.get("SHEETS_URL", ""),
        token=st.secrets.get("SHEETS_TOKEN", ""),
        user=USER,
    )
    st.session_state["_usage"].log("login")
USAGE = st.session_state["_usage"]

KEYS = groq_keys()
if not KEYS:
    st.error(t("no_groq_secret"))
    st.stop()

# The registry's Groq provider is constructed with no keys — the app owns
# them, so hand them over now. Anything asking the registry for the "llm"
# or "stt" capability depends on this line having run.
PROVIDERS.set_groq_keys(KEYS)

# Groq's keys also get a ring, so a rate limit hands off to the next key
# and the tired one rests instead of failing the job. This is what lets a
# long transcription keep going instead of dying at the first 429.
#
# SECURITY: this ring lives in session_state ONLY. It must never go
# through persist_keys()/localStorage like the user-supplied rings do —
# these are the APP's keys from secrets, and writing them into a user's
# browser would hand them out. get_ring() is deliberately not used here.
if "_groq_ring" not in st.session_state:
    _gr = kr.new_ring()
    for k in KEYS:
        _gr["keys"].append({"key": k, "fp": kr.fingerprint(k), "state": "new",
                            "label": "app key", "last_error": "", "calls": 0,
                            "chars": 0, "cool_until": 0})
    st.session_state["_groq_ring"] = _gr
PROVIDERS.get("groq").ring = st.session_state["_groq_ring"]


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


def translate_text(llm, text: str, source_lang: str, target_lang: str) -> str:
    """Translate through whatever is patched to AI, with whatever model is
    selected for it. Was hardwired to Groq's gpt-oss-120b; that is now
    merely the default, and Claude or a different Groq model is a patch
    away.

    The model note that earned the original choice, kept because it is
    still the reason gpt-oss-120b is the Groq default: it returned four
    clean translations with correct grammar including French subjunctive,
    while qwen/qwen3.6-27b wrapped two of four in a visible multi-paragraph
    <think> block — once so long the reply was cut off before any
    translation appeared. See HANDOVER.md.
    """
    return llm.complete(
        f"Translate the following {source_lang} text into {target_lang}. "
        f"Output ONLY the translation, nothing else, no quotes, no notes.\n\n{text}",
        system=("You are a translator. Return only the translation, with no "
                "preamble, no commentary and no quotation marks around it."),
    ).strip()


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


def transcribe_any_size(path: str, model: str, language: str, progress_cb=None,
                        on_wait=None):
    """Thin wrapper over ttt.audio.transcribe_any_size.

    This used to be a SECOND copy of the tiering logic living in app.py,
    which meant the patient per-chunk retry built in the module never
    reached the app at all — a long job still lost audio the moment every
    key was resting. One implementation, in the module, used from here.

    Returns (text, method, reusable_path) as before; the module also hands
    back the temp files it made, and they are cleaned up unless the caller
    still needs the reusable one for a later Correct pass.
    """
    text, method, reusable, temps = ttt_audio.transcribe_any_size(
        path,
        lambda p: transcribe(p, model, language),
        progress_cb=progress_cb,
        on_wait=on_wait,
    )
    ttt_audio.cleanup(*[x for x in temps if x != reusable])
    return text, method, reusable


# ----------------------------------------------------------------------
# Per-user settings — session_state, then browser localStorage, then a
# server-side file. Streamlit Community Cloud doesn't guarantee disk across
# restarts, so the file is a same-instance convenience, not a durable store;
# localStorage is the one that really survives.
# ----------------------------------------------------------------------
DEFAULT_SETTINGS = {"ui_lang": "hr", "speech_lang": "hr", "voice": "Gabrijela",
                    "voice_engine": "edge", "sp_voice": "beatrice_32",
                    "transcribe_engine": "groq", "text_scale": a11y.DEFAULT_SCALE}
SETTINGS_KEYS = ("ui_lang", "speech_lang", "voice", "voice_engine", "sp_voice",
                 "transcribe_engine",
                 "route_stt", "route_tts", "route_llm", "text_scale")
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
    for k in SETTINGS_KEYS:
        if values.get(k):
            st.session_state[k] = values[k]


# ----------------------------------------------------------------------
# Provider keys — Speechify and (next) AssemblyAI, bring-your-own-key.
# Ported from Baba's own MA_READER_SPEECHIFY (speechify_keyring.py) and the
# testing philosophy in Key_Tester's handoff — never reject a key by shape,
# rank/guess only; a rejected key is buried, a rate-limited one rests and
# comes back, a network hiccup changes nothing. Storage is adapted: the
# original kept one JSON file on local disk, which Streamlit Cloud does not
# reliably keep (see HANDOVER.md, incident 1) — so each provider's ring
# lives in the same session_state + localStorage + server-file mechanism
# already built for settings, under its own key.
# ----------------------------------------------------------------------
import re as _re
import base64 as _b64
import urllib.request as _ureq
import urllib.error as _uerr

PROVIDER_KEYS_LS_KEY = f"maha_keys_{USER}"


def _keys_file(user: str) -> str:
    d = os.path.join(tempfile.gettempdir(), "maha_keys")
    os.makedirs(d, exist_ok=True)
    safe = "".join(c for c in user if c.isalnum()) or "user"
    return os.path.join(d, safe + ".json")


def _load_server_keys(user: str) -> dict:
    try:
        with open(_keys_file(user), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_server_keys(user: str, rings: dict) -> None:
    try:
        with open(_keys_file(user), "w", encoding="utf-8") as f:
            json.dump(rings, f)
    except Exception:
        pass


def _fp(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def mask_key(key: str) -> str:
    k = (key or "").strip()
    if len(k) <= 10:
        return (k[:2] + "…") if k else ""
    return k[:5] + "…" + k[-4:]


def new_ring() -> dict:
    return {"keys": [], "active": 0}


def ring_pick(ring: dict, start: int = 0):
    keys = ring["keys"]
    n = len(keys)
    if not n:
        return None
    now = time.time()
    for j in range(n):
        i = (start + j) % n
        k = keys[i]
        if k["state"] == "dead":
            continue
        if k["state"] == "cool":
            if k.get("cool_until", 0) > now:
                continue
            k["state"] = "new"
        return i
    return None


def ring_import(ring: dict, raw: str, prefixes: tuple, min_len: int = 16,
                generic_min: int = 24) -> int:
    """Find keys in messy pasted/uploaded text. Prefixed keys are taken
    exactly; if nothing carries a known prefix, fall back to long mixed
    letter+digit runs — never dropped for 'wrong shape', only ranked.

    Line-aware, same as Key_Tester's KeyParser: each found key carries the
    file line directly above it (verbatim) as a label — usually a username
    or account note, not the key itself. Blank or absent -> no label."""
    lines = (raw or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    url_re = _re.compile(r"https?://\S+")
    token_re = _re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]{11,}")

    def tokens_on(line):
        cleaned = url_re.sub(
            lambda m: m.group(0) if any(p in m.group(0).lower() for p in prefixes) else " ", line)
        return [m.group(0).strip(".-_") for m in token_re.finditer(cleaned)
               if len(m.group(0)) >= 12]

    def is_prefixed(t):
        low = t.lower()
        return any(low.startswith(p) for p in prefixes) and len(t) >= min_len

    per_line = [tokens_on(ln) for ln in lines]
    found = [(tok, i) for i, cands in enumerate(per_line) for tok in cands if is_prefixed(tok)]
    if not found:
        found = [(tok, i) for i, cands in enumerate(per_line) for tok in cands
                 if len(tok) >= generic_min and any(ch.isdigit() for ch in tok)
                 and any(ch.isalpha() for ch in tok)]

    have = {k["key"] for k in ring["keys"]}
    seen, added = set(), 0
    for key, line_idx in found:
        if key in seen or key in have:
            continue
        seen.add(key)
        label = lines[line_idx - 1].strip() if line_idx > 0 else ""
        ring["keys"].append({"key": key, "fp": _fp(key), "state": "new",
                             "last_error": "", "calls": 0, "cool_until": 0,
                             "label": label})
        added += 1
    return added


def persist_keys(rings: dict) -> None:
    # BROWSER ONLY. A user's API keys are the most sensitive thing this
    # app holds, and the server-side file was shared container state keyed
    # by username — so anyone who guessed a password could have read the
    # real holder's keys straight off disk. The same reasoning that moved
    # the archive off the server applies here with more force: keys cost
    # money and outlive the session. Nothing is written to disk; the
    # browser is the only store.
    #
    # Cost of this: keys do not survive a cleared browser and must be
    # re-imported. That is the correct trade — the file was never durable
    # on Streamlit Cloud anyway, so it bought almost nothing and risked a
    # great deal.
    queue_ls(writes={PROVIDER_KEYS_LS_KEY: json.dumps(rings)})


def load_keys() -> dict:
    """session_state, else localStorage, else server file, else empty."""
    if "_rings" in st.session_state:
        return st.session_state["_rings"]
    raw = LS_DATA.get(PROVIDER_KEYS_LS_KEY)
    rings = None
    if raw:
        try:
            rings = json.loads(raw)
        except Exception:
            rings = None
    # Deliberately NOT falling back to the server file: see persist_keys.
    # Reading from it would reintroduce exactly the leak that writing to
    # it created.
    st.session_state["_rings"] = rings or {}
    return st.session_state["_rings"]


def provider_models(provider, force: bool = False):
    """(models, live, error) for a provider, asked from the provider itself.

    Fetched fresh and then held for this session, with a refresh button
    beside each engine. Streamlit re-runs the whole script on every click,
    so literally re-fetching "on every interaction" would mean several
    calls per second and a rate limit within a minute — the cache is what
    makes an always-current list practical rather than what compromises it.
    """
    ck = f"_models_{provider.id}"
    if force or ck not in st.session_state:
        try:
            if provider.id == "groq":
                st.session_state[ck] = provider.models()
            elif provider.needs_key:
                ring = get_ring(provider.id)
                if not kr.usable(ring):
                    st.session_state[ck] = ([], False, "no key")
                else:
                    st.session_state[ck] = provider.models(
                        fetch=lambda attempt: kr.rotate(ring, lambda k: attempt(k)))
                    save_rings()
            else:
                st.session_state[ck] = provider.models()
        except Exception as e:
            st.session_state[ck] = ([], False, str(e)[:120])
    return st.session_state[ck]


def chosen_model(provider) -> str:
    """The model id this provider should use, or "" for its own default."""
    return st.session_state.get(f"model_{provider.id}", "")


def provider_usable(provider) -> bool:
    """Keyless providers are always usable; keyed ones only once a key
    that has not been buried exists. This is the one place that knows how
    'usable' is decided, so ttt/routing.py stays free of storage."""
    if not getattr(provider, "needs_key", True):
        return True
    if provider.id == "groq":
        return bool(KEYS)
    return kr.usable(get_ring(provider.id))


def current_routes() -> dict:
    """task id -> the provider that should do it right now."""
    return RO.all_routes(PROVIDERS, provider_usable, st.session_state)


class STTBridge:
    """Whatever is patched to REC, behind one transcribe().

    Same idea as LLMBridge: the tab should not know whether Groq or
    AssemblyAI answered, nor how each one is keyed. `model=None` means the
    engine's own default, so the model dropdown is honoured when set and
    ignored gracefully when not.
    """

    def __init__(self, provider):
        self.provider = provider
        self.id = provider.id

    @property
    def handles_big_files(self) -> bool:
        """AssemblyAI takes a file of any size itself; Groq needs the
        tiered split. This is the one place that difference lives."""
        return self.id == "assemblyai"

    def transcribe(self, path, language, model=None, progress_cb=None) -> str:
        chosen = model or chosen_model(self.provider) or None
        if self.id == "assemblyai":
            ring = get_ring("assemblyai")
            try:
                return self.provider.transcribe(
                    lambda attempt: kr.rotate(ring, lambda k: attempt(k)),
                    path, language=language,
                    **({"model": chosen} if chosen else {}),
                    progress_cb=progress_cb)
            finally:
                save_rings()
        # Groq: the app's own keys, and the existing tiered path.
        return transcribe(path, chosen or PRIMARY_MODEL, language)

    def accurate_model(self):
        """What Correct should re-run with: the most accurate model this
        engine has, regardless of what is selected for everyday use —
        that is the entire point of the button."""
        if self.id == "groq":
            return CORRECTION_MODEL
        return None      # AssemblyAI's default already is its best


def stt_bridge():
    prov = current_routes().get("stt")
    return STTBridge(prov) if prov else None


class LLMBridge:
    """Whatever is patched to the AI job, behind one complete().

    Providers differ underneath — Groq holds the app's own keys, Claude
    rotates the person's key ring — so this adapts both to the single
    shape ttt/transform.py and the translator expect. Neither of them
    should know, or change, when the patch moves.
    """

    def __init__(self, provider):
        self.provider = provider
        self.id = provider.id

    def complete(self, prompt, system=None, **kw):
        model = chosen_model(self.provider) or None
        if self.provider.needs_key and self.provider.id != "groq":
            ring = get_ring(self.provider.id)
            try:
                return self.provider.complete(
                    lambda attempt: kr.rotate(ring, lambda k: attempt(k)),
                    prompt, system=system, model=model, **kw)
            finally:
                save_rings()
        return self.provider.complete(prompt, system=system, model=model, **kw)


def llm_bridge():
    """The AI engine to use right now, or None if none is usable."""
    prov = current_routes().get("llm")
    return LLMBridge(prov) if prov else None


def cp_row(text: str, where: str, state_key: str = None):
    """The row that sits ABOVE a text box in Baba's own app: the round
    amber CP in the middle, clear on the right.

    Paste belongs on the left and is not here yet — deliberately. The
    component iframe is granted clipboard-WRITE but not clipboard-READ
    (measured, HANDOVER §14), so a paste button built like this one would
    do nothing for every real user. It needs the native paste event
    instead, which is its own spoon. A button that lies is worse than a
    button that is missing.
    """
    has_text = bool((text or "").strip())
    with st.container(key="cprow_" + where):
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if has_text:
                components.html(
                    copybtn.cp_html(text, done_label=t("copy_done_short"),
                                    failed_label="X"),
                    height=copybtn.CP_HEIGHT)
        if has_text and state_key:
            def _clear(k=state_key):
                st.session_state[k] = ""
            c3.button(t("clear_btn"), key=f"clear_{where}", on_click=_clear)


def copy_pill(text: str, where: str):
    """Kept as the plain wide copy button for places where the round CP
    would be too much furniture."""
    if not (text or "").strip():
        return
    components.html(
        copybtn.html(
            text,
            label=t("copy_idle"), busy=t("copy_busy"),
            done=t("copy_done"), failed=t("copy_failed"),
            scale=a11y.clamp(st.session_state.get("text_scale", a11y.DEFAULT_SCALE)),
        ),
        height=copybtn.HEIGHT,
    )


def text_size_pills(where: str):
    """A - / size / + row placed directly above the text it changes.

    Above, not buried in Settings: someone who cannot read the screen must
    not have to navigate a menu they cannot read in order to make it
    readable. Every reading surface gets its own row, all driving the one
    shared setting, so the size is consistent everywhere and adjustable
    from wherever the person happens to be.
    """
    scale = a11y.clamp(st.session_state.get("text_scale", a11y.DEFAULT_SCALE))

    def _set(delta_fn):
        st.session_state["text_scale"] = delta_fn(
            st.session_state.get("text_scale", a11y.DEFAULT_SCALE))
        persist_settings()

    c1, c2, c3 = st.columns([1, 2, 1])
    c1.button("A−", key=f"tsz_minus_{where}", help=t("text_smaller"),
              disabled=a11y.at_min(scale),
              on_click=_set, args=(a11y.smaller,))
    c2.caption(f"{t('text_size')} {a11y.percent(scale)}%")
    c3.button("A+", key=f"tsz_plus_{where}", help=t("text_bigger"),
              disabled=a11y.at_max(scale),
              on_click=_set, args=(a11y.bigger,))


def audio_seconds(path) -> float:
    """Length of an audio file for the usage log. Any failure returns 0 —
    a statistic is never worth interrupting a person's work for."""
    try:
        from ttt import audio as _audio
        return _audio.duration_seconds(path) if path else 0.0
    except Exception:
        return 0.0


def get_ring(provider_id: str) -> dict:
    """The ONE way to get a provider's ring. Always attached to the stored
    rings dict, so every state change (a key found dead, the rotation
    position, call counts) lands somewhere real.

    This replaces `load_keys().get(x) or new_ring()`, which silently
    detached the ring whenever that provider had no keys yet and threw away
    everything written to it. See HANDOVER: audit, 17.8.2026.
    """
    return load_keys().setdefault(provider_id, kr.new_ring())


def save_rings() -> None:
    """Persist whatever the rings currently say. Cheap and idempotent, so
    call it after anything that could have changed a key's state — the
    cost of forgetting is a dead key resurrecting and wasting a request on
    every reload."""
    persist_keys(load_keys())


# ---------- Speechify ----------
SPEECHIFY_PREFIXES = ("sk_", "sws_", "sa_", "spk_")
SP_CURATED = ["beatrice_32", "dominic_32", "edmund_32", "geffen_32",
              "harper_32", "hugh_32", "imogen_32", "wyatt_32"]


def sp_error_kind(status: int) -> str:
    if status in (401, 402, 403):
        return "dead"
    if status == 429:
        return "cool"
    return "soft"


def sp_error_message(status: int, body: str) -> str:
    msgs = {401: "Speechify rejected the key (401).",
            402: "No Speechify credit left on this account (402).",
            403: "This key cannot use that voice (403) — celebrity voices need a licensing plan.",
            404: "Speechify does not know that voice id (404).",
            429: "Speechify rate limit reached (429)."}
    if status in msgs:
        return msgs[status]
    if status >= 500:
        return f"Speechify had a server error ({status})."
    return f"Speechify refused the request ({status}) {(body or '')[:150]}"


def sp_call(key: str, path: str, payload=None, method: str = "GET", timeout: int = 60):
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = _ureq.Request("https://api.speechify.ai" + path, data=data,
                        headers=headers, method=method)
    try:
        with _ureq.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
        return (json.loads(body) if body.strip() else {}), None, None
    except _uerr.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        return None, sp_error_message(e.code, body), sp_error_kind(e.code)
    except Exception as e:
        return None, f"Could not reach Speechify: {e}", "soft"


def sp_request(ring: dict, path: str, payload=None, method: str = "GET", timeout: int = 60):
    keys = ring["keys"]
    n = len(keys)
    if not n:
        return None, "No Speechify keys yet — add one in Settings."
    idx = ring.get("active", 0) % n
    for _ in range(n):
        i = ring_pick(ring, idx)
        if i is None:
            break
        k = keys[i]
        data, err, kind = sp_call(k["key"], path, payload, method, timeout)
        if not err:
            k["state"] = "ok"
            k["last_error"] = ""
            k["calls"] = k.get("calls", 0) + 1
            ring["active"] = i
            return data, None
        if kind == "dead":
            k["state"] = "dead"
            k["last_error"] = err
            idx = (i + 1) % n
            continue
        if kind == "cool":
            k["state"] = "cool"
            k["cool_until"] = time.time() + 120
            k["last_error"] = err
            idx = (i + 1) % n
            continue
        return None, err   # not the key's fault — stop, don't burn the ring
    return None, f"All {n} Speechify key(s) are unavailable right now."


def sp_test_one(key: str):
    _, err, kind = sp_call(key, "/v1/voices?locale=en&limit=1")
    return err, kind


def render_key_list(ring: dict, rings_all: dict, provider: str, test_one_fn):
    """label · first 4 chars · state, with its own Test button per key —
    not a single test-all, so one key can be checked without re-testing
    the whole ring. test_one_fn(key_str) -> (err, kind)."""
    for idx, k in enumerate(ring["keys"]):
        icon = {"ok": "🟢", "new": "⚪", "cool": "🟡", "dead": "🔴"}.get(k["state"], "⚪")
        label = k.get("label") or t("no_label")
        kcol1, kcol2 = st.columns([3, 1])
        with kcol1:
            st.caption(f"{icon} **{label}**  ·  {k['key'][:4]}…")
            if k.get("last_error"):
                st.caption(f"　{k['last_error'][:60]}")
        with kcol2:
            def _test_this(i=idx):
                kk = ring["keys"][i]
                err, kind = test_one_fn(kk["key"])
                if not err:
                    kk["state"] = "ok"
                    kk["last_error"] = ""
                elif kind == "dead":
                    kk["state"] = "dead"
                    kk["last_error"] = err
                else:
                    kk["last_error"] = err
                persist_keys(rings_all)
            st.button(t("test_btn"), key=f"{provider}_test_{idx}",
                     on_click=_test_this)


def sp_model_for(voice_id: str) -> str:
    """Which Speechify model a given voice can actually use.

    The older SPEECHIFY_API_GUIDE recommends simba-3.2 and says not to
    hardcode a model; MA Reader v3's handover goes further and records what
    was measured against the live API: simba-3.2 answers HTTP 400 for any
    voice whose id does not end in _32, which is almost the whole catalogue.
    The curated eight all end in _32 so they take 3.2; anything swapped in
    from the wider catalogue falls back to simba-english."""
    return "simba-3.2" if voice_id.endswith("_32") else "simba-english"


def sp_synthesize(ring: dict, text: str, voice_id: str, model: str = None):
    """Returns (audio_bytes, seconds, marks). marks is a list of
    {start, end, start_time, end_time} — start/end are character offsets
    into `text` itself (exact, not inferred), start_time/end_time are
    seconds into the audio. Punctuation-only marks are dropped. Empty list
    if the response carried no usable marks (caller treats that the same
    as None — falls back to sentence-level highlight)."""
    data, err = sp_request(ring, "/v1/audio/speech", {
        "input": text[:2000], "voice_id": voice_id,
        "audio_format": "mp3", "model": model or sp_model_for(voice_id),
    }, method="POST", timeout=90)
    if err:
        raise RuntimeError(err)
    audio = _b64.b64decode(data["audio_data"])

    marks = []

    def _walk(node):
        if not isinstance(node, dict):
            return
        if node.get("type") == "word":
            val = node.get("value", "") or ""
            if any(c.isalnum() for c in val):   # skip punctuation-only marks
                st_ = node.get("start_time")
                en_ = node.get("end_time")
                if st_ is not None and en_ is not None:
                    marks.append({
                        "start": int(node.get("start", 0)),
                        "end": int(node.get("end", 0)),
                        "start_time": st_ / 1000.0,
                        "end_time": en_ / 1000.0,
                    })
        for child in (node.get("chunks") or []):
            _walk(child)

    _walk(data.get("speech_marks") or {})
    marks.sort(key=lambda m: m["start_time"])

    total = max((m["end_time"] for m in marks), default=0.0)
    if total <= 0:
        total = max(1.0, len(text.split()) * 0.38)
    return audio, total, marks


# ---------- AssemblyAI ----------
# No distinctive prefix (32-hex, per Key_Tester's KeyParser: "HEX32 ->
# assemblyai") — an empty prefix tuple means ring_import's prefixed-pass
# never matches anything, so every AssemblyAI key is found via the generic
# fallback heuristic. Confirmed against 5 real keys, not assumed.
ASSEMBLYAI_PREFIXES = ()
AAI_BASE = "https://api.assemblyai.com"


def aai_error_kind(status: int) -> str:
    if status in (401, 403):
        return "dead"
    if status == 429:
        return "cool"
    return "soft"


def aai_error_message(status: int, body: str) -> str:
    msgs = {401: "AssemblyAI rejected the key (401).",
            403: "AssemblyAI refused this request (403).",
            429: "AssemblyAI rate limit reached (429)."}
    if status in msgs:
        return msgs[status]
    if status >= 500:
        return f"AssemblyAI had a server error ({status})."
    return f"AssemblyAI refused the request ({status}) {(body or '')[:150]}"


def aai_call(key: str, path: str, payload=None, method: str = "GET",
            data: bytes = None, extra_headers: dict = None, timeout: int = 30):
    headers = {"authorization": key}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"
    elif data is not None:
        body = data
    if extra_headers:
        headers.update(extra_headers)
    req = _ureq.Request(AAI_BASE + path, data=body, headers=headers, method=method)
    try:
        with _ureq.urlopen(req, timeout=timeout) as r:
            resp = r.read().decode("utf-8", "replace")
        return (json.loads(resp) if resp.strip() else {}), None, None
    except _uerr.HTTPError as e:
        try:
            resp = e.read().decode("utf-8", "replace")
        except Exception:
            resp = ""
        return None, aai_error_message(e.code, resp), aai_error_kind(e.code)
    except Exception as e:
        return None, f"Could not reach AssemblyAI: {e}", "soft"


def aai_test_one(key: str):
    _, err, kind = aai_call(key, "/v2/transcript?limit=1")
    return err, kind


def aai_transcribe(ring: dict, path: str, language: str = "hr",
                   model: str = "universal-3-pro", progress_cb=None) -> str:
    """Full upload -> submit -> poll flow, rotating through the ring on a
    dead or rate-limited key exactly like sp_request/the Groq ring. A key
    that's simply unreachable (network) is NOT the key's fault and stops
    the attempt rather than burning through the whole ring over it."""
    keys = ring["keys"]
    n = len(keys)
    if not n:
        raise RuntimeError("No AssemblyAI keys yet — add one in Settings.")
    idx = ring.get("active", 0) % n
    last_err = "no keys available"
    for _ in range(n):
        i = ring_pick(ring, idx)
        if i is None:
            break
        k = keys[i]

        if progress_cb:
            progress_cb("upload")
        with open(path, "rb") as f:
            audio_bytes = f.read()
        up, err, kind = aai_call(k["key"], "/v2/upload", method="POST",
                                 data=audio_bytes,
                                 extra_headers={"content-type": "application/octet-stream"},
                                 timeout=1800)
        if err:
            last_err = err
            if kind == "dead":
                k["state"] = "dead"; k["last_error"] = err
            elif kind == "cool":
                k["state"] = "cool"; k["cool_until"] = time.time() + 120; k["last_error"] = err
            else:
                raise RuntimeError(err)
            idx = (i + 1) % n
            continue

        cfg = {"audio_url": up["upload_url"], "speech_models": [model]}
        if language == "auto":
            cfg["language_detection"] = True
        else:
            cfg["language_code"] = language
        if progress_cb:
            progress_cb("queue")
        data, err, kind = aai_call(k["key"], "/v2/transcript", payload=cfg, method="POST")
        if err:
            last_err = err
            if kind == "dead":
                k["state"] = "dead"; k["last_error"] = err
            elif kind == "cool":
                k["state"] = "cool"; k["cool_until"] = time.time() + 120; k["last_error"] = err
            else:
                raise RuntimeError(err)
            idx = (i + 1) % n
            continue

        tid = data["id"]
        t0 = time.time()
        if progress_cb:
            progress_cb("process")
        while time.time() - t0 < 7200:
            time.sleep(0.6 if time.time() - t0 < 4 else (1.2 if time.time() - t0 < 12 else 3.0))
            data, err, kind = aai_call(k["key"], "/v2/transcript/" + tid)
            if err:
                last_err = err
                break   # a poll error mid-job: try the next key from scratch
            status = data.get("status")
            if status == "completed":
                k["state"] = "ok"
                k["last_error"] = ""
                k["calls"] = k.get("calls", 0) + 1
                ring["active"] = i
                return (data.get("text") or "").strip()
            if status == "error":
                last_err = data.get("error") or "AssemblyAI reported an error"
                break
        else:
            last_err = "AssemblyAI took too long (over 2 hours)"
        idx = (i + 1) % n
    raise RuntimeError(f"All {n} AssemblyAI key(s) failed. Last: {last_err}")


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
    values = {k: st.session_state.get(k) for k in SETTINGS_KEYS}
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


def pick_sp_voice(voice_id: str):
    st.session_state["sp_voice"] = voice_id
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
                name, key=f"{prefix}_{name}",
                type="primary" if name == current else "secondary",
                on_click=pick_voice, args=(name,),
            )


# ----------------------------------------------------------------------
# Gear — settings + help, upper right. Nothing else in the top bar.
# ----------------------------------------------------------------------
# Wrapped in a keyed container so the 6:1 ratio survives the pill CSS —
# without it both columns shrink to their content and the gear lands on
# the left, which is where it wrongly sat until this was found.
with st.container(key="topbar"):
    _, gear_col = st.columns([6, 1])
with gear_col:
    with st.popover("⚙", use_container_width=False):
        lang_now = st.session_state.get("ui_lang", "hr")
        lcol1, lcol2 = st.columns(2)
        lcol1.button("[HR]", key="ui_hr",
                     type="primary" if lang_now == "hr" else "secondary",
                     on_click=set_ui_lang, args=("hr",))
        lcol2.button("[ENG]", key="ui_en",
                     type="primary" if lang_now == "en" else "secondary",
                     on_click=set_ui_lang, args=("en",))

        st.caption(t("settings_speech"))
        scol1, scol2 = st.columns(2)
        speech_now = st.session_state.get("speech_lang", "hr")
        scol1.button(t("lang_hr"), key="sp_hr",
                     type="primary" if speech_now == "hr" else "secondary",
                     on_click=set_speech_lang, args=("hr",))
        scol2.button(t("lang_en"), key="sp_en",
                     type="primary" if speech_now == "en" else "secondary",
                     on_click=set_speech_lang, args=("en",))

        st.caption(t("settings_voice"))
        voice_picker("setvoice")

        with st.expander(t("speechify_title")):
            rings = load_keys()
            sp_ring = get_ring("speechify")

            st.file_uploader(t("key_file_label"), key="sp_key_file", label_visibility="collapsed")
            st.text_area(t("key_paste_label"), key="sp_key_paste", height=70,
                         label_visibility="collapsed", placeholder=t("key_paste_ph"))

            def _sp_import():
                raw = ""
                f = st.session_state.get("sp_key_file")
                if f is not None:
                    raw += f.getvalue().decode("utf-8", "replace")
                raw += " " + (st.session_state.get("sp_key_paste") or "")
                added = ring_import(sp_ring, raw, SPEECHIFY_PREFIXES)
                persist_keys(rings)
                st.session_state["_sp_msg"] = (
                    f"{t('keys_added')}: {added}" if added else t("no_keys_found"))

            st.button(t("import_keys_btn"), key="sp_import_btn",
                      use_container_width=True, on_click=_sp_import)

            if sp_ring["keys"]:
                render_key_list(sp_ring, rings, "sp", sp_test_one)

            if st.session_state.get("_sp_msg"):
                st.caption(st.session_state.pop("_sp_msg"))

            # ---- the whole catalogue --------------------------------
            # 979 voices across 36 locales, not the curated eight. Loaded
            # on request rather than on every settings open, because it is
            # five paged calls. NOTHING filters by language on purpose:
            # any Speechify voice may read any text, and Croatian in an
            # English voice both sounds fine and keeps its word timings.
            if kr.usable(sp_ring):
                st.caption(t("vc_title"))
                cat = st.session_state.get("_sp_catalogue")

                def _load_catalogue():
                    try:
                        voices, err = PROVIDERS.get("speechify").catalogue(
                            lambda a: kr.rotate(sp_ring, lambda k: a(k)))
                        save_rings()
                        st.session_state["_sp_catalogue"] = voices
                        if err:
                            st.session_state["_sp_msg"] = str(err)[:100]
                    except Exception as e:
                        st.session_state["_sp_msg"] = str(e)[:100]

                if not cat:
                    st.button(t("vc_load"), key="vc_load_btn", on_click=_load_catalogue)
                else:
                    locales = sorted({v.lang for v in cat if v.lang})
                    fcol1, fcol2 = st.columns(2)
                    loc = fcol1.selectbox(
                        "loc", [t("vc_any")] + locales, key="vc_loc",
                        label_visibility="collapsed")
                    gen = fcol2.selectbox(
                        "gen", [t("vc_any"), "F", "M"], key="vc_gen",
                        label_visibility="collapsed")
                    q = st.text_input(t("vc_search"), key="vc_q",
                                      label_visibility="collapsed",
                                      placeholder=t("vc_search"))

                    shown = [v for v in cat
                             if (loc == t("vc_any") or v.lang == loc)
                             and (gen == t("vc_any") or v.gender == gen)
                             and (not q or q.lower() in v.name.lower())]
                    st.caption(f"{len(shown)} {t('vc_count')}")

                    cur = st.session_state.get("sp_voice", "beatrice_32")
                    names = {v.id: f"{v.name} · {v.lang} · {v.gender}" for v in shown}
                    ids = [v.id for v in shown][:400]   # keep the widget sane
                    if ids:
                        idx = ids.index(cur) if cur in ids else 0

                        def _use_voice():
                            st.session_state["sp_voice"] = st.session_state["vc_sel"]
                            persist_settings()

                        st.selectbox("voice", ids, index=idx, key="vc_sel",
                                     format_func=lambda i: names.get(i, i),
                                     label_visibility="collapsed",
                                     on_change=_use_voice)
                    st.caption(f"{t('vc_current')}: {cur}")
                    st.caption(t("vc_note"))


        with st.expander(t("assemblyai_title")):
            aai_ring = get_ring("assemblyai")

            st.file_uploader(t("key_file_label"), key="aai_key_file", label_visibility="collapsed")
            st.text_area(t("key_paste_label"), key="aai_key_paste", height=70,
                         label_visibility="collapsed", placeholder=t("key_paste_ph"))

            def _aai_import():
                raw = ""
                f = st.session_state.get("aai_key_file")
                if f is not None:
                    raw += f.getvalue().decode("utf-8", "replace")
                raw += " " + (st.session_state.get("aai_key_paste") or "")
                added = ring_import(aai_ring, raw, ASSEMBLYAI_PREFIXES)
                persist_keys(rings)
                st.session_state["_aai_msg"] = (
                    f"{t('keys_added')}: {added}" if added else t("no_keys_found"))

            st.button(t("import_keys_btn"), key="aai_import_btn",
                      use_container_width=True, on_click=_aai_import)

            if aai_ring["keys"]:
                render_key_list(aai_ring, rings, "aai", aai_test_one)

            if st.session_state.get("_aai_msg"):
                st.caption(st.session_state.pop("_aai_msg"))


        with st.expander(t("routing_title")):
            # A patch bay, the way a digital desk routes buses: engines
            # down the side, functions across the top, and you press the
            # crosspoint where they meet. Reading a row tells you what one
            # engine is doing; reading a column tells you who does one job.
            # Everything here is derived from the registry, so a new
            # provider grows a new row on its own.
            ui_lang = st.session_state.get("ui_lang", "hr")
            rows, _routes = RO.matrix(PROVIDERS, provider_usable, st.session_state)
            widths = [1] * (1 + len(RO.TASKS))   # equal, so columns align

            with st.container(key="patchbay"):
                head = st.columns(widths)
                head[0].caption("")
                for i, task in enumerate(RO.TASKS):
                    head[i + 1].caption(f"**{task.short}**")

                for prov, cells in rows:
                    rcols = st.columns(widths)
                    rcols[0].caption(prov.label)
                    for i, (task, state) in enumerate(cells):
                        cell = rcols[i + 1]
                        if state == RO.BLANK:
                            # Not a gap — an engine that cannot do this
                            # job. Shown, not hidden, so the grid keeps
                            # its shape and every column stays readable.
                            cell.caption("·")
                        elif state == RO.NOKEY:
                            cell.button("✕", key=f"pb_{task.id}_{prov.id}",
                                        disabled=True)
                        else:
                            def _patch(k=task.setting_key, v=prov.id):
                                st.session_state[k] = v
                                persist_settings()
                            # No help= here: a tooltip wraps the button in
                            # inline spans with zero width, so width:100%
                            # collapses and the grid loses its columns.
                            # The legend under the bay carries the meaning.
                            cell.button(
                                "●" if state == RO.PATCHED else "○",
                                key=f"pb_{task.id}_{prov.id}",
                                type="primary" if state == RO.PATCHED else "secondary",
                                on_click=_patch)

            st.caption("  ·  ".join(f"**{tk.short}** {tk.label(ui_lang)}"
                                    for tk in RO.TASKS))

            # ---- model per engine ---------------------------------
            # Asked from the provider itself, so a model released years
            # from now appears here without this app being touched. An
            # engine with nothing patched is skipped: choosing a model for
            # a job nobody gave it is noise.
            st.caption("")
            for prov, cells in rows:
                if not any(state == RO.PATCHED for _, state in cells):
                    continue
                if not provider_usable(prov):
                    continue
                models, live, merr = provider_models(prov)
                if not models:
                    continue
                mcol, rcol = st.columns([5, 1])
                ids = [m.id for m in models]
                labels = {m.id: m.label() for m in models}
                cur = chosen_model(prov)
                idx = ids.index(cur) if cur in ids else 0

                def _pick_model(pid=prov.id, key=f"msel_{prov.id}"):
                    st.session_state[f"model_{pid}"] = st.session_state[key]
                    persist_settings()

                mcol.selectbox(
                    f"{prov.label} — {t('model_label')}", ids, index=idx,
                    key=f"msel_{prov.id}", format_func=lambda i: labels.get(i, i),
                    on_change=_pick_model)
                rcol.button("↻", key=f"mref_{prov.id}",
                            help=t("model_refresh"),
                            on_click=lambda pr=prov: provider_models(pr, force=True))
                st.caption(("✓ " + t("model_live")) if live
                           else ("· " + t("model_static")))
                if merr:
                    st.caption("⚠ " + str(merr)[:90])

        if is_admin():
            with st.expander(t("admin_title")):
                st_ = USAGE.status()
                st.caption(t("admin_on") if st_["enabled"] else t("admin_off"))
                st.caption(f"{t('admin_sent')}: {st_['sent']}   ·   "
                           f"{t('admin_failed')}: {st_['failed']}")
                st.caption(f"{t('admin_session')}: {st_['session_minutes']}")
                if st_["last_error"]:
                    st.caption("⚠ " + st_["last_error"][:120])

                # The people who can log in ARE the passwords in secrets,
                # so this is the definitive list — and it is what the
                # sheet will grow a tab for. Never show the passwords
                # themselves; the owner already knows them, and anyone
                # looking over a shoulder should not learn them here.
                names = [p.strip().lower() for p in app_passwords() if p.strip()]
                st.caption(f"{t('admin_users')}: {len(names)}")
                st.caption("  ·  ".join(names))

                def _test_signal():
                    USAGE.log("test", 1, UNIT_CHARS, "admin")
                    st.session_state["_admin_msg"] = t("admin_test_sent")
                    st.session_state["_admin_msg_until"] = time.time() + 8

                st.button(t("admin_test"), key="admin_test_btn", on_click=_test_signal)
                _am, _au = st.session_state.get("_admin_msg"), st.session_state.get("_admin_msg_until", 0)
                if _am and time.time() < _au:
                    st.caption(_am)
                elif _am:
                    st.session_state.pop("_admin_msg", None)

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
    "nav", ["transcribe", "talk", "translate", "read"], format_func=lambda k: t("tab_" + k),
    key="active_tab", required=True, label_visibility="collapsed",
)
active = st.session_state.get("active_tab") or "transcribe"


def do_correct():
    try:
        path = st.session_state.get("flac_path")
        lang = st.session_state.get("last_lang", "hr")
        if not path or not os.path.exists(path):
            raise RuntimeError("Original audio is no longer available.")
        stt_now = stt_bridge()
        if stt_now is None:
            raise RuntimeError(t("routing_none"))
        if stt_now.handles_big_files:
            corrected = stt_now.transcribe(path, lang, model=stt_now.accurate_model())
            st.session_state["transcript_box"] = corrected
            st.session_state["flac_path"] = path
            st.session_state["_transcribe_method"] = "direct"
        else:
            corrected, method, reusable = transcribe_any_size(
                path, stt_now.accurate_model() or CORRECTION_MODEL, lang)
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


def _highlight_span(text: str, start: int = None, end: int = None) -> str:
    """HTML-escaped text with [start:end) wrapped in the gold highlight span.
    With no range, the whole text is wrapped (sentence-level, the Edge case).
    Bounds are clamped defensively — a mark that's ever slightly out of
    range must never crash the read, just highlight nothing that run."""
    if start is None or end is None:
        return ('<span style="background:#f59e0b;color:#0b0d10;'
                'border-radius:4px;padding:1px 4px;">' + html.escape(text) + "</span>")
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))
    return (html.escape(text[:start]) +
            '<span style="background:#f59e0b;color:#0b0d10;'
            'border-radius:4px;padding:1px 4px;">' + html.escape(text[start:end]) + "</span>" +
            html.escape(text[end:]))


def _subtitle(text: str, start: int = None, end: int = None) -> str:
    inner = _highlight_span(text, start, end) if text else ""
    return f'<div class="subtitle-box">{inner}</div>'


def _render_page(page_sentences: list, current_idx: int, doc_slot,
                 word_start: int = None, word_end: int = None) -> None:
    parts = []
    for j, s in enumerate(page_sentences):
        if j == current_idx:
            parts.append(_highlight_span(s, word_start, word_end))
        else:
            parts.append(html.escape(s))
    doc_slot.markdown(" ".join(parts), unsafe_allow_html=True)


def read_sentences_live(raw: str, synth_fn, doc_slot, sub_slot, audio_slot,
                        page_key: str, page_slot, progress_slot=None,
                        speed: float = 1.0, gap: float = 0.0):
    """Shared by Talk and Translate: synthesize and play one sentence at a
    time. Highlights word-by-word when the engine can back it with real
    per-word timing (Speechify's speech_marks, measured from the audio it
    just generated — precise, not inferred); falls back to sentence-level
    otherwise (Edge — its word boundaries are on its own clock and drift,
    see HANDOVER.md for why that was deliberately dropped everywhere else).

    synth_fn(text) -> (audio_bytes, seconds) or (audio_bytes, seconds, marks).
    marks is a list of {start, end, start_time, end_time} in the same shape
    sp_synthesize returns, or falsy/absent for sentence-level.

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

    total_chars = sum(len(x) for x in page_sentences)
    spoken_chars = 0

    for i, sent in enumerate(page_sentences):
        if progress_slot is not None:
            from ttt import read_tab as _RT
            progress_slot.caption(_RT.progress_line(
                spoken_chars, total_chars, i + 1, len(page_sentences),
                speed=speed, sentence_gap=gap))
        try:
            result = synth_fn(sent)
        except Exception as e:
            st.error(f"{t('read_fail')} {i + 1}: {e}")
            break
        audio_bytes, dur = result[0], result[1]
        marks = result[2] if len(result) > 2 else None

        if marks:
            # Word-level: play once, then step the highlight through each
            # mark's own measured window — never touches playback rate.
            audio_slot.audio(audio_bytes, format="audio/mp3", autoplay=True)
            for wi, m in enumerate(marks):
                _render_page(page_sentences, i, doc_slot, m["start"], m["end"])
                sub_slot.markdown(_subtitle(sent, m["start"], m["end"]), unsafe_allow_html=True)
                nxt = marks[wi + 1]["start_time"] if wi + 1 < len(marks) else dur
                time.sleep(max(0.02, nxt - m["start_time"]))
        else:
            _render_page(page_sentences, i, doc_slot)
            sub_slot.markdown(_subtitle(sent), unsafe_allow_html=True)
            audio_slot.audio(audio_bytes, format="audio/mp3", autoplay=True)
            time.sleep(dur + 0.15)

        spoken_chars += len(sent)
        if gap:
            time.sleep(gap)

    doc_slot.markdown(html.escape(" ".join(page_sentences)))
    sub_slot.markdown(_subtitle(""), unsafe_allow_html=True)

    # Log what was actually SPOKEN, not what was pasted — a page that was
    # never reached should not count against anyone's usage.
    if spoken_chars:
        USAGE.log("read", spoken_chars, UNIT_CHARS,
                  st.session_state.get("voice_engine", "edge"))

    # A key can be discovered dead or rate-limited DURING a read, so the
    # ring must be written back afterwards. Missing this was a real bug:
    # a key buried mid-session came back on the next reload and wasted a
    # request every single time. Cheap and idempotent; always do it.
    save_rings()

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
        llm = llm_bridge()
        if llm is None:
            raise RuntimeError(t("routing_none"))
        st.session_state["translate_out"] = translate_text(
            llm, text, LANG_FULL[src], LANG_FULL[tgt])
        USAGE.log("translate", len(text), UNIT_CHARS, llm.id)
    except Exception as e:
        st.session_state["_translate_error"] = f"{t('translate_fail')}: {e}"


def lang_pills(prefix: str, which: str, current: str):
    cols = st.columns(len(LANGS5))
    for col, code in zip(cols, LANGS5):
        col.button(
            code.upper(), key=f"{prefix}_{code}",
            type="primary" if code == current else "secondary",
            on_click=_set_translate_lang, args=(which, code),
        )


# ----------------------------------------------------------------------
# Transcribe
# ----------------------------------------------------------------------
if active == "transcribe":
    # Which engine transcribes is the switchboard's decision, and which
    # model it uses is the dropdown's. The tab asks for neither by name.
    stt = stt_bridge()
    if stt is None:
        st.error(t("routing_none"))
        st.stop()
    t_engine = stt.id

    speech_now = st.session_state.get("speech_lang", "hr")
    lcol1, lcol2 = st.columns(2)
    lcol1.button(t("lang_hr"), key="tr_hr",
                 type="primary" if speech_now == "hr" else "secondary",
                 on_click=set_speech_lang, args=("hr",))
    lcol2.button(t("lang_en"), key="tr_en",
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
                    text = stt.transcribe(flac_path, lang_code)
                st.session_state["transcript_box"] = text
                st.session_state["flac_path"] = flac_path
                st.session_state["last_lang"] = lang_code
                st.session_state["_transcribe_method"] = "direct"
                st.session_state["_transcribe_provider"] = t_engine
                USAGE.log("transcribe", audio_seconds(flac_path),
                          UNIT_SECONDS, t_engine)
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
                if stt.handles_big_files:
                    stage_map = {"upload": (0.2, "aai_stage_upload"),
                                "queue": (0.5, "aai_stage_queue"),
                                "process": (0.7, "aai_stage_process")}

                    def _cb(stage):
                        frac, key = stage_map.get(stage, (0.5, "aai_stage_process"))
                        progress_bar.progress(frac, text=t(key))

                    text = stt.transcribe(tmp.name, lang_code, progress_cb=_cb)
                    method, reusable = "direct", tmp.name
                else:
                    def _cb(i, n):
                        progress_bar.progress((i + 1) / n, text=f"{t('chunk_progress')} {i + 1}/{n}")

                    def _on_wait(idx, attempt, secs, err):
                        # Say WHY nothing is happening. A silent pause of
                        # up to two minutes looks like a hang; naming the
                        # rest makes it obviously deliberate.
                        progress_bar.progress(
                            0.5, text=t("chunk_waiting").format(s=secs, i=idx + 1))

                    text, method, reusable = transcribe_any_size(
                        tmp.name, chosen_model(stt.provider) or PRIMARY_MODEL,
                        lang_code, progress_cb=_cb, on_wait=_on_wait)
                progress_bar.empty()
                st.session_state["transcript_box"] = text
                st.session_state["last_lang"] = lang_code
                st.session_state["flac_path"] = reusable
                st.session_state["_transcribe_method"] = method
                st.session_state["_transcribe_provider"] = t_engine
                USAGE.log("transcribe", audio_seconds(reusable),
                          UNIT_SECONDS, t_engine)
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
        text_size_pills("transcript")
        # His order, from the handoff: the round CP sits ABOVE the source
        # box, not below it. Reaching for copy should not mean scrolling
        # past the text you just made.
        cp_row(st.session_state.get("transcript_box", ""), "transcript",
               state_key="transcript_box")
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

        # ---- AI text transform -------------------------------------
        # Presets for the everyday things, plus a free box for anything
        # else. Every run keeps the previous version so a bad result is
        # always one press away from being undone — the text is often
        # something the person just dictated and cannot easily retype.
        def _apply_transform(preset="", instruction=""):
            source = (st.session_state.get("transcript_box") or "").strip()
            try:
                llm = llm_bridge()
                if llm is None:
                    raise RuntimeError(t("routing_none"))
                out = TR.run(llm, source, instruction=instruction, preset=preset)
                st.session_state["_transcript_prev"] = source
                st.session_state["transcript_box"] = out
                USAGE.log("transform", len(source), UNIT_CHARS, llm.id)
            except Exception as e:
                st.session_state["_ai_error"] = f"{t('ai_fail')}: {e}"

        # GRAMMAR and RE-SHAPE side by side, full width, amber — the two
        # things people actually do to dictated text, given the weight
        # they have in his app. The rest stay as small pills underneath.
        gcol1, gcol2 = st.columns(2)
        gcol1.button(t("grammar_btn"), key="tr_grammar", type="primary",
                     use_container_width=True,
                     on_click=_apply_transform, args=("fix", ""))
        gcol2.button(t("reshape_btn"), key="tr_reshape", type="primary",
                     use_container_width=True,
                     on_click=_apply_transform, args=("tidy", ""))

        rest = [p for p in TR.PRESETS if p not in ("fix", "tidy")]
        pcols = st.columns(len(rest))
        for i, pid in enumerate(rest):
            pcols[i].button(
                TR.preset_label(pid, st.session_state.get("ui_lang", "hr")),
                key="tr_preset_" + pid, on_click=_apply_transform, args=(pid, ""))

        st.text_input(t("ai_ask"), key="ai_instruction",
                      label_visibility="collapsed", placeholder=t("ai_ask"))

        acol1, acol2 = st.columns(2)
        acol1.button(t("ai_apply"), key="ai_apply_btn",
                     on_click=lambda: _apply_transform(
                         "", st.session_state.get("ai_instruction", "")))
        if st.session_state.get("_transcript_prev"):
            def _undo():
                prev = st.session_state.pop("_transcript_prev", None)
                if prev is not None:
                    st.session_state["transcript_box"] = prev
            acol2.button(t("ai_undo"), key="ai_undo_btn", on_click=_undo)

        if st.session_state.get("_ai_error"):
            st.error(st.session_state.pop("_ai_error"))

# ----------------------------------------------------------------------
# Talk
# ----------------------------------------------------------------------
elif active == "talk":
    sp_ring_talk = get_ring("speechify")
    _tts = current_routes()["tts"]
    engine = _tts.id if _tts else "edge"

    if engine == "speechify":
        # The curated eight are quick picks, NOT a limit — any of the 979
        # voices chosen in Settings shows up here too, and any voice may
        # read any language. If the chosen voice is not one of the eight,
        # it gets its own lit pill so the picker always shows the truth.
        st.caption(t("engine_speechify"))
        current_sp = st.session_state.get("sp_voice", "beatrice_32")
        quick = list(SP_CURATED)
        if current_sp not in quick:
            quick.insert(0, current_sp)
        cols = st.columns(4)
        for i, vid in enumerate(quick[:8]):
            cols[i % 4].button(
                vid.split("_")[0].replace("-", " ").title(), key=f"talksp_{vid}",
                type="primary" if vid == current_sp else "secondary",
                on_click=pick_sp_voice, args=(vid,),
            )
        chosen_sp_voice = current_sp

        def synth_fn(s):
            return sp_synthesize(sp_ring_talk, s, chosen_sp_voice)
    else:
        voice_picker("talkvoice")
        vkey = VOICE_TO_VKEY[st.session_state.get("voice", "Gabrijela")]

        def synth_fn(s):
            audio, dur = tk.synth_sentence(s, vkey)
            return audio, dur, None

    text_size_pills("talk")
    cp_row(st.session_state.get("talk_text", ""), "talk", state_key="talk_text")
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
        read_sentences_live(raw, synth_fn, doc_slot, sub_slot, audio_slot, "talk_page", page_slot)
    else:
        sub_slot.markdown(_subtitle(""), unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Translate — Groq (openai/gpt-oss-120b) between five European languages,
# then an optional Read in the target language's own neural voice.
# ----------------------------------------------------------------------
elif active == "translate":
    st.session_state.setdefault("translate_src", "hr")
    st.session_state.setdefault("translate_tgt", "en")

    lang_pills("srcpill", "src", st.session_state["translate_src"])
    st.text_area("src", key="translate_src_text", height=120,
                 label_visibility="collapsed", placeholder=t("translate_src_ph"))

    _, swap_col, _ = st.columns([2.5, 1, 2.5])
    swap_col.button("⇄", key="swap_langs",
                     help=t("swap_help"), on_click=swap_translate_langs)

    lang_pills("tgtpill", "tgt", st.session_state["translate_tgt"])
    st.button(t("translate_btn"), key="do_translate_btn", use_container_width=True,
              on_click=do_translate)

    if st.session_state.get("_translate_error"):
        st.error(st.session_state.pop("_translate_error"))

    if "translate_out" in st.session_state:
        text_size_pills("translate")
        cp_row(st.session_state.get("translate_out", ""), "translate")
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
            tvkey = TRANSLATE_VKEY.get(tgt, "ukF")
            read_sentences_live(raw, lambda s: tk.synth_sentence(s, tvkey) + (None,),
                               tdoc_slot, tsub_slot, taudio_slot, "translate_page", tpage_slot)
        else:
            tsub_slot.markdown(_subtitle(""), unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Read — MA Reader's workflow, adapted to Streamlit and no permanent
# storage. The tab is thin on purpose: everything that could be a module
# is one (ttt.read_tab for the archive, ttt.reader for the loop), so this
# block is only wiring. See ttt/read_tab.py for what ported and what did
# not, and why.
# ----------------------------------------------------------------------
elif active == "read":
    from ttt import read_tab as RT

    # local_only: saved texts are the person's own documents and never
    # touch the server. The temp-file layer is shared container state
    # keyed by username, so anyone who guessed a password could have read
    # the previous holder's saved text out of it. Preferences still use
    # both layers; content does not.
    archive_store = Store(RT.ARCHIVE_NS, USER, ls_read=LS_DATA,
                          ls_write=lambda k, v: queue_ls(writes={k: v}) if v is not None
                          else queue_ls(removes=[k]),
                          local_only=True)
    if "_archive" not in st.session_state:
        st.session_state["_archive"] = RT.load_archive(archive_store)
    archive = st.session_state["_archive"]

    # Which engine speaks here follows the same setting the Talk tab uses,
    # so a voice chosen once is the voice everywhere.
    sp_ring_read = get_ring("speechify")
    _rtts = current_routes()["tts"]
    read_engine = _rtts.id if _rtts else "edge"

    if read_engine == "speechify":
        sp_voice = st.session_state.get("sp_voice", "beatrice_32")

        def read_synth(s):
            return PROVIDERS.get("speechify").synth(
                lambda attempt: kr.rotate(sp_ring_read, lambda k: attempt(k)),
                s, sp_voice)
    else:
        voice_picker("readvoice")
        rvkey = VOICE_TO_VKEY[st.session_state.get("voice", "Gabrijela")]

        def read_synth(s):
            return tk.synth_sentence(s, rvkey) + (None,)

    text_size_pills("read")
    cp_row(st.session_state.get("read_text", ""), "read", state_key="read_text")
    st.text_area(t("tab_read"), key="read_text", height=170,
                 label_visibility="collapsed", placeholder=t("read_paste_ph"))

    scol, gcol = st.columns(2)
    speed = scol.slider(t("read_speed"), 0.5, 2.0,
                        float(st.session_state.get("read_speed", 1.0)), 0.1,
                        key="read_speed")
    gap = gcol.slider(t("read_gap"), 0.0, 2.0,
                      float(st.session_state.get("read_gap", 0.0)), 0.1,
                      key="read_gap")

    bcol1, bcol2 = st.columns(2)
    read_go = bcol1.button(t("read_start"), key="read_go_btn")

    def _keep_text():
        txt = (st.session_state.get("read_text") or "").strip()
        if txt:
            st.session_state["_archive"] = RT.add_piece(
                st.session_state.get("_archive", []), txt)
            RT.save_archive(archive_store, st.session_state["_archive"])
            st.session_state["_read_msg"] = t("read_saved")
            st.session_state["_read_msg_until"] = time.time() + 6

    bcol2.button(t("read_save"), key="read_keep_btn", on_click=_keep_text)
    # Hold the confirmation for a few seconds of wall clock rather than
    # popping it on the next rerun — Streamlit reruns for many reasons
    # (a slider nudge, an expander opening), and a message that vanishes
    # before it is read is the same as no message at all.
    _msg, _until = st.session_state.get("_read_msg"), st.session_state.get("_read_msg_until", 0)
    if _msg and time.time() < _until:
        st.caption(_msg)
    elif _msg:
        st.session_state.pop("_read_msg", None)

    prog_slot = st.empty()
    rdoc_slot = st.empty()
    rsub_slot = st.empty()
    raudio_slot = st.empty()
    rpage_slot = st.empty()

    if read_go or st.session_state.pop("read_page_auto", False):
        raw = (st.session_state.get("read_text") or "").strip()
        read_sentences_live(raw, read_synth, rdoc_slot, rsub_slot, raudio_slot,
                            "read_page", rpage_slot, progress_slot=prog_slot,
                            speed=speed, gap=gap)
    else:
        rsub_slot.markdown(_subtitle(""), unsafe_allow_html=True)

    with st.expander(f"{t('read_archive')} ({len(archive)})"):
        if not archive:
            st.caption(t("read_empty"))
        for piece in archive:
            acol1, acol2, acol3 = st.columns([4, 1, 1])
            acol1.caption(piece["title"])

            def _open(d=piece["digest"]):
                for p in st.session_state.get("_archive", []):
                    if p["digest"] == d:
                        st.session_state["read_text"] = p["text"]
                        break

            def _delete(d=piece["digest"]):
                st.session_state["_archive"] = RT.remove_piece(
                    st.session_state.get("_archive", []), d)
                RT.save_archive(archive_store, st.session_state["_archive"])

            acol2.button(t("read_open"), key="ropen_" + piece["digest"][:8],
                         on_click=_open)
            acol3.button(t("read_delete"), key="rdel_" + piece["digest"][:8],
                         on_click=_delete)
        st.caption(t("read_storage_note"))
