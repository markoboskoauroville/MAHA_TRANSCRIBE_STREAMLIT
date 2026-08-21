"""
Maha Transcribe — Streamlit / Groq edition.

Transcribe: record → ffmpeg downsample to 16kHz mono FLAC (Groq's own
documented preprocessing target) → Whisper on Groq. Groq only.
Talk: paste text → read aloud live, sentence by sentence, with a subtitle line.
"""

import os
import sys
import json
import glob
import hmac
import html
import threading
import time
import hashlib
import io
import tempfile
import subprocess
import base64
from concurrent.futures import ThreadPoolExecutor

# Bumped on every change. Also the stale-module stamp below, so the two
# can never drift apart.
APP_VERSION = "v99 (a) (integrity pass: five real bugs, one false-green)"

# How many blocks to keep ready ahead of the one playing. Three, so a
# hand-off is never heard even if one block is slow or one request has to
# be retried on another key.
PREFETCH_AHEAD = 3

import streamlit as st
from groq import Groq

import streamlit.components.v1 as components

# ----------------------------------------------------------------------
# STALE MODULE GUARD — read this before removing it.
#
# Streamlit re-executes app.py on every rerun but keeps imported modules
# cached in sys.modules for the LIFE OF THE PROCESS. After a redeploy a
# warm process therefore runs the NEW app.py against OLD ttt modules, and
# the first call to anything newly added dies with AttributeError. That
# has now taken this app down THREE times: ls_bridge, then
# help_text.MORE_LABEL, then copybtn.cp_html. Each time the code on
# GitHub was correct and every local test passed, because a local run is
# always a cold start.
#
# Guarding individual call sites did not scale — the login screen was
# hardened and the next new function broke somewhere else. So the cause
# is removed instead: when the build stamp changes, every ttt module is
# dropped from sys.modules BEFORE the imports below, so they are imported
# fresh. Costs one re-import per deploy, nothing per rerun.
#
# The stamp is derived from APP_VERSION, which is already bumped on every
# change, so the two cannot drift apart.
# ----------------------------------------------------------------------
_BUILD_STAMP = APP_VERSION
if getattr(sys, "_ttt_build", None) != _BUILD_STAMP:
    for _name in [n for n in list(sys.modules) if n == "ttt" or n.startswith("ttt.")]:
        del sys.modules[_name]
    for _name in ("talk_engine", "help_text"):
        sys.modules.pop(_name, None)
    sys._ttt_build = _BUILD_STAMP

import talk_engine as tk
import help_text
from ttt import keyring as kr
from ttt import providers as PROVIDERS
from ttt.store import Store
from ttt.usage import UsageLog, UNIT_SECONDS, UNIT_CHARS
from ttt import transform as TR_
from ttt import vision
from ttt import notes as NOTES
from ttt import routing as RO
from ttt import engines as EN
from ttt import audio as ttt_audio
from ttt import a11y
from ttt import speech as SPEECH
from ttt import sheet as SHEET
from ttt import accounts as ACCOUNTS
from ttt import intake
from ttt import errlog
from ttt import drive as DRIVE
from ttt import help_page as HELP_PAGE
from ttt import wordtimes as WORDTIMES
from ttt import read_tab as RT
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

    /* The patch bay's CSS lived here and is gone with it (v91). Engines
       replaced it: two named presets instead of a nine-cell grid. */

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
st.markdown(theme.css(st.session_state.get("scheme", "amber"),
                      st.session_state.get("font_family", "mono")),
            unsafe_allow_html=True)

# The reading stylesheet, regenerated from the person's own text size on
# every run. Injected AFTER the base sheet so it wins, and kept separate
# so the base sheet stays about layout while this one is only about
# readability. See ttt/a11y.py for which WCAG criteria each rule serves.
st.markdown(a11y.css(st.session_state.get("text_scale", a11y.DEFAULT_SCALE)),
            unsafe_allow_html=True)


PRIMARY_MODEL = "whisper-large-v3-turbo"   # fast first pass
CORRECTION_MODEL = "whisper-large-v3"      # slower, more accurate — used by Correct

# ONE MODEL, EVERY LANGUAGE: whisper-large-v3.
#
# v60 split this — turbo for English, the full model for everything else —
# on the assumption that turbo's speed was worth having where its accuracy
# held up. Measured on 24 English clips whose exact spoken text was known:
# turbo made 35 errors in 340 words, large-v3 made 36. One word apart, in
# 340. There is no accuracy reason to prefer either.
#
# Baba: "Why don't we use the large model for English as well? I can wait.
# I am patient yogi." With accuracy equal and the choice his, the tie is
# broken toward the better model and toward having ONE code path instead
# of a language-to-model table that can be wrong.
#
# HONESTLY NOT MEASURED: turbo's speed advantage on LONG files. It is a
# distilled model and should be quicker, but the timings came back with
# 20-fold variance between identical runs — queue noise, not a
# measurement — so no number is claimed here. Audio is transcribed in
# ten-minute chunks, so the exposure is bounded either way.
#
# THE LANGUAGE IS NEVER GUESSED. Measured on Croatian across all four
# combinations: leaving the language OFF degrades BOTH models badly,
# scattering commas through every phrase and inventing words like "privy"
# and "liedenji". The HR/ENG control is an instruction, not a hint, and
# auto-detection is used nowhere in this app.
def model_for(language: str) -> str:
    return CORRECTION_MODEL

# Croatian first everywhere, English second.
# ----------------------------------------------------------------------
# Symbols instead of words for the controls that have an obvious one.
# Baba: "there are too much letters in this app" — and he is right, a
# wall of Croatian verbs is heavy on a small screen.
#
# BUT every glyph keeps its word as the tooltip AND as its accessible
# name. A symbol alone is faster for someone who already knows it and
# worse for someone who does not, and this app is built for people who
# may be confused as well as people who cannot see well. The picture
# carries the meaning; the word is still there for anyone who needs it.
#
# Only glyphs from the basic geometric/arrow blocks are used, because
# those render in the monospace stack everywhere. No emoji: they arrive
# coloured, break the palette, and vary wildly between phones.
SYM = {
    "read":   "\u25b6",   # play
    "stop":   "\u25a0",   # stop
    "clear":  "\u2715",   # cross
    "paste":  "\u21e9",   # down arrow: bring text in
    "undo":   "\u21ba",   # anticlockwise
    "save":   "\u2605",   # star
    "next":   "\u25b8",   # small play, for the next page
    # Translate needs its OWN glyph. It used ▶ and the aria injector maps
    # ▶ to "Read" for every button on the page, so a screen reader
    # announced the translate button as "Read" — the injector cannot tell
    # two identical glyphs apart. An arrow also reads better here: it is
    # "into", not "play".
    "go":     "\u2192",   # right arrow: translate INTO
}

VOICE_SHORT = {"Gabrijela": "Gabby", "Srecko": "Srećko"}
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
    # Single letters. The tab bar is the one row that is always on
    # screen, so it should cost the least. T transcribe, R read, TR
    # translate, and the gear.
    "tab_transcribe":     {"en": "T",                "hr": "T"},
    # The cassette deck transport. Words, not only symbols: the shapes
    # carry the meaning for anyone who knows a tape deck, and the word
    # carries it for everyone else.
    "rec_btn":   {"en": "rec",   "hr": "snimaj"},
    "rec_pause": {"en": "pause", "hr": "pauza"},
    "rec_stop":  {"en": "stop",  "hr": "stop"},
    "rec_upload": {"en": "open",   "hr": "otvori"},
    "wave_play":  {"en": "play",  "hr": "sviraj"},
    "wave_pause": {"en": "pause", "hr": "pauza"},
    "wave_back":  {"en": "back",  "hr": "natrag"},
    "wave_next":  {"en": "next",  "hr": "dalje"},
    "rec_retry":   {"en": "retry",   "hr": "ponovi"},
    "mode_single": {"en": "single", "hr": "jedan"},
    "mode_multi":  {"en": "multi",  "hr": "više"},
    "arc_title":     {"en": "archive",  "hr": "arhiva"},
    "arc_clear_all": {"en": "delete all", "hr": "obriši sve"},
    "arc_load_help": {"en": "Put this back in the box",
                      "hr": "Vrati ovo u okvir"},
    "arc_del_help":  {"en": "Delete this one", "hr": "Obriši ovo"},
    "arc_del_sel":   {"en": "delete ({n})", "hr": "obriši ({n})"},
    "arc_sel_help":  {"en": "Tick to select for deleting",
                      "hr": "Označi za brisanje"},
    "nothing_heard": {"en": "The audio arrived but no speech was found in it.",
                      "hr": "Zvuk je stigao ali u njemu nije pronađen govor."},
    "keeping_audio": {"en": "Saving the recording…",
                      "hr": "Spremam snimku…"},
    "status_word": {"en": "status", "hr": "status"},
    "stt_errors":  {"en": "Whisper refused:", "hr": "Whisper odbio:"},
    "rec_sending": {"en": "sending", "hr": "šaljem"},
    "img_unavailable": {"en": "Reading text from pictures is out of order.",
                        "hr": "Čitanje teksta sa slika trenutno ne radi."},
    "file_unknown": {"en": "Cannot use this file — {why}.",
                     "hr": "Ne mogu koristiti ovu datoteku — {why}."},
    "pick_big":  {"en": "That file is too large for the deck — use this box.",
                  "hr": "Datoteka je prevelika za deck — koristi ovaj okvir."},
    "tab_talk":           {"en": "R",                "hr": "R"},
    "speech_lang_label":  {"en": "Speech language",  "hr": "Jezik govora"},
    "lang_en":            {"en": "ENG",              "hr": "ENG"},
    "lang_hr":            {"en": "HR",               "hr": "HR"},
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
    "account_title":      {"en": "Your account",     "hr": "Tvoj račun"},
    "log_out":            {"en": "Log out",          "hr": "Odjavi se"},
    "logged_out":         {"en": "Logged out.",      "hr": "Odjavljen."},
    "pw_current":         {"en": "Current password", "hr": "Trenutna lozinka"},
    "pw_new":             {"en": "New password",     "hr": "Nova lozinka"},
    "pw_repeat":          {"en": "Repeat the new password",
                           "hr": "Ponovi novu lozinku"},
    "pw_change":          {"en": "Change password",  "hr": "Promijeni lozinku"},
    "pw_changed":         {"en": "Password changed. Every other device has "
                                 "been logged out.",
                           "hr": "Lozinka promijenjena. Svi drugi uređaji su "
                                 "odjavljeni."},
    "pw_mismatch":        {"en": "The two new passwords are not the same.",
                           "hr": "Dvije nove lozinke nisu iste."},
    "pw_short":           {"en": "At least 8 characters.",
                           "hr": "Najmanje 8 znakova."},
    "pw_wrong":           {"en": "That is not your current password.",
                           "hr": "To nije tvoja trenutna lozinka."},
    "pw_unreachable":     {"en": "Could not reach the accounts script. "
                                 "Nothing was changed.",
                           "hr": "Nije moguće doći do skripte za račune. "
                                 "Ništa nije promijenjeno."},
    "forgotten":          {"en": "Forgotten.",       "hr": "Zaboravljeno."},
    "no_password_secret": {"en": "No password set in Secrets. Add APP_PASSWORDS (a list) in Streamlit Cloud → Settings → Secrets.",
                            "hr": "Lozinka nije postavljena u Secrets. Dodaj APP_PASSWORDS (listu) u Streamlit Cloud → Settings → Secrets."},
    "no_groq_secret":     {"en": "No Groq key in Secrets. Add GROQ_API_KEYS (a list) in Streamlit Cloud → Settings → Secrets.",
                            "hr": "Nema Groq ključa u Secrets. Dodaj GROQ_API_KEYS (listu) u Streamlit Cloud → Settings → Secrets."},
    "tab_translate":      {"en": "TR",               "hr": "TR"},
    "tab_read":           {"en": "Read",             "hr": "Čitaonica"},
    # The gear is the tab label itself — a symbol everyone already
    # knows, and one less word in a row of words.
    # TWO GEARS WERE INDISTINGUISHABLE — they differed only by a
    # zero-width space, which is invisible by definition. Baba wants the
    # SAME gear in a brighter colour, not a different glyph.
    #
    # Streamlit renders markdown in segmented_control labels, so the
    # colour comes from the label itself: no CSS, nothing positional to
    # break when a module is added or removed. VERIFIED in a real browser
    # — ":orange[⚙]" renders a coloured span at rgb(226,102,12) and the
    # markdown does not leak through as literal text.
    "tab_settings":       {"en": ":orange[\u2699]",  "hr": ":orange[\u2699]"},
    # Same glyph as the owner's gear on purpose: they are the same KIND
    # of thing, and only the colour says which is which.
    #
    # BUT THE STRINGS MUST DIFFER. st.segmented_control matches options by
    # their FORMATTED LABEL, not by their value — two options rendering
    # the identical "⚙" collapsed into one, and pressing the first
    # selected the second. Reproduced exactly: tab 4 pressed, tab 5
    # checked. A zero-width space makes the strings distinct while
    # leaving them pixel-identical on screen.
    "tab_looks":          {"en": "\u2699\u200b",      "hr": "\u2699\u200b"},
    "tab_help":           {"en": "H",                "hr": "H"},

    "tab_log":            {"en": "L",                "hr": "L"},
    "log_title":          {"en": "Error log",        "hr": "Zapis grešaka"},
    "log_empty":          {"en": "Nothing has gone wrong yet.",
                           "hr": "Zasad nije bilo grešaka."},
    "log_clear":          {"en": "clear log",        "hr": "obriši zapis"},
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
    "method_picture":     {"en": "Read from a picture.", "hr": "Pročitano iz slike."},
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
    "pick_label":         {"en": "Pick a sound file or a picture",
                            "hr": "Odaberi zvučnu datoteku ili sliku"},
    "img_label":          {"en": "Or read a picture",  "hr": "Ili pročitaj sliku"},
    "img_working":        {"en": "Reading the picture…", "hr": "Čitam sliku…"},
    "img_none":           {"en": "No text found in that picture.",
                            "hr": "U toj slici nije pronađen tekst."},
    "img_nomodel":        {"en": "no model here can read a picture right now",
                           "hr": "nijedan model trenutno ne može čitati sliku"},
    "img_fail":           {"en": "Could not read the picture",
                            "hr": "Nije uspjelo čitanje slike"},
    "img_no_model":       {"en": "No engine here can read pictures.",
                            "hr": "Nijedan pogon ovdje ne može čitati slike."},
    "img_done":           {"en": "Read from a picture.", "hr": "Pročitano iz slike."},
    "gen_part":           {"en": "Making part {i} of {n}…",
                            "hr": "Pripremam dio {i} od {n}…"},
    "gen_audio":          {"en": "Making the audio…",  "hr": "Pripremam zvuk…"},
    "new_text":           {"en": "New text",           "hr": "Novi tekst"},
    "prev_sentence":      {"en": "Previous sentence",  "hr": "Prethodna rečenica"},
    "next_sentence":      {"en": "Next sentence",      "hr": "Sljedeća rečenica"},
    "paste_btn":          {"en": "paste",             "hr": "zalijepi"},
    "paste_hint":         {"en": "tap, then paste",   "hr": "dodirni, pa zalijepi"},
    "paste_done":         {"en": "pasted ✓",          "hr": "zalijepljeno ✓"},
    "translate_btn_word": {"en": "translate",         "hr": "prevedi"},
    "grammar_word":       {"en": "grammar",           "hr": "gramatika"},
    "reshape_word":       {"en": "reshape",           "hr": "preoblikuj"},
    "transcript_ph":      {"en": "Your words will appear here",
                            "hr": "Ovdje će se pojaviti tvoje riječi"},
    "new_take_word":      {"en": "new",               "hr": "novo"},
    "archive_word":       {"en": "archive",           "hr": "arhiva"},
    "clear_word":         {"en": "clear",             "hr": "obriši"},
    "copy_word":          {"en": "copy",              "hr": "kopiraj"},
    "copy_done_word":     {"en": "copied",            "hr": "kopirano"},
    "translate_out_ph":   {"en": "The translation will appear here",
                            "hr": "Ovdje će se pojaviti prijevod"},
    "settings_owner_only": {"en": "Settings are managed by the owner.",
                            "hr": "Postavkama upravlja vlasnik."},
    "settings_lang":      {"en": "Interface language", "hr": "Jezik sučelja"},
    "settings_engine":    {"en": "Engine",             "hr": "Motor"},
    "eng_check":          {"en": "check engine",       "hr": "provjeri motor"},
    "eng_good":           {"en": "all parts answered", "hr": "svi dijelovi rade"},
    "eng_bad":            {"en": "this engine cannot run",
                           "hr": "ovaj motor ne može raditi"},
    "eng_stale":          {"en": "the engine changed — check it again",
                           "hr": "motor je promijenjen — provjeri ponovno"},
    "eng_keyless":        {"en": "no key needed",      "hr": "ne treba ključ"},
    "eng_nokeys":         {"en": "no working key",     "hr": "nema ispravnog ključa"},
    "eng_task_stt":       {"en": "transcribe",         "hr": "transkripcija"},
    "eng_task_tts":       {"en": "read aloud",         "hr": "čitanje"},
    "eng_task_llm":       {"en": "AI text",            "hr": "AI tekst"},
    "src_label":          {"en": "Source",             "hr": "Izvor"},
    "src_mic":            {"en": "microphone",         "hr": "mikrofon"},
    "src_system":         {"en": "computer audio",     "hr": "zvuk računala"},
    "t2_hint":            {"en": "Press rec, then choose a tab or window "
                                 "and TICK THE AUDIO BOX. Windows shares "
                                 "system sound; macOS needs BlackHole; "
                                 "Android cannot do this at all.",
                           "hr": "Pritisni rec, odaberi karticu ili prozor "
                                 "i OZNAČI KUĆICU ZA ZVUK. Windows dijeli "
                                 "zvuk sustava; macOS treba BlackHole; "
                                 "Android ovo ne može."},
    "notes_search":       {"en": "Search notes",       "hr": "Traži bilješke"},
    "notes_search_ph":    {"en": "search your notes",  "hr": "traži po bilješkama"},
    "notes_found":        {"en": "{n} of {all}",       "hr": "{n} od {all}"},
    "notes_none":         {"en": "nothing matches",    "hr": "nema pogodaka"},
    "note_close":         {"en": "close",              "hr": "zatvori"},
    "note_cut":           {"en": "cut",                "hr": "reži"},
    "note_line":          {"en": "line",               "hr": "redak"},
    "note_del":           {"en": "delete",             "hr": "obriši"},
    "note_del_sure":      {"en": "delete — sure?",     "hr": "obriši — sigurno?"},
    "note_to_box":        {"en": "to the box",         "hr": "u okvir"},
    "note_new":           {"en": "new note",           "hr": "nova bilješka"},
    "note_made":          {"en": "made",               "hr": "nastalo"},
    "note_edited":        {"en": "edited",             "hr": "uređeno"},
    "sys_busy":           {"en": "stop the recording before changing the source",
                           "hr": "zaustavi snimanje prije promjene izvora"},
    "sys_noaudio":        {"en": "no sound was shared — tick the audio box "
                                 "in the sharing window and try again",
                           "hr": "zvuk nije podijeljen — označi kućicu za "
                                 "zvuk i pokušaj ponovno"},
    "sys_nosystem":       {"en": "this browser cannot capture computer audio",
                           "hr": "ovaj preglednik ne može snimiti zvuk računala"},
    "sys_refused":        {"en": "sharing was cancelled",
                           "hr": "dijeljenje je otkazano"},
    "wave_save":          {"en": "save",               "hr": "spremi"},
    "eng_nousers":        {"en": "no users tab yet — run TTT-LLL ▸ Set up "
                                 "users tab in the sheet, then deploy a "
                                 "New version",
                           "hr": "nema kartice korisnika"},
    "eng_global_word":    {"en": "global",              "hr": "globalno"},
    "eng_users_title":    {"en": "Engine per user",     "hr": "Motor po korisniku"},
    "eng_mixed":          {"en": "mixed",              "hr": "miješano"},
    "eng_saved":          {"en": "saved to the sheet for everyone",
                           "hr": "spremljeno u tablicu za sve"},
    "eng_notsaved":       {"en": "this session only — the sheet did not "
                                 "take it (deploy a New version?)",
                           "hr": "samo ova sesija — tablica nije primila"},
    "usage_off":          {"en": "Usage log not connected.",
                            "hr": "Zapis korištenja nije spojen."},
    # SHORT LABELS. Baba: "text size does not need to be text size, just
    # write TXT. Typeface, shorten it. Colour, put just one letter — as we
    # have up there. Everybody understands one letter." The nav row is
    # already letters, so the panel matches it and the labels stop eating
    # a whole line each.
    "looks_size":         {"en": "TXT",              "hr": "TXT"},
    "looks_font":         {"en": "TY",               "hr": "TY"},
    "looks_scheme":       {"en": "C",                "hr": "C"},
    "looks_preview":      {"en": "The quick brown fox jumps over the lazy dog. 0123456789",
                            "hr": "Gojazni đačić s ljutim che pjeva u fioci. 0123456789"},
    "sig_looks":          {"en": "looks",             "hr": "izgled"},
    "sig_transcribe":     {"en": "transcribe",        "hr": "transkripcija"},
    "sig_read":           {"en": "read",              "hr": "čitanje"},
    "sig_translate":      {"en": "translate",         "hr": "prijevod"},
    "pick_any":           {"en": "Upload",            "hr": "Upload"},
    "pick_sound":         {"en": "Sound file",        "hr": "Zvučna datoteka"},
    "pick_image":         {"en": "Picture",           "hr": "Slika"},
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
    lang = st.session_state.get("ui_lang", "en")
    entry = STRINGS.get(key, {})
    return entry.get(lang, entry.get("en", key))


def safe_text(name: str) -> str:
    """Pull a block of prose out of help_text for the current language.

    Deliberately forgiving: help is documentation, and missing documentation
    must never be able to take the app down (see HANDOVER.md, incident 1).
    """
    try:
        block = getattr(help_text, name, {}) or {}
        lang = st.session_state.get("ui_lang", "en")
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
# English is the default interface language. This line used to say
# "hr" and quietly won over every other change, which is why the app
# kept coming back in Croatian however many defaults were switched.
st.session_state.setdefault("ui_lang", "en")
if not PASSWORDS:
    st.error(t("no_password_secret"))
    st.stop()


def auth_url() -> str:
    return str(st.secrets.get("AUTH_URL", "") or "")


def auth_token() -> str:
    """THE LOGIN TOKEN, never the admin one. It may ask whether a pair is
    right, hand back a remembered session, and change a password when the
    current one is supplied. It cannot make, rename or delete anybody."""
    return str(st.secrets.get("AUTH_LOGIN_TOKEN", "") or "")


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

# The paste target. A REAL component, because it has to send the pasted
# text back to Python — components.html is one-way. Declared here in the
# entrypoint for the same reason as the bridge above: a component
# declared inside a module can go stale in a warm process.
_PASTE_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "paste_frontend")
try:
    _paste_component = components.declare_component("ttt_paste", path=_PASTE_FRONTEND)
except Exception:
    _paste_component = None

_CASSETTE_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "cassette_frontend")
try:
    _cassette_component = components.declare_component(
        "ttt_cassette", path=_CASSETTE_FRONTEND)
except Exception:
    _cassette_component = None

_WAVE_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "waveform_frontend")
try:
    _wave_component = components.declare_component("ttt_wave", path=_WAVE_FRONTEND)
except Exception:
    _wave_component = None

_PLAYER_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "player_frontend")
try:
    _player_component = components.declare_component("ttt_player", path=_PLAYER_FRONTEND)
    _NOTE_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "note_frontend")
    _note_component = components.declare_component("ttt_note", path=_NOTE_FRONTEND)
except Exception:
    _player_component = None
    _note_component = None


def cassette_recorder(key: str, source: str = "mic"):
    """The transport row. Returns the recording once, or None.

    Returns a BytesIO so the caller can keep using .getvalue() exactly as
    it did with st.audio_input — the recording path downstream is
    untouched, which is the whole point of swapping only the capture.

    Never raises: a recorder that fails must leave the page standing.
    """
    if _cassette_component is None:
        return None
    try:
        # THE ACKNOWLEDGEMENT. The component holds the recording until it
        # sees its own stamp come back, and resends it up to five times if
        # it does not. Without this echo every take would appear to fail.
        # It must be sent on EVERY render, not only the one that received
        # the value, because the run that receives it is not necessarily
        # the run the component is listening on.
        val = _cassette_component(
            labels={"rec": t("rec_btn"), "pause": t("rec_pause"),
                    "stop": t("rec_stop"), "upload": t("rec_upload"),
                    "retry": t("rec_retry"), "sending": t("rec_sending"),
                    "noaudio": t("sys_noaudio"), "nosystem": t("sys_nosystem"),
                    "sysrefused": t("sys_refused"), "busy": t("sys_busy")},
            source=source,
            # The list lives in Python so it can grow — a tab, a window,
            # a named virtual device — without touching the component.
            sources=[{"id": "mic", "label": t("src_mic")},
                     {"id": "system", "label": t("src_system")}],
            ack=st.session_state.get(f"_cassette_seen_{key}"),
            key=key, default=None)
    except Exception:
        return None
    if not isinstance(val, dict):
        return None
    # A SOURCE CHANGE ARRIVES ON THE SAME CHANNEL as a recording, and it
    # must not be mistaken for one. Handled before the stamp bookkeeping,
    # because it is not a take and has nothing to acknowledge.
    if val.get("source"):
        chosen = str(val["source"])
        if chosen != st.session_state.get("rec_source"):
            st.session_state["rec_source"] = chosen
            persist_settings()
            st.rerun()
        return None

    stamp = val.get("at")
    seen = f"_cassette_seen_{key}"
    if stamp and st.session_state.get(seen) == stamp:
        return None                     # already taken; do not re-transcribe
    st.session_state[seen] = stamp

    # Too large to cross the websocket base64'd. Streamlit's own uploader
    # has a proper transfer path for that, so it is revealed rather than
    # the person being told no.
    if val.get("toobig"):
        st.session_state["_show_big_upload"] = True
        return None

    # Pasted text arrives as text, not bytes. It needs no router and no
    # ffmpeg — it is already words, so it goes straight to the box.
    if val.get("text"):
        deliver_text(val["text"])
        st.session_state["_transcribe_method"] = "pasted"
        st.session_state["flac_path"] = None
        return None

    if not val.get("b64"):
        return None
    try:
        raw = base64.b64decode(val["b64"])
    except Exception:
        return None
    if not raw:
        return None
    buf = io.BytesIO(raw)
    buf.name = val.get("name") or "take.webm"
    # The browser knows the type better than the filename does; keep it
    # for the router, which prefers content but uses mime to resolve a
    # webm container that could hold either sound or picture.
    st.session_state["_take_mime"] = val.get("mime") or ""
    return buf


def paste_target(where: str, width: int = 96):
    """Returns pasted text once, or None. Never raises: a paste box that
    fails must not take the page down."""
    if _paste_component is None:
        return None
    try:
        val = _paste_component(
            # The word, not the arrow: this sits in a command row where
            # every other item is readable.
            labels={"idle": t("paste_btn"), "hint": t("paste_hint"),
                    "done": t("paste_done"), "word": t("paste_btn")},
            width=width, key=f"paste_{where}", default=None)
    except Exception:
        return None
    if not isinstance(val, dict):
        return None
    stamp = val.get("at")
    seen_key = f"_paste_seen_{where}"
    if stamp and st.session_state.get(seen_key) != stamp:
        st.session_state[seen_key] = stamp
        return val.get("text") or None
    return None


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
    """Log somebody in without them typing, if their browser can prove it.

    TWO SHAPES, because there are two kinds of person.

    The owner's is unchanged: sha256 of a built-in password, compared
    here against APP_PASSWORDS. That only ever worked because the app
    knows those passwords by heart.

    IT NEVER KNOWS THE FAMILY'S. So for every one of them the old code
    compared their digest against a list it could not possibly be in, and
    Remember me silently did nothing — they retyped every time. The fix
    is not a bigger list: it is a token the SCRIPT can check. The browser
    holds it, the sheet holds only its hash, and one round trip says yes
    or no.

    Never raises. A remembered login that cannot be checked is simply not
    a login, and the person meets the login screen as usual.
    """
    token = LS_DATA.get(AUTH_LS_KEY)
    if not token:
        return

    if str(token).startswith("{"):
        try:
            blob = json.loads(token)
            who, tok = str(blob.get("u") or ""), str(blob.get("t") or "")
        except Exception:
            return
        if not who or not tok:
            return
        try:
            got = ACCOUNTS.remember_login(auth_url(), auth_token(), who, tok)
        except Exception:
            got = None            # never a dependency, never a crash
        if got:
            st.session_state["_authed"] = True
            st.session_state["_user"] = got["user"]
            st.session_state["_via_accounts"] = True
            st.session_state["_remember_token"] = tok
            if EN.get(got.get("engine", "")):
                st.session_state["_assigned_engine"] = got["engine"]
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

        # BOTH BOXES FIRE THIS. Now that there is a username field above
        # the password, on_change runs when someone finishes typing their
        # NAME — with the password still empty. Treating that as an
        # attempt marked the login wrong before they had typed it and
        # spent one of the throttle's tries, so a person could throttle
        # themselves simply by filling the form top to bottom.
        #
        # An empty password is not an attempt. Nothing to compare, no
        # verdict, no failure recorded.
        if not entered:
            return

        # Refuse to even compare while the throttle is running, so a
        # guesser gains nothing by hammering. See ttt/gate.py for what
        # this does and does not protect against.
        tstate = st.session_state.setdefault("_gate", {})
        allowed, wait = gate.check(tstate, time.time())
        if not allowed:
            st.session_state["_authed"] = False
            st.session_state["_gate_wait"] = wait
            return

        # THE ACCOUNTS SCRIPT IS ASKED FIRST, when a username was given.
        #
        # NOT the main sheet script any more. That one compared the
        # password as PLAIN TEXT against column 2, and leaving it in the
        # chain would mean anyone who typed a password back into that
        # column had a way in that skipped the hashing entirely — the
        # whole point, quietly undone by a spreadsheet edit.
        #
        # Baba: "Username, password, I am defining in the sheet. These
        # users are my family." So identity is a NAME now, not the
        # password itself — which is what makes per-user settings, Drive
        # folders and usage rows readable instead of being labelled with
        # a secret.
        #
        # IT CANNOT LOCK ANYONE OUT. An unreachable sheet, a missing
        # users tab and a wrong password are all just "no", and the
        # built-in APP_PASSWORDS are then tried exactly as before. §1 is
        # the reason this is written so carefully: a failure on the login
        # screen is total, because nobody can get past it to reach
        # anything else.
        matched = None
        who = ""
        name = (st.session_state.get("_user_input") or "").strip()
        if name:
            try:
                got = ACCOUNTS.login(
                    auth_url(), auth_token(), name, entered,
                    remember=bool(st.session_state.get("_remember_me")))
            except Exception:
                got = None            # never a dependency, never a crash
            if got:
                matched = entered
                who = got["user"]
                st.session_state["_via_accounts"] = True
                if got.get("remember"):
                    st.session_state["_remember_token"] = got["remember"]
                # Their own engine, if the sheet gives them one. A blank
                # cell means "use the global engine", so it is not an
                # override and must not be treated as one.
                if EN.get(got.get("engine", "")):
                    st.session_state["_assigned_engine"] = got["engine"]

        if matched is None:
            matched = next((p for p in PASSWORDS
                            if hmac.compare_digest(entered, p)), None)
            who = matched or ""

        st.session_state["_authed"] = matched is not None
        if matched is not None:
            gate.record_success(tstate)
            st.session_state.pop("_gate_wait", None)
            st.session_state["_user"] = who
            if st.session_state.get("_remember_me"):
                # THE NAME AND A TOKEN for an accounts user; the old
                # digest for the owner's built-in password. Never the
                # password itself, in either shape.
                tok = st.session_state.get("_remember_token")
                if tok and st.session_state.get("_via_accounts"):
                    queue_ls(writes={AUTH_LS_KEY: json.dumps({"u": who, "t": tok})})
                else:
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
    # A NAME ABOVE THE PASSWORD. Optional on purpose: leave it empty and
    # the old password-only login still works, so nobody who already has
    # a password has to learn anything on the day this ships.
    st.text_input(labels.get("username", "Username"), key="_user_input",
                  on_change=_entered)
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
            # KEEP IT. transcribe_any_size falls through its tiers on an
            # exception, so without this the real reason Whisper refused —
            # a rate limit, a size rejection, a timeout — was swallowed and
            # the screen simply showed nothing. Baba waited on a 7 MB take
            # with no way to see that anything had gone wrong at all.
            try:
                errs = st.session_state.setdefault("_stt_errors", [])
                errs.append(f"key {idx + 1}: {type(e).__name__}: {e}"[:300])
                del errs[:-12]
            except Exception:
                pass
            errlog.add(st.session_state, "whisper",
                       f"{type(e).__name__}: {e}",
                       f"key {idx + 1} of {len(KEYS)}, model {model}, "
                       f"language {language}")
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
    ffmpeg reads. Groq's documented 16kHz mono FLAC target, PLUS levelling.

    LEVELLED FIRST, THEN TRANSCODED. Groq's own command has no filter, and
    this path went without one for a long time, which meant a phone held
    away from the mouth was sent to Whisper as quietly as it was recorded.
    Measured word error rate against a clean reference:

        very quiet (-32dB), clean      2.9%  ->  0.0%
        quiet with heavy room noise    7.2%  ->  2.9%
        quiet with light room noise    0.0%  ->  2.9%
        loud and clean                 0.0%  ->  0.0%

    It rescues the two cases that actually fail in the field and costs a
    little on one case that was already perfect. Worth it.

    -sample_fmt s16 IS NOT OPTIONAL AND MUST NOT BE REMOVED. loudnorm
    works internally in floating point, so adding it to Groq's command
    silently promotes the FLAC encoder's output from 16-bit to 24-bit and
    every file becomes ~48% larger for a transcript Whisper returns
    byte-identical either way. That trap cost a full diagnosis in v52 —
    see HANDOVER.md §19. Anywhere loudnorm goes, s16 goes with it.
    """
    out_path = in_path + ".flac"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", in_path, "-af", ttt_audio.LOUDNORM,
             "-ar", "16000", "-ac", "1", "-sample_fmt", ttt_audio.SAMPLE_FMT,
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
DEFAULT_SETTINGS = {"ui_lang": "en", "engine": EN.DEFAULT,
                    "rec_source": "mic",
                    "speech_lang": "hr", "voice": "Gabrijela",
                    "voice_engine": "edge", "sp_voice": "beatrice_32",
                    "transcribe_engine": "groq", "text_scale": a11y.DEFAULT_SCALE}
SETTINGS_KEYS = ("ui_lang", "engine", "rec_source",
                 "speech_lang", "voice", "voice_engine", "sp_voice",
                 "transcribe_engine",
                 "route_stt", "route_tts", "route_llm", "text_scale",
                 "scheme", "font_family", "append_mode")
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


# Bumped when a stored preference must be overridden rather than obeyed.
# The interface language went English in v39, but anyone who had used the
# app already had "hr" saved and kept seeing Croatian — the setting was
# doing its job, which is exactly why the change appeared not to work.
SETTINGS_EPOCH = 2


def _apply_settings(values: dict) -> None:
    """Seed session_state. Only safe before the matching widgets render."""
    stale = int(values.get("epoch", 1)) < SETTINGS_EPOCH
    for k in SETTINGS_KEYS:
        if k == "ui_lang" and stale:
            continue            # let the new default win, once
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
        with c1:
            if state_key:
                # A paste TARGET, not a clipboard reader — the iframe is
                # not granted clipboard-read, so the obvious version would
                # fail silently. See paste_frontend/index.html.
                got = paste_target(where)
                if got:
                    st.session_state[state_key] = got
                    st.rerun()
        with c2:
            if has_text:
                components.html(
                    copybtn.cp_html(text, done_label=t("copy_done_short"),
                                    failed_label="X"),
                    height=copybtn.CP_HEIGHT)
        if has_text and state_key:
            def _clear(k=state_key):
                st.session_state[k] = ""
            c3.button(SYM["clear"], key=f"clear_{where}", help=t("clear_btn"), on_click=_clear)


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
            # Match the row it sits in: same typeface, same prose colour.
            fg=theme.SCHEMES.get(
                st.session_state.get("scheme", "amber"),
                theme.SCHEMES["amber"]).get("prose", "#f2ddb4"),
            font=theme.FONTS.get(st.session_state.get("font", "mono"),
                                 theme.FONTS["mono"]),
        ),
        height=copybtn.HEIGHT,
    )


FLASH_SECONDS = 0.9


def flash(name: str):
    """Mark a command as just-pressed, so it can light up briefly.

    Streamlit reruns after a click, so the press itself is invisible by
    the time the page redraws — :active never gets a chance to show. A
    short-lived stamp in session_state gives the next render something to
    colour, which is what makes the row feel like it responded.
    """
    st.session_state[f"_flash_{name}"] = time.time()


def flashing(name: str) -> bool:
    at = st.session_state.get(f"_flash_{name}", 0)
    return bool(at) and (time.time() - at) < FLASH_SECONDS


# Roughly how wide a monospace character is at the command font size.
# Components live in iframes and cannot size themselves to their text the
# way a button can, so their width is computed instead of measured.
CMD_CHAR_PX = 9
CMD_PAD_PX = 30


def sheet_config() -> dict:
    """Everything the sheet says, fetched once per session.

    Once, because a settings read on every rerun would be several fetches
    a second. Never a dependency: an empty dict is a perfectly good
    answer and every reader falls back to a built-in default.
    """
    if "_sheet_config" not in st.session_state:
        st.session_state["_sheet_config"] = SHEET.fetch(
            str(st.secrets.get("SHEETS_URL", "") or ""),
            str(st.secrets.get("SHEETS_TOKEN", "") or ""))
    return st.session_state["_sheet_config"]


def sheet_prompt(key: str) -> str:
    return SHEET.prompt(sheet_config(), key, USER)


def user_engine_panel():
    """The owner assigns each person their engine.

    Baba: *"I want in this panel to have list of all users and assign
    them engines. Your normal user doesn't have these settings. He is
    working with engine which I assign."*

    Owner only, and the list comes from the sheet's users tab —
    usernames and engines, never passwords, because the script has no
    endpoint that returns them.
    """
    url = str(st.secrets.get("SHEETS_URL", "") or "")
    token = str(st.secrets.get("SHEETS_TOKEN", "") or "")
    if "_users_list" not in st.session_state:
        try:
            st.session_state["_users_list"] = SHEET.list_users(url, token)
        except Exception:
            st.session_state["_users_list"] = []
    people = st.session_state.get("_users_list") or []

    if not people:
        # Said plainly rather than showing an empty panel that looks
        # broken. The two likely causes are both actionable.
        st.caption(t("eng_nousers"))
        return

    def _assign(username, engine_id):
        ok = SHEET.set_user_engine(url, token, username, engine_id)
        st.session_state["_users_msg"] = username + (
            " → " + engine_id if ok else "  " + t("eng_notsaved"))
        if ok:
            st.session_state.pop("_users_list", None)

    for person in people:
        who = person.get("user", "")
        theirs = (person.get("engine") or "").strip().lower()
        cols = st.columns([1.6, 1.4, 2.0, 1.0])
        cols[0].text(who)
        for col, eng in zip(cols[1:3], EN.ENGINES):
            col.button(eng.label, key="ue_%s_%s" % (who, eng.id),
                       type="primary" if theirs == eng.id else "secondary",
                       on_click=_assign, args=(who, eng.id),
                       use_container_width=True)
        # A BLANK ENGINE IS NOT AN ENGINE — it means "use the global
        # one", so it needs its own way back rather than being an
        # unreachable state once anything has been assigned.
        cols[3].button(t("eng_global_word"), key="ue_%s_none" % who,
                       type="primary" if not theirs else "secondary",
                       on_click=_assign, args=(who, ""),
                       use_container_width=True)

    if st.session_state.get("_users_msg"):
        st.caption(st.session_state.pop("_users_msg"))


def adopt_sheet_engine():
    """Apply the engine the SHEET names, once per session.

    Baba: *"we need to do this kind of settings inside the sheet."* The
    engine is the app's, not one person's, so the sheet is where it
    belongs — it is the only store that is shared, durable and editable
    by hand without a deploy.

    ONCE PER SESSION, and only when the person has not chosen for
    themselves in this session. Re-applying it on every rerun would undo
    a press the moment it was made, which reads as the buttons being
    dead. So the sheet sets the starting point and a press wins from
    then on, until the next session.

    Never a dependency: an unreachable sheet, an empty row or a name
    that is not an engine all leave the routes exactly as they were.
    """
    if st.session_state.get("_sheet_engine_done"):
        return
    cfg = sheet_config()
    if not cfg:
        return                      # no sheet is not an error
    st.session_state["_sheet_engine_done"] = True
    # THE PERSON'S OWN ENGINE WINS. Baba: "each user can have separate
    # engine settings I've written in the sheet, and you serve the user."
    # It comes back from login_ on the users tab; the global settings row
    # is the fallback for anyone who has no engine of their own.
    name = (st.session_state.get("_assigned_engine") or "").strip().lower()
    if not EN.get(name):
        name = SHEET.setting(cfg, EN.SETTING_KEY, USER).strip().lower()
    engine = EN.get(name)
    if engine is None:
        return                      # a typo must not switch anything
    if st.session_state.get("_engine_chosen_here"):
        return                      # this person already pressed a button
    for key, value in EN.route_settings(engine).items():
        st.session_state[key] = value
    st.session_state[EN.SETTING_KEY] = engine.id


def adopt_sheet_keys():
    """Take any keys the sheet holds that this session does not.

    They are keys like any other: same ring, same rotation, same
    shredding. Added only when missing, so a key someone typed into
    Settings is never quietly replaced by one from the sheet.
    """
    cfg = sheet_config()
    if not cfg or st.session_state.get("_sheet_keys_done"):
        return
    st.session_state["_sheet_keys_done"] = True
    changed = False
    for prov in PROVIDERS.keyed_providers():
        extra = SHEET.keys_for(cfg, prov.id)
        if not extra:
            continue
        ring = get_ring(prov.id)
        have = {k["key"] for k in ring["keys"]}
        for k in extra:
            if k not in have:
                ring["keys"].append({"key": k, "fp": kr.fingerprint(k),
                                     "state": "new", "label": "sheet",
                                     "last_error": "", "calls": 0, "chars": 0,
                                     "cool_until": 0})
                changed = True
    if changed:
        save_rings()


def nav_tabs():
    """The tab list. The owner gets a second settings entry.

    Two gears, deliberately different: the GREY one is how the app looks
    — font, size, colours — and belongs to whoever is using it. The AMBER
    one is engines and keys, and only the owner ever sees it. Colour does
    the explaining, so neither needs a word.
    """
    # ONE T, NOT TWO. T2 was a second tab for computer audio; it is a
    # SOURCE now, chosen in a dropdown inside T. Baba: "we just have one
    # T and there will be dropdown for the source." Everything after
    # capture was already identical, so a second tab was a second place
    # to keep the same screen in step.
    tabs = ["transcribe", "talk", "translate", "looks"]
    if is_admin():
        tabs.append("settings")
        tabs.append("log")
    # HELP IS ALWAYS LAST. It is the one tab whose position should never
    # move as other modules come and go — somebody looking for help looks
    # at the end of the row.
    tabs.append("help")
    return tabs


def cmd_width(word: str) -> int:
    return max(64, len(word) * CMD_CHAR_PX + CMD_PAD_PX)


def size_controls():
    """Text size, in Settings and nowhere else.

    − and + used to ride on every command row. Baba removed them: they
    appeared four times, they were the only controls that changed how the
    app looks rather than what it does, and a decision made once does not
    belong beside the ones made constantly.
    """
    scale = a11y.clamp(st.session_state.get("text_scale", a11y.DEFAULT_SCALE))
    steps = []
    v = a11y.MIN_SCALE
    while v <= a11y.MAX_SCALE + 0.001:
        steps.append(round(v, 2))
        v = round(v + a11y.STEP, 2)

    cols = st.columns(min(len(steps), 8))
    for i, val in enumerate(steps[:8]):
        def _pick(x=val):
            st.session_state["text_scale"] = x
            persist_settings()
        cols[i].button(f"{a11y.percent(val)}", key=f"sz_{i}",
                       use_container_width=True,
                       type="primary" if abs(scale - val) < 0.01 else "secondary",
                       on_click=_pick)


def cmd_row(where: str, items, target_key: str = None, copy_text: str = "",
            with_size: bool = False):
    """THE row. Every command in the app is built here, so there is one
    appearance and one behaviour to keep right.

    Cells are sized to their WORD rather than forced equal — Baba's
    correction, and it is better: "copy" needs less room than "reshape",
    and equal cells wasted the width that a phone does not have.

    − and + ride at the end of the same row. They are commands too; the
    only reason they were a separate row was that they used to be a
    different kind of control.
    """
    row = list(items)
    scale = a11y.clamp(st.session_state.get("text_scale", a11y.DEFAULT_SCALE))

    def _smaller():
        st.session_state["text_scale"] = a11y.smaller(
            st.session_state.get("text_scale", a11y.DEFAULT_SCALE))
        persist_settings()

    def _bigger():
        st.session_state["text_scale"] = a11y.bigger(
            st.session_state.get("text_scale", a11y.DEFAULT_SCALE))
        persist_settings()

    if with_size:
        row += [("−", f"sz_minus_{where}", _smaller),
                ("+", f"sz_plus_{where}", _bigger)]

    widths = []
    for label, _, _ in row:
        word = t("copy_word") if label == "copy" else (
            t("paste_btn") if label == "paste" else label)
        widths.append(cmd_width(word))

    with st.container(key=f"cmdrow_{where}"):
        cols = st.columns(widths)
        for col, (label, key, cb), w in zip(cols, row, widths):
            with col:
                if label == "copy":
                    components.html(
                        copybtn.cp_html(copy_text or "", label=t("copy_word"),
                                        done_label=t("copy_done_word"),
                                        failed_label="—", size=0),
                        height=44, width=w)
                else:
                    disabled = (label == "−" and a11y.at_min(scale)) or \
                               (label == "+" and a11y.at_max(scale))
                    st.button(label, key=key, use_container_width=True,
                              disabled=disabled,
                              type="primary" if flashing(key or label) else "secondary",
                              on_click=cb)


def tab_signature(name: str):
    """A quiet word at the bottom right saying which tab you are on.

    The tab bar is single letters now — T, R, TR — which is compact but
    tells a newcomer nothing. This is the counterweight: the full word,
    once, in the same dim monospace as the recorder's 00:00, aligned to
    the right margin so it reads as a signature on the panel rather than
    as another control. Settings has none; the gear already says it.
    """
    # AND WHICH ENGINE IS RUNNING. Baba: "in the corner of the frame you
    # need to write current engine — the status and confirmation all
    # parts work."
    #
    # It is DERIVED from the routes every render, never read back from
    # the stored name, so patching one crosspoint by hand shows "mixed"
    # instead of a label that is quietly no longer true.
    #
    # The tick is only added when a check has actually PASSED for this
    # engine. An unchecked engine gets the name and nothing else, because
    # a tick that means "probably" is the thing this corner must never
    # say.
    eng = EN.current(st.session_state)
    label = eng.label if eng else t("eng_mixed")
    res = st.session_state.get("_engine_check") or {}
    mark = ""
    if eng and res.get("engine") == eng.id:
        mark = " ✓" if res.get("state") == EN.OK else " ✗"
    bits = [x for x in (html.escape(name), html.escape(label) + mark) if x]
    st.markdown('<div class="tabsig">' + "  ·  ".join(bits) + '</div>',
                unsafe_allow_html=True)


def name_the_symbols():
    """Give the symbol buttons a real name for assistive technology.

    Streamlit hardcodes aria-label="" on its buttons, so a glyph-only
    button ends up with the GLYPH as its accessible name — verified from
    the accessibility tree, where ▶ and ■ were announced as the character
    itself, which a screen reader reads as "black right-pointing
    triangle". On an app built for people who cannot see well that is not
    a trade worth making, so the words are put back where only assistive
    technology sees them.

    Done from a component iframe because CSS cannot set an attribute.
    The iframe is srcdoc, so same-origin, so it can reach the parent DOM.
    A MutationObserver keeps it applied across Streamlit's re-renders.
    Purely additive: if any of it fails, the buttons still work and only
    the announcement is lost.
    """
    mapping = {
        SYM["read"]: t("read_btn"), SYM["stop"]: t("stop_btn"),
        SYM["clear"]: t("clear_btn"), SYM["undo"]: t("ai_undo"),
        SYM["save"]: t("read_save"), SYM["paste"]: t("paste_btn"),
        SYM["next"]: t("next_page"),
        SYM["go"]: t("translate_btn"),
    }
    components.html(
        "<script>(function(){"
        "var M=" + json.dumps(mapping, ensure_ascii=False) + ";"
        "function apply(){try{"
        "var d=window.parent.document;"
        "d.querySelectorAll('button').forEach(function(b){"
        "  var s=(b.innerText||'').trim();"
        "  if(M[s]){ b.setAttribute('aria-label', M[s]); b.setAttribute('title', M[s]); }"
        "});}catch(e){}}"
        "apply(); setTimeout(apply,300); setTimeout(apply,1200);"
        "try{var o=new MutationObserver(function(){apply();});"
        "o.observe(window.parent.document.body,{childList:true,subtree:true});}catch(e){}"
        "})();</script>", height=0)


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
    values["epoch"] = SETTINGS_EPOCH
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


def log_out():
    """Hand the phone over.

    Three things, and the ORDER matters. The script is told first, while
    the session still knows which token to revoke; then the session is
    emptied; then the browser's copy is queued for removal — queued
    AFTER the clear, or the clear would throw the queue away with
    everything else.

    Telling the script is best effort. If it cannot be reached the
    browser's copy still goes, so the person is out on this phone either
    way — the revocation is merely delayed, not cancelled.
    """
    who = st.session_state.get("_user", "")
    tok = st.session_state.get("_remember_token", "")
    if who and tok:
        try:
            ACCOUNTS.remember_forget(auth_url(), auth_token(), who, tok)
        except Exception:
            pass

    st.session_state.clear()
    queue_ls(removes=[AUTH_LS_KEY])
    st.session_state["_authed"] = False
    st.session_state["_logged_out"] = True


def change_own_password():
    """The current password is the proof, not the token. See ttt/accounts.

    Checked HERE as well as in the script — not because the script is
    trusted less, but because a mismatch or a short password should cost
    nobody a network round trip and half a second of hashing.
    """
    cur = st.session_state.get("_pw_cur", "")
    new = st.session_state.get("_pw_new", "")
    rep = st.session_state.get("_pw_rep", "")
    st.session_state["_pw_msg"] = ""

    if not cur or not new:
        return
    if new != rep:
        st.session_state["_pw_msg"] = ("bad", t("pw_mismatch"))
        return
    if len(new) < 8:
        st.session_state["_pw_msg"] = ("bad", t("pw_short"))
        return

    ok, err = ACCOUNTS.change_password(auth_url(), auth_token(),
                                       st.session_state.get("_user", ""),
                                       cur, new)
    if ok:
        # Every device was just forgotten, including this one. Mint a
        # fresh token so the person who just changed their password is
        # not the one it logs out.
        st.session_state["_remember_token"] = ""
        if st.session_state.get("_remember_me"):
            try:
                got = ACCOUNTS.login(auth_url(), auth_token(),
                                     st.session_state.get("_user", ""), new,
                                     remember=True)
            except Exception:
                got = None
            if got and got.get("remember"):
                st.session_state["_remember_token"] = got["remember"]
                queue_ls(writes={AUTH_LS_KEY: json.dumps(
                    {"u": st.session_state.get("_user", ""), "t": got["remember"]})})
        else:
            queue_ls(removes=[AUTH_LS_KEY])
        st.session_state["_pw_msg"] = ("good", t("pw_changed"))
    elif err == "unreachable":
        st.session_state["_pw_msg"] = ("bad", t("pw_unreachable"))
    elif err.startswith("too short"):
        st.session_state["_pw_msg"] = ("bad", t("pw_short"))
    else:
        st.session_state["_pw_msg"] = ("bad", t("pw_wrong"))

    # NEVER LEFT LYING IN THE SESSION, whether it worked or not.
    for k in ("_pw_cur", "_pw_new", "_pw_rep"):
        st.session_state[k] = ""


def voice_picker(prefix: str, on_pick=None):
    """Every voice on ONE row, short names, no language headings.

    Baba: "HR ENG, it's not necessary. Gabrijela Srecko, we know, are
    Croats. Sonia and Ryan are English people." He is right — the headings
    cost two lines to say what the names already say, and on a phone that
    is real estate the text box needs. Gabrijela is shortened to Gabby for
    the same reason; the full name stays in the tooltip.
    """
    current = st.session_state.get("voice", "Gabrijela")
    names = [n for group in VOICES_BY_LANG.values() for n in group]
    # ONE ROW, ALWAYS. A wrapped fourth voice costs a whole line of a
    # phone screen to say nothing — the keyed container lets the
    # stylesheet force nowrap, the same override the command row and the
    # archive rows already use.
    with st.container(key="voicerow"):
        cols = st.columns(len(names))
    for col, name in zip(cols, names):
        col.button(
            VOICE_SHORT.get(name, name), key=f"{prefix}_{name}",
            type="primary" if name == current else "secondary",
            help=name,
            # on_pick lets the reader rebuild a reading already in flight
            # when the voice changes. Nothing else passes it, so every
            # other caller behaves exactly as before.
            on_click=(lambda n=name: (pick_voice(n), on_pick and on_pick()))
            if on_pick else pick_voice,
            args=() if on_pick else (name,))


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
            t1_set_text(corrected)
            st.session_state["flac_path"] = path
            st.session_state["_transcribe_method"] = "direct"
        else:
            corrected, method, reusable = transcribe_any_size(
                path, stt_now.accurate_model() or CORRECTION_MODEL, lang)
            t1_set_text(corrected)
            st.session_state["flac_path"] = reusable
            st.session_state["_transcribe_method"] = method
    except Exception as e:
        st.session_state["_correct_error"] = str(e)


def read_this():
    """Move to the Talk tab, carry the text over, pick the voice that matches
    the language just transcribed, and start reading — no popup, no extra tap."""
    st.session_state["talk_text"] = t1_text()
    lang = st.session_state.get("last_lang", "hr")
    current = st.session_state.get("voice", "Gabrijela")
    if VOICE_LANG.get(current) != lang:
        st.session_state["voice"] = VOICES_BY_LANG[lang][0]
    st.session_state["active_tab"] = "talk"
    st.session_state["_auto_read"] = True


def _highlight_span(text: str, start: int = None, end: int = None) -> str:
    """HTML-escaped text with [start:end) coloured as the spoken word.

    COLOUR ONLY, AND ONLY THE WORD. Baba: "don't highlight the sentence at
    all, no background, only the current word spoken."

    The amber block is gone. It marked the whole sentence when no word
    range was known, which meant a quarter of the screen changed colour
    every few seconds and the eye had nothing precise to follow. A single
    red word is where the voice IS.

    Red #ef4444 was chosen by measurement, not taste: 5.17:1 against the
    reading background (WCAG AA) and 2.83:1 against the cream prose around
    it — the highest separation of the reds tested, so it reads as a
    DIFFERENT word rather than merely a tinted one.

    NOTHING HERE TOUCHES LAYOUT. No background, no padding, no weight, no
    border. Colour is painted and cannot reflow a line, which is what
    makes the highlight steady while it moves word by word — see §21 and
    tests/test_shake.py, which must stay at zero.

    With no range, NOTHING is highlighted. That is deliberate: when the
    word is not known, marking the whole sentence would be guessing in
    paint.
    """
    if start is None or end is None:
        return html.escape(text)
    hl = 'color:#ef4444;'
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))
    if end <= start:
        return html.escape(text)      # nothing to colour; no empty span
    return (html.escape(text[:start]) +
            f'<span style="{hl}">' + html.escape(text[start:end]) + "</span>" +
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


def read_picture(raw: bytes, filename: str = "") -> str:
    """Read the words out of a photograph.

    THE FUNCTION WAS MISSING, NOT THE CAPABILITY. `ttt/vision.py` has had
    `read_image` since it was written, and app.py has imported `vision`
    all along — but the call site named `read_picture`, which existed
    nowhere. pyflakes has been reporting it since 92c4cbb and it has been
    listed as "still dead" in three handover sections. The whole fault
    was a missing twelve lines of plumbing.

    It could not crash the app because the call sits inside a `try`, so
    what a person actually saw was "picture failed: name 'read_picture'
    is not defined" — an error that reads like a bug in Python rather
    than a feature that was never connected.

    vision.py never touches a key: it is handed a `call` that does.
    """
    prov = PROVIDERS.get("groq")
    if prov is None:
        raise RuntimeError(t("routing_none"))

    # Ask the provider which of ITS models take an image, rather than
    # naming one here. vision.py is emphatic about this — "THE MODEL IS
    # DISCOVERED, NEVER HARDCODED" — because a name written into a file
    # goes stale the day Groq retires it, and then pictures break for
    # everyone at once with no warning.
    names = vision.find_vision_models(prov.raw_models())
    if not names:
        # No fallback name on purpose. Guessing one would turn a clear
        # "none available" into a confusing 404 from the API.
        raise RuntimeError(t("img_nomodel"))

    return vision.read_image(prov.raw_chat, names[0], raw, filename)

# load_from_archive() lived here and is gone with the archive UI (v98).
# A note is opened and edited in place now; "to the box" inside an open
# note is what putting one back looks like.


@st.cache_resource(show_spinner=False)
def _drive_store(url: str, token: str, secret: str, user: str, on: bool):
    """One store per user per configuration. Cached because building it is
    cheap but doing it on every rerun is noise."""
    return DRIVE.DriveStore(url=url, token=token, secret=secret,
                            user=user, enabled=on)


def drive_store():
    """The Drive store, or a disabled one. NEVER None, so callers do not
    need an `if` around every use.

    Off unless ALL of these are true: the sheet says store_audio, the
    secrets carry DRIVE_SECRET, and the sheet URL and token exist. Any one
    missing and it is simply disabled — a half-configured store that
    half-works is worse than one that plainly does not.
    """
    try:
        secret = str(st.secrets.get("DRIVE_SECRET", "") or "")
        on = bool(secret) and SHEET.flag(sheet_config(), "store_audio", USER)
        return _drive_store(
            str(st.secrets.get("SHEETS_URL", "") or ""),
            str(st.secrets.get("SHEETS_TOKEN", "") or ""),
            secret, USER, on)
    except Exception:
        return DRIVE.DriveStore(enabled=False)


def start_keeping(flac_path: str, seconds: float, language: str):
    """Begin storing the audio IN THE BACKGROUND and return the worker.

    The FLAC exists before transcription starts, so the upload and Whisper
    can run at the same time. Measured: a two-minute take costs 9s to
    store and several to transcribe; done one after the other that is the
    sum, done together it is the larger of the two.

    THE STORE IS BUILT ON THIS THREAD, ON PURPOSE. Building it reads
    st.secrets and the sheet config, and a thread started by Streamlit has
    no script context — touching session state from inside would raise or,
    worse, silently read nothing. The worker only does network I/O with
    values it was handed.
    """
    store = drive_store()
    if not store.enabled or not flac_path:
        return None
    box = {"rec_id": None, "error": ""}

    def _work():
        try:
            box["rec_id"] = store.store(flac_path, seconds=seconds,
                                        language=language)
            if not box["rec_id"]:
                box["error"] = store.last_error or "no reason given"
        except Exception as e:
            box["error"] = f"{type(e).__name__}: {e}"

    th = threading.Thread(target=_work, daemon=True)
    th.start()
    return (th, box)


def finish_keeping(worker, wait: float = 90.0) -> str:
    """Wait for the background store and report. Returns the rec_id or "".

    A DEADLINE, because a thread that never finishes would otherwise hold
    the run open forever. If it overruns, the words are already on screen
    and the upload is simply abandoned — daemon threads die with the
    process and Drive is left with an orphan part, which is the harmless
    direction.
    """
    if not worker:
        return ""
    th, box = worker
    th.join(timeout=wait)
    if th.is_alive():
        errlog.add(st.session_state, "drive",
                   f"storing did not finish within {wait:.0f}s")
        return ""
    if box["error"]:
        errlog.add(st.session_state, "drive",
                   "could not store the recording", box["error"])
    return box["rec_id"] or ""


def keep_audio(flac_path: str, seconds: float, language: str) -> None:
    """Put a finished recording in Drive. Never raises, never blocks.

    STORAGE MUST NOT BE ABLE TO COST A TRANSCRIPT. The words are already
    on screen by the time this runs; if Drive is down, or the folder is
    wrong, or the script was never redeployed, the only consequence is
    that this take cannot be transcribed again later without re-uploading.
    That is a small loss and it is never worth an error message over the
    thing the person actually came for.
    """
    store = drive_store()
    if not store.enabled or not flac_path:
        return
    try:
        rec_id = store.store(flac_path, seconds=seconds, language=language)
        if rec_id:
            st.session_state["_last_rec_id"] = rec_id
        else:
            errlog.add(st.session_state, "drive",
                       "could not store the recording",
                       store.last_error or "no reason given")
    except Exception as e:
        errlog.add(st.session_state, "drive",
                   f"{type(e).__name__}: {e}")


# =====================================================================
#  ENGINES
# =====================================================================

def engine_test_one(provider_id):
    """Prove ONE provider can actually be reached. (state, detail).

    Not "is a key present" — that is the §47 mistake, where a failure
    path and a success path both answered ok. This calls the provider's
    own test_key against a real endpoint, so a green light means the
    network agreed.
    """
    prov = PROVIDERS.get(provider_id)
    if prov is None:
        return EN.FAIL, "no such engine part"
    if not prov.needs_key:
        # Edge is keyless. There is nothing to authenticate, so there is
        # nothing to prove here — saying "ok" would claim a test that
        # never ran.
        return EN.SKIP, t("eng_keyless")

    if provider_id == "groq":
        # Groq's keys are the app's own, from Streamlit secrets, not a
        # user ring — so they are read from the provider, not get_ring().
        keys = list(getattr(prov, "keys", []) or [])
        if not keys:
            return EN.FAIL, t("eng_nokeys")
        last = ""
        for k in keys:
            err, _kind = prov.test_key(k)
            if not err:
                return EN.OK, ""
            last = str(err)[:120]
        return EN.FAIL, last or t("eng_nokeys")

    ring = get_ring(provider_id)
    entries = [e for e in (ring.get("keys") or []) if e.get("state") != "dead"]
    if not entries:
        return EN.FAIL, t("eng_nokeys")
    last = ""
    for entry in entries:
        key = entry.get("key") or ""
        if not key:
            continue
        err, kind = prov.test_key(key)
        if not err:
            return EN.OK, ""
        last = str(err)[:120]
        if kind:
            entry["state"] = "dead" if kind == "dead" else entry.get("state", "new")
    save_rings()
    return EN.FAIL, last or t("eng_nokeys")


def pick_engine(engine_id):
    """Choose an engine: write its routes, and forget any stale verdict.

    The check result is dropped on purpose. A green tick left over from
    the engine you were on a moment ago is worse than no tick, because
    it is read as applying to the one you just chose.
    """
    engine = EN.get(engine_id)
    if engine is None:
        return
    for key, value in EN.route_settings(engine).items():
        st.session_state[key] = value
    st.session_state[EN.SETTING_KEY] = engine.id
    # A PRESS OUTRANKS THE SHEET for the rest of this session. Without
    # this the sheet's value would be re-applied on the next rerun and
    # the button would appear not to work.
    st.session_state["_engine_chosen_here"] = True
    st.session_state.pop("_engine_check", None)
    persist_settings()

    # AND WRITE IT TO THE SHEET, so it is the engine for everybody.
    # Baba: "this is global settings for all users." Admin only — one
    # person's press must not silently change what everyone else runs.
    #
    # The sheet is a convenience here as everywhere: if the write fails
    # the choice still holds for this session, and the only loss is that
    # it does not follow to the next one or to anyone else. Said plainly
    # rather than swallowed, because a global setting that quietly did
    # not save is worse than one that never claimed to.
    if is_admin():
        ok = SHEET.put_setting(
            str(st.secrets.get("SHEETS_URL", "") or ""),
            str(st.secrets.get("SHEETS_TOKEN", "") or ""),
            EN.SETTING_KEY, engine.id)
        st.session_state["_engine_saved"] = bool(ok)
        # The cached config is now stale — drop it so the next read sees
        # what was just written rather than what was there at login.
        if ok:
            st.session_state.pop("_sheet_config", None)
            st.session_state.pop("_sheet_engine_done", None)


def run_engine_check():
    engine = EN.get(st.session_state.get(EN.SETTING_KEY, EN.DEFAULT))
    if engine is None:
        return
    state, rows = EN.check(engine, engine_test_one)
    st.session_state["_engine_check"] = {
        "engine": engine.id, "state": state, "rows": rows,
        "at": time.strftime("%H:%M"),
    }


def engine_now():
    """The engine the ROUTES currently amount to, or None for a mixed
    board. Derived, never trusted from the stored name — someone can
    patch one crosspoint by hand and the label must not keep claiming an
    engine that is no longer running."""
    return EN.current(st.session_state)


def _revoice():
    """A voice was chosen. If a reading is in flight, rebuild it.

    Baba: "while the audio is playing, user can change the voice, and
    then you're going to re-render audio."

    The cache is dropped and the INDEX IS KEPT, so the new voice takes
    over from the block being listened to rather than starting the whole
    text again — changing voice in the middle of a long piece must not
    cost the listener their place.
    """
    job = st.session_state.get("_talk_job")
    if job:
        job["cache"] = {}
        st.session_state.pop("_talk_player_seen", None)
        st.session_state["_talk_revoice"] = True


def _voice_row_synth_only(engine, sp_ring_talk):
    """The synth closure WITHOUT drawing the buttons.

    Rebuilding a reading's voice must not put a second row of voices on
    the page — the row is rendered once, further down, and this is only
    the function that makes the sound.
    """
    if engine == "speechify":
        current_sp = st.session_state.get("sp_voice", "beatrice_32")

        def synth_fn(text):
            return sp_synthesize(sp_ring_talk, text, current_sp)
        return synth_fn

    vkey = VOICE_TO_VKEY[st.session_state.get("voice", "Gabrijela")]

    def synth_fn(text):
        return tk.synth_sentence(text, vkey) + (None,)
    return synth_fn


def _voice_row(engine, sp_ring_talk):
    """The voices, ALWAYS on screen — writing or playing.

    They used to render only in the writing state, so the one moment a
    voice is easiest to judge, while it is speaking, was the one moment
    it could not be changed.
    """
    if engine == "speechify":
        current_sp = st.session_state.get("sp_voice", "beatrice_32")
        quick = list(SP_CURATED)
        if current_sp not in quick:
            quick.insert(0, current_sp)
        cols = st.columns(4)
        for i, vid in enumerate(quick[:8]):
            cols[i % 4].button(
                vid.split("_")[0].replace("-", " ").title(), key=f"talksp_{vid}",
                type="primary" if vid == current_sp else "secondary",
                on_click=lambda v=vid: (pick_sp_voice(v), _revoice()))

        def synth_fn(text):
            return sp_synthesize(sp_ring_talk, text, current_sp)
        return synth_fn

    voice_picker("talkvoice", on_pick=_revoice)
    vkey = VOICE_TO_VKEY[st.session_state.get("voice", "Gabrijela")]

    def synth_fn(text):
        return tk.synth_sentence(text, vkey) + (None,)
    return synth_fn


# The source used to be a Streamlit selectbox on its own row. It is now
# a gear in the deck's own upper-right corner (v95): the input is set
# once and then forgotten, so it should not sit on the panel competing
# with rec — and a page dropdown inside a Technics deck was furniture
# borrowed from somewhere else.


# =====================================================================
#  THE NOTES
# =====================================================================

OPEN_KEY = "_open_note"


def open_note(note_id):
    st.session_state[OPEN_KEY] = note_id
    st.session_state.pop("_note_seen", None)


def close_note():
    st.session_state.pop(OPEN_KEY, None)
    st.session_state.pop("_note_seen", None)


def note_from_transcript(text):
    """Every finished transcript becomes a note.

    When a note is OPEN the words go into it instead of making another —
    that is what "talk directly to the note" means. The deck neither
    knows nor cares which of the two is happening.
    """
    body = (text or "").strip()
    if not body:
        return None
    open_id = st.session_state.get(OPEN_KEY)
    if open_id and NOTES.get(st.session_state, open_id):
        NOTES.append(st.session_state, open_id, body)
        return open_id
    return NOTES.add(st.session_state, body,
                     language=st.session_state.get("last_lang", ""),
                     rec_id=st.session_state.get("_last_rec_id", ""))


def notes_panel():
    """The list: a search field, then the notes."""
    all_notes = NOTES.items(st.session_state)
    if not all_notes:
        return                      # nothing yet, and no empty furniture

    with st.container(key="notesbox"):
        # THE SEARCH FIELD IS ALWAYS AT THE TOP — Keep's arrangement, and
        # the right one: it is how you reach a note, so it comes before
        # the notes.
        st.text_input(t("notes_search"), key="notes_q",
                      placeholder=t("notes_search_ph"),
                      label_visibility="collapsed")
        q = st.session_state.get("notes_q", "")
        shown = NOTES.search(st.session_state, q) if q.strip() else all_notes

        if q.strip():
            st.caption(t("notes_found").format(n=len(shown), all=len(all_notes)))
        if not shown:
            st.caption(t("notes_none"))
            return

        for n in shown:
            # ONE CARD, ONE PRESS, WHOLE WIDTH. A card with a tick, a
            # title and a menu is three targets in a row on a phone. Here
            # the card IS the target, and everything else lives inside
            # the note once it is open.
            st.button(
                "%s\n\n%s" % (NOTES.heading(n), NOTES.body_preview(n, 70)),
                key="note_%s" % n["id"], use_container_width=True,
                on_click=open_note, args=(n["id"],))


def note_open_view():
    """One note, taking over the module.

    Baba: "the note is taking over the user interface, like opening a new
    document in Word." So the list, the command row and the main box are
    not drawn at all while a note is open — not hidden with CSS, not
    drawn. Two writing surfaces on one screen is two places the words
    might have gone.
    """
    note_id = st.session_state.get(OPEN_KEY)
    note = NOTES.get(st.session_state, note_id)
    if note is None:
        close_note()
        return False

    def _save_title():
        NOTES.update(st.session_state, note_id,
                     title=st.session_state.get("note_title_%s" % note_id, ""))

    def _del_arm():
        st.session_state["_note_del_armed"] = note_id

    def _del_do():
        NOTES.remove(st.session_state, note_id)
        st.session_state.pop("_note_del_armed", None)
        close_note()

    with st.container(key="noteopen"):
        head, back = st.columns([4, 1.3])
        head.text_input("title", key="note_title_%s" % note_id,
                        value=NOTES.heading(note),
                        label_visibility="collapsed", on_change=_save_title)
        back.button(t("note_close"), key="note_close",
                    on_click=close_note, use_container_width=True)

        if _note_component is not None:
            ev = _note_component(
                text=note.get("text", ""),
                scale=a11y.clamp(st.session_state.get("text_scale",
                                                      a11y.DEFAULT_SCALE)),
                labels={"rec": t("rec_btn"), "cut": t("note_cut"),
                        "line": t("note_line")},
                recording=False,
                key="note_ed_%s" % note_id, default=None)

            if isinstance(ev, dict):
                # The editor sends on every keystroke, so the stamp is
                # what stops one edit being re-applied on every rerun.
                if st.session_state.get("_note_seen") != ev.get("at"):
                    st.session_state["_note_seen"] = ev.get("at")
                    if isinstance(ev.get("text"), str):
                        NOTES.update(st.session_state, note_id, text=ev["text"])
                    if ev.get("rec"):
                        st.session_state["_note_wants_rec"] = True
        else:
            # No component: still editable, only without the arrows.
            st.text_area("note", value=note.get("text", ""),
                         key="note_plain_%s" % note_id, height=260,
                         label_visibility="collapsed",
                         on_change=lambda: NOTES.update(
                             st.session_state, note_id,
                             text=st.session_state.get(
                                 "note_plain_%s" % note_id, "")))

        c1, c2, c3 = st.columns([1, 1, 1])
        c1.button(t("note_to_box"), key="note_to_box",
                  use_container_width=True,
                  on_click=lambda: t1_set_text(note.get("text", "")))
        c2.button(t("note_new"), key="note_new_from",
                  use_container_width=True, on_click=close_note)
        # DELETE IS TWO PRESSES. One press on a whole note, in an app
        # with no undo anywhere, is not a risk worth taking.
        if st.session_state.get("_note_del_armed") == note_id:
            c3.button(t("note_del_sure"), key="note_del2", type="primary",
                      use_container_width=True, on_click=_del_do)
        else:
            c3.button(t("note_del"), key="note_del",
                      use_container_width=True, on_click=_del_arm)

        st.caption("%s %s   %s" % (
            t("note_made"), note.get("made", note.get("at", "")),
            ("·  " + t("note_edited") + " " + note["edited"])
            if note.get("edited") else ""))
    return True


def _lang_mode_row():
    """HR / ENG / single / multi.

    MOVED UP in v88, into the slot the status line used to occupy —
    directly under the deck. Baba: "these buttons will not be anymore at
    the bottom, they will be exactly where status line was before."

    It belongs there: both pairs answer "what happens when I press
    stop", so they are read BEFORE recording, not found afterwards at
    the foot of the page.
    """
    with st.container(key="langrow"):
        lcol1, lcol2, mcol1, mcol2, _ = st.columns([1, 1, 1.4, 1.4, 1.2])
        speech_now = st.session_state.get("speech_lang", "hr")
        lcol1.button(t("lang_hr"), key="tr_hr",
                     type="primary" if speech_now == "hr" else "secondary",
                     on_click=set_speech_lang, args=("hr",))
        lcol2.button(t("lang_en"), key="tr_en",
                     type="primary" if speech_now == "en" else "secondary",
                     on_click=set_speech_lang, args=("en",))
        # Single or multi, in the same row as the language, because both
        # answer "what happens when I press stop".
        appending = bool(st.session_state.get("append_mode"))
        mcol1.button(t("mode_single"), key="tr_single",
                     type="secondary" if appending else "primary",
                     on_click=set_append_mode, args=(False,))
        mcol2.button(t("mode_multi"), key="tr_multi",
                     type="primary" if appending else "secondary",
                     on_click=set_append_mode, args=(True,))


# =====================================================================
#  THE TRANSCRIPT IS NO LONGER WIDGET STATE  (v88)
#
#  For three sessions the transcript reached the archive and not the
#  box. Every path was read and every path was correct, which is the
#  signature of the CONTAINER being wrong rather than the code that
#  fills it.
#
#  `transcript_box` was the text_area's own widget key. Streamlit owns a
#  widget's key: it restores that slot from the frontend's copy on a
#  rerun, and it garbage-collects the slot when the widget does not
#  render on a run. The deck acknowledges every take by posting back,
#  and each post is another rerun (§30) — so a value written by Python
#  was competing with the browser's idea of what was in that box, on a
#  component that reruns several times per recording.
#
#  §25 already learned the mirror image of this: "never reuse a widget's
#  key as a place to keep the widget's output." This is the same lesson
#  from the other side, and the fix is the same shape — keep the value
#  somewhere Streamlit does not manage.
#
#  _t1_text is the truth. Nothing else is. The text_area is only a VIEW
#  of it:
#    * it is given the value explicitly, never through its key
#    * its key carries a generation number, so delivering new text
#      mounts a NEW widget, which is the one reliable way to make a
#      text_area show a value it did not previously hold
#    * typing in it syncs back through on_change, without bumping the
#      generation, so a keystroke does not remount the box under the
#      person's fingers
# =====================================================================

T1_TEXT = "_t1_text"
T1_GEN = "_t1_text_gen"


def t1_text() -> str:
    """The transcript. The single source of truth for T1's box."""
    return st.session_state.get(T1_TEXT, "") or ""


def t1_set_text(value: str) -> None:
    """Replace the transcript AND remount the box so it is shown.

    Bumping the generation is not decoration. A text_area that already
    exists keeps the value the browser last sent it; only a widget with
    a key it has never seen takes a fresh `value=`.
    """
    st.session_state[T1_TEXT] = value or ""
    st.session_state[T1_GEN] = int(st.session_state.get(T1_GEN, 0)) + 1


def t1_area_key() -> str:
    return "tx_area_%d" % int(st.session_state.get(T1_GEN, 0))


def deliver_text(new_text: str, keep: bool = True) -> None:
    """Put a finished transcript into the box, honouring single/multi.

    SINGLE overwrites. MULTI appends, so a long piece of work can be done
    in sittings — record for a while, stop, eat, come back, record again,
    and the pieces gather in one place instead of the last one wiping the
    rest. Baba: "How you eat elephant? Spoon by spoon."

    Every route goes through here — recorder, opened file, pasted text —
    because a mode that only worked for one of them would be worse than
    no mode at all.
    """
    new_text = (new_text or "").strip()
    if not new_text:
        return
    # KEPT BEFORE IT IS SHOWN. Every route arrives here — recorder, opened
    # file, pasted text — so archiving here catches all of them and cannot
    # be forgotten when a fourth route is added later.
    if keep:
        # THE REC_ID TRAVELS WITH THE TEXT. Session state dies on reload;
        # Drive does not. An archive row that carries the rec_id can still
        # be retranscribed or deleted in a session that starts tomorrow,
        # which is the whole reason for storing the audio at all.
        # ONE STORE, NOT TWO. archive.add() went on running here after
        # v98 replaced the archive with notes, filling a sixty-item list
        # nothing displayed — the same words kept twice, and the classic
        # way for two copies to drift apart. adopt_archive still reads
        # anything a previous session left behind, so nothing is lost.
        note_from_transcript(new_text)
    if st.session_state.get("append_mode"):
        old = t1_text().rstrip()
        # A blank line between takes: they are separate sittings and read
        # as separate paragraphs. Joining them with a space would run two
        # thoughts together and there is no way to tell them apart after.
        t1_set_text((old + "\n\n" + new_text) if old else new_text)
    else:
        t1_set_text(new_text)

    # WHAT ACTUALLY LANDED IN THE BOX. Baba reported text reaching the
    # archive but not the box, and reasoning about it from the source got
    # nowhere — every path looked correct. This records the truth at the
    # moment it happens, so the log answers it instead of a guess.
    errlog.add(st.session_state, "deliver",
               "delivered %d chars, box now %d chars, mode %s"
               % (len(new_text),
                  len(t1_text()),
                  "multi" if st.session_state.get("append_mode") else "single"))


def set_append_mode(on: bool):
    st.session_state["append_mode"] = bool(on)
    persist_settings()


def wave_cues(marks):
    """Turn the reader's sentence marks into the waveform player's cues.

    The reader has always produced SENTENCE marks — text plus character
    offsets plus start and end times — which is already the shape
    ttt/cues.py produces. So no new timing is computed here: the two views
    read the SAME numbers, which is the only way the subtitle, the red
    word and the sentence jump can be guaranteed not to drift apart.

    `first`/`last` are left at -1 because these are sentences, not words;
    the player shows the line without a lit word when it has no word
    times, and that is the honest degradation.
    """
    out = []
    for m in (marks or []):
        try:
            t0 = m.get("start_time")
            t1 = m.get("end_time")
            if t0 is None or t1 is None:
                continue
            out.append({"text": str(m.get("text", "")),
                        "start": float(t0), "end": float(max(t1, t0)),
                        "first": -1, "last": -1})
        except Exception:
            continue
    return out


def _drop_take():
    """Forget the recording that is being held.

    WHY THIS EXISTS. `clear` and `new` used to pop `_digest` and nothing
    else — but since v57 the take itself lives in session state under
    `_take_mic_N`, so the very next run found audio with no digest,
    decided it was fresh, RE-TRANSCRIBED it and put the text straight
    back. The button worked; the deck undid it a fraction of a second
    later, which is exactly how it looked on the phone: a cell that
    highlights and does nothing.

    Anything that clears the transcript must also forget the audio.
    """
    for k in [k for k in list(st.session_state)
              if k.startswith("_take_mic_") or k.startswith("_cassette_seen_")]:
        st.session_state.pop(k, None)
    st.session_state.pop("_take_mime", None)


def _derive_marks(sent: str, audio_bytes, dur: float):
    """Word marks for audio whose engine reported none. None on any doubt.

    Never raises and never blocks the reading: every failure path returns
    None, and the caller then reads the sentence exactly as it did before
    this existed. A highlight is a courtesy; the audio is the point.
    """
    try:
        if not audio_bytes or not dur:
            return None
        ring = get_ring("groq")
        if not ring:
            return None
        # speech_lang is the key the reader actually sets ('hr'/'en').
        # An invented key would silently read None and cost Whisper its
        # language hint, which matters most on Croatian.
        lang = st.session_state.get("speech_lang") or None
        return WORDTIMES.marks_for(
            sent, audio_bytes, dur,
            rotate=lambda attempt: kr.rotate(ring, lambda k: attempt(k)),
            language=lang)
    except Exception:
        return None


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

        if not marks:
            # The engine gave no word marks — this is Edge. Recover them
            # from the audio it just rendered, by asking Whisper for word
            # timestamps and mapping what it HEARD onto what we are
            # DISPLAYING. Measured against Speechify's exact marks on
            # held-out sentences: median 47 ms, 80% inside 100 ms, against
            # 119 ms median for a proportional guess. Full method and the
            # approaches that failed: docs/WORD_TIMINGS.md.
            #
            # It costs one call (~0.4 s) before this sentence starts, and
            # it is allowed to fail: marks stays None and the reader does
            # exactly what it did before, sentence at a time.
            marks = _derive_marks(sent, audio_bytes, dur)

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
            f"{SYM['next']} {page_idx + 2}/{n_pages}",
            key=page_key + "_nextbtn",
            help=t("next_page"), on_click=_next_page,
        )


def _set_translate_lang(which: str, code: str):
    st.session_state["translate_" + which] = code




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


# Spare keys from the sheet, if it has any and this session lacks them.
# Placed here rather than beside the ring setup because the helper is
# defined further down — calling it earlier is a NameError, which is the
# same ordering mistake that took every tab down in v33.
try:
    adopt_sheet_keys()
    adopt_sheet_engine()
except Exception:
    pass          # the sheet is never allowed to break startup


# ----------------------------------------------------------------------
# Tab bar. A segmented control rather than st.tabs, because st.tabs cannot
# be switched from Python — its session_state updates but the visible
# selection does not follow (verified in a browser), and Read this has to
# be able to move the user to the Talk tab by itself.
# ----------------------------------------------------------------------
st.session_state.setdefault("active_tab", "transcribe")
st.segmented_control(
    "nav", nav_tabs(),
    format_func=lambda k: t("tab_" + k),
    key="active_tab", required=True, label_visibility="collapsed",
)
active = st.session_state.get("active_tab") or "transcribe"
name_the_symbols()


# ONE MODULE, TWO SOURCES.
#
# Everything after capture is identical — the router, ffmpeg, chunking,
# Whisper, the archive, Drive, the box — so the microphone and the
# computer's own sound differ in exactly one thing: which stream the
# deck opens. That is a dropdown, not a second tab.
if active == "transcribe":
    _source = st.session_state.get("rec_source", "mic")
    _t2 = _source == "system"

    # A NOTE TAKES OVER THE MODULE. The deck still renders — the whole
    # point is talking INTO the note — but the list, the command row and
    # the main box do not. Two writing surfaces on one screen is two
    # places the words might have gone, and for someone who cannot see
    # well that is the difference between an app and a puzzle.
    NOTES.adopt_archive(st.session_state)
    _note_is_open = bool(st.session_state.get(OPEN_KEY))
    # Recorder, then Sound, then Picture, then the language switch at the
    # bottom. Baba's order, and the right one: the thing people came to do
    # is first, and the setting they rarely change is last.
    stt = stt_bridge()
    if stt is None:
        st.error(t("routing_none"))
        st.stop()
    t_engine = stt.id
    lang_code = st.session_state.get("speech_lang", "hr")

    # A new take needs its own command. Without one, the only way to
    # record again was to work out that the recorder had to be cleared
    # first — which is not a thing anyone should have to work out.
    # THE CASSETTE DECK. st.audio_input cannot be restyled into a transport
    # row with a live scope, so capture is a real component now. Only the
    # CAPTURE changed — the bytes go into exactly the same ffmpeg and
    # transcribe path as before, which is why this swap is small.
    #
    # Format is webm/opus at 128 kbit, because MediaRecorder cannot produce
    # WAV in any browser. Measured transparent: through this app's ffmpeg
    # chain, Whisper returns the same words as a WAV reference. 32 kbit was
    # NOT transparent, so the bitrate floor is real. See HANDOVER §22.
    # SEPARATE KEYS PER SOURCE. Session state is one flat namespace
    # shared by every module (§57), and the held take lives under
    # "_take_" + rec_key — so a microphone take and a computer-audio take
    # must not be able to overwrite one another.
    rec_key = ("sys_%d" if _t2 else "mic_%d") % st.session_state.get("_mic_gen", 0)
    # The key changes with the source, so switching mid-session gives the
    # component a key it has never seen and it starts clean rather than
    # holding a take captured from the other input.
    # A KEYED CONTAINER so the deck sits on the same frame rhythm as
    # everything else. Rendered bare, the component's iframe carried its
    # own spacing and nothing could reach it from the stylesheet, which
    # is why there was visibly more room under the deck than between any
    # other two frames.
    with st.container(key="deckbox"):
        audio = cassette_recorder(rec_key, source=_source)

    # THE OPEN NOTE SITS DIRECTLY UNDER THE DECK, because the deck is now
    # the note's own record button — speak, and the words land in the
    # note that is open rather than in a new one.
    if _note_is_open:
        note_open_view()
        # STOP HERE. Everything below — the command row, the box, the
        # card list — belongs to the module's own writing surface, and a
        # note has taken the module over. Not hidden with CSS: not drawn.
        # The first attempt put this stop AFTER the command row was
        # built, so grammar and clear were still on screen underneath an
        # open note, pointed at text that was no longer in front of
        # anybody.
        tab_signature(t("sig_transcribe"))
        st.stop()

    if _t2:
        # UNDER the dropdown it explains, not above the deck. One line,
        # and only what is different — what the browser will and will not
        # offer is the component's job to report when rec is pressed, not
        # this line's job to guess in advance.
        st.caption(t("t2_hint"))
    # STORE IT UNDER A DIFFERENT KEY. rec_key belongs to the component
    # widget, and Streamlit refuses to let anything else write to a key a
    # widget owns — assigning to it raises StreamlitAPIException on the
    # very next run, which is what crashed the app on the phone in v56.
    hold_key = "_take_" + rec_key
    if audio is not None:
        st.session_state[hold_key] = audio
    else:
        audio = st.session_state.get(hold_key)

    def _new_take():
        # NEW MEANS START AGAIN. It reset the deck and dropped the held
        # audio but left the text on screen, so pressing it changed
        # nothing a person could see — which is indistinguishable from a
        # dead button, and is what Baba reported. In multi mode this is
        # also the only way to begin a fresh document.
        st.session_state["_mic_gen"] = st.session_state.get("_mic_gen", 0) + 1
        t1_set_text("")
        for k in ("_digest", "_pick_digest", "flac_path", "_transcript_prev",
                  "_transcribe_method", "_last_run", "_stt_errors"):
            st.session_state.pop(k, None)
        _drop_take()
        flash("tx_new")

    if audio is not None:
        digest = hashlib.md5(audio.getvalue()).hexdigest()
        if st.session_state.get("_digest") != digest:
            old_flac = st.session_state.get("flac_path")
            if old_flac and os.path.exists(old_flac):
                os.remove(old_flac)
            st.session_state["_digest"] = digest
            try:
                raw = audio.getvalue()
                # WHAT IS THIS FILE? Decided by content first, name second.
                # A phone will hand over 'recording.wav' that is really an
                # m4a, and the share sheet sometimes supplies no extension
                # at all. Handing a picture to ffmpeg produces a codec
                # error about audio streams, which tells the person
                # nothing about what they actually did.
                plan = intake.route(
                    name=getattr(audio, "name", ""),
                    mime=st.session_state.get("_take_mime", ""),
                    head=raw[:64], size=len(raw), spoken_limit=SAFE_BYTES)

                # THE RETURN PATH, SAID OUT LOUD. The send is verbose and
                # the return was silent, so a take that produced nothing
                # looked identical to one still working. Every stage is
                # timed and named, and the line survives the rerun.
                st.session_state.pop("_stt_errors", None)
                stage = {"in": intake.describe(getattr(audio, "name", ""),
                                               st.session_state.get("_take_mime", ""),
                                               raw[:64]),
                         "in_kb": len(raw) // 1024}
                _t0 = time.time()

                if plan["pipeline"] == "read":
                    deliver_text(raw.decode("utf-8", errors="replace"))
                    st.session_state["_transcribe_method"] = "text"
                    st.session_state["flac_path"] = None
                elif plan["pipeline"] == "ocr":
                    # No route for a picture until read_picture is
                    # restored (HANDOVER §24). Say so plainly rather than
                    # letting ffmpeg fail about missing audio streams.
                    st.error(t("img_unavailable"))
                elif plan["pipeline"] == "transcribe":
                    with st.spinner(t("preparing_audio")):
                        flac_path = to_flac16k(raw)
                    stage["convert_s"] = time.time() - _t0
                    stage["out"] = "16 kHz mono FLAC"
                    stage["out_kb"] = os.path.getsize(flac_path) // 1024
                    stage["mins"] = audio_seconds(flac_path) / 60.0
                    # BOTH PATHS AT ONCE. The audio starts going to Drive
                    # here, and Whisper gets it on the next line. Neither
                    # waits for the other.
                    _keeper = start_keeping(flac_path,
                                            audio_seconds(flac_path), lang_code)
                    _t1 = time.time()
                    # ALWAYS through transcribe_any_size. This path used
                    # to call the provider directly, so a long take or a
                    # big upload died at Groq's 25 MB limit with nothing
                    # to show for it. The module already knows how to cut
                    # a file into ten-minute pieces, feed them one at a
                    # time and stitch the results back into one
                    # transcript, with a marker where a piece failed
                    # rather than a silent hole.
                    prog = st.progress(0.0, text=t("transcribing"))

                    def _cb(done, total):
                        try:
                            prog.progress(min(1.0, done / max(total, 1)),
                                          text=f"{t('transcribing')} {done}/{total}")
                        except Exception:
                            pass

                    text, method, reusable = transcribe_any_size(
                        flac_path, chosen_model(stt.provider) or model_for(lang_code),
                        lang_code, progress_cb=_cb)
                    prog.empty()
                    stage["transcribe_s"] = time.time() - _t1
                    stage["chars"] = len((text or "").strip())
                    stage["method"] = method
                    st.session_state["_last_run"] = stage
                    # THE WORDS GO ON SCREEN FIRST. Nothing may come
                    # between the transcript and the person who spoke it.
                    #
                    # keep_audio() used to run HERE, before delivery, and
                    # my own comment claimed it was "after the words are
                    # safe" — it was not. A Drive upload is the whole
                    # recording sent again as base64 to Apps Script, and
                    # while it ran the transcript sat finished in a
                    # variable with nothing on screen. Recording, stopping,
                    # and never getting the words back is exactly what that
                    # looks like.
                    #
                    # Storage is a convenience for LATER. It must never
                    # stand in front of the thing the person came for.
                    deliver_text(text)
                    # An EMPTY transcript is a real outcome and must say so.
                    # deliver_text ignores empty text on purpose, so without
                    # this the screen would show nothing at all and look
                    # exactly like a job still running — which is what
                    # happened on Baba's 7 MB take.
                    if not stage["chars"]:
                        errlog.add(st.session_state, "transcribe",
                                   "empty transcript — audio arrived, no speech found",
                                   f"{stage.get('in','?')} {stage.get('in_kb',0)} KB, "
                                   f"{stage.get('mins',0):.1f} min, "
                                   f"method {stage.get('method','?')}")
                        st.warning(t("nothing_heard"))

                    # The upload has been running all through the
                    # transcription. Usually it is already done and this
                    # returns at once.
                    with st.spinner(t("keeping_audio")):
                        _rec_id = finish_keeping(_keeper)
                    if _rec_id:
                        st.session_state["_last_rec_id"] = _rec_id
                        stage["rec_id"] = _rec_id
                        # THE PAIR IS COMPLETED HERE, and it cannot be
                        # done any earlier: the audio upload runs
                        # alongside Whisper, so at the moment it starts
                        # there is no transcript to store yet. The text
                        # goes in once both exist, into the same folder,
                        # so trashing that folder takes them both.
                        #
                        # After deliver_text, never before. Storage is a
                        # convenience for later and must never stand
                        # between someone and the words they just spoke.
                        if text:
                            _st = drive_store()
                            if not _st.put_text(_rec_id, text):
                                errlog.add(
                                    st.session_state, "drive",
                                    "transcript not stored beside the audio",
                                    _st.last_error or "no reason given")
                    # And let the recording go: a 7 MB take is ~7 MB of
                    # bytes plus ~9 MB of base64 still held by the
                    # component, which is memory this instance cannot
                    # spare once the words are out.
                    st.session_state.pop(hold_key, None)
                    st.session_state["flac_path"] = reusable
                    st.session_state["last_lang"] = lang_code
                    st.session_state["_transcribe_method"] = method
                    st.session_state["_transcribe_provider"] = t_engine
                    USAGE.log("transcribe", audio_seconds(reusable),
                              UNIT_SECONDS, t_engine)
                else:
                    st.error(t("file_unknown").format(why=plan["reason"]))
            except Exception as e:
                st.session_state["_last_run"] = {"error": str(e)[:300]}
                errlog.add(st.session_state, "transcribe",
                           f"{type(e).__name__}: {e}",
                           f"{stage.get('in','?')} {stage.get('in_kb',0)} KB"
                           if "stage" in dir() else "")
                st.error(str(e))

    # THE LANGUAGE AND MODE ROW NOW SITS HERE, in the slot the status
    # line used to hold — directly under the deck.
    _lang_mode_row()

    # ONE upload, and the file decides what happens to it. Two pickers
    # meant choosing before doing, and choosing wrongly was possible;
    # a person with a file in their hand should not have to classify it
    # first. `type` is left OPEN rather than listing extensions, because
    # Android's chooser greys out anything not in the accept list — which
    # is what made pictures unselectable when the lists were combined.
    # The deck's fourth cell is the file picker now, so this box normally
    # is not shown at all — one row instead of two. It appears only when a
    # file was too big for the component channel, which is the one case
    # Streamlit's own uploader still does better.
    picked = None
    if st.session_state.get("_show_big_upload"):
        st.caption(t("pick_big"))
        picked = st.file_uploader(
            t("pick_any"), label_visibility="collapsed", key="any_upload")

    if picked is not None:
        raw = picked.getvalue()
        digest = hashlib.md5(raw).hexdigest()
        if st.session_state.get("_pick_digest") != digest:
            st.session_state["_pick_digest"] = digest
            name = (picked.name or "").lower()
            is_image = name.endswith((".png", ".jpg", ".jpeg", ".webp",
                                      ".gif", ".bmp", ".heic", ".heif"))
            if is_image:
                try:
                    with st.spinner(t("img_working")):
                        text = read_picture(raw, picked.name)
                    save_rings()
                    if text.strip():
                        t1_set_text(text)
                        st.session_state["_transcribe_method"] = "picture"
                        st.session_state["flac_path"] = None
                        USAGE.log("picture", len(text), UNIT_CHARS, "groq")
                    else:
                        st.info(t("img_none"))
                except Exception as e:
                    st.error(f"{t('img_fail')}: {e}")
            else:
                old_flac = st.session_state.get("flac_path")
                if old_flac and os.path.exists(old_flac):
                    try:
                        os.remove(old_flac)
                    except Exception:
                        pass
                suffix = "_" + "".join(c for c in picked.name
                                       if c.isalnum() or c in "._-")
                tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                tmp.write(raw)
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
                            progress_bar.progress((i + 1) / n,
                                                  text=f"{t('chunk_progress')} {i + 1}/{n}")

                        def _on_wait(idx, attempt, secs, err):
                            progress_bar.progress(
                                0.5, text=t("chunk_waiting").format(s=secs, i=idx + 1))

                        text, method, reusable = transcribe_any_size(
                            tmp.name, chosen_model(stt.provider) or model_for(lang_code),
                            lang_code, progress_cb=_cb, on_wait=_on_wait)
                    progress_bar.empty()
                    # THROUGH deliver_text, like every other route. This
                    # path set the box directly, so an uploaded big file
                    # was never archived and ignored single/multi — the
                    # exact drift the one-helper rule exists to prevent.
                    deliver_text(text)
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
                    if st.session_state.get("flac_path") != tmp.name and os.path.exists(tmp.name):
                        try:
                            os.remove(tmp.name)
                        except Exception:
                            pass

    # THE BOX IS ALWAYS HERE. Baba: "I don't want the parts of user
    # interface are appearing and disappearing." A screen that grows new
    # sections as you use it is a screen you have to re-learn each time;
    # a box that is simply empty tells you where the words will land.
    st.session_state.setdefault(T1_TEXT, "")

    def _clear_all():
        t1_set_text("")
        for k in ("_transcript_prev", "flac_path", "_digest", "_pick_digest",
                  "_transcribe_method"):
            st.session_state.pop(k, None)
        _drop_take()
        flash("tx_clear")

    def _apply_transform(preset="", instruction=""):
        source = t1_text().strip()
        try:
            llm = llm_bridge()
            if llm is None:
                raise RuntimeError(t("routing_none"))
            # The wording comes from the sheet when it has one, so it can
            # be changed by hand without a deploy.
            custom = sheet_prompt("prompt_grammar" if preset == "fix"
                                  else "prompt_reshape") if preset else ""
            out = TR_.run(llm, source, instruction=instruction or custom,
                          preset="" if custom else preset)
            st.session_state["_transcript_prev"] = source
            t1_set_text(out)
            USAGE.log("transform", len(source), UNIT_CHARS, llm.id)
        except Exception as e:
            st.session_state["_ai_error"] = f"{t('ai_fail')}: {e}"

    def _grammar():
        _apply_transform("fix", "")
        flash("tx_grammar")

    def _reshape():
        _apply_transform("tidy", "")
        flash("tx_reshape")

    cmd_row("tx", [
        (t("new_take_word"), "tx_new", _new_take),
        ("copy", None, None),
        (t("grammar_word"), "tx_grammar", _grammar),
        (t("reshape_word"), "tx_reshape", _reshape),
        (t("clear_word"), "tx_clear", _clear_all),
    ], copy_text=t1_text())

    # A VIEW OF _t1_text, never the owner of it. The key carries the
    # generation, so delivering text mounts a new widget that takes the
    # new `value=`; typing syncs back without bumping it, or the box
    # would remount under the person's fingers on every keystroke.
    _area_key = t1_area_key()

    def _sync_typed():
        st.session_state[T1_TEXT] = st.session_state.get(_area_key, "")

    st.text_area(t("transcript_label"), value=t1_text(), key=_area_key,
                 height=200, on_change=_sync_typed,
                 label_visibility="collapsed", placeholder=t("transcript_ph"))

    if st.session_state.get("_ai_error"):
        st.error(st.session_state.pop("_ai_error"))

    # ---- the archive -------------------------------------------------
    # A second frame under the recording frame, as Baba described it.
    # Everything transcribed lands here by itself; before this, the only
    # copy of a take was whatever happened to be in the box, and `new` or
    # another recording lost it.
    #
    # Tapping a row puts it back in the box, THROUGH deliver_text — so in
    # multi it appends and in single it replaces, and one archive item is
    # what gets operated on, which is what Baba asked for.
    #
    # No new furniture: the same terminal row of cells as everywhere else.
    # ---- THE NOTES ----------------------------------------------
    #
    # Baba: "imagine the first tab is Keep from Google, with the ability
    # to talk to create a note, and once the note is created the user can
    # talk directly to the note. He does not need to edit with fingers."
    #
    # This replaced the archive, which could only put a transcript back
    # in the box. See ttt/notes.py for why a note is a different thing
    # from a take, and note_frontend/ for why the editor is a component.
    # adopt_archive already ran at the top of this module — it is cheap
    # and marker-guarded, but calling it twice per render is noise.
    notes_panel()

    # THE STATUS BOX, MOVED TO THE FOOT OF THE MODULE (v88).
    #
    # Baba: "status line below the player must be removed, display
    # collapsed." It no longer sits between the deck and the words, and
    # it no longer opens by itself — §34 gave it the auto-open so an
    # error could not be missed, but for a reader who cannot see well an
    # expander springing open mid-screen moves everything under it,
    # which is the worse failure. It is admin-only anyway, and every
    # error is in L regardless.
    _lr = st.session_state.get("_last_run")
    _errs = st.session_state.get("_stt_errors") or []
    # ADMIN ONLY. Baba: "this status line you are hiding from users, only
    # admins can see this." Codec names, convert seconds and Whisper's
    # refusals are diagnostics, and this is an app for people who cannot
    # read well — a line they cannot act on is noise in the way of the
    # words they came for.
    #
    # Nothing is lost by hiding it: every one of these already goes to
    # the L module through errlog, which is where it can be copied and
    # sent on. And the things a USER can act on are separate and stay —
    # the "nothing was heard" warning and the st.error paths above.
    if (_lr or _errs) and is_admin():
        # FOLDED AWAY BY DEFAULT, so it costs no room on a phone. It opens
        # BY ITSELF when something went wrong, because an error nobody can
        # see is the thing that wastes an evening. Small type, the same
        # monospace as the line above it.
        # EVERY KEY MUST BE UNIQUE WITHIN ONE RUN. Four containers shared
        # key="statusbox" and two of them landed in the admin panel
        # together, which is StreamlitDuplicateElementKey. The CSS matches
        # on [class*="st-key-statusbox"], so a suffix costs nothing and
        # the styling still applies to all of them.
        with st.container(key="statusbox_run"):
            with st.expander(t("status_word"), expanded=False):
                if _errs:
                    st.text(t("stt_errors"))
                    for _line in _errs:
                        st.text("  " + _line)
                if _lr and _lr.get("error"):
                    st.text("⚠ " + str(_lr["error"])[:300])
                elif _lr:
                    _bits = []
                    if _lr.get("in"):
                        _bits.append(f"{_lr['in']} {_lr.get('in_kb',0):,} KB")
                    if _lr.get("out"):
                        _bits.append(f"→ {_lr['out']} {_lr.get('out_kb',0):,} KB")
                    if _lr.get("mins"):
                        _bits.append(f"{_lr['mins']:.1f} min")
                    if _lr.get("convert_s"):
                        _bits.append(f"convert {_lr['convert_s']:.1f}s")
                    if _lr.get("transcribe_s"):
                        _bits.append(f"transcribe {_lr['transcribe_s']:.1f}s")
                    if _lr.get("method"):
                        _bits.append(str(_lr["method"]))
                    _bits.append(f"{_lr.get('chars',0):,} chars")
                    st.text("  ·  ".join(_bits))


    tab_signature(t("sig_transcribe"))


elif active == "talk":
    # ONE PLAYER FOR THE WHOLE TEXT.
    #
    # Baba's design, and the right one: paste, the box goes away, the
    # audio is made, and then there is only a player and the sentence
    # being spoken. No audio bar per sentence, no gap at every full stop,
    # and the elapsed and remaining time come free from the audio itself.
    #
    # Two states, never both: WRITING (paste + box + go) and PLAYING
    # (player + subtitle + new text).
    sp_ring_talk = get_ring("speechify")
    _tts = current_routes()["tts"]
    engine = _tts.id if _tts else "edge"

    job = st.session_state.get("_talk_job")

    if job:
        # ---- PLAYING, one part at a time ----------------------------
        # Only ever ONE player on screen. When a part finishes, the
        # component says so, the next part is made, and the player is
        # replaced in the same place. Baba: "you just remove that player
        # and put at the same place the other player."
        # A VOICE WAS CHANGED WHILE PLAYING. The cache was dropped by
        # _revoice; the synth closure still points at the OLD voice, so it
        # has to be rebuilt here — on the main thread, before any worker
        # touches it. The index is untouched, so the new voice takes over
        # from the block being listened to.
        if st.session_state.pop("_talk_revoice", False):
            job["synth"] = _voice_row_synth_only(engine, sp_ring_talk)

        idx = job["index"]
        parts = job["parts"]
        cached = job["cache"].get(idx)

        def _make_quiet(i):
            """Worker body. Swallows its own errors so one failed block
            cannot cancel the others, and touches no Streamlit API."""
            try:
                _make(i)
            except Exception:
                pass

        def _make(i):
            """Build block i into the cache. Returns it."""
            if i in job["cache"] or i >= len(parts):
                return job["cache"].get(i)
            ss, char_off = parts[i]
            path, marks, total, temps = SPEECH.build_part(
                ss, job["synth"], char_off, job["full_text"])
            with open(path, "rb") as f:
                audio = f.read()
            ttt_audio.cleanup(*temps)
            job["cache"][i] = {"audio": audio, "marks": marks}
            return job["cache"][i]

        if cached is None:
            with st.spinner(t("gen_part").format(i=idx + 1, n=len(parts))):
                cached = _make(idx)
            save_rings()

        scale = a11y.clamp(st.session_state.get("text_scale", a11y.DEFAULT_SCALE))
        if _wave_component is not None:
            # THE WAVEFORM PLAYER, in the same place the old one stood.
            # Baba: "you just remove that player and put at the same place
            # the other player."
            ev = _wave_component(
                src="data:audio/mpeg;base64," + base64.b64encode(cached["audio"]).decode(),
                cues=wave_cues(cached["marks"]), words=[], wtimes=[],
                labels={"play": t("wave_play"), "pause": t("wave_pause"),
                        "back": t("wave_back"), "next": t("wave_next"),
                        "save": t("wave_save")},
                part=idx + 1, parts=len(parts),
                scale=scale, autoplay=True, key="talk_player", default=None)
            # The part finished: move to the next one and let the spinner
            # above make it. Guarded by a stamp so one finish is one move.
            if isinstance(ev, dict) and ev.get("at"):
                seen = st.session_state.get("_talk_player_seen")
                if seen != ev["at"] and idx + 1 < len(parts):
                    st.session_state["_talk_player_seen"] = ev["at"]
                    job["index"] = idx + 1
                    st.rerun()

        # THE VOICES, ON SCREEN WHILE IT PLAYS. Baba: "the voices should
        # be always available on screen, so while the audio is playing
        # user can change the voice and then you re-render audio." A
        # voice is easiest to judge while it is speaking, and that was
        # exactly when it could not be changed.
        _voice_row(engine, sp_ring_talk)

        def _new_text():
            st.session_state.pop("_talk_job", None)
            st.session_state.pop("_talk_player_seen", None)
            st.session_state.pop("_talk_revoice", False)

        st.button(t("new_text"), key="talk_new", on_click=_new_text)

        # THREE BLOCKS AHEAD, BUILT IN PARALLEL.
        #
        # This runs AFTER the player is on the page. The player is a
        # client-side iframe already playing, so Python carrying on here
        # does not interrupt the sound — that is what makes prefetching
        # free from the listener's point of view.
        #
        # In parallel rather than one after another: three blocks built
        # in sequence take three times as long, and the whole point is to
        # stay far enough ahead that a hand-off is never heard. The
        # provider calls are network-bound, so threads overlap the waiting
        # almost perfectly.
        #
        # Safe because ttt/keyring.rotate() takes a lock around choosing a
        # key and recording its verdict (but NOT around the request), so
        # several threads can share one key ring without racing. Nothing
        # in the worker touches Streamlit — st.* is not thread-safe, so
        # the workers only synthesise and write files, and save_rings()
        # is called back here on the main thread.
        wanted = [i for i in range(idx + 1, min(idx + 1 + PREFETCH_AHEAD, len(parts)))
                  if i not in job["cache"]]
        if wanted:
            try:
                with ThreadPoolExecutor(max_workers=len(wanted)) as pool:
                    list(pool.map(_make_quiet, wanted))
                save_rings()
            except Exception:
                pass          # a failed prefetch only costs a short wait later

    else:
        # ---- WRITING -------------------------------------------------
        # THE PLAYER IS AT THE TOP, exactly as the deck is in T1. Baba:
        # "we use T1 as the master designer, copy to R the same layout."
        # One shape for both modules: the transport is the first thing
        # under the tabs in each, so a hand goes to the same place without
        # looking, whichever module is open.
        # PLAY ON THE DECK IS WHAT STARTS THE READING. Baba: "users
        # should click play right on the deck itself, this button is
        # redundant." So the separate go button below the box is gone and
        # the transport's own play cell does it — one control for
        # starting and for pausing, in the place a hand already goes.
        _has_text = bool((st.session_state.get("talk_text") or "").strip())
        _start = False
        if _wave_component is not None:
            _ev0 = _wave_component(
                src="", cues=[], words=[], wtimes=[],
                labels={"play": t("wave_play"), "pause": t("wave_pause"),
                        "back": t("wave_back"), "next": t("wave_next"),
                        "save": t("wave_save")},
                part=0, parts=0, startable=_has_text,
                scale=a11y.clamp(st.session_state.get(
                    "text_scale", a11y.DEFAULT_SCALE)),
                autoplay=False, key="talk_player_idle",
                default=None)
            # One press is one start. The stamp guards against the
            # component re-reporting the same press across reruns, the
            # same rule the finish signal follows.
            if isinstance(_ev0, dict) and _ev0.get("start"):
                if st.session_state.get("_talk_start_seen") != _ev0.get("at"):
                    st.session_state["_talk_start_seen"] = _ev0.get("at")
                    _start = True

        synth_fn = _voice_row(engine, sp_ring_talk)

        def _clear_talk():
            st.session_state["talk_text"] = ""
            flash("rd_clear")

        def _keep_text():
            txt = (st.session_state.get("talk_text") or "").strip()
            if txt:
                st.session_state["_archive"] = RT.add_piece(
                    st.session_state.get("_archive", []), txt)
                RT.save_archive(archive_store, st.session_state["_archive"])
            flash("rd_keep")

        cmd_row("rd", [
                (t("archive_word"), "rd_keep", _keep_text),
            (t("clear_word"), "rd_clear", _clear_talk),
        ], target_key="talk_text")

        st.text_area(t("tab_talk"), key="talk_text", height=150,
                     label_visibility="collapsed", placeholder=t("talk_placeholder"))

        # THE PLAYER IS ALWAYS HERE, greyed until there is something to
        # play. Baba's rule from the start: "no new elements appearing on
        # the screen. Everything is already there, only greyed out."
        #
        # It used to exist only inside `if job:`, so pressing read made a
        # whole player bar appear and everything below it jumped down the
        # page. The bar is the tallest thing in this module; that jump was
        # the worst one in the app.
        # (the go button lived here and is gone — see the deck above)
        go = _start

        # The archive, brought over from the tab that was merged away.
        archive_store = Store(RT.ARCHIVE_NS, USER, ls_read=LS_DATA,
                              ls_write=lambda k, v: queue_ls(writes={k: v}) if v is not None
                              else queue_ls(removes=[k]),
                              local_only=True)
        if "_archive" not in st.session_state:
            st.session_state["_archive"] = RT.load_archive(archive_store)

        def _keep_text():
            txt = (st.session_state.get("talk_text") or "").strip()
            if txt:
                st.session_state["_archive"] = RT.add_piece(
                    st.session_state.get("_archive", []), txt)
                RT.save_archive(archive_store, st.session_state["_archive"])



        # NOT named `archive`: that shadowed the imported module for the
        # rest of this block, so any archive.* call here would have hit a
        # list and raised. Nothing called one yet — this is closing the
        # trap before somebody does.
        read_pieces = st.session_state.get("_archive", [])
        if read_pieces:
            with st.expander(f"{t('read_archive')} ({len(read_pieces)})"):
                for piece in read_pieces:
                    acol1, acol2, acol3 = st.columns([4, 1, 1])
                    acol1.caption(piece["title"])

                    def _open(d=piece["digest"]):
                        for pc in st.session_state.get("_archive", []):
                            if pc["digest"] == d:
                                st.session_state["talk_text"] = pc["text"]
                                break

                    def _delete(d=piece["digest"]):
                        st.session_state["_archive"] = RT.remove_piece(
                            st.session_state.get("_archive", []), d)
                        RT.save_archive(archive_store, st.session_state["_archive"])

                    acol2.button(t("read_open"), key="ropen_" + piece["digest"][:8],
                                 on_click=_open)
                    acol3.button(SYM["clear"], key="rdel_" + piece["digest"][:8],
                                 help=t("read_delete"), on_click=_delete)
                st.caption(t("read_storage_note"))
        if go or st.session_state.pop("_auto_read", False):
            raw = (st.session_state.get("talk_text") or "").strip()
            if raw:
                sentences = tk.sentences_of(raw)
                st.session_state["_talk_job"] = {
                    "parts": SPEECH.plan_blocks(sentences),
                    "full_text": " ".join(sentences),
                    "index": 0, "cache": {}, "synth": synth_fn,
                }
                USAGE.log("read", len(raw), UNIT_CHARS, engine)
                st.rerun()
            else:
                st.info(t("nothing_to_read"))


    tab_signature(t("sig_read"))


elif active == "translate":
    # THE LANGUAGE MATRIX SITS BETWEEN THE BOXES.
    #
    # Baba's arrow: both language rows belong in the gap between the two
    # text boxes — from on top, to underneath — so the pair reads as one
    # matrix pointing from the box above into the box below. Before, the
    # "from" row was stranded at the top of the tab with nothing near it
    # to be "from" of.
    #
    # COMMANDS TOUCH THE BOX THEY ACT ON, in one left-aligned terminal
    # row separated by pipes:  paste | translate | clear
    # Same size, same colour, evenly spaced, hard against the box, so the
    # row reads as a line of commands rather than as scattered buttons.
    st.session_state.setdefault("translate_src", "hr")
    st.session_state.setdefault("translate_tgt", "en")
    st.session_state.setdefault("translate_out", "")

    def _clear_src():
        st.session_state["translate_src_text"] = ""
        st.session_state["translate_out"] = ""
        flash("tr_src")

    def _do_translate():
        do_translate()
        flash("tr_go")

    cmd_row("trsrc", [
        (t("clear_word"), "tr_clear_src", _clear_src),
    ], target_key="translate_src_text")

    st.text_area("src", key="translate_src_text", height=120,
                 label_visibility="collapsed", placeholder=t("translate_src_ph"))

    # TRANSLATE BELONGS TO THE MATRIX, not to the command row.
    #
    # Baba's reasoning, and it is the workflow principle again: you pick
    # the languages, THEN you translate. So the button sits beside the two
    # language rows and spans both — it is the action for the pair, not
    # for either one. Its label may break across two lines rather than
    # push anything off the screen.
    with st.container(key="trmatrix"):
        mcol, bcol = st.columns([4, 1.4])
        with mcol:
            lang_pills("srcpill", "src", st.session_state["translate_src"])
            lang_pills("tgtpill", "tgt", st.session_state["translate_tgt"])
        with bcol:
            st.button(t("translate_btn_word"), key="do_translate_btn",
                      use_container_width=True, on_click=_do_translate)

    if st.session_state.get("_translate_error"):
        st.error(st.session_state.pop("_translate_error"))

    def _clear_out():
        st.session_state["translate_out"] = ""
        flash("tr_out")

    cmd_row("trout", [
        ("copy", None, None),
        (t("clear_word"), "tr_clear_out", _clear_out),
    ], copy_text=st.session_state.get("translate_out", ""))

    st.text_area("out", key="translate_out", height=150,
                 label_visibility="collapsed", placeholder=t("translate_out_ph"))

    tab_signature(t("sig_translate"))


elif active == "looks":
    # HOW THE APP LOOKS — everyone gets this. Size, typeface, colour.
    # Deliberately separate from engines and keys: what a person sees is
    # theirs to set, what the app talks to is the owner's.
    st.caption(t("looks_size"))
    size_controls()

    st.caption(t("looks_font"))
    fcols = st.columns(3)
    for col, (fid, label) in zip(fcols, [("mono", "mono"), ("sans", "sans"),
                                         ("serif", "serif")]):
        def _pick_font(f=fid):
            st.session_state["font_family"] = f
            persist_settings()
        col.button(label, key=f"font_{fid}", use_container_width=True,
                   type="primary" if st.session_state.get("font_family", "mono") == fid
                   else "secondary", on_click=_pick_font)

    st.caption(t("looks_scheme"))
    scols = st.columns(4)
    for col, sid in zip(scols, ["amber", "green", "cyan", "paper"]):
        def _pick_scheme(x=sid):
            st.session_state["scheme"] = x
            persist_settings()
        col.button(sid, key=f"scheme_{sid}", use_container_width=True,
                   type="primary" if st.session_state.get("scheme", "amber") == sid
                   else "secondary", on_click=_pick_scheme)

    st.text_area("preview", key="looks_preview", height=110,
                 label_visibility="collapsed", value=t("looks_preview"))

    # YOUR ACCOUNT — everyone, not the owner. The amber gear is engines
    # and keys and belongs to Baba; this is the two things that are a
    # person's own: getting out, and their own password.
    st.divider()
    st.subheader(t("account_title"))

    # LOG OUT IS UNCONDITIONAL. Whatever got you in — a password, a
    # remembered token, the emergency door — must have a way out, or a
    # shared phone cannot be handed over. It is the one control on this
    # page that must never be hidden by a condition.
    st.button(t("log_out"), key="log_out_btn", on_click=log_out,
              use_container_width=True)

    # The password half only for people who HAVE one here. Somebody who
    # came through APP_PASSWORDS has no row to change, and the script
    # would answer a flat no that reads like a bug.
    if st.session_state.get("_via_accounts") and auth_url():
        st.text_input(t("pw_current"), type="password", key="_pw_cur")
        st.text_input(t("pw_new"), type="password", key="_pw_new")
        st.text_input(t("pw_repeat"), type="password", key="_pw_rep")
        st.button(t("pw_change"), key="pw_change_btn",
                  on_click=change_own_password, use_container_width=True)
        _msg = st.session_state.get("_pw_msg")
        if _msg:
            (st.success if _msg[0] == "good" else st.error)(_msg[1])

    tab_signature(t("sig_looks"))


# T2 IS BUILT NOW and is handled by the shared branch above. The
# description-only module it used to be is gone: it existed so the shape
# of the app was honest about what was coming, and keeping it beside a
# working deck would have been two answers to one question.


elif active == "help":
    # The whole page is ONE component holding both languages, so the HR/ENG
    # toggle inside it is instant and does not move you in the text. Doing
    # it with Streamlit buttons would rerun the script, rebuild the page
    # and throw you back to the top — which is the one thing Baba asked it
    # not to do.
    components.html(HELP_PAGE.page(st.session_state.get("ui_lang", "hr")),
                    height=620, scrolling=True)


elif active == "log":
    # ADMIN ONLY. Errors in this app are caught in many places on purpose,
    # so that a failed transcription does not lose the audio and a failed
    # highlight does not stop the reading. That patience kept swallowing
    # the REASON, which is what cost an evening on a 7 MB take. Every
    # caught error is now written here as well as handled.
    st.subheader(t("log_title"))
    _rows = errlog.entries(st.session_state)
    if not _rows:
        st.caption(t("log_empty"))
    else:
        _all = errlog.as_text(st.session_state)
        # The whole history in one press — the point of the module is that
        # it can be handed to somebody else.
        components.html(
            copybtn.html(_all, label=t("copy_idle"), busy=t("copy_busy"),
                         done=t("copy_done"), failed=t("copy_failed"),
                         scale=a11y.clamp(st.session_state.get(
                             "text_scale", a11y.DEFAULT_SCALE)),
                         fg=theme.SCHEMES.get(
                             st.session_state.get("scheme", "amber"),
                             theme.SCHEMES["amber"]).get("prose", "#f2ddb4"),
                         font=theme.FONTS.get(
                             st.session_state.get("font", "mono"),
                             theme.FONTS["mono"])),
            height=copybtn.HEIGHT)
        st.button(t("log_clear"), key="log_clear",
                  on_click=lambda: errlog.clear(st.session_state))
        with st.container(key="statusbox_log"):
            _day = None
            for _e in _rows:
                if _e.get("day") != _day:
                    _day = _e.get("day")
                    st.text(f"--- {_day} ---")
                st.text(f"{_e.get('t','')}  [{_e.get('where','')}]  "
                        f"{_e.get('msg','')}")
                if _e.get("detail"):
                    st.text(f"            {_e['detail']}")


elif active == "settings":
    # THE SIMPLEST THING THAT WORKS, AND ONLY FOR THE OWNER.
    #
    # Baba: "I don't like this patch bay and other things. Make it as
    # simple as possible... settings are hidden from other users."
    #
    # So: keys, language, help. Nothing else. The patch bay, the model
    # pickers and the voice catalogue still EXIST and still work — they
    # are just not shown, because choosing an engine is a decision the
    # owner makes once for everyone, not something a reader should meet.
    # Routing falls back to the defaults, which is what it already did
    # whenever nothing was chosen.
    if not is_admin():
        st.caption(t("settings_owner_only"))
    else:
        # Small, at the top, out of the way. It is a health reading, not a
        # heading — it was sitting among the controls in body type, which
        # is why the panel read as cluttered.
        _u = USAGE.status()
        with st.container(key="statusbox_admin"):
            st.text(f"{t('admin_sent')}: {_u['sent']}  ·  "
                    f"{t('admin_failed')}: {_u['failed']}"
                    if _u["enabled"] else t("usage_off"))

        # ---- who the app talks to ---------------------------------
        rings = load_keys()
        for prov in PROVIDERS.keyed_providers():
            ring = get_ring(prov.id)
            n = len(ring["keys"])
            live = sum(1 for k in ring["keys"] if k["state"] != "dead")
            with st.expander(f"{prov.label}  ·  {live}/{n}" if n else prov.label):
                st.file_uploader(t("key_file_label"), key=f"{prov.id}_key_file",
                                 label_visibility="collapsed")
                st.text_area(t("key_paste_label"), key=f"{prov.id}_key_paste",
                             height=68, label_visibility="collapsed",
                             placeholder=t("key_paste_ph"))

                def _import(pid=prov.id, pr=prov):
                    raw = ""
                    f = st.session_state.get(f"{pid}_key_file")
                    if f is not None:
                        raw += f.getvalue().decode("utf-8", "replace")
                    raw += " " + (st.session_state.get(f"{pid}_key_paste") or "")
                    added = kr.import_keys(get_ring(pid), raw,
                                           prefixes=pr.key_prefixes)
                    save_rings()
                    st.session_state["_key_msg"] = (
                        f"{t('keys_added')}: {added}" if added else t("no_keys_found"))

                st.button(t("import_keys_btn"), key=f"{prov.id}_import",
                          on_click=_import)

                if ring["keys"]:
                    render_key_list(ring, rings, prov.id,
                                    (lambda pr: (lambda key: pr.test_key(key)))(prov))

        if st.session_state.get("_key_msg"):
            st.caption(st.session_state.pop("_key_msg"))

        # ---- THE ENGINE -------------------------------------------
        # This replaced the interface-language pills. Baba: "instead of
        # interface language, which will be always English, no question
        # asked, we write engine." The STRINGS table keeps both languages
        # and the login screen still offers five — this is only the
        # in-app chrome, which is now English and settled.
        #
        # GLOBAL, not per-user: it is the app's engine, so it is stored
        # beside the app's own settings rather than in one person's
        # browser.
        # THE ENGINE IS THE OWNER'S TO SET. Baba: "your normal user
        # doesn't have these settings, he is working with engine which I
        # assign." A normal user is not shown the controls at all —
        # hidden rather than disabled, because a dead button invites a
        # question that has no good answer for the person asking it.
        with st.container(key="statusbox_engine"):
            elab, ecol1, ecol2 = st.columns([1.1, 2.1, 2.8])
            elab.text(t("settings_engine"))
            _now = engine_now()
            _now_id = _now.id if _now else ""
            for col, eng in zip((ecol1, ecol2), EN.ENGINES):
                col.button(eng.label, key="eng_%s" % eng.id,
                           type="primary" if eng.id == _now_id else "secondary",
                           help=eng.note,
                           on_click=pick_engine, args=(eng.id,),
                           use_container_width=True)

            # Did the global save land? A global setting that quietly
            # did not save is worse than one that never claimed to.
            if "_engine_saved" in st.session_state:
                st.caption(t("eng_saved") if st.session_state["_engine_saved"]
                           else t("eng_notsaved"))

            # CHECK ENGINE. Baba: "it will just check if it can connect,
            # it means keys are good, engine can work."
            st.button(t("eng_check"), key="eng_check",
                      on_click=run_engine_check)

            _res = st.session_state.get("_engine_check")
            if _res:
                # A verdict about a DIFFERENT engine is worse than none —
                # it is read as applying to the one on screen.
                if _res.get("engine") != _now_id:
                    st.caption(t("eng_stale"))
                else:
                    _bad = _res.get("state") == EN.FAIL
                    st.caption(("✗ " if _bad else "✓ ") +
                               (t("eng_bad") if _bad else t("eng_good")) +
                               "  ·  " + _res.get("at", ""))
                    for _row in _res.get("rows", []):
                        _p = PROVIDERS.get(_row["provider"])
                        _name = getattr(_p, "label", None) or _row["provider"]
                        _jobs = ", ".join(
                            t("eng_task_" + j) for j in
                            EN.tasks_for(EN.get(_now_id), _row["provider"])
                        ) if _now_id else ""
                        _mark = {EN.OK: "✓", EN.FAIL: "✗", EN.SKIP: "–"}.get(
                            _row["state"], "?")
                        st.text("  %s %s (%s) %s" % (
                            _mark, _name, _jobs, _row.get("detail", "")))

            # ---- ONE ENGINE PER PERSON ----------------------------
            st.text(t("eng_users_title"))
            user_engine_panel()

        # Help lived here as an expander AND as its own module. Two copies
        # of the same text drift apart, and the module is the one people
        # find. Removed rather than kept in sync.

    tab_signature("")
