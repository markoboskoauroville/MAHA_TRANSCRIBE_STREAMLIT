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
import shutil
import tempfile
import subprocess
import base64
from concurrent.futures import ThreadPoolExecutor

# Bumped on every change. Also the stale-module stamp below, so the two
# can never drift apart.
APP_VERSION = "v182 (VR — virtual rehearsal, 24 voices and 18 emotions)"

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
from ttt.providers import assemblyai as AAI
from ttt import providers as PROVIDERS
from ttt.store import Store
from ttt.usage import UsageLog, UNIT_SECONDS, UNIT_CHARS
from ttt import transform as TR_
from ttt import eta as ETA
from ttt import vr as VR
from ttt import vision
from ttt import notes as NOTES
from ttt.providers.groq import FAST_STT as GROQ_FAST_STT
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
                      st.session_state.get("font_family", "mono"),
                      st.session_state.get("ui_scale", 1.0)),
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

# CROATIAN SPELLING FOR A CROATIAN VOICE. "Gabby" is an English
# shortening of a Croatian name, sitting next to Srećko who kept his
# diacritic. Baba noticed; he is right that it looked borrowed.
VOICE_SHORT = {"Gabrijela": "Gabi", "Srecko": "Srećko"}
VOICES_BY_LANG = {"hr": ["Gabrijela", "Srecko"], "en": ["Sonia", "Ryan"]}
VOICE_TO_VKEY = {"Gabrijela": "hrF", "Srecko": "hrM", "Sonia": "ukF", "Ryan": "ukM"}
VOICE_LANG = {"Gabrijela": "hr", "Srecko": "hr", "Sonia": "en", "Ryan": "en"}

# Translate tab + the login screen's language pills. European only, on
# purpose, in the order Baba asked for: Croatian first, English second.
LANGS5 = ["hr", "en", "it", "de", "fr"]
# THE TR GRID GETS A SIXTH — Baba, 24.8.2026: "add Spanish, one more
# pill, three letters." The pill says SPA; the code underneath stays
# "es", which is what the model expects.
#
# TRANSLATION ONLY, AND NOWHERE ELSE. Baba, explicitly: "I am not talking
# about talking in Spanish, only translate — do not use Spanish anywhere
# else in this app." So Spanish is a TARGET the model writes into, and
# that is all. It has no voice, it is not in TRANSLATE_VKEY, and it is
# not in LANGS5, which also draws the LOGIN pills — those switch the
# interface, which exists in English and Croatian only.
#
# The consequence, written down rather than discovered later: nothing in
# this app can SPEAK a Spanish translation. There is no read-aloud on the
# TR tab today, so nothing breaks; if one is ever added, it must skip or
# refuse Spanish rather than hand it to a Croatian voice.
LANGS_TR = ["hr", "en", "it", "de", "fr", "es"]
LANG_FULL = {"hr": "Croatian", "en": "English", "it": "Italian", "de": "German",
             "fr": "French", "es": "Spanish"}
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
    "lang_auto":          {"en": "AUTO",               "hr": "AUTO"},
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
    "eta_working":        {"en": "transcribing",     "hr": "prepisujem"},
    "note_all":           {"en": "select all",      "hr": "označi sve"},
    "note_none_sel":      {"en": "select none",     "hr": "odznači sve"},
    "note_del_n":         {"en": "delete",          "hr": "obriši"},
    "note_del_n_sure":    {"en": "delete %d — sure?", "hr": "obriši %d — sigurno?"},
    "note_read":          {"en": "read",            "hr": "čitaj"},
    "note_one_only":      {"en": "one note at a time", "hr": "jedna bilješka odjednom"},
    "note_sel_help":      {"en": "Tick to select",  "hr": "Označi za odabir"},
    "tr_read_src":        {"en": "read",            "hr": "čitaj"},
    "tr_voice_f":         {"en": "female",          "hr": "ženski"},
    "tr_voice_m":         {"en": "male",            "hr": "muški"},
    "tr_deck_idle":       {"en": "nothing loaded",  "hr": "ništa nije učitano"},
    "tr_reading":         {"en": "making the voice…", "hr": "pripremam glas…"},
    "tab_vr":             {"en": "VR",               "hr": "VR"},
    "sig_vr":             {"en": "virtual rehearsal","hr": "virtualna proba"},
    "vr_text_ph":         {"en": "Paste the line to rehearse",
                           "hr": "Zalijepi rečenicu za probu"},
    "vr_speak":           {"en": "rehearse",         "hr": "probaj"},
    "vr_voices":          {"en": "the cast",         "hr": "glumci"},
    "vr_emotions":        {"en": "the direction",    "hr": "redateljska uputa"},
    "vr_note_ph":         {"en": "your own direction (optional)",
                           "hr": "vlastita uputa (neobavezno)"},
    "vr_no_key":          {"en": "No Hume key yet — the owner adds one in Settings.",
                           "hr": "Nema Hume ključa — vlasnik ga dodaje u postavkama."},
    "vr_empty":           {"en": "Hume answered with no audio.",
                           "hr": "Hume nije vratio zvuk."},
    "vr_all_busy":        {"en": "Every Hume key is busy right now.",
                           "hr": "Svi Hume ključevi su trenutno zauzeti."},
    "vr_coffee":          {"en": "Hume AI is drinking coffee ☕ — %d seconds",
                           "hr": "Hume AI pije kavu ☕ — %d sekundi"},
    "vr_too_many":        {"en": "Four directions at once is already a lot — the rest are ignored.",
                           "hr": "Četiri upute odjednom su već mnogo — ostale se zanemaruju."},
    "vr_nothing":         {"en": "Nothing to rehearse yet.",
                           "hr": "Još nema što probati."},
    "vr_now":             {"en": "reading as: %s",   "hr": "čita kao: %s"},
    "eta_learning":       {"en": "learning how long this takes",
                           "hr": "učim koliko ovo traje"},
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

    # GOLD, AND THE WORD. Baba's rule for the whole bar: "everything
    # that is gold belongs to the admin... my log should be gold, and
    # write log there, not only L." A single letter needs learning; the
    # word does not, and the colour already says whose it is.
    "tab_log":            {"en": ":orange[log]",     "hr": ":orange[log]"},
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
    "read_failed":        {"en": "That voice would not read this — try "
                                 "another voice, or again in a moment.",
                           "hr": "Taj glas ovo nije mogao pročitati — "
                                 "probaj drugi glas ili za koji trenutak."},
    "gen_part":           {"en": "Making part {i} of {n}…",
                            "hr": "Pripremam dio {i} od {n}…"},
    "gen_audio":          {"en": "Making the audio…",  "hr": "Pripremam zvuk…"},
    "rd_hint":            {"en": "press play to read",
                           "hr": "pritisni play za čitanje"},
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
    "custom_word":        {"en": "custom",             "hr": "po želji"},
    "custom_hint":        {"en": "say what to change",
                           "hr": "reci što promijeniti"},
    "custom_do":          {"en": "do it",              "hr": "napravi"},
    "custom_cancel":      {"en": "cancel",             "hr": "odustani"},
    "clear_word":         {"en": "clear",             "hr": "obriši"},
    "copy_word":          {"en": "copy",              "hr": "kopiraj"},
    "copy_done_word":     {"en": "copied",            "hr": "kopirano"},
    "translate_out_ph":   {"en": "The translation will appear here",
                            "hr": "Ovdje će se pojaviti prijevod"},
    "settings_owner_only": {"en": "Settings are managed by the owner.",
                            "hr": "Postavkama upravlja vlasnik."},
    "rec_title":          {"en": "your recordings",   "hr": "tvoje snimke"},
    "rec_keep_label":     {"en": "after transcribing",
                           "hr": "nakon prepisivanja"},
    "rec_keep":           {"en": "keep audio",       "hr": "čuvaj zvuk"},
    "rec_bin":            {"en": "delete after",     "hr": "obriši poslije"},
    "rec_keep_why":       {"en": "Audio is kept, so it can be played or "
                                 "transcribed again.",
                           "hr": "Zvuk se čuva pa se može ponovno slušati "
                                 "ili prepisati."},
    "rec_bin_why":        {"en": "Audio is deleted once the words are out. "
                                 "Nothing to play back later.",
                           "hr": "Zvuk se briše čim su riječi gotove. "
                                 "Nema se što poslije slušati."},
    "rec_none":           {"en": "nothing stored yet", "hr": "još ništa"},
    "rec_has_text":       {"en": "text", "hr": "tekst"},
    "rec_all":            {"en": "select all",       "hr": "označi sve"},
    "rec_none_sel":       {"en": "select none",      "hr": "poništi sve"},
    "rec_one_only":       {"en": "one file at a time",
                           "hr": "jedna datoteka odjednom"},
    "rec_close_play":     {"en": "close player",     "hr": "zatvori"},
    "rec_play":           {"en": "play",              "hr": "slušaj"},
    "rec_again":          {"en": "transcribe again",  "hr": "prepiši ponovno"},
    "aai_title":          {"en": "your AssemblyAI key",
                           "hr": "tvoj AssemblyAI ključ"},
    "aai_paste":          {"en": "AssemblyAI key",  "hr": "AssemblyAI ključ"},
    "aai_paste_ph":       {"en": "paste your key here",
                           "hr": "zalijepi svoj ključ ovdje"},
    "aai_save":           {"en": "save key",         "hr": "spremi ključ"},
    "aai_none":           {"en": "No key yet. Without one, transcription "
                                 "uses the free engine.",
                           "hr": "Nema ključa. Bez njega se koristi "
                                 "besplatni pogon."},
    "aai_have":           {"en": "key: %s",          "hr": "ključ: %s"},
    "aai_using_paid":     {"en": "AssemblyAI is doing the transcribing.",
                           "hr": "AssemblyAI prepisuje."},
    "aai_using_free":     {"en": "The free engine is doing the transcribing. "
                                 "Your key is saved but unused.",
                           "hr": "Prepisuje besplatni pogon. Ključ je "
                                 "spremljen ali se ne koristi."},
    "aai_left":           {"en": "about %.0f hours left  ·  $%.2f of credit  "
                                 "·  %.1f hours used, $%.2f",
                           "hr": "otprilike %.0f h preostalo  ·  $%.2f "
                                 "kredita  ·  %.1f h iskorišteno, $%.2f"},
    "aai_rates":          {"en": "pre-recorded $%.2f/hr  ·  streaming $%.2f/hr",
                           "hr": "snimljeno $%.2f/h  ·  streaming $%.2f/h"},
    "aai_estimate":       {"en": "An estimate: this counts only what this "
                                 "app transcribed.",
                           "hr": "Procjena: broji samo ono što je ova "
                                 "aplikacija prepisala."},
    "aai_pay":            {"en": "AssemblyAI pricing and top-up →",
                           "hr": "AssemblyAI cijene i nadoplata →"},
    "aai_test":           {"en": "test key",         "hr": "provjeri ključ"},
    "aai_ok":             {"en": "the key works",    "hr": "ključ radi"},
    "aai_del":            {"en": "delete key",       "hr": "obriši ključ"},
    "aai_del_sure":       {"en": "delete — sure?",   "hr": "obriši — sigurno?"},
    "aai_fix":            {"en": "topped up? set the credit",
                           "hr": "nadoplatio? postavi kredit"},
    "aai_credit_label":   {"en": "credit in dollars",
                           "hr": "kredit u dolarima"},
    "aai_credit_save":    {"en": "save credit",      "hr": "spremi kredit"},
    "sp_title":           {"en": "your Speechify key",
                           "hr": "tvoj Speechify ključ"},
    "sp_paste_ph":        {"en": "paste your key here",
                           "hr": "zalijepi svoj ključ ovdje"},
    "sp_save":            {"en": "save key",         "hr": "spremi ključ"},
    "sp_none":            {"en": "No key yet. Without one, reading uses the "
                                 "free voices.",
                           "hr": "Nema ključa. Bez njega čitanje koristi "
                                 "besplatne glasove."},
    "sp_have":            {"en": "key: %s",          "hr": "ključ: %s"},
    "sp_test":            {"en": "test key",         "hr": "provjeri ključ"},
    "sp_ok":              {"en": "the key works",    "hr": "ključ radi"},
    "sp_del":             {"en": "delete key",       "hr": "obriši ključ"},
    "sp_del_sure":        {"en": "delete — sure?",   "hr": "obriši — sigurno?"},
    "sp_pay":             {"en": "Speechify pricing and top-up →",
                           "hr": "Speechify cijene i nadoplata →"},
    "quick_title":        {"en": "quick settings",   "hr": "brze postavke"},
    "quick_stt":          {"en": "transcribe: %s",   "hr": "prepisuje: %s"},
    "quick_tts":          {"en": "talk: %s",         "hr": "govori: %s"},
    "quick_trim":         {"en": "silences: %s",     "hr": "tišine: %s"},
    "quick_free":         {"en": "free",             "hr": "besplatno"},
    "quick_aai":          {"en": "AssemblyAI",       "hr": "AssemblyAI"},
    "quick_edge":         {"en": "Edge",             "hr": "Edge"},
    "quick_sp":           {"en": "Speechify",        "hr": "Speechify"},
    "quick_on":           {"en": "cut",              "hr": "režem"},
    "quick_off":          {"en": "kept",             "hr": "čuvam"},
    "quick_need_key":     {"en": "No key for that engine yet — add one "
                                 "below.",
                           "hr": "Još nema ključa za taj pogon — dodaj ga "
                                 "ispod."},
    "trim_label":         {"en": "remove silences",  "hr": "ukloni tišine"},
    "trim_why_on":        {"en": "Silent gaps are cut before uploading, so "
                                 "you pay for the words and not the pauses.",
                           "hr": "Tišine se režu prije slanja, pa plaćaš "
                                 "riječi a ne pauze."},
    "trim_why_off":       {"en": "The whole recording is sent, pauses and "
                                 "all.",
                           "hr": "Šalje se cijela snimka, sa svim pauzama."},
    "trim_saved":         {"en": "silence removed: %.0fs less audio sent "
                                 "(%.0f%% smaller)",
                           "hr": "tišina uklonjena: %.0fs manje zvuka "
                                 "(%.0f%% manje)"},
    "rec_refresh":        {"en": "refresh",           "hr": "osvježi"},
    "rec_seen":           {"en": "list read at %s",   "hr": "popis učitan u %s"},
    "rec_save":           {"en": "save",              "hr": "spremi"},
    "rec_save_one":       {"en": "fetching %d of %d  ·  %s  ·  %.1fs",
                           "hr": "dohvaćam %d od %d  ·  %s  ·  %.1fs"},
    # `rec_save_ready` is gone. It said "press each one to save it to
    # this device" above a stack of buttons at the foot of the panel.
    # The buttons sit under their own rows now, where the instruction is
    # the button — a line of prose explaining a control that is already
    # obvious is a line nobody reads twice.
    "rec_save_done":      {"en": "done",               "hr": "gotovo"},
    "rec_del":            {"en": "delete",            "hr": "obriši"},
    "rec_del_sure":       {"en": "delete %d?",        "hr": "obrisati %d?"},
    "rec_del_done":       {"en": "%d deleted in %.1fs",
                           "hr": "obrisano %d u %.1fs"},
    "rec_del_part":       {"en": "%d deleted, %d could not be — %.1fs",
                           "hr": "obrisano %d, nije %d — %.1fs"},
    "rec_del_working":    {"en": "deleting %d of %d",
                           "hr": "brišem %d od %d"},
    "rec_del_now":        {"en": "%d of %d  ·  %s  ·  %.1fs",
                           "hr": "%d od %d  ·  %s  ·  %.1fs"},
    "rec_step_get":       {"en": "fetching the audio",
                           "hr": "dohvaćam zvuk"},
    "rec_step_say":       {"en": "transcribing",     "hr": "prepisujem"},
    "rec_get_wait":       {"en": "part %d of %d  ·  waiting  ·  %.1fs",
                           "hr": "dio %d od %d  ·  čekam  ·  %.1fs"},
    "rec_get_part":       {"en": "part %d of %d  ·  %.0f KB  ·  %.1fs",
                           "hr": "dio %d od %d  ·  %.0f KB  ·  %.1fs"},
    "rec_say_part":       {"en": "reading part %d of %d  ·  %.1fs",
                           "hr": "čitam dio %d od %d  ·  %.1fs"},
    "rec_say_chunk":      {"en": "piece %d of %d  ·  %.1fs",
                           "hr": "komad %d od %d  ·  %.1fs"},
    # NOT "rec_retry" — that is already the deck's retry BUTTON. Two
    # meanings on one key is how a button ends up labelled with a
    # sentence about waiting.
    "rec_wait_again":     {"en": "no answer — trying again (%d), %ds",
                           "hr": "nema odgovora — pokušavam opet (%d), %ds"},
    "rec_getting":        {"en": "fetching the audio…",
                           "hr": "dohvaćam zvuk…"},
    "rec_gone":           {"en": "That audio could not be fetched whole.",
                           "hr": "Zvuk se nije mogao dohvatiti cijeli."},
    "rec_again_done":     {"en": "transcribed again — it is in the box",
                           "hr": "ponovno prepisano — u okviru je"},
    "rec_failed":         {"en": "That recording could not be used.",
                           "hr": "Ta snimka se nije mogla upotrijebiti."},
    "settings_lang":      {"en": "Interface language", "hr": "Jezik sučelja"},
    "settings_engine":    {"en": "Engine",             "hr": "Motor"},
    "eng_check":          {"en": "test",               "hr": "test"},
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
    "login_remembered":   {"en": "Remembered on this device — press Enter, "
                                 "or the button",
                           "hr": "Zapamćeno na ovom uređaju — pritisni Enter "
                                 "ili gumb"},
    "login_continue":     {"en": "Continue as {who}", "hr": "Nastavi kao {who}"},
    "login_notme":        {"en": "Not me — sign in as someone else",
                           "hr": "Nisam ja — prijavi se kao netko drugi"},
    "tx_tonote":          {"en": "add to notes",       "hr": "dodaj u bilješke"},
    "tx_tonote_done":     {"en": "kept",               "hr": "spremljeno"},
    "notes_title":        {"en": "your notes",       "hr": "tvoje bilješke"},
    "notes_search":       {"en": "Search notes",       "hr": "Traži bilješke"},
    "notes_search_ph":    {"en": "search your notes",  "hr": "traži po bilješkama"},
    "notes_found":        {"en": "{n} of {all}",       "hr": "{n} od {all}"},
    "notes_none":         {"en": "nothing matches",    "hr": "nema pogodaka"},
    "note_working":       {"en": "transcribing…",      "hr": "prepisujem…"},
    "note_close":         {"en": "close",              "hr": "zatvori"},
    "note_cut":           {"en": "cut",                "hr": "reži"},
    "note_line":          {"en": "line",               "hr": "redak"},
    "note_del":           {"en": "delete",             "hr": "obriši"},
    # SHORTER THAN WHAT IT REPLACES, not longer. "delete — sure?" was
    # wider than "delete user" and was cut at the panel edge — §27
    # forbids a cut word outright. `sure?` says the same thing in a
    # cell built for the shorter one, and the question mark is the
    # whole message: you pressed delete, and this asks again.
    "note_del_sure":      {"en": "sure?",              "hr": "sigurno?"},
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
    "eng_global_word":    {"en": "global",              "hr": "globalno"},
    # ---- THE PEOPLE PANEL (step 9) --------------------------------
    # Said in the fewest words that are still true. Every one of these
    # is read by the one person who can lock everybody out, so none of
    # them may be cheerful about something that did not happen.
    "adm_title":          {"en": "People",            "hr": "Ljudi"},
    "adm_noconn":         {"en": "the accounts script is not connected — "
                                 "add AUTH_URL and AUTH_ADMIN_TOKEN to "
                                 "Secrets",
                           "hr": "skripta računa nije spojena — dodaj "
                                 "AUTH_URL i AUTH_ADMIN_TOKEN u Secrets"},
    "adm_noanswer":       {"en": "the accounts script did not answer. "
                                 "Nobody is locked out — the app still "
                                 "opens with APP_PASSWORDS",
                           "hr": "skripta računa nije odgovorila. Nitko "
                                 "nije zaključan — aplikacija se i dalje "
                                 "otvara s APP_PASSWORDS"},
    "adm_nobody":         {"en": "the users tab is there and it is empty",
                           "hr": "kartica korisnika postoji i prazna je"},
    "adm_newpw":          {"en": "Write this down NOW. It is shown once "
                                 "and can never be read again.",
                           "hr": "Zapiši ovo SADA. Prikazuje se jednom i "
                                 "više se nikada ne može pročitati."},
    "adm_written":        {"en": "I have written it down",
                           "hr": "Zapisao sam"},
    "adm_add_title":      {"en": "Add a person",      "hr": "Dodaj osobu"},
    "adm_name":           {"en": "name",              "hr": "ime"},
    "adm_note":           {"en": "note (optional)",   "hr": "bilješka (nije obavezno)"},
    "adm_need_name":      {"en": "a username is needed",
                           "hr": "treba korisničko ime"},
    "adm_need_pw":        {"en": "a password is needed",
                           "hr": "treba lozinka"},
    "adm_add":            {"en": "add",               "hr": "dodaj"},
    # NOT OPTIONAL ANY MORE (v123). The word stayed behind in the
    # placeholder for four versions, telling people the opposite of what
    # the form does — which is worse than saying nothing.
    "adm_pw":             {"en": "password",
                           "hr": "lozinka"},
    # The whole message, ready to send. %s in order: name, username,
    # password. It says the change is coming so it does not arrive as a
    # surprise the first time they log in.
    "adm_ready":          {"en": "%s, your account is ready.\n"
                                 "Username: %s\n"
                                 "Password: %s\n"
                                 "The first time you log in it will ask "
                                 "you to choose your own password.",
                           "hr": "%s, tvoj račun je spreman.\n"
                                 "Korisničko ime: %s\n"
                                 "Lozinka: %s\n"
                                 "Prvi put kad se prijaviš tražit će te "
                                 "da odabereš svoju lozinku."},
    "adm_ready_url":      {"en": "Open: %s\n", "hr": "Otvori: %s\n"},
    "adm_copy":           {"en": "one tap on the corner copies it",
                           "hr": "jedan dodir na kut kopira poruku"},
    # The forced change. A FAMILY screen, so these are full sentences.
    # SHORT ENOUGH FOR ONE LINE. The first wording ran to two, breaking
    # mid-sentence — "Worth / changing." — which made the widest thing on
    # the screen the one saying the least. Baba: "it looks
    # unprofessional and amateurish", and a sentence broken in the wrong
    # place is most of why.
    "must_hint":          {"en": "This password was chosen for you.",
                           "hr": "Ovu lozinku je odabrao netko drugi."},
    "must_go":            {"en": "change it",         "hr": "promijeni"},
    "must_later":         {"en": "later",             "hr": "kasnije"},
    "must_title":         {"en": "Choose your own password",
                           "hr": "Odaberi svoju lozinku"},
    "must_why":           {"en": "This password was made for you. Now "
                                 "choose one that only you know.",
                           "hr": "Ovu lozinku je netko napravio za tebe. "
                                 "Sada odaberi onu koju znaš samo ti."},
    "must_old":           {"en": "the password you were given",
                           "hr": "lozinka koju si dobio"},
    "must_new":           {"en": "your new password",
                           "hr": "tvoja nova lozinka"},
    "must_again":         {"en": "type it once more",
                           "hr": "upiši je još jednom"},
    "must_save":          {"en": "Save my password",
                           "hr": "Spremi moju lozinku"},
    "must_nomatch":       {"en": "The two do not match.",
                           "hr": "Ove dvije nisu iste."},
    "must_done":          {"en": "Saved. This is your password now.",
                           "hr": "Spremljeno. To je sada tvoja lozinka."},
    "adm_who":            {"en": "who",                "hr": "tko"},
    "adm_engine":         {"en": "engine",             "hr": "motor"},
    "adm_reset":          {"en": "reset password",             "hr": "nova lozinka"},
    "adm_delete":         {"en": "delete user",  "hr": "obriši korisnika"},
    "adm_rename":         {"en": "rename user",  "hr": "preimenuj korisnika"},
    # The reason is written where the dead button is, not in a document
    # nobody has open at the moment they wonder.
    "adm_rename_why":     {"en": "rename waits until the main script "
                                 "reads the frozen folder column — doing "
                                 "it now would leave this person's "
                                 "recordings under the old name",
                           "hr": "preimenovanje čeka da glavna skripta "
                                 "čita zamrznuti stupac mape — sada bi "
                                 "snimke ostale pod starim imenom"},
    "adm_setpw":          {"en": "new password (or leave empty)",
                           "hr": "nova lozinka (ili prazno)"},
    "adm_yourpw":         {"en": "your own password",
                           "hr": "tvoja vlastita lozinka"},
    "adm_ask_delete":     {"en": "Delete %s? Their recordings are kept.",
                           "hr": "Obrisati %s? Snimke ostaju."},
    "adm_ask_reset":      {"en": "New password for %s? Their remembered "
                                 "devices are signed out.",
                           "hr": "Nova lozinka za %s? Zapamćeni uređaji "
                                 "se odjavljuju."},
    "adm_yes":            {"en": "confirm",           "hr": "potvrdi"},
    "adm_cancel":         {"en": "cancel",            "hr": "odustani"},
    "adm_nopw":           {"en": "no password yet",   "hr": "još nema lozinku"},
    "adm_gone":           {"en": "%s is gone",        "hr": "%s je obrisan"},
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
    # FULL WORDS. Baba: "full name." TXT, TY and C are initialisms only
    # their author can read — and this is the screen a family member
    # opens when they cannot see the text well enough.
    "looks_iface":        {"en": "interface size",   "hr": "veličina sučelja"},
    "looks_default":      {"en": "default",           "hr": "zadano"},
    "looks_size":         {"en": "text size",        "hr": "veličina teksta"},
    "looks_font":         {"en": "typeface",         "hr": "pismo"},
    "looks_scheme":       {"en": "colour",           "hr": "boja"},
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


def owner_edge():
    """A gold edge round the whole panel when the owner is signed in.

    Baba: "so I know I am a special gold user." He can delete an account,
    reset somebody's password and change the engine for the whole family,
    and until now the only sign of that was two extra tabs — nothing to
    notice on a phone at speed.

    ONE RULE, EMITTED LATE, and not a parameter on theme.css(): that
    stylesheet is written before anyone has logged in, so it cannot know
    who this is. Adding an `owner` argument there would mean either
    moving the whole sheet after authentication — the riskiest reorder in
    the file — or carrying a flag that is always False on the run that
    matters.

    It uses var(--amber), the SAME token as the signature at the foot, so
    the edge and the word `admin` are one colour by construction and stay
    together when the scheme changes.
    """
    if not is_admin():
        return
    st.markdown(
        "<style>.block-container{border-color:var(--amber) !important}</style>",
        unsafe_allow_html=True)


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


def auth_admin_token() -> str:
    """THE ADMIN TOKEN, read in exactly one place: the people panel.

    It can make, rename, delete and re-password anybody, so it is kept
    apart from the token every phone in the house carries. Missing is not
    an error — it means the panel says so and does nothing, which is the
    §1 behaviour: no credential may ever be the reason the app fails to
    open.
    """
    return str(st.secrets.get("AUTH_ADMIN_TOKEN", "") or "")


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
            # PREPARED, NOT ENTERED. Baba: "wait, here be calm, no rush.
            # Then I press Enter, and I am in... otherwise maybe I am
            # logged in as Marko, maybe I am admin, I do not know who I
            # am." A shared phone makes that a real question, and being
            # thrown straight inside answers it too late.
            st.session_state["_remembered"] = {
                "user": got["user"], "token": tok,
                "engine": got.get("engine", ""), "kind": "accounts",
                "must_change": bool(got.get("must_change")),
            }
        return

    for p in PASSWORDS:
        if hmac.compare_digest(token, _digest(p)):
            st.session_state["_remembered"] = {
                "user": p, "token": token, "kind": "password",
            }
            return


def forget_remembered():
    """"Not me." Clear the remembered login and show an empty form.

    A shared phone is exactly why this button exists: the next person
    must be able to get to their own name without knowing what "forget
    me" in a settings screen means.
    """
    st.session_state.pop("_remembered", None)
    st.session_state["_user_input"] = ""
    queue_ls(removes=[AUTH_LS_KEY])


def enter_remembered():
    """Complete a remembered login. Only ever called by a press."""
    r = st.session_state.get("_remembered") or {}
    if not r.get("user"):
        return False
    st.session_state["_authed"] = True
    st.session_state["_user"] = r["user"]
    if r.get("kind") == "accounts":
        st.session_state["_via_accounts"] = True
        st.session_state["_remember_token"] = r.get("token", "")
        if EN.get(r.get("engine", "")):
            st.session_state["_assigned_engine"] = r["engine"]
        if r.get("must_change"):
            st.session_state["_must_change"] = True
    st.session_state.pop("_remembered", None)
    return True


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
        """RECORD THE ATTEMPT. Do not perform it.

        A callback cannot repaint: `st.rerun()` inside one is a no-op and
        Streamlit says so on screen. v113 put the rerun here and it never
        ran — the warning Baba photographed IS that fix failing.

        So the callback does the one thing callbacks are for: it captures
        what was typed and clears the box. The login itself happens in
        the main body below, where finishing simply falls through to the
        app — no repaint to ask for, because the run that draws the app
        is the run that logged you in.
        """
        typed = st.session_state.get("_pw_input", "")
        st.session_state["_pw_input"] = ""

        # AN EMPTY PASSWORD IS A REMEMBERED PERSON'S PRESS — but only
        # because this is now a FORM. The reason it was forbidden in v114
        # was that both boxes fired this handler, so typing a USERNAME
        # went straight through with nothing confirmed. A form submits
        # only when the button is pressed or Enter is struck in it, so
        # "empty" here means somebody deliberately asked to go in, not
        # that they are halfway through filling the form.
        _r = st.session_state.get("_remembered") or {}
        _name = (st.session_state.get("_user_input") or "").strip().lower()
        if not typed and _r.get("user") and _name in ("", _r["user"]):
            # AND THE NAME MUST STILL BE THEIRS.
            #
            # Without that last condition this was the v114 bug wearing a
            # new coat: type "emina" over the filled-in "baba", submit
            # with an empty password, and BABA was signed in — somebody
            # let into an account under a name they did not type. Caught
            # by the tests, which is the whole reason they name the
            # person rather than only checking that a login happened.
            enter_remembered()
            return

        st.session_state["_login_try"] = typed

    def _attempt(entered):

        # BOTH BOXES FIRE THIS. Now that there is a username field above
        # the password, on_change runs when someone finishes typing their
        # NAME — with the password still empty. Treating that as an
        # attempt marked the login wrong before they had typed it and
        # spent one of the throttle's tries, so a person could throttle
        # themselves simply by filling the form top to bottom.
        #
        # An empty password is not an attempt. Nothing to compare, no
        # verdict, no failure recorded — AND NO WAY IN.
        #
        # It used to enter a remembered person here, on the reasoning
        # that an empty password was their press. It is not: BOTH BOXES
        # FIRE THIS HANDLER, so typing a USERNAME and pressing Enter —
        # the most ordinary thing anybody does on a login screen — went
        # straight through with no password and nothing confirmed. The
        # v100 login exists precisely so that nobody is thrown inside
        # before they know who they are, and this branch was quietly
        # undoing it.
        #
        # `enter_remembered()` is now reachable from ONE place: the
        # Continue as {name} button. A press, and only a press.
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
                # Their own engine. Every row has one of two answers
                # now; an older row saying 'free' resolves through
                # EN.get, and anything unreadable leaves the routes
                # alone rather than guessing.
                if EN.get(got.get("engine", "")):
                    st.session_state["_assigned_engine"] = got["engine"]
                if got.get("must_change"):
                    st.session_state["_must_change"] = True

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
            # REPAINT NOW, do not wait for the browser-storage component.
            #
            # Ticking Remember me queues a localStorage write, and that
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

    # THE LOGIN HAPPENS HERE, in the main body, not in the callback.
    # Whatever the callback captured is spent exactly once.
    _try = st.session_state.pop("_login_try", None)
    if _try:
        _attempt(_try)

    if st.session_state.get("_authed"):
        return True

    # ENGLISH BY DEFAULT. Baba: "everything must be in English." The five
    # pills are still there and the choice sticks for the session, so his
    # mother presses HR once — but the screen a stranger meets, and the
    # screen he meets on a fresh browser, is one language throughout.
    # Mixed was the real complaint: Croatian labels above an English
    # button reads as broken rather than as bilingual.
    st.session_state.setdefault("login_lang", "en")
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
    _rem = st.session_state.get("_remembered") or {}
    if _rem.get("user") and not st.session_state.get("_user_input"):
        # Fill the name in, so the first thing they see is WHO they are
        # about to be. Set before the widget is created, never after —
        # §63's lesson about widget keys.
        st.session_state["_user_input"] = _rem["user"]

    # A FORM, and it has to be one.
    #
    # With plain widgets, TYPING AND THEN CLICKING Log in did nothing:
    # the click blurs the field, but Streamlit has not committed the new
    # value by the time the button's callback runs, so the callback read
    # an empty box. Enter worked, because Enter commits. Found by typing
    # and clicking in a real browser — every AppTest check passed either
    # way, since AppTest has no blur and no focus.
    #
    # A form commits every widget inside it and THEN runs the submit
    # callback. That ordering is the entire reason forms exist, and it is
    # the one mechanism that makes a button and a keypress do the same
    # thing here.
    #
    # The language pills stay OUTSIDE it: they must act the moment they
    # are pressed, and a form would hold them until submit.
    with st.form("login_form", clear_on_submit=False, border=False):
        st.text_input(labels.get("username", "Username"), key="_user_input")
        st.text_input(labels["password"], type="password", key="_pw_input",
                      placeholder="••••••••" if _rem.get("user") else "")
        # A VISIBLE WAY IN. Baba: "give me an action button immediately,
        # Log in, just that button... no hiding please." Enter still
        # works — a form submits on Enter in any of its fields — but
        # Enter is invisible, and an invisible control is one somebody
        # has to be TOLD about. This screen is the first thing his
        # mother meets.
        st.form_submit_button(labels.get("login", "Log in"),
                              type="primary", use_container_width=True,
                              on_click=_entered)

    # "Continue as {name}" lived here and is gone (v116). Baba: "Login is
    # enough." Two gold buttons a centimetre apart, doing almost the same
    # thing, is a choice nobody asked to make — and the name is already
    # filled in above, so Log in says everything the second button said.
    #
    # A remembered person still gets in without typing: submitting with
    # an EMPTY password completes their login, in _entered below.
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
    # A KEYED CONTAINER so the stylesheet can strip the frame off THIS
    # expander only. Baba: "just remove this frame around it, let it be
    # a >." On the login screen the box drew a heavy panel around a
    # single closed line, which read as a section with something in it
    # rather than as one quiet way in. Elsewhere expanders keep their
    # frame — there they hold real content.
    with st.container(key="loginmore"):
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
            # INSIDE THE FOLD-OUT, where the comment above always said it
            # was. It has been sitting open below it — three paragraphs
            # about installing an icon on a phone, on the screen a person
            # meets before they have typed anything. That is the wall of
            # text this expander exists to fold away.
            st.markdown("---")
            st.markdown(_ht("LOGIN_GUIDE", ll))
    return False


if not check_password():
    st.stop()

USER = st.session_state.get("_user") or "shared"


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


def must_change_notice():
    """A password somebody else chose is a temporary password.

    The account was made with one that was typed into a panel, read
    aloud and sent through a chat app. This is where it stops being the
    one that opens the door.

    THE ONLY THING ON THE SCREEN. Not a banner, not a nag in Settings —
    a person who can dismiss it will, and the account keeps the password
    that went through WhatsApp. It is placed here, immediately after the
    login gate, so nothing else is drawn behind it.

    HARD RULE 6 GOVERNS THIS SCREEN COMPLETELY. The dense owner's panel
    is behind is_admin() and this is not: it is the FIRST screen a new
    person ever sees, and half of them do not read easily. Full
    sentences, one field under another, a button they cannot miss.

    NEVER A TRAP. `_must_done` means it succeeded in this session, so a
    stale reply cannot ask twice; log out stays reachable; and a script
    that does not know about the flag simply never sets it, which is why
    a missing field is read as false in ttt/accounts.py.
    """
    # A RECOMMENDATION, NOT A GATE.
    #
    # Baba: "just recommend to change the password, but it should work
    # immediately without stopping user from using the app... we are not
    # torturing the user or forcing it to do anything."
    #
    # This used to st.stop() the whole app until the password was
    # changed. For a family that is the wrong trade: the first thing his
    # mother would meet is a screen she did not ask for, standing
    # between her and the one thing she opened the app to do.
    #
    # WHAT IT COSTS, said plainly: the password Baba handed them stays
    # valid until they choose to change it. He said it aloud, sent it in
    # a message, and it is in his own screenshot — so it is a password
    # several places know. The flag stays set until the change actually
    # happens, so the reminder returns next session; it is a nudge that
    # does not give up, rather than a wall.
    if not st.session_state.get("_must_change"):
        return
    if st.session_state.get("_must_done"):
        return
    if st.session_state.get("_must_later"):
        return

    with st.container(key="mustnotice"):
        # THE WORDS ON THEIR OWN LINE, the two actions under them.
        # Measured at 420px: forced onto one row the sentence was cut at
        # the panel edge and both buttons were squeezed out of existence
        # — §27 forbids the first and the second is worse. A sentence
        # needs a line; two short buttons do not need much of one.
        st.markdown('<div class="mustsay">%s</div>' % html.escape(
            t("must_hint")), unsafe_allow_html=True)
        c2, c3, _msp = st.columns([1.2, 1, 2.2])
        # STRAIGHT TO THE PLACE IT IS DONE. "Offer the link directly to
        # that" — the change-password fields live in the grey gear, and
        # telling somebody to go and find them is most of the friction.
        c2.button(t("must_go"), key="_must_go", type="primary",
                  use_container_width=True,
                  on_click=lambda: st.session_state.update(
                      {"active_tab": "looks"}))
        c3.button(t("must_later"), key="_must_later_btn",
                  use_container_width=True,
                  on_click=lambda: st.session_state.update(
                      {"_must_later": True}))


must_change_notice()

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
            # "auto" AND EMPTY ARE OMITTED, NOT SENT.
            #
            # Whisper detects the language itself when the parameter is
            # absent; sending "auto" is a 400 and the key rotation then
            # burns through every key and returns nothing. That is
            # exactly what Baba saw: "auto does not bring anything, no
            # transcription at all."
            #
            # THIS IS A SECOND COPY. ttt/providers/groq.py has the same
            # call and was fixed for auto in v118 — but this path never
            # reaches it. app.py talks to the Groq SDK directly here,
            # which is the "one implementation, in the module" rule
            # broken, and the cost of breaking it was a fix that looked
            # complete and changed nothing.
            # AN EMPTY MODEL FALLS BACK, it is not sent.
            #
            # Groq answers `'model' is a required property` — a 400 — and
            # the rotation then burns every key and returns nothing. The
            # note's own red button passed "" meaning "the engine's
            # default", which is what ttt/providers/groq.py has always
            # understood (`model or FAST_STT`). This copy did not, which
            # is the same two-implementations fault as the language bug,
            # in the same function, found one version later.
            kw = dict(file=(os.path.basename(path), None),
                      model=model or GROQ_FAST_STT,
                      response_format="text", temperature=0.0)
            if language and language != "auto":
                kw["language"] = language
            with open(path, "rb") as f:
                kw["file"] = (os.path.basename(path), f.read())
                resp = client.audio.transcriptions.create(**kw)
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
                    # UPGRADE, v175 -> v176: stored settings from before the
                    # per-language sets carry sp_voice but no sp_model. Every
                    # pick that COULD have been stored then was a _32 voice,
                    # and simba-3.2 is right for all of them — so this
                    # default is the correct model for every old pick.
                    "sp_model": "simba-3.2",
                    "transcribe_engine": "groq", "text_scale": a11y.DEFAULT_SCALE}
SETTINGS_KEYS = ("ui_lang", "engine", "rec_source",
                 "speech_lang", "voice", "voice_engine", "sp_voice", "sp_model",
                 "transcribe_engine",
                 "route_stt", "route_tts", "route_llm", "text_scale",
                 "scheme", "font_family", "append_mode",
                 # INTERFACE SIZE, saved like every other preference —
                 # otherwise somebody who shrinks the app finds it big
                 # again at their next login, which reads as the setting
                 # not working rather than not being kept.
                 "ui_scale",
                 # KEEP OR DISCARD THE AUDIO. Saved like every other
                 # preference — a choice about whether recordings can
                 # ever be recovered must not quietly reset itself.
                 #
                 # NOT "keep_audio": there is already a FUNCTION of that
                 # name in this module. A settings key and a function
                 # sharing a name is a reader's trap, and one of them
                 # would eventually be mistaken for the other.
                 "keep_recordings", "trim_silence",
                 # THE PERSON'S OWN ASSEMBLYAI KEY, and what they have
                 # spent against it. In the settings sheet like every
                 # other preference: `_save_server_settings` writes to a
                 # disk Streamlit Cloud wipes on every redeploy, so that
                 # alone would lose the key on the next deploy.
                 "aai_key", "aai_on", "aai_rate", "aai_credit", "sp_key",
                 "aai_spent_s")
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
    """Keep settings on the server's disk as well as in the browser.

    SILENT ONLY BECAUSE IT IS THE SECOND COPY. Streamlit Cloud's disk is
    ephemeral — it is wiped on every redeploy — so this is a convenience
    for a person who returns within the same container, and the BROWSER
    copy is the one that actually carries settings between sessions.
    Losing this one costs nothing that the other does not already hold.

    That is a real reason and it is written down, because a bare `pass`
    here reads identical to the note-storage bug that took days to find:
    a save that fails and says nothing. The difference is that this one
    has a backup and that one did not.
    """
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
    """task id -> the provider that should do it right now.

    THE PERSON'S OWN ASSEMBLYAI KEY OVERRIDES THE ROUTE, when they have
    one and have turned it on. Baba: "a toggle to use either Whisper free
    or AssemblyAI." The toggle saved from v171 and nothing read it; this
    is the line that reads it.
    """
    routes = RO.all_routes(PROVIDERS, provider_usable, st.session_state)
    if (st.session_state.get("aai_on")
            and str(st.session_state.get("aai_key") or "").strip()):
        # PROVIDERS.get(), not a scan of PROVIDERS.all() — there is no
        # all(). pyflakes cannot catch a method that does not exist on a
        # module, so this is the kind of thing that reaches a phone.
        prov = PROVIDERS.get("assemblyai")
        if prov is not None:
            routes["stt"] = prov
    return routes


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
                # THE FAST PATH, IF THIS CLIP MAY TAKE IT. v167 wrote the
                # rules and tested them; this is the line that asks.
                #
                # NOBODY IS TOLD WHICH PATH RAN. TTT mini's reasoning,
                # kept: "from where Marko sits the only difference is how
                # long the words take." A clip that cannot take the fast
                # path takes the slow one silently.
                #
                # AND A FAILURE FALLS BACK rather than surfacing. Fast is
                # a preference; arriving is not — so if the sync endpoint
                # refuses for any reason, the async path still runs and
                # the words still come. The cost is one wasted call on a
                # clip under two minutes, which is under half a penny.
                try:
                    if self.provider.use_sync(
                            language, path, ttt_audio.duration_seconds(path)):
                        out = self.provider.transcribe_sync(
                            lambda attempt: kr.rotate(ring, lambda k: attempt(k)),
                            path, language=language)
                        if out:
                            return out
                except Exception as e:
                    errlog.add(st.session_state, "transcribe",
                               "fast path refused, using the slow one",
                               "{}: {}".format(type(e).__name__, e))

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


# THE BRAILLE SPINNER. Baba, 24.8.2026: "put Braille spinner there and in
# parentheses note which engine is working at the moment."
#
# Ten frames of U+280x. They are one character wide in every monospace
# face and they animate by cycling, so the line never changes width —
# which matters more than it sounds: a status line that grows and shrinks
# drags everything under it up and down while a person is watching it.
BRAILLE = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def braille_line(engine: str, tick: int, eta_text: str = "") -> str:
    """One status line: spinner, what is happening, which engine, how
    long. The engine is named because two of them can do this job and
    "transcribing…" alone never said which one was asked."""
    frame = BRAILLE[tick % len(BRAILLE)]
    line = "%s %s (%s)" % (frame, t("eta_working"), engine or "?")
    if eta_text:
        line += " · %s" % eta_text
    return line


# ---------------------------------------------------------------------
# THE ETA. Samples live in the sheet's `eta` tab because Streamlit
# Cloud's disk is wiped on every redeploy — a text file would lose the
# history at exactly the moment a fresh estimate matters, and the sheet
# also lets a phone and a laptop feed one history. Both calls are
# convenience only: a sheet that is slow, unreachable or running an old
# script costs an estimate and never a transcript.
# ---------------------------------------------------------------------

def _sheet_pair():
    return (str(st.secrets.get("SHEETS_URL", "") or ""),
            str(st.secrets.get("SHEETS_TOKEN", "") or ""))


def eta_seconds(engine: str, audio_s: float):
    """How long this take will probably need, or None while the app is
    still learning. Cached per engine for the session so a rerun does
    not fetch the whole history again."""
    try:
        url, token = _sheet_pair()
        if not url or not token:
            return None
        ck = "_eta_samples_" + (engine or "any")
        if ck not in st.session_state:
            st.session_state[ck] = SHEET.get_timings(url, token, engine=engine)
        return ETA.estimate(st.session_state[ck], audio_s, engine)
    except Exception:
        return None


def remember_timing(engine: str, audio_s: float, wall_s: float,
                    parts: int = 1, ok: bool = True) -> None:
    """Write one measurement and fold it into this session's cache, so
    the very next take is already estimated from it rather than after a
    reload. Silent on every failure, on purpose."""
    try:
        if not (audio_s > 0 and wall_s > 0):
            return
        sample = {"engine": engine, "audio_s": float(audio_s),
                  "wall_s": float(wall_s)}
        if not ETA.usable(sample):
            return          # a stall is not a measurement of speed
        ck = "_eta_samples_" + (engine or "any")
        st.session_state.setdefault(ck, []).append(sample)
        url, token = _sheet_pair()
        SHEET.put_timing(url, token, USER, engine, audio_s, wall_s, parts, ok)
    except Exception:
        pass


def talking_engine() -> str:
    """WHO TALKS — one answer, from one place.

    THE BUG THIS CLOSES, reported by Baba 24.8.2026: flipping Quick
    Settings to Speechify left the voice pills showing Gabrijela and
    Srecko. Two keys were answering the same question and they were not
    the same key. Quick Settings wrote `voice_engine`; the R tab's picker
    read `current_routes()["tts"]`, which is set by the ROUTING, and the
    flip never touched it. Nothing was broken in either half — they
    simply were not connected, which is the shape of failure that
    HOW_WE_WORK names: the code is reachable, correct, and nothing leads
    to it.

    The route stays the source of truth, because the engine sheet and the
    tier both set it and neither knows about Quick Settings. What changed
    is that the flip now writes the route as well, so there is one answer
    and this function reads it.
    """
    tts = current_routes().get("tts")
    if tts is not None:
        return tts.id
    return str(st.session_state.get("voice_engine") or "edge")


def llm_bridge():
    """The AI engine to use right now, or None if none is usable."""
    prov = current_routes().get("llm")
    return LLMBridge(prov) if prov else None


def flash(name: str):
    """Mark a command as just-pressed, so it can light up briefly.

    Streamlit reruns after a click, so the press itself is invisible by
    the time the page redraws — :active never gets a chance to show. A
    short-lived stamp in session_state gives the next render something to
    colour, which is what makes the row feel like it responded.
    """
    st.session_state[f"_flash_{name}"] = time.time()


# HOW LONG A CONFIRMATION STAYS ON SCREEN.
#
# This lived BETWEEN two functions I deleted at the gate, and my slice —
# "from this def to the next def" — swallowed it with the second one.
# pyflakes caught it in the same breath, which is the argument for
# running the checks again after every deletion rather than at the end:
# "deleting dead code exposes more dead code behind it", and sometimes
# it exposes live code that was standing behind it.
FLASH_SECONDS = 0.9


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


def admin_dense():
    """The owner's screen: square, tight, and labels beside their boxes.

    NO SELECTOR SCOPE, and that is the robust choice rather than the
    lazy one: this stylesheet is emitted ONLY while the owner's tab is
    rendering, and Streamlit rebuilds the page every run, so it simply
    does not exist on any other screen. A sibling selector tied to some
    other container would have been one refactor away from silently
    styling nothing.

    docs/HOW_WE_WORK.md,
    "Who each screen is for": the family's modules keep rule 6 whole —
    44px targets, generous type, room to breathe. This screen is read by
    one person who knows what every word means, and there the room is
    the problem rather than the kindness.

    Square corners are not decoration either: they say "you are somewhere
    else" at a glance, the same job the gold edge does, without another
    colour.
    """
    st.markdown("""<style>
    .stButton button {
      border-radius: 3px !important;
      min-height: 0 !important;
      padding: 0.25rem 0.7rem !important;
      font-size: 0.74rem !important;
    }
    input {
      border-radius: 3px !important;
      padding: 0.25rem 0.5rem !important;
      font-size: 0.76rem !important;
    }
    /* Rows sit on each other. The default rhythm is built for thumbs on
       a reading screen; this is a control panel. */
    div[data-testid="stVerticalBlock"] {
      gap: 0.18rem !important;
    }
    /* A LINE-HEIGHT WITH THE TIGHT GAP. Rows sitting on each other is
       the point of this panel; rows sitting THROUGH each other is not.
       "all parts answered" printed across the line beneath it because
       the gap was closed without giving the text room of its own. */
    [data-testid="stCaptionContainer"], [data-testid="stText"] {
      line-height: 1.45 !important;
      margin: 0 !important;
    }
    [data-testid="stElementContainer"] {
      margin: 0 !important;
    }
    /* ONE horizontal line as the only separator, thin and quiet. */
    hr {
      margin: 0.45rem 0 !important;
      border-color: var(--line);
      opacity: 0.5;
    }
    /* Radios in a row, small, with no wasted label block above them. */
    [data-testid="stRadio"] label p {
      font-size: 0.74rem !important;
    }
    [data-testid="stRadio"] > label {
      display: none !important;
    }
    /* The table of people: tight leading, no panel around it. */
    pre {
      font-size: 0.72rem !important;
      line-height: 1.35 !important;
      padding: 0.4rem 0.5rem !important;
      border-radius: 3px !important;
    }
    .stCaption, 
    [data-testid="stText"] {
      font-size: 0.72rem !important;
    }
    </style>""", unsafe_allow_html=True)


def user_admin_panel():
    """WHO EXISTS — make, unmake, re-password, and give each an engine.

    Baba asked for this at the very start: *"I want in this panel to have
    list of all users and assign them engines. Your normal user doesn't
    have these settings."* It grew into the rest of it — adding a person
    used to mean opening a spreadsheet.

    IT TALKS TO THE ACCOUNTS SCRIPT, NOT THE MAIN ONE. That script owns
    the users tab now, holds the hashes, and answers with its own admin
    token. The old version of this panel asked the main script and said
    "no users tab yet" whenever that script was behind, which was true
    about the deployment and a lie about the tab.

    NOTHING HERE MAY BE A DEPENDENCY (§1). Every call returns rather than
    raises, an unreachable script is a sentence on the screen, and the
    door that always opens — APP_PASSWORDS — is untouched by all of it.
    """
    url, token = auth_url(), auth_admin_token()
    if not url or not token:
        st.caption(t("adm_noconn"))
        return
    # admin_dense() is emitted once by the settings module, above.

    # THE NEW PASSWORD GOES FIRST, above everything, because it is the
    # one thing on this screen that cannot be fetched again. Under the
    # list it would arrive below the fold on a phone.
    shown = st.session_state.get("_adm_shown")
    if shown:
        # A WHOLE SENTENCE, NOT A PASSWORD ON ITS OWN. What he does next
        # is send this to somebody, and st.code puts a copy button in its
        # corner — one tap on a phone, instead of selecting a bare word
        # and typing the rest of the message around it.
        #
        # It is built from what the SCRIPT sent back, never from what was
        # typed into the box: against a deployment older than this one a
        # chosen password is ignored and a generated one comes back, and
        # the message he sends has to be the one that works.
        who, pw = shown[0], shown[1]
        link = str(st.secrets.get("APP_URL", "") or "")
        st.code(((t("adm_ready_url") % link) if link else "")
                + t("adm_ready") % (who.capitalize(), who, pw), language=None)
        # TWO LINES REMOVED. "one tap on the corner copies it" explained
        # a button that is now simply visible, and "Write this down NOW"
        # told him to do the thing he had just done — he chose the
        # password himself, so it is already written down. Both were
        # true when the app generated passwords and nobody knew them.
        #
        # The dismiss stays: it is the only thing that takes a password
        # off the screen, and a password that lingers through a session
        # is a password in the next screenshot.
        st.button(t("adm_written"), key="adm_written",
                  on_click=lambda: st.session_state.pop("_adm_shown", None))

    if "_adm_people" not in st.session_state:
        st.session_state["_adm_people"] = ACCOUNTS.users(url, token)
    people = st.session_state["_adm_people"]

    def forget():
        """The list is stale the moment anything changes it."""
        st.session_state.pop("_adm_people", None)

    def proof():
        """The administrator's own password, taken and not kept."""
        return st.session_state.get("_adm_proof", "")

    # ---- the five actions, each ending in a sentence ----------------
    def do_engine(who, engine_id):
        ok, err = ACCOUNTS.user_engine(url, token, who, engine_id)
        st.session_state["_adm_msg"] = who + (" → " + engine_id
                                              if ok else "  " + err)
        if ok:
            forget()

    def do_create():
        name = str(st.session_state.get("_adm_name", "")).strip().lower()
        chosen = str(st.session_state.get("_adm_pw", ""))
        if not name:
            st.session_state["_adm_msg"] = t("adm_need_name")
            return
        # BOTH ARE REQUIRED. An empty password used to mean "generate
        # one", which made the field read as optional. Saying no here,
        # with the reason, is clearer than silently doing something else.
        if not chosen:
            st.session_state["_adm_msg"] = t("adm_need_pw")
            return
        pw, err = ACCOUNTS.user_create(url, token, name, "", "",
                                       password=chosen)
        if pw:
            st.session_state["_adm_shown"] = (name, pw)
            st.session_state["_adm_msg"] = ""
            st.session_state.pop("_adm_name", None)
            st.session_state.pop("_adm_pw", None)
            forget()
        else:
            st.session_state["_adm_msg"] = err

    def do_reset(who):
        pw, err = ACCOUNTS.user_password(
            url, token, who, USER, proof(),
            password=str(st.session_state.get("_adm_newpw", "")))
        st.session_state.pop("_adm_newpw", None)
        if pw:
            st.session_state["_adm_shown"] = (who, pw)
            st.session_state["_adm_msg"] = ""
        else:
            st.session_state["_adm_msg"] = err
        close_ask()

    def do_delete(who):
        ok, err = ACCOUNTS.user_delete(url, token, who, USER, proof())
        st.session_state["_adm_msg"] = (t("adm_gone") % who) if ok else err
        if ok:
            forget()
        close_ask()

    def open_ask(kind, who):
        st.session_state["_adm_ask"] = (kind, who)

    def close_ask():
        st.session_state.pop("_adm_ask", None)
        # The password box unmounts with the strip, so the typed value
        # must go with it rather than waiting in state for next time.
        st.session_state.pop("_adm_proof", None)

    # ---- who exists -------------------------------------------------
    if people is None:
        # NOT THE SAME AS NOBODY, and the difference is the whole reason
        # this reads from `None` rather than an empty list.
        st.caption(t("adm_noanswer"))
        return
    if not people:
        st.caption(t("adm_nobody"))

    ask = st.session_state.get("_adm_ask") or ("", "")

    # ---- ONE LIST, ONE SELECTION ------------------------------------
    #
    # Baba: "optimize the real estate... make everything with radio
    # buttons, and always give me a list so I can see who is registered.
    # It is not for users who are old. It is for a young administrator
    # who is very smart."
    #
    # THIS PANEL IS THE ONE PLACE THE ACCESSIBILITY RULES DO NOT GOVERN,
    # and the exception is deliberate and scoped. Hard rule 6 — 44px
    # targets, large type, nothing clipped — exists for his mother and
    # his father, who do not read easily. They never see this screen: it
    # is behind is_admin(), and it is read by one person who knows
    # exactly what every word means. Six buttons per person was 24
    # targets for four people, most of a phone screen, to say something a
    # single line says better.
    #
    # The exception must not leak. Anything a FAMILY MEMBER can reach
    # keeps rule 6 entirely.
    if people:
        # The whole table in one glance: who, which engine, whether they
        # have a password yet, and their note.
        # THE LIST FOLDS AWAY. Baba: "if I have 300 people it will fill
        # up my whole interface — just make it a folder, a small greater
        # than sign, and then I click and I see who the people are."
        #
        # Three names fit; thirty do not, and the panel is meant to be
        # read at a glance. The count is on the fold's own line, so
        # closed it still answers "how many".
        rows = []
        for person in people:
            known = EN.get(person.get("engine") or "")
            # "must" is worth a column of its own: it says the password
            # he handed over has not been replaced yet, so the person has
            # not logged in even once.
            mark = ("no pw" if not person.get("hashed")
                    else "must" if person.get("must_change") else "")
            rows.append("%-14s %-10s %-5s %s" % (
                person.get("user", ""),
                known.id if known else EN.DEFAULT,
                mark,
                (person.get("note") or "")[:28]))
        with st.expander("%s · %d" % (t("adm_title"), len(people))):
            st.code("\n".join(rows), language=None)

        # A DROPDOWN FOR PEOPLE, a radio for the engine. Baba: "each user
        # should appear under the dropdown list, and then I am dropping
        # down this user, and I can delete him or change his password."
        #
        # The difference is how many there are. Engines are three and
        # will stay three, so a radio shows all of them at once and
        # choosing costs one press. People grow — a radio for a family of
        # eight is eight rows standing open forever, when the list above
        # already says who exists. The dropdown holds one name and opens
        # only when he means to change it.
        names = [p.get("user", "") for p in people]
        who = st.selectbox(t("adm_who"), names, key="_adm_pick",
                           label_visibility="collapsed")

        current = next((p for p in people if p.get("user") == who), {})
        theirs = (current.get("engine") or "").strip().lower()

        # The engine as a radio: one choice out of two now, not three.
        # The third was blank, meaning "follow the global row", and a
        # state that is neither of the two real answers is a state he
        # has to remember the meaning of.
        opts = [e.id for e in EN.ENGINES]
        # SHORT LABELS HERE ONLY. "Speechify / AssemblyAI / Claude" is
        # right where the owner is CHOOSING an engine and needs to know
        # what he is buying. Beside a person's name he already knows, and
        # the full names wrapped the row onto two lines with a gap
        # between them — seen with four people on the screen, not
        # predicted.
        # THE TIER WORD, from the engines themselves. Two hand-written
        # strings here would be a third place the names live, and this
        # panel is exactly where "normal" was still being shown after
        # v123 renamed it.
        labels_by_id = {e.id: e.tier for e in EN.ENGINES}
        # AN OLD ROW SAYS 'free' AND MUST NOT LAND ON THE WRONG BUTTON.
        # EN.get resolves the old word to the current engine; anything
        # unreadable falls to the first option rather than to nothing.
        known = EN.get(theirs)
        theirs = known.id if known else opts[0]
        # A WIDGET KEY OUTLIVES THE OPTIONS IT WAS SET FROM. This radio
        # offered "" for "global" until today; a session still holding
        # that value makes Streamlit raise ValueError deep inside its own
        # element tree — a white panel, not a wrong label. Clearing the
        # stale value is one line and cannot be triggered by any input.
        wkey = "_adm_engine_%s" % who
        if st.session_state.get(wkey) not in opts:
            st.session_state.pop(wkey, None)
        picked = st.radio(
            t("adm_engine"), opts,
            index=opts.index(theirs) if theirs in opts else 0,
            format_func=lambda k: labels_by_id[k],
            key="_adm_engine_%s" % who, horizontal=True,
            label_visibility="collapsed")
        if picked != theirs:
            do_engine(who, picked)
            st.rerun()

        # RENAME · RESET PASSWORD · DELETE USER, in that order, as links.
        #
        # Baba: "these should be links at the top, not buttons... the
        # order is more logical for me: first rename, then reset
        # password, and delete user is the last thing."
        #
        # The order is an argument about danger as much as habit: rename
        # changes a word, reset changes a password, delete ends an
        # account. Least harm first, most harm last, so a hand moving
        # down the row is moving toward the thing it should hesitate
        # over.
        #
        # FULL WORDS. "reset" and "delete" alone leave "reset what" and
        # "delete what" to be inferred beside a person's name.
        # MEASURED, NOT GUESSED: at 1 : 1.3 : 1.1 the words "delete user"
        # wrapped to a second line on a 420px screen. The three shares
        # follow the three lengths.
        acts = st.columns([1.15, 1.3, 1.15])
        acts[0].button(t("adm_rename"), key="ad_rename",
                       disabled=True, help=t("adm_rename_why"),
                       use_container_width=True)
        acts[1].button(t("adm_reset"), key="ad_reset",
                       on_click=open_ask, args=("reset", who),
                       use_container_width=True)
        # DISABLED ON PURPOSE, with the reason in the tooltip rather than
        # in a document nobody has open. The accounts script freezes a
        # folder column at creation; the MAIN script still builds
        # USERS/<user>/ from the login name, so a rename today would walk
        # away from somebody's recordings. The day the main script reads
        # that column, this line loses `disabled` and nothing else about
        # it changes.
        acts[2].button(t("adm_delete"), key="ad_del",
                       on_click=open_ask, args=("delete", who),
                       use_container_width=True)

        # THE CONFIRM STRIP SITS UNDER THE PERSON IT IS ABOUT — with one
        # list and one selection, "the person it is about" is whoever is
        # selected, and the strip names them so the wrong row cannot be
        # deleted by a mis-tap higher up.
        if ask[1] == who and ask[0] in ("delete", "reset"):
            # A RED FRAME ONLY FOR DELETE. Baba: "when I delete any
            # user, confirm should be in a red frame, and confirm should
            # be a red button — not too much red, so I know I am
            # deleting."
            #
            # Not for reset: a reset is recoverable, a delete is not, and
            # red that appears for both says nothing about either. Red
            # is reserved for the one action with no way back — the same
            # reservation the recording dot lives under.
            _danger = ask[0] == "delete"
            with st.container(key="askstrip_danger" if _danger
                              else "askstrip"):
                st.text((t("adm_ask_delete") if _danger
                         else t("adm_ask_reset")) % who)
                if not _danger:
                    # THE NEW PASSWORD, CHOSEN. Baba: "I am assigning
                    # password as I like." Empty still means "make me
                    # one", which is the right answer when he has
                    # nothing in mind — but it is no longer the ONLY
                    # answer, which it was until now.
                    st.text_input(t("adm_setpw"), key="_adm_newpw",
                                  placeholder=t("adm_setpw"),
                                  label_visibility="collapsed")
            # NO PASSWORD BOX. It used to sit here, BELOW the confirm
            # buttons — so pressing yes sent an empty one and the script
            # refused, which reads as being asked for something there is
            # nowhere to type. Baba asked for it gone; auth_script no
            # longer requires it. The two presses remain, because one
            # press on a whole account is still not a risk worth taking.
                yn = st.columns([1, 1])
                yn[0].button(t("adm_yes"),
                             key="ad_yes_danger" if _danger else "ad_yes",
                             type="primary",
                             on_click=do_delete if _danger else do_reset,
                             args=(who,), use_container_width=True)
                yn[1].button(t("adm_cancel"), key="ad_no",
                             on_click=close_ask, use_container_width=True)

    # ---- add a person, UNLESS something is being confirmed ------------
    #
    # Baba: "at that time I want the name and password to disappear...
    # if I am deleting, there should be no name, password, add or other
    # unnecessary stuff."
    #
    # He is right, and it explains the confusion he reported: pressing
    # RESET seemed to ask for a name AND a password, because the add-a-
    # person form sits directly under the confirm strip and reads as
    # part of it. Nothing was wrong; two things were adjacent.
    #
    # THIS IS A DELIBERATE EXCEPTION to "no new elements appearing on
    # the screen. Everything is already there, only greyed out." That
    # rule protects a person who is trying to find a control. This is
    # the opposite case: the owner has already found one, and is about
    # to end an account. Fewer things on screen is the kindness here.
    if st.session_state.get("_adm_ask"):
        return

    # ---- add a person ------------------------------------------------
    #
    # ONE LINE PER FIELD, label beside the box rather than above it.
    # Baba: "put name and then input box, not name and then new line
    # input box." Two fields stacked with their labels above was six
    # rows for two values.
    st.markdown("---")
    # THE LABEL GOES INSIDE THE BOX.
    #
    # A label column beside it was measured starting at two different x
    # positions for the two rows, even with one ratio: st.text renders
    # preformatted text that does not wrap, so the longer word — "note
    # (optional)" — stretched its own column and pushed its box right.
    #
    # A placeholder cannot drift out of alignment, because there is
    # nothing beside it to align WITH. It is also one row shorter per
    # field, which is the whole point of this screen.
    # USERNAME AND PASSWORD. Nothing else.
    #
    # Baba: "why do I have note, actually I do not need note — just
    # username, password, and then I add user." The note column stays in
    # the sheet, where a word about somebody is occasionally useful; it
    # is the FORM that had a field nobody fills.
    #
    # AND THE PASSWORD IS NOT OPTIONAL. It used to mean "make me one if
    # you leave it empty", which reads as optional on a form and is not
    # what he wants: he hands people a password he chose and can say out
    # loud. Empty is refused now, with the reason on screen.
    #
    # NOT a password field: he is choosing one to read out and send, not
    # typing his own, and a row of dots he cannot check is how a typo
    # becomes a person who cannot log in.
    st.text_input(t("adm_name"), key="_adm_name",
                  placeholder=t("adm_name"), label_visibility="collapsed")
    st.text_input(t("adm_pw"), key="_adm_pw",
                  placeholder=t("adm_pw"), label_visibility="collapsed")
    st.button(t("adm_add"), key="ad_add", on_click=do_create)

    if st.session_state.get("_adm_msg"):
        st.caption(st.session_state.pop("_adm_msg"))


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
    # WHITE IS YOURS, GOLD IS HIS — and the gold ones are grouped at
    # the END. Baba: "everything that is gold belongs to the admin, and
    # it will be grouped to the right side, so I can see what users see
    # and what I see."
    #
    # The whole bar becomes readable without reading: everything up to
    # the first gold tab is what a family member has, and everything
    # after it is the owner's. For a family member the gold group is
    # simply absent, so their row ends at help — which is where help was
    # always meant to be, at the end of what they have.
    #
    # This reverses v110, where the owner's gear was put FIRST on his
    # own instruction. The grouping serves the same wish better: he
    # wanted his own things distinguishable, and a group says that more
    # clearly than a position does.
    # VR SITS AFTER TR, so the tabs read T · R · TR · VR — the two
    # reading tabs, then the two that transform before they read.
    tabs = ["transcribe", "talk", "translate", "vr", "looks", "help"]
    if is_admin():
        tabs += ["settings", "log"]
    return tabs


def cmd_width(word: str) -> int:
    return max(64, len(word) * CMD_CHAR_PX + CMD_PAD_PX)


def box_links(where: str, text: str, on_clear=None, extra=None):
    """copy · clear, as links, under a text box. Everywhere.

    Baba: "under all tabs we have text box, copy clear under. As an
    action link, not an action button. Copy is more important than
    clear, that is the rule."

    ONE HELPER, THREE MODULES. T, R and TR each had their own
    arrangement — a bordered command row here, a single link there,
    copy in one and not the other. Three shapes for one idea is three
    things to keep in step, and they had already drifted.

    `extra` is for a module's own afterthought action — T's "add to
    notes" — so it lands on this line rather than starting another.

    It renders nothing when the box is empty. There is no copying and
    no clearing to be done, and a dead link is a question with no good
    answer.
    """
    body = (text or "").strip()
    # THE ROW IS ALWAYS THERE when a module offers extras, because one
    # of them — add to notes — now has a job to do on an EMPTY box:
    # making a blank note to speak into. Hiding the row would hide that.
    #
    # copy and clear still only appear when there is something to copy
    # or clear: a dead link is a question with no good answer.
    if not body and not extra:
        return
    # THE KEY SAYS WHETHER THE BOX IS EMPTY, because a Streamlit
    # container cannot be given a class and the stylesheet has to tell
    # the two cases apart: glued to the box when there is text, and
    # standing off it when there is not.
    with st.container(key="boxlinks_%s%s" % (where, "" if body else "_empty")):
        items = []
        if body:
            items.append(("copy", None))
            if on_clear is not None:
                items.append(("clear", on_clear))
        items += list(extra or [])
        cols = st.columns([1] * len(items))
        for col, (kind, cb) in zip(cols, items):
            with col:
                if kind == "copy":
                    # The copy button is a COMPONENT — it has to be, to
                    # reach the clipboard — so it cannot be a Streamlit
                    # button styled into a link. Its own stylesheet makes
                    # it look like one.
                    components.html(
                        copybtn.cp_html(body, label=t("copy_word"),
                                        done_label=t("copy_done_word"),
                                        failed_label="—", size=0,
                                        link=True),
                        height=24)
                elif kind == "clear":
                    st.button(t("clear_word"), key="bl_clear_%s" % where,
                              on_click=cb, use_container_width=True)
                else:
                    label, key, fn = kind, cb[0], cb[1]
                    st.button(label, key=key, on_click=fn,
                              use_container_width=True)


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
    # THE TIER, NOT THE PARTS. Baba: "their technical names are going
    # bye bye — it is free or it is studio."
    #
    # "Edge / Groq" answers a question nobody asks at the foot of a
    # page. "free" answers the one they do: which one am I on, and is
    # this the paid one. The parts are still named in the owner's panel,
    # where he is CHOOSING between them and needs to know what he buys.
    #
    # v123 claimed to have done this and did not — the comment was
    # written and the line was not changed, which is why the foot of the
    # page went on saying "Edge / Groq" for nine versions while the
    # commit message said otherwise.
    label = (eng.tier if eng else t("eng_mixed"))
    res = st.session_state.get("_engine_check") or {}
    mark = ""
    # THROUGH EN.get, NOT BY STRING. A verdict recorded before the engine
    # was renamed says "free", and comparing the words would quietly drop
    # a tick that had been earned. The check for a DIFFERENT engine still
    # fails to match, which is the part that matters.
    checked = EN.get(res.get("engine", ""))
    if eng and checked is eng:
        mark = " ✓" if res.get("state") == EN.OK else " ✗"
    # AND WHO YOU ARE. Baba: "show me who I am." On a shared phone the
    # question "am I Marko or am I admin" has no other answer on the
    # screen once the login is behind you.
    #
    # ONLY WHEN IT IS ACTUALLY A NAME. `_user` holds the ACCOUNT name for
    # an accounts login — but the APP_PASSWORDS fallback stores the
    # PASSWORD THAT MATCHED in the same slot (see check_password: `who =
    # matched`). Printing it here would put the owner's password at the
    # foot of every page, in every screenshot, for as long as the session
    # lasts. So the name is shown when the accounts script named them,
    # "shared" when nobody is named, and NOTHING when the value is a
    # password wearing a name's clothes. Do not "simplify" this to USER.
    who = ""
    if st.session_state.get("_via_accounts"):
        who = USER
    elif not st.session_state.get("_user"):
        who = USER            # the "shared" default, which names nobody

    bits = [x for x in (html.escape(name), html.escape(label) + mark,
                        html.escape(who)) if x]
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
# THE SPEECHIFY SEATS, PER LANGUAGE — Baba's own list, 24.8.2026.
# English: four British voices on simba-3.2, the curated set.
# Croatian: Speechify has no hr-HR on any model (all 988 catalogue voices
# walked live, 24.8.2026), so Croatian is read the Slavic way — Ukrainian,
# Polish and Russian voices on simba-multilingual, Lesya first.
#
# THE MODEL SITS BESIDE THE VOICE, PER ROW, NEVER GLOBALLY. beatrice_32
# appears in BOTH rows and needs simba-3.2 for English but
# simba-multilingual for Croatian — the _32 suffix rule cannot know that,
# which is why each seat carries its model. All eight seats verified
# against the live API: ids found in the catalogue, one real synth per
# model path, billed character counts matching sent counts exactly.
SP_VOICES_BY_LANG = {
    "hr": [("lesya",       "Lesya",    "simba-multilingual"),
           ("beatrice_32", "Beatrice", "simba-multilingual"),
           ("dominika",    "Dominika", "simba-multilingual"),
           ("daria",       "Daria",    "simba-multilingual")],
    "en": [("beatrice_32", "Beatrice", "simba-3.2"),
           ("imogen_32",   "Imogen",   "simba-3.2"),
           ("edmund_32",   "Edmund",   "simba-3.2"),
           ("hugh_32",     "Hugh",     "simba-3.2")],
}

# What a finger held on the name learns — Baba's own descriptions.
SP_VOICE_HELP = {
    ("hr", "lesya"):       "Lesya — Ukrainian female, Slavic sounds",
    ("hr", "beatrice_32"): "Beatrice — British female, warm, speaks Slavic",
    ("hr", "dominika"):    "Dominika — Polish female",
    ("hr", "daria"):       "Daria — Russian female",
    ("en", "beatrice_32"): "Beatrice — British female, warm",
    ("en", "imogen_32"):   "Imogen — British female",
    ("en", "edmund_32"):   "Edmund — British male",
    ("en", "hugh_32"):     "Hugh — British male",
}

def sp_default_voice(lang: str):
    """(voice_id, model) of a language's first seat — Lesya for Croatian,
    Beatrice for English, English if the language has no seats."""
    rows = SP_VOICES_BY_LANG.get(lang) or SP_VOICES_BY_LANG["en"]
    return rows[0][0], rows[0][2]



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


# ---------------------------------------------------------------------
# HUME — VR's provider. The same ring, the same rotation, the same
# vocabulary of dead / cool / soft as Speechify and Groq, because a
# fourth way of handling keys is a fourth thing to get wrong.
#
# ONE DIFFERENCE, AND IT IS THE IMPORTANT ONE: Hume's limit is PER MINUTE
# and 429 is COMMON RATHER THAN EXCEPTIONAL. On the other providers a 429
# means something is wrong; here it means the app went too fast. So a 429
# does NOT rotate to another key first — it is reported as a wait, and
# VR.wait_left is what stops it happening at all.
# ---------------------------------------------------------------------

# Hume is behind Cloudflare and refuses a request with no User-Agent.
# See hume_call for the measurement.
HUME_UA = "TTT-LLL/1.0 (+https://ttt-lll.streamlit.app)"


def hume_error_kind(status: int) -> str:
    if status in (401, 402):
        # 401 rejected, 402 out of credit — rotating to another key is
        # the right move for both.
        return "dead"
    if status == 429:
        return "cool"
    if status == 403:
        # NOT "dead". Cloudflare returns 403 for a browser-signature ban
        # (error 1010) that has nothing to do with the key, and burning
        # every key in the ring over it would take VR down for good
        # while every key was perfectly fine.
        return "soft"
    return "soft"


def hume_error_message(status: int, body: str) -> str:
    msgs = {400: "Hume refused the request (400) — usually the voice name.",
            401: "Hume rejected the key (401).",
            402: "No Hume credit left on this account (402).",
            403: "Hume refused the request (403). If this says 1010 it is "
                 "Cloudflare, not the key.",
            404: "Hume does not know that voice (404).",
            429: "Hume is drinking coffee (429) — it limits per minute."}
    if status in msgs:
        return msgs[status]
    return "Hume error %d" % status


def hume_call(key: str, payload: dict, timeout: int = 120):
    """One POST to Hume. Returns (data, error, kind).

    THE KEY IS NEVER IN THE RETURNED TEXT. Hume quotes the request back
    in some error bodies, so the body is scrubbed of anything key-shaped
    before it can reach a screen or a log.
    """
    req = _ureq.Request(
        "https://api.hume.ai/v0/tts",
        data=json.dumps(payload).encode("utf-8"),
        headers={"X-Hume-Api-Key": key, "Content-Type": "application/json",
                 "Accept": "application/json",
                 # A USER-AGENT IS NOT DECORATION HERE. Hume sits behind
                 # Cloudflare, which answers urllib's DEFAULT agent with
                 # 403 "error code: 1010" — a browser-signature ban that
                 # looks exactly like a rejected key. Measured 24.8.2026:
                 # no UA -> 403 every time; ANY ordinary UA -> 200 every
                 # time, same key, same body, same second.
                 #
                 # This is why the app names itself on every request.
                 "User-Agent": HUME_UA},
        method="POST")
    try:
        with _ureq.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
        return (json.loads(body) if body.strip() else {}), None, None
    except _uerr.HTTPError as e:
        try:
            raw = e.read().decode("utf-8", "replace")
        except Exception:
            raw = ""
        raw = _re.sub(r"[A-Za-z0-9_\-]{32,}", "[redacted]", raw)[:200]
        return None, hume_error_message(e.code, raw), hume_error_kind(e.code)
    except Exception as e:
        return None, "Could not reach Hume: %s" % e, "soft"


def hume_speak(ring: dict, text: str, voice_name: str, direction: str):
    """(wav bytes, seconds) or (None, error). Rotates the ring exactly as
    Speechify does, and treats 429 as a wait rather than a bad key."""
    keys = ring["keys"]
    n = len(keys)
    if not n:
        return None, t("vr_no_key")
    payload = {"utterances": [{"text": text[:VR.TEXT_CAP],
                               "description": direction,
                               "voice": {"name": voice_name,
                                         "provider": "HUME_AI"}}],
               "format": {"type": "wav"}, "num_generations": 1}
    idx = ring.get("active", 0) % n
    last = ""
    for _ in range(n):
        i = ring_pick(ring, idx)
        if i is None:
            break
        k = keys[i]
        data, err, kind = hume_call(k["key"], payload)
        if not err:
            k["state"] = "ok"
            k["last_error"] = ""
            k["calls"] = k.get("calls", 0) + 1
            ring["active"] = i
            try:
                gen = (data.get("generations") or [])[0]
                return (_b64.b64decode(gen["audio"]),
                        float(gen.get("duration") or 0)), None
            except (IndexError, KeyError, TypeError, ValueError):
                return None, t("vr_empty")
        last = err
        if kind == "dead":
            k["state"] = "dead"
            k["last_error"] = err
            idx = (i + 1) % n
            continue
        if kind == "cool":
            # A MINUTE, NOT TWO. Hume's window is per minute, so parking
            # a key for 120s the way Speechify does would idle a working
            # key for twice as long as it needs.
            k["state"] = "cool"
            k["cool_until"] = time.time() + 60
            k["last_error"] = err
            idx = (i + 1) % n
            continue
        return None, err
    return None, last or t("vr_all_busy")


def hume_test_one(key: str):
    """Cheapest possible proof a key works: list one voice, generate
    nothing. A test that synthesises would spend a rate-limit slot the
    person is about to want."""
    req = _ureq.Request(
        "https://api.hume.ai/v0/tts/voices?provider=HUME_AI&page_size=1",
        headers={"X-Hume-Api-Key": key, "Accept": "application/json",
                 "User-Agent": HUME_UA})
    try:
        with _ureq.urlopen(req, timeout=30) as r:
            r.read()
        return None, None
    except _uerr.HTTPError as e:
        return hume_error_message(e.code, ""), hume_error_kind(e.code)
    except Exception as e:
        return "Could not reach Hume: %s" % e, "soft"


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


# ---- NOTES THAT SURVIVE A RELOAD -------------------------------------
#
# Baba: "notes are not surviving between sessions — I create a note, I
# log in as Emina again, and the note is gone."
#
# They lived in session_state alone, which dies with the tab. Everything
# a person types was being kept exactly as long as they kept the page
# open, which makes a notebook a scratchpad.
#
# THE BROWSER, NOT DRIVE — for now, deliberately. The Drive half is
# designed (§60: every note already carries the rec_id of its audio) but
# needs the MAIN script changed and deployed, and Baba's notes are
# disappearing today. localStorage is already wired, already carries his
# settings and his remember-token, and costs no deploy.
#
# WHAT THAT DOES NOT DO, so nobody discovers it the hard way: notes stay
# on THIS device. They will not follow Emina to her phone, and clearing
# the browser loses them. Drive is the durable answer and this is not
# it — it is the difference between losing a note on reload and losing
# it on a new device.
NOTES_LS_KEY = f"maha_notes_{USER}"


def persist_notes():
    """Write the notebook to the browser, IF it differs from the copy
    already written.

    The guard is not an optimisation. Queueing a write makes the bridge
    run, and the bridge is a component whose round trip costs a rerun —
    an unconditional write every render would mean an app that never
    settles.
    """
    try:
        now = json.dumps(st.session_state.get(NOTES.KEY, []),
                         ensure_ascii=False, sort_keys=True)
    except Exception:
        return                    # never a dependency, never a crash
    if now == st.session_state.get("_notes_saved"):
        return
    st.session_state["_notes_saved"] = now
    queue_ls(writes={NOTES_LS_KEY: now})

    # AND TO DRIVE, beside the recordings. Baba: "notes should be saved
    # in the same location where audio files are saved, and a simple
    # text file as a backup."
    #
    # THE BROWSER IS THE FAST COPY AND DRIVE IS THE TRUE ONE. The
    # browser answers instantly and works with the sheet disconnected;
    # Drive follows a person to another device and survives a cleared
    # browser. Neither alone is enough, and Drive alone would put a
    # network round trip in front of every note.
    #
    # It NEVER blocks and never raises: a notebook that will not save to
    # Drive must still save to the browser, and the person must still be
    # able to type.
    try:
        store = drive_store()
        if store is not None and getattr(store, "enabled", False):
            store.put_notes(now)
    except Exception:
        pass
    # AND ONE MORE RUN, SO THE QUEUE IS ACTUALLY FLUSHED.
    #
    # The bridge runs at the TOP of a script run and sends whatever was
    # queued BEFORE it. A write queued down here therefore waits for the
    # next run — and if the person stops touching the app, that run never
    # comes and the note is never written. Measured: localStorage held
    # `[]` while three notes sat on the screen.
    #
    # It cannot loop: `_notes_saved` is set above, so the next run finds
    # nothing to write and returns before reaching this line.
    st.rerun()


def restore_notes():
    """Read them back, ONCE per session, and only when there is nothing
    in memory already.

    The guard matters: this runs on every render, and overwriting live
    notes with the last-saved copy would undo whatever was said in the
    seconds before the write landed.
    """
    if st.session_state.get("_notes_restored"):
        return

    # WAIT FOR THE BRIDGE. LS_DATA is filled by a COMPONENT, and a
    # component reports nothing on the run that creates it — so on the
    # first render after a reload it is empty, and it is empty in
    # exactly the same way whether the browser has notes or not.
    #
    # My first version set the flag here, before looking. It therefore
    # gave up on the one render where there was nothing to find yet, and
    # never tried again: the notes were written to storage correctly and
    # never read back. Caught by reloading a real browser, not by any
    # test — AppTest has no component to wait for.
    if not LS_DATA:
        return

    st.session_state["_notes_restored"] = True
    raw = LS_DATA.get(NOTES_LS_KEY)

    # DRIVE WHEN THE BROWSER HAS NOTHING. A new device, or a cleared
    # browser: the notebook is not here but it is in Drive, and that is
    # exactly the case the browser copy cannot cover.
    #
    # Only when the browser is empty — not as a merge. Two copies of a
    # notebook edited in two places cannot be merged without deciding
    # which edit loses, and guessing at that would lose somebody's
    # words. The browser is the working copy; Drive is what fills it
    # when it is empty.
    if not raw:
        try:
            store = drive_store()
            if store is not None and getattr(store, "enabled", False):
                raw = store.get_notes()
        except Exception:
            raw = None

    if not raw or st.session_state.get(NOTES.KEY):
        return
    try:
        got = json.loads(raw)
    except Exception:
        return
    if isinstance(got, list):
        st.session_state[NOTES.KEY] = got


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


def pick_sp_voice(voice_id: str, model: str = None):
    # THE MODEL TRAVELS WITH THE PICK. beatrice_32 exists in both language
    # rows with different models, so the id alone is ambiguous; whoever
    # renders the button knows which row it sat in and says so here.
    st.session_state["sp_voice"] = voice_id
    st.session_state["sp_model"] = model or sp_model_for(voice_id)
    persist_settings()


def forget_me():
    queue_ls(removes=[AUTH_LS_KEY])
    st.session_state["_forgotten"] = True




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
        # AND THE NUDGE IS SETTLED. Somebody who arrived on a password
        # Baba chose has done the thing the notice was asking for, and
        # it must not greet them again on the next login. The script
        # clears the flag in the sheet on this same call; these two keys
        # are the session's copy of that.
        st.session_state["_must_done"] = True
        st.session_state.pop("_must_change", None)
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
    """Every voice on ONE row, grouped by language.

    A REVERSAL, AND A DELIBERATE ONE. The headings were removed once, on
    Baba's own reasoning: "HR ENG, it's not necessary — Gabrijela and
    Srećko, we know, are Croats." Now he wants them back: "put HR and
    then Gabi Srećko, then ENG then Sonia Ryan."

    Both readings are right about different people. He knows which voice
    speaks which language; somebody meeting the app does not, and four
    names in a row tell them nothing. So the tags return — but as TAGS,
    dim and small, not as headings on lines of their own. The row still
    costs one line, which is what the removal was protecting.
    """
    current = st.session_state.get("voice", "Gabrijela")
    with st.container(key="voicerow"):
        # A narrow cell for each tag, a wider one for each voice.
        widths, cells = [], []
        for lang, names in VOICES_BY_LANG.items():
            widths.append(0.55)
            # THE SAME WORDS AS THE PILLS IN T — HR and ENG. lang.upper()
            # gave "EN", which is correct and is not what the rest of the
            # app says. Two names for one language on two screens is how
            # somebody starts wondering whether they mean the same thing.
            cells.append(("tag", t("lang_" + lang)))
            for n in names:
                widths.append(1.0)
                cells.append(("voice", n))
        cols = st.columns(widths)
        for col, (kind, val) in zip(cols, cells):
            if kind == "tag":
                col.markdown('<div class="vtag">%s</div>' % html.escape(val),
                             unsafe_allow_html=True)
                continue
            col.button(
                VOICE_SHORT.get(val, val), key=f"{prefix}_{val}",
                type="primary" if val == current else "secondary",
                help=val,
                # on_pick lets the reader rebuild a reading already in
                # flight when the voice changes. Nothing else passes it.
                on_click=(lambda n=val: (pick_voice(n), on_pick and on_pick()))
                if on_pick else pick_voice,
                args=() if on_pick else (val,))


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


def _match_voice_to(lang: str):
    """Pick a voice that speaks `lang`, in whichever engine is talking.

    Lifted out of read_this so the note path and the transcript path
    cannot drift — when the Speechify seats changed at v176, one copy
    would have been updated and the other would not.
    """
    if lang not in VOICES_BY_LANG:
        lang = "hr"
    if talking_engine() == "speechify":
        rows = SP_VOICES_BY_LANG.get(lang) or ()
        cur = (st.session_state.get("sp_voice"),
               st.session_state.get("sp_model"))
        if rows and not any((vid, model) == cur for vid, _l, model in rows):
            vid, model = sp_default_voice(lang)
            st.session_state["sp_voice"] = vid
            st.session_state["sp_model"] = model
    else:
        current = st.session_state.get("voice", "Gabrijela")
        if VOICE_LANG.get(current) != lang:
            st.session_state["voice"] = VOICES_BY_LANG[lang][0]


def read_this():
    """Move to the Talk tab, carry the text over, pick the voice that matches
    the language just transcribed, and start reading — no popup, no extra tap."""
    st.session_state["talk_text"] = t1_text()
    # ONE IMPLEMENTATION, used from here and from read_note().
    _match_voice_to(st.session_state.get("last_lang", "hr"))
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
        url = str(st.secrets.get("SHEETS_URL", "") or "")
        token = str(st.secrets.get("SHEETS_TOKEN", "") or "")
        flag = SHEET.flag(sheet_config(), "store_audio", USER)
        on = bool(secret) and bool(url) and bool(token) and flag

        # SAY WHY IT IS OFF, ONCE PER SESSION.
        #
        # Baba recorded three times, nothing reached Drive, and the log
        # held nothing at all. That silence is this function: any one
        # condition missing and the store is disabled, and every caller
        # then returns early WITHOUT an error because a disabled store
        # is not a failure.
        #
        # It is not a failure and it is not nothing either. Somebody
        # whose recordings are quietly not being kept deserves to know
        # which of the four things is missing — the secret, the URL, the
        # token, or the sheet's own switch.
        if not on and not st.session_state.get("_drive_off_logged"):
            st.session_state["_drive_off_logged"] = True
            missing = [n for n, v in (("DRIVE_SECRET", secret),
                                      ("SHEETS_URL", url),
                                      ("SHEETS_TOKEN", token),
                                      ("the sheet's store_audio switch", flag))
                       if not v]
            errlog.add(st.session_state, "drive",
                       "NOT KEEPING RECORDINGS — nothing is being stored",
                       "missing: " + ", ".join(missing))

        return _drive_store(url, token, secret, USER, on)
    except Exception as e:
        # The same silence, one layer out: this used to swallow whatever
        # went wrong reading the sheet and hand back a disabled store.
        if not st.session_state.get("_drive_off_logged"):
            st.session_state["_drive_off_logged"] = True
            errlog.add(st.session_state, "drive",
                       "NOT KEEPING RECORDINGS — could not work out whether "
                       "storage is on",
                       "{}: {}".format(type(e).__name__, e))
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
        current_model = (st.session_state.get("sp_model")
                         or sp_model_for(current_sp))

        def synth_fn(text):
            return sp_synthesize(sp_ring_talk, text, current_sp, current_model)
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
        # THE SAME SHAPE AS THE EDGE PICKER: a language tag, then its
        # voices, HR first — one visual language across engines, the tags
        # saying the same words the pills in T say. One row per language
        # because eight names and two tags will not fit one line on a
        # 390px phone, and a wrapped row reads as a broken one.
        current_sp = st.session_state.get("sp_voice", "beatrice_32")
        current_model = (st.session_state.get("sp_model")
                         or sp_model_for(current_sp))
        for lang, rows in SP_VOICES_BY_LANG.items():
            # The container key contains "voicerow" so the one-line CSS in
            # theme.py applies to these rows exactly as it does to Edge's.
            with st.container(key=f"voicerowsp_{lang}"):
                cols = st.columns([0.55] + [1.0] * len(rows))
                cols[0].markdown('<div class="vtag">%s</div>'
                                 % html.escape(t("lang_" + lang)),
                                 unsafe_allow_html=True)
                for col, (vid, label, model) in zip(cols[1:], rows):
                    # beatrice_32 sits in both rows, so "current" is the
                    # (voice, model) pair — the id alone would light both.
                    col.button(
                        label, key=f"talksp_{lang}_{vid}",
                        type=("primary" if (vid == current_sp
                                            and model == current_model)
                              else "secondary"),
                        help=SP_VOICE_HELP.get((lang, vid), label),
                        on_click=lambda v=vid, m=model: (
                            pick_sp_voice(v, m), _revoice()))

        def synth_fn(text):
            return sp_synthesize(sp_ring_talk, text, current_sp, current_model)
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


def read_note(note_id: str):
    """Send one note to R and start reading it.

    Baba: "user can open any note and press Read, and this note goes to
    the generation and plays automatically through the player above."

    THE SAME HANDOFF `read_this` ALREADY DOES from T, reusing its voice
    logic rather than copying it — app.py has been bitten twice by two
    copies of one idea drifting apart, and this is exactly that shape.
    The only difference is where the words come from.
    """
    note = NOTES.get(st.session_state, note_id)
    if note is None:
        return
    body = (note.get("text") or "").strip()
    if not body:
        return          # nothing to read, and a silent player is a fault report
    st.session_state["talk_text"] = body
    _match_voice_to(note.get("language")
                    or st.session_state.get("speech_lang", "hr"))
    close_note()        # the note gave up the screen; R is taking over
    st.session_state["active_tab"] = "talk"
    st.session_state["_auto_read"] = True


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


def transcribe_note_take():
    """A take recorded inside a note. Transcribe it and add it there.

    Runs OUTSIDE the component's own render, on a rerun, because
    transcription takes seconds and the editor must not be held open
    mid-frame waiting for it.

    Everything below capture is the shared path — the router chooses the
    engine, ffmpeg makes the FLAC, the bridge transcribes. Only the
    destination is different, and the destination is the whole point:
    the words join the note that is open.
    """
    take = st.session_state.pop("_note_take", None)
    if not take:
        return
    note_id = take.get("note_id")
    if not NOTES.get(st.session_state, note_id):
        return                       # the note went away; drop it quietly

    try:
        raw = base64.b64decode(take["b64"])
    except Exception:
        errlog.add(st.session_state, "note", "take could not be decoded", "")
        return
    if not raw:
        return

    buf = io.BytesIO(raw)
    buf.name = "note-take.webm"
    st.session_state["_take_mime"] = take.get("mime", "")

    lang = st.session_state.get("speech_lang", "hr")
    seconds = float(take.get("seconds") or 0)
    # DECLARED BEFORE THE TRY, so a failure that happens before the
    # upload starts cannot become a NameError further down — and
    # finish_keeping(None) is already defined to return "" rather than
    # complain.
    _nkeeper = None
    try:
        with st.spinner(t("note_working")):
            stt = stt_bridge()
            if stt is None:
                raise RuntimeError(t("routing_none"))
            # The SAME two branches the rest of the app uses: an engine
            # that takes big files gets the file, and one that does not
            # goes through the chunking wrapper. Written once in
            # ttt/audio.py and reached from here rather than copied —
            # §"one implementation, in the module, used from here".
            # BOTH RECORDERS, or the setting would be true of the deck
            # and not the note — the split that hid the note storage gap
            # for fifty versions.
            flac = maybe_trim(to_flac16k(raw))
            # KEEP THE AUDIO. Baba: "storage should work for both
            # systems, recording and note."
            #
            # It never did. This path made a FLAC, transcribed it, and
            # let it go — every word spoken into a note has had its
            # audio thrown away since notes gained a recorder in v101.
            # The deck's takes were kept and the note's were not, and
            # nothing said so, because failing to keep something you
            # never promised to keep raises no error.
            #
            # Started HERE, alongside Whisper, exactly as the deck does
            # it: the upload and the transcription run at the same time,
            # so keeping costs the person no waiting.
            _nkeeper = start_keeping(flac, audio_seconds(flac), lang)
            if stt.handles_big_files:
                text = stt.transcribe(flac, lang)
            else:
                # No model named: "" means the engine's own default,
                # which is the fast pass. A note take is a short spoken
                # line, not the Correct button's careful second reading.
                text, _method, _reusable = transcribe_any_size(
                    flac, "", lang)
    except Exception as e:
        errlog.add(st.session_state, "note", "take failed", str(e))
        st.session_state["_note_error"] = str(e)
        # THE UPLOAD MAY ALREADY BE RUNNING. If the transcription failed
        # after it started, letting this return would leave audio in
        # Drive with no transcript beside it — the orphan half-pair §60
        # exists to prevent. Waiting for it means the recording is at
        # least whole and findable, even though the words were lost.
        if _nkeeper:
            try:
                _orphan = finish_keeping(_nkeeper)
                if _orphan:
                    errlog.add(st.session_state, "drive",
                               "audio kept, but its transcript failed",
                               "recording %s has no text" % _orphan)
            except Exception:
                pass
        return

    # AND FINISH KEEPING IT, with its transcript beside it — the same
    # pair the deck makes, so a note's audio is as findable as any other
    # recording and neither half can exist without the other.
    #
    # AFTER the transcription, never before: storage is a convenience for
    # later and must not stand between somebody and the words they just
    # spoke.
    try:
        _nrec = finish_keeping(_nkeeper)
        if _nrec:
            # THE SAME INVALIDATION, both recorders. A note's take is a
            # recording like any other, and "the list is stale" must be
            # true of both or the deck refreshes and the note does not.
            st.session_state.pop("_recs", None)
        if _nrec and (text or "").strip():
            _nst = drive_store()
            if not _nst.put_text(_nrec, text):
                errlog.add(st.session_state, "drive",
                           "note transcript not stored beside its audio",
                           _nst.last_error or "no reason given")
            # THE SAME SETTING, THE SAME PLACE IN THE SEQUENCE. A note's
            # take obeys it too, or "delete after" would be true of one
            # recorder and not the other — which is exactly the split
            # that hid the note storage gap for fifty versions.
            if not st.session_state.get("keep_recordings", True):
                _nst.delete(_nrec)
                st.session_state.pop("_recs", None)
    except Exception as e:
        errlog.add(st.session_state, "drive", "keeping the note take failed",
                   "{}: {}".format(type(e).__name__, e))

    body = (text or "").strip()
    if not body:
        st.session_state["_note_error"] = t("nothing_heard")
        return

    NOTES.append(st.session_state, note_id, body, at=take.get("caret"))
    USAGE.log("transcribe", seconds, UNIT_SECONDS, stt.id)


def keep_as_note():
    """Keep what is in the box as a note.

    The ONE way a transcript becomes a note now. It reads `t1_text()`
    rather than the raw transcript, so whatever he has done to it since —
    grammar, reshape, a hand edit — is what gets kept.
    """
    # AN EMPTY BOX MAKES AN EMPTY NOTE. Baba: "add to notes, if it is
    # empty then it simply adds empty note."
    #
    # That is what `new` used to be for, and it is the more useful half
    # of it: a blank note to open and speak into, rather than a blank
    # box. It used to return here and do nothing at all, which read as
    # a broken button.
    body = t1_text().strip()
    nid = NOTES.add(st.session_state, body, allow_empty=True,
                    language=st.session_state.get("last_lang", ""),
                    rec_id=st.session_state.get("_last_rec_id", ""))
    st.session_state["_note_kept"] = True
    # AN EMPTY NOTE OPENS ITSELF. There is nothing to see on the card and
    # nothing to read in the list — the only reason to make one is to put
    # something in it, so it goes straight to the place where that
    # happens. A note WITH text stays closed: it is finished, and the
    # list is where it belongs.
    if nid and not body:
        open_note(nid)


def _rec_save(recs):
    """Fetch the ticked recordings and offer each as a download.

    Baba: "add option to export recorded file to local hard disk. One or
    multiple? All works. If there are multiples, they should download one
    after the other."

    IT FETCHES; IT DRAWS NOTHING. The buttons are rendered by
    _rec_save_here, inside the row each file came from — Baba: "download
    link should appear under the file, the same as the player does."

    WHY IT IS A BUTTON PER FILE AND NOT ONE AUTOMATIC RUN.
    A browser will not let a page push files at somebody unasked — that
    is a download bomb, and every browser blocks it after the first. So
    "one after the other" is a stack of buttons, pressed in turn, which
    is the only honest way to do it and is also recoverable: a person who
    changes their mind halfway just stops pressing.

    THE BYTES MUST BE IN HAND FIRST. st.download_button needs the data
    at render time, so fetching ten recordings means ten waits before
    anything appears — narrated, like everything else here that makes
    somebody wait.
    """
    ids = list(st.session_state.get("_rec_saving") or [])
    if not ids:
        return

    store = drive_store()
    ready = st.session_state.setdefault("_rec_files", {})
    todo = [i for i in ids if i not in ready]

    if todo:
        started = time.time()
        bar = st.progress(0.0, text=t("rec_step_get"))
        line = st.empty()
        for k, rid in enumerate(todo):
            row = next((r for r in recs if str(r.get("rec_id")) == rid), None)
            if not row:
                continue
            line.markdown('<div class="readhint">%s</div>' % html.escape(
                t("rec_save_one") % (k + 1, len(todo), rid,
                                     time.time() - started)),
                unsafe_allow_html=True)
            tmp = tempfile.mkdtemp(prefix="save_")
            try:
                parts = store.fetch(rid, int(row.get("parts") or 1), tmp)
                if not parts:
                    errlog.add(st.session_state, "drive",
                               "could not fetch a recording to save", rid)
                    continue
                # ONE ENTRY PER PART, because that is what is actually
                # stored. Merging them would need a joiner this codebase
                # does not have, and inventing one to save a file is a
                # new failure mode for no gain.
                for pi, pth in enumerate(parts):
                    with open(pth, "rb") as fh:
                        ready.setdefault(rid, []).append(
                            ("%s%s.flac" % (rid, "" if len(parts) == 1
                                            else "_part%d" % (pi + 1)),
                             fh.read()))
            except Exception as e:
                errlog.add(st.session_state, "drive", "saving failed",
                           "%s: %s" % (rid, e))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            bar.progress((k + 1) / max(len(todo), 1), text=t("rec_step_get"))
        bar.empty()
        line.empty()

    # NOTHING IS DRAWN HERE ANY MORE. This function fetches; the buttons
    # are drawn by _rec_save_here, inside the row each file came from.


def _rec_save_here(rid):
    """The download link for one recording, under its own row."""
    ready = st.session_state.get("_rec_files") or {}
    files = ready.get(rid)
    if not files:
        return

    for name, blob in files:
        st.download_button(
            "%s  ·  %.0f KB" % (name, len(blob) / 1024.0),
            data=blob, file_name=name, mime="audio/flac",
            key="dl_%s" % name, use_container_width=True)

    # DONE BELONGS TO THIS FILE, not to the whole batch. Dropping the
    # bytes one recording at a time means somebody saving ten does not
    # have to keep all ten in memory until the last is pressed — and a
    # dozen recordings held in session state is a dozen this instance
    # cannot spare, the same reason the deck lets a take go once the
    # words are out.
    def _clear_one():
        got = st.session_state.get("_rec_files") or {}
        got.pop(rid, None)
        left = st.session_state.get("_rec_saving") or []
        st.session_state["_rec_saving"] = [i for i in left if i != rid]
        if not got:
            st.session_state.pop("_rec_files", None)
            st.session_state.pop("_rec_saving", None)

    st.button(t("rec_save_done"), key="rec_save_close_%s" % rid,
              on_click=_clear_one)


def _rec_after_actions(recs):
    """Re-transcribe, after the panel has drawn.

    PLAY IS NOT HERE ANY MORE. It moved into the row itself, under the
    file it belongs to. This is only the one action that has nowhere
    sensible to live inside the list: a second reading fills the box at
    the top of the screen, so it belongs after the panel, not in it.
    """
    msg = st.session_state.pop("_rec_msg", None)
    if msg:
        (st.success if msg[0] == "good" else st.error)(msg[1])

    rid = st.session_state.pop("_rec_again", None)
    if not rid:
        return
    row = next((r for r in recs if str(r.get("rec_id")) == rid), None)
    if not row:
        return

    # A SECOND READING IS A LONG WAIT AND IT MUST SAY SO.
    #
    # Baba: "it takes a long time until it actually gets transcribed, so
    # user is confused what's going on... show what you can fetch from
    # the transferring information."
    #
    # Three phases, and each one can report something real:
    #   1. the DOWNLOAD — which part, of how many, and its size, from
    #      drive.fetch's on_part
    #   2. the TRANSCRIPTION — which chunk, of how many, from
    #      ttt/audio.py's progress_cb, which has always been there and
    #      was simply never wired to anything here
    #   3. a RETRY — the module waits and tries again on a transient
    #      failure, and on_wait says which attempt and how long
    #
    # None of this is invented: every number comes from a callback the
    # code already had. Guessing at a percentage would be worse than
    # silence, because a bar that lies is a bar nobody believes twice.
    store = drive_store()
    tmp = tempfile.mkdtemp(prefix="again_")
    started = time.time()
    bar = st.progress(0.0, text=t("rec_step_get"))
    line = st.empty()

    def _say(msg):
        line.markdown('<div class="readhint">%s</div>' % html.escape(msg),
                      unsafe_allow_html=True)

    try:
        got = {"bytes": 0}

        def _on_part(done, total, size):
            # size is None while a part is STILL COMING, and a number
            # once it has landed. The bar only moves on arrival; the
            # line names the part either way, so a long wait has
            # something on it rather than the last part's figures.
            if size is None:
                _say(t("rec_get_wait") % (done, total,
                                          time.time() - started))
                return
            got["bytes"] += size
            # HALF THE BAR IS THE DOWNLOAD, half the transcription. Not
            # because they take equal time — they do not — but because a
            # bar that jumps to 90% and sits there is worse than one
            # that moves steadily through two honest halves.
            bar.progress(0.5 * (done / max(total, 1)), text=t("rec_step_get"))
            _say(t("rec_get_part") % (done, total, got["bytes"] / 1024.0,
                                      time.time() - started))

        parts = store.fetch(rid, int(row.get("parts") or 1), tmp,
                            on_part=_on_part)
        if not parts:
            st.error(t("rec_gone"))
            return

        def _on_chunk(done, total):
            bar.progress(0.5 + 0.5 * (done / max(total, 1)),
                         text=t("rec_step_say"))
            _say(t("rec_say_chunk") % (done, total, time.time() - started))

        def _on_wait(attempt, pause, err):
            # A RETRY IS THE MOMENT SOMEBODY MOST NEEDS TELLING. The app
            # is doing something patient and looks identical to an app
            # doing nothing.
            _say(t("rec_wait_again") % (attempt, pause))

        text = ""
        for i, pth in enumerate(parts):
            _say(t("rec_say_part") % (i + 1, len(parts),
                                      time.time() - started))
            more, _m, _r = transcribe_any_size(
                pth, "", str(row.get("language") or ""),
                progress_cb=_on_chunk, on_wait=_on_wait)
            if (more or "").strip():
                text = (text.rstrip() + "\n\n" + more.strip()
                        if text else more.strip())

        took = time.time() - started
        bar.empty()
        line.empty()
        if text.strip():
            # INTO THE BOX, not over the old transcript. A second reading
            # is a new take of the same audio, and which one is better is
            # Baba's call, not the app's.
            t1_set_text(text)
            st.success(t("rec_again_done") + "  ·  %.1fs" % took)
        else:
            st.warning(t("nothing_heard"))
    except Exception as e:
        bar.empty()
        line.empty()
        errlog.add(st.session_state, "drive", "could not use that recording",
                   "{}: {}".format(type(e).__name__, e))
        st.error(t("rec_failed"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def maybe_trim(flac_path):
    """Cut the silent gaps, if the person has asked for that.

    Baba: "add option in the settings, remove silences, so user can
    choose and experiment with the feature."

    A SETTING RATHER THAN A DEFAULT, and that is the right way in. The
    saving is real — measured at 48% on a clip shaped like dictation —
    but the cost of being wrong is a clipped first syllable, which costs
    a re-record. Somebody who can turn it off and compare will find that
    out in a minute; somebody who cannot will just think the app eats
    words.

    OFF BY DEFAULT for the same reason. Nobody's dictation changes shape
    because a new version arrived.

    Returns the path to send. The ORIGINAL on any doubt: ttt/audio.py
    hands it straight back on a failure, an empty result, or a saving
    too small to be worth a second file.
    """
    if not st.session_state.get("trim_silence"):
        return flac_path
    try:
        out, before, after = ttt_audio.trim_silence(flac_path)
    except Exception as e:
        errlog.add(st.session_state, "audio", "could not trim the silence",
                   "{}: {}".format(type(e).__name__, e))
        return flac_path
    if out != flac_path and before:
        # WORTH SAYING OUT LOUD, because this is the one setting whose
        # effect is invisible in the result: the words are the same and
        # only the bill is different. A person experimenting with it
        # needs to see what it did.
        st.session_state["_trim_note"] = t("trim_saved") % (
            before - after, 100.0 * (before - after) / before)
    return out


def assemblyai_panel():
    """The person's own AssemblyAI key: paste, test, delete, and the credit.

    Baba asked for this three versions ago and I built the arithmetic
    underneath it instead, then said so and moved on to the next thing.
    That was the wrong order — the arithmetic is invisible without this.

    WHERE THE KEY LIVES. In the settings sheet, per person, like every
    other preference. `_save_server_settings` writes to a disk Streamlit
    Cloud wipes on every redeploy, so that alone would lose it.

    WHAT IS SHOWN IS AN ESTIMATE AND SAYS SO. The hours left counts down
    from what THIS APP has transcribed, not from AssemblyAI's own
    billing. Somebody using their key elsewhere will see a figure that is
    too generous and there is no way for this app to know.
    """
    st.markdown('<div class="setlabel">%s</div>' % html.escape(
        t("aai_title")), unsafe_allow_html=True)

    key = str(st.session_state.get("aai_key") or "")

    if not key:
        # NO KEY YET: a box to paste into, and nothing else. Offering a
        # toggle for a provider nobody can reach is offering a switch
        # that does nothing.
        # A SPACE, NOT A LABEL. Baba: "your assembled key and key
        # overlapping." The heading above says what this is; the input's
        # own label rendered on top of it, because
        # label_visibility="collapsed" hides a label from SIGHT and
        # Streamlit lays it out anyway.
        #
        # THIS IS THE FOURTH TIME — the recordings heading in v156, the
        # keep-audio radio in v171, the trim toggle, and now this. The
        # rule, written where the next reader will meet it: when a
        # keyed heading sits above a widget, the widget's label is " ",
        # never the same words again.
        st.text_input(" ", key="_aai_new", type="password",
                      placeholder=t("aai_paste_ph"),
                      label_visibility="collapsed")

        def _save_key():
            fresh = str(st.session_state.get("_aai_new") or "").strip()
            if not fresh:
                return
            st.session_state["aai_key"] = fresh
            # A NEW KEY STARTS WITH THE FREE CREDIT AND NOTHING SPENT.
            # If it is not a new account the person can say so — that is
            # what the credit box is for.
            st.session_state.setdefault("aai_credit", AAI.FREE_CREDIT_USD)
            st.session_state["aai_spent_s"] = 0.0
            st.session_state["_aai_new"] = ""
            persist_settings()

        st.button(t("aai_save"), key="aai_save", on_click=_save_key,
                  use_container_width=True)
        st.markdown('<div class="readhint">%s</div>' % html.escape(
            t("aai_none")), unsafe_allow_html=True)
        return

    # A KEY IS HERE. Masked, never shown: a key on screen is a key in the
    # next screenshot, and this whole session has been screenshots.
    st.markdown('<div class="readhint">%s</div>' % html.escape(
        t("aai_have") % kr.mask(key)), unsafe_allow_html=True)

    # WHICH ENGINE DOES THE WORK. Baba: "a toggle to use either Whisper
    # free or AssemblyAI."
    def _set_on():
        st.session_state["aai_on"] = bool(st.session_state.get("_aai_on_pick"))
        persist_settings()

    st.toggle(" ", key="_aai_on_pick",
              value=bool(st.session_state.get("aai_on")),
              label_visibility="collapsed", on_change=_set_on)
    st.markdown('<div class="readhint">%s</div>' % html.escape(
        t("aai_using_paid") if st.session_state.get("aai_on")
        else t("aai_using_free")), unsafe_allow_html=True)

    # ---- WHAT IS LEFT ------------------------------------------------
    credit = float(st.session_state.get("aai_credit") or 0.0)
    spent_s = float(st.session_state.get("aai_spent_s") or 0.0)
    spent = AAI.cost_of(spent_s)
    left = max(0.0, credit - spent)
    hours = AAI.hours_for(left)

    st.markdown(
        '<div class="readhint">%s</div>'
        % html.escape(t("aai_left") % (hours, left, spent_s / 3600.0, spent)),
        unsafe_allow_html=True)
    st.markdown(
        '<div class="readhint">%s</div>'
        % html.escape(t("aai_rates") % (AAI.RATE_PER_HOUR[AAI.ASYNC_MODEL],
                                        AAI.RATE_PER_HOUR[AAI.SYNC_MODEL_ID])),
        unsafe_allow_html=True)
    # AN ESTIMATE, SAID PLAINLY. This app only knows what it transcribed.
    st.markdown('<div class="readhint">%s</div>' % html.escape(
        t("aai_estimate")), unsafe_allow_html=True)
    st.markdown(
        '<a class="paylink" href="https://www.assemblyai.com/pricing" '
        'target="_blank" rel="noopener">%s</a>' % html.escape(t("aai_pay")),
        unsafe_allow_html=True)

    # ---- test · correct the credit · delete --------------------------
    c1, c2 = st.columns([1, 1])

    def _test():
        try:
            # `kind` says WHY it failed — dead key versus rate limit —
            # and the cost document is explicit that condemning a busy
            # key wastes credit on the next one. Not used yet, so it is
            # not bound: an unused name is a promise the code is not
            # keeping.
            err, _kind = AAI.AssemblyAI().test_key(
                str(st.session_state.get("aai_key") or ""))
        except Exception as e:
            err = "%s: %s" % (type(e).__name__, e)
        st.session_state["_aai_msg"] = (
            ("good", t("aai_ok")) if not err else ("bad", str(err)[:160]))

    c1.button(t("aai_test"), key="aai_test", on_click=_test,
              use_container_width=True)

    if st.session_state.get("_aai_del_armed"):
        def _delete():
            for k in ("aai_key", "aai_on", "aai_credit", "aai_spent_s"):
                st.session_state.pop(k, None)
            st.session_state.pop("_aai_del_armed", None)
            persist_settings()
        c2.button(t("aai_del_sure"), key="aai_del2", on_click=_delete,
                  use_container_width=True)
    else:
        c2.button(t("aai_del"), key="aai_del",
                  on_click=lambda: st.session_state.update(
                      {"_aai_del_armed": True}),
                  use_container_width=True)

    msg = st.session_state.pop("_aai_msg", None)
    if msg:
        (st.success if msg[0] == "good" else st.error)(msg[1])

    # TOPPED UP? SAY SO. The app cannot know, and a number that can only
    # go down is wrong the first time somebody pays.
    with st.expander(t("aai_fix")):
        st.number_input(t("aai_credit_label"), key="_aai_credit_new",
                        value=float(credit), min_value=0.0, step=5.0)

        def _set_credit():
            st.session_state["aai_credit"] = float(
                st.session_state.get("_aai_credit_new") or 0.0)
            st.session_state["aai_spent_s"] = 0.0
            persist_settings()

        st.button(t("aai_credit_save"), key="aai_credit_save",
                  on_click=_set_credit, use_container_width=True)


# REMOVED AT THE DELIVERY GATE, G4. Each was orphaned by a change of
# mine and left behind:
#   cmd_row        v139, when the last command row left T
#   size_controls  v137, when text size became a box you type in
#   copy_pill      superseded by box_links
#   cp_row         superseded by box_links
#
# Confirmed unreferenced across the whole project — app, modules, tests,
# frontends and docs — not merely within this file. Git remembers them;
# commenting them out would be "dead code that has learned to survive
# the checks".


def speechify_panel():
    """The person's own Speechify key. The same shape as AssemblyAI's.

    Baba: "the same way we give user control over its own key for
    AssemblyAI, we're going to do it for Speechify. Same controls, same
    link, same text, everything is the same, so just different provider."

    WHAT IS DELIBERATELY NOT THE SAME: there is no hours-left figure.
    AssemblyAI bills per hour of audio and Baba gave me the two rates, so
    a countdown there is arithmetic. Speechify bills per CHARACTER and I
    do not have that rate from him — inventing one would put a wrong
    number under a heading that looks authoritative, which is worse than
    an honest gap. The link goes to their pricing page, which does know.
    """
    st.markdown('<div class="setlabel">%s</div>' % html.escape(
        t("sp_title")), unsafe_allow_html=True)

    key = str(st.session_state.get("sp_key") or "")

    if not key:
        st.text_input(" ", key="_sp_new", type="password",
                      placeholder=t("sp_paste_ph"),
                      label_visibility="collapsed")

        def _save():
            fresh = str(st.session_state.get("_sp_new") or "").strip()
            if not fresh:
                return
            st.session_state["sp_key"] = fresh
            st.session_state["_sp_new"] = ""
            persist_settings()

        st.button(t("sp_save"), key="sp_save", on_click=_save,
                  use_container_width=True)
        st.markdown('<div class="readhint">%s</div>' % html.escape(
            t("sp_none")), unsafe_allow_html=True)
        return

    st.markdown('<div class="readhint">%s</div>' % html.escape(
        t("sp_have") % kr.mask(key)), unsafe_allow_html=True)
    st.markdown(
        '<a class="paylink" href="https://speechify.com/api/#pricing" '
        'target="_blank" rel="noopener">%s</a>' % html.escape(t("sp_pay")),
        unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])

    def _test():
        try:
            err, _kind = PROVIDERS.get("speechify").test_key(
                str(st.session_state.get("sp_key") or ""))
        except Exception as e:
            err = "%s: %s" % (type(e).__name__, e)
        st.session_state["_sp_msg"] = (
            ("good", t("sp_ok")) if not err else ("bad", str(err)[:160]))

    c1.button(t("sp_test"), key="sp_test", on_click=_test,
              use_container_width=True)

    if st.session_state.get("_sp_del_armed"):
        def _del():
            for k in ("sp_key", "_sp_del_armed"):
                st.session_state.pop(k, None)
            # AND STOP TALKING WITH IT. A voice engine set to Speechify
            # with no Speechify key is a reader that says nothing, which
            # looks like the reader being broken.
            if st.session_state.get("voice_engine") == "speechify":
                st.session_state["voice_engine"] = "edge"
            if st.session_state.get("route_tts") == "speechify":
                st.session_state["route_tts"] = "edge"
            persist_settings()
        c2.button(t("sp_del_sure"), key="sp_del2", on_click=_del,
                  use_container_width=True)
    else:
        c2.button(t("sp_del"), key="sp_del",
                  on_click=lambda: st.session_state.update(
                      {"_sp_del_armed": True}), use_container_width=True)

    m = st.session_state.pop("_sp_msg", None)
    if m:
        (st.success if m[0] == "good" else st.error)(m[1])


def quick_settings():
    """The three switches worth reaching in one press.

    Baba: "at the top of the settings you need to give toggle buttons...
    name this row Quick Settings", after Android's own quick settings —
    the things you change often, above the things you set once.

    THREE, AND THEY ARE THE THREE HE NAMED: which engine transcribes,
    which engine talks, and whether silence is cut. Everything else in
    this tab is a decision made once; these three are decisions made in
    the middle of working.
    """
    st.markdown('<div class="setlabel">%s</div>' % html.escape(
        t("quick_title")), unsafe_allow_html=True)

    with st.container(key="quickrow"):
        q1, q2, q3 = st.columns([1, 1, 1])

        # 1 · WHO TRANSCRIBES. One button, not two: it shows what is
        # running and pressing it changes to the other. A pair of
        # buttons for two mutually exclusive states is one button's
        # worth of information taking twice the room.
        aai_ready = bool(str(st.session_state.get("aai_key") or "").strip())
        on = bool(st.session_state.get("aai_on")) and aai_ready

        def _flip_stt():
            if not aai_ready:
                # NOTHING TO FLIP TO. Said rather than silently ignored:
                # a button that does nothing teaches that buttons might.
                st.session_state["_quick_msg"] = t("quick_need_key")
                return
            st.session_state["aai_on"] = not on
            persist_settings()

        q1.button(t("quick_stt") % (t("quick_aai") if on else t("quick_free")),
                  key="q_stt", on_click=_flip_stt, use_container_width=True)

        # 2 · WHO TALKS. Edge is free and Speechify is the paid voice.
        sp_ready = bool(str(st.session_state.get("sp_key") or "").strip())
        talking = str(st.session_state.get("voice_engine") or "edge")

        def _flip_tts():
            if not sp_ready:
                st.session_state["_quick_msg"] = t("quick_need_key")
                return
            nxt = "edge" if talking == "speechify" else "speechify"
            st.session_state["voice_engine"] = nxt
            # AND THE ROUTE, which is what the R tab's voice pills read.
            # Writing only the setting is exactly the bug: the button
            # changed its own label and nothing else in the app moved.
            st.session_state["route_tts"] = nxt
            persist_settings()

        q2.button(t("quick_tts") % (t("quick_sp") if talking == "speechify"
                                    else t("quick_edge")),
                  key="q_tts", on_click=_flip_tts, use_container_width=True)

        # 3 · SILENCE. The same setting as below, reachable here.
        def _flip_trim():
            st.session_state["trim_silence"] = not bool(
                st.session_state.get("trim_silence"))
            persist_settings()

        q3.button(t("quick_trim") % (t("quick_on") if st.session_state.get(
                      "trim_silence") else t("quick_off")),
                  key="q_trim", on_click=_flip_trim, use_container_width=True)

    qm = st.session_state.pop("_quick_msg", None)
    if qm:
        st.markdown('<div class="readhint">%s</div>' % html.escape(qm),
                    unsafe_allow_html=True)


def note_number(i):
    """1. 2. 3. — Baba: "please add a serial number next to each note."

    THE POSITION IN THE LIST, not an id. It changes when notes are
    deleted or when a search narrows the list, and that is right: the
    number exists to point at — "open number three" — so it has to match
    what somebody is counting on the screen in front of them, not what
    the note was called when it was made.
    """
    return "%d." % (i + 1)


def recordings_panel():
    """The recordings in Drive: list, play, transcribe again, delete.

    IT LIVES IN T. A recording is made on that screen and belongs on it;
    Settings is where you change how the app behaves, not where you go
    through what you said.

    THIS IS A SYSTEM TOOL, and Baba named it as one: "for this kind of
    interface, when we are doing file management, it's like a system
    tool." Everything here is a LINK, not a pill. A pill is a choice you
    are being offered; a link is a thing you do to what you have
    selected, and file managers have always looked like the second.
    """
    store = drive_store()
    if not store.enabled:
        return

    if "_recs" not in st.session_state:
        st.session_state["_recs"] = store.list()
        # WHEN, not just what. A list that cannot say when it was read
        # is a list nobody can tell is stale.
        st.session_state["_recs_at"] = time.strftime("%H:%M:%S")
    recs = st.session_state["_recs"] or []

    # THE PANEL NO LONGER HANDS ITSELF OVER TO A DELETION. It used to
    # replace the whole list with one bar, so the rows somebody was
    # looking at disappeared while they were being deleted. The list
    # stays now, and the row being removed carries its own bar.

    with st.expander("%s · %d" % (t("rec_title"), len(recs))):
        if not recs:
            st.caption(t("rec_none"))
            return

        ids = [str(r.get("rec_id") or "") for r in recs]
        picked = [i for i in ids if st.session_state.get("_rp_%s" % i)]

        # REFRESH, AND WHEN THE LIST WAS LAST READ.
        #
        # Baba expects the count to go up the moment a recording is
        # stored, and the code does that: the store happens earlier in
        # the run than this panel, so the dropped cache is refetched in
        # the same pass. But a cached remote list should never be a
        # thing somebody has to TRUST — if it can be stale, it must say
        # when it was read and offer to read it again.
        #
        # This is also the honest answer to "why is my recording not
        # here": one press settles it, instead of a guess about whose
        # fault it is.
        _rc1, _rc2 = st.columns([1, 2.2])
        # ONE KEY, no top/bottom suffix: this sits in the PANEL, drawn
        # once, not in the action row that is drawn twice. The `where`
        # in my first draft was copied from _rec_actions and referred to
        # a variable that does not exist here — pyflakes caught it
        # immediately, which is exactly what it is for.
        _rc1.button(t("rec_refresh"), key="rec_refresh",
                    on_click=lambda: st.session_state.pop("_recs", None),
                    use_container_width=True)
        _seen = st.session_state.get("_recs_at")
        if _seen:
            _rc2.markdown('<div class="readhint">%s</div>' % html.escape(
                t("rec_seen") % _seen), unsafe_allow_html=True)

        _rec_actions(picked, ids, "top")

        # FETCH BEFORE THE ROWS ARE DRAWN, not after.
        #
        # This lived in _rec_after_actions, which runs once the whole
        # list has already rendered — so the bytes arrived a render too
        # late and the buttons appeared only on the NEXT interaction.
        # Nothing failed; the save link simply did not show up, which is
        # the worst kind of wrong.
        #
        # A row can only draw a download button for bytes that already
        # exist, so the fetching has to happen first.
        _rec_save(recs)

        playing = st.session_state.get("_rec_playing")
        for r in recs:
            rid = str(r.get("rec_id") or "")
            mins = float(r.get("seconds") or 0) / 60.0
            st.checkbox(
                "%s · %.1f min%s" % (
                    str(r.get("created") or "")[:16], mins,
                    "  ·  " + t("rec_has_text") if r.get("has_text") else ""),
                key="_rp_%s" % rid)

            # THE PLAYER SITS UNDER ITS OWN FILE. Baba: "when user choose
            # any file and press play, the player should appear below
            # that file in the list."
            #
            # It used to appear at the foot of the panel, which is fine
            # with three recordings and wrong with thirty: a player a
            # long way from the row that summoned it belongs to nothing
            # in particular.
            if playing == rid:
                _rec_play_here(r)

            # AND THE SAVE LINK UNDER ITS OWN FILE TOO. Baba: "download
            # link should appear under the file, the same as the player
            # does."
            #
            # The same reason, and I had already had it once: a control
            # a long way from the row that summoned it belongs to
            # nothing in particular. With ten recordings ticked, a stack
            # of ten buttons at the foot of the panel is ten names to
            # match against ten rows by reading — while under each row
            # there is nothing to match, because it is already there.
            _rec_save_here(rid)

            # AND THE DELETE'S OWN PROGRESS, under the row going away.
            _rec_delete_here(rid)

        _rec_actions(picked, ids, "bottom")

    _rec_after_actions(recs)

    # AND ONLY NOW, WITH EVERYTHING DRAWN, the one delete that is queued.
    # The row and its bar are already on screen, so the wait happens in
    # front of somebody rather than behind a blank panel.
    if st.session_state.get("_rec_doing"):
        _run_one_deletion()


def _rec_actions(picked, all_ids, where):
    """select all · play · transcribe again · delete.

    Drawn twice, top and bottom, so the keys carry `where` — two
    Streamlit widgets cannot share a key even when they are one idea.

    ALWAYS DRAWN, never hidden. This is the change from the first
    version: links that vanish when nothing is ticked make the panel
    jump as you tick, and a person cannot learn where a control lives if
    it is not there when they look. They GREY OUT instead.
    """
    n = len(picked)
    everything = len(all_ids) and n == len(all_ids)

    with st.container(key="recacts_%s" % where):
        c0, c1, c2, c4, c3 = st.columns([1.1, 0.8, 1.5, 0.9, 1.1])

        # SELECT ALL, and the same link clears it. One control for a
        # thing and its opposite, because "select all" next to "select
        # none" is two words for one decision.
        def _toggle_all():
            for i in all_ids:
                st.session_state["_rp_%s" % i] = not everything
            st.session_state.pop("_rec_del_armed", None)

        c0.button(t("rec_none_sel") if everything else t("rec_all"),
                  key="rec_all_%s" % where, on_click=_toggle_all,
                  use_container_width=True)

        # ONE FILE FOR PLAY AND FOR TRANSCRIBE, MANY FOR DELETE.
        #
        # Baba: "grey out action links for playing multiple files and
        # transcribing multiple files. Only deletion of the multiple
        # files is possible."
        #
        # He is right about the asymmetry and it is not arbitrary:
        # playing two files at once is not a thing, and transcribing
        # several would produce one box of text with no way to tell
        # whose words were whose. Deleting many is the one act that
        # genuinely means the same thing done repeatedly.
        one = (n == 1)
        c1.button(t("rec_play"), key="rec_play_%s" % where,
                  disabled=not one,
                  help=None if one else t("rec_one_only"),
                  on_click=lambda: st.session_state.update(
                      {"_rec_playing": picked[0] if picked else None}),
                  use_container_width=True)
        c2.button(t("rec_again"), key="rec_again_%s" % where,
                  disabled=not one,
                  help=None if one else t("rec_one_only"),
                  on_click=lambda: st.session_state.update(
                      {"_rec_again": picked[0] if picked else None}),
                  use_container_width=True)

        # SAVE WORKS ON MANY, like delete. Baba: "one or multiple, all
        # works." Copying a file to a disk is the same act repeated,
        # exactly as deleting is — unlike playing or transcribing, where
        # several at once is not a thing.
        c4.button(t("rec_save"), key="rec_save_%s" % where,
                  disabled=not n,
                  on_click=lambda: st.session_state.update(
                      {"_rec_saving": list(picked)}),
                  use_container_width=True)

        if st.session_state.get("_rec_del_armed") and n:
            c3.button(t("rec_del_sure") % n, key="rec_del2_%s" % where,
                      on_click=lambda: st.session_state.update(
                          {"_rec_doing": list(picked),
                           "_rec_doing_total": len(picked),
                           "_rec_doing_started": time.time(),
                           "_rec_del_armed": False}),
                      use_container_width=True)
        else:
            c3.button(t("rec_del"), key="rec_del_%s" % where,
                      disabled=not n,
                      on_click=lambda: st.session_state.update(
                          {"_rec_del_armed": True}),
                      use_container_width=True)


def _rec_play_here(row):
    """Fetch one recording and play it, right under its own row.

    THE AUDIO IS CACHED FOR THE SESSION. This runs on every render while
    a player is open — a tick of any checkbox redraws the whole panel —
    and fetching a recording from Drive each time would make the list
    unusable.
    """
    rid = str(row.get("rec_id") or "")
    cache = st.session_state.setdefault("_rec_audio", {})

    if rid not in cache:
        store = drive_store()
        tmp = tempfile.mkdtemp(prefix="play_")
        try:
            with st.spinner(t("rec_getting")):
                parts = store.fetch(rid, int(row.get("parts") or 1), tmp)
            if not parts:
                # fetch() returns [] rather than a partial list on
                # purpose: a missing middle piece would play as a
                # recording that simply skips, with nothing to show it.
                st.error(t("rec_gone"))
                return
            blobs = []
            for pth in parts:
                with open(pth, "rb") as fh:
                    blobs.append(fh.read())
            cache[rid] = blobs
        except Exception as e:
            errlog.add(st.session_state, "drive", "could not fetch a recording",
                       "{}: {}".format(type(e).__name__, e))
            st.error(t("rec_failed"))
            return
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    blobs = cache.get(rid) or []
    for i, blob in enumerate(blobs):
        # A long take is stored as ten-minute pieces on purpose. They are
        # numbered rather than merged: there is no joiner in this
        # codebase, and inventing one would mean an ffmpeg concat and a
        # new failure mode for no gain.
        if len(blobs) > 1:
            st.caption("%d / %d" % (i + 1, len(blobs)))
        # AUTOPLAY, AND ONLY THE FIRST PIECE.
        #
        # Baba: "user needs to press play — please make it autoplay."
        # He is right: he picked the file and pressed play, and being
        # asked to press play again is one press too many.
        #
        # `autoplay` is st.audio's own argument, so there is nothing to
        # invent here. Only piece ONE starts by itself: three players
        # all starting at once would be three voices over each other,
        # which is the opposite of what he asked for.
        #
        # A BROWSER MAY REFUSE, and that is not a bug to chase. Autoplay
        # with sound is blocked until somebody has interacted with the
        # page — and by the time this renders, Baba has ticked a box and
        # pressed a link, so the gesture is there. Where a browser still
        # says no, the player is sitting right there with its own button.
        st.audio(blob, format="audio/flac", autoplay=(i == 0))

    st.button(t("rec_close_play"), key="rec_stop_%s" % rid,
              on_click=lambda: st.session_state.update({"_rec_playing": None}))


def _rec_delete_here(rid):
    """The delete's own progress, under the row being deleted.

    Baba: "progress bar for delete should appear under the file itself,
    same as player, same as download. Everything is same logic."

    THE THIRD TIME THIS RULE HAS COME UP, and he is right that it is one
    rule: whatever an action produces belongs to the row that caused it.
    The player, the save link, and now this.
    """
    queue = st.session_state.get("_rec_doing") or []
    if not queue or queue[0] != rid:
        return
    total = int(st.session_state.get("_rec_doing_total") or len(queue))
    done = total - len(queue) + 1
    st.progress(done / max(total, 1),
                text=t("rec_del_working") % (done, total))


def _run_one_deletion():
    """Delete the recording at the head of the queue, then come back.

    ONE DELETE PER RENDER, which is what makes the per-row progress
    honest. The old version looped through every recording inside a
    single run and drew one bar for the whole batch, so the panel
    vanished and the list somebody was looking at went away while its
    rows were being removed.

    THE DRAWING HAS ALREADY HAPPENED by the time this runs: the row and
    its bar are on screen, and Streamlit streams elements as the script
    makes them, so the wait happens in front of somebody.

    ONE AT A TIME ALSO MEANS a failure names the recording it happened
    to and everything after it still gets its chance; a batch call would
    be quicker and would fail as one lump.
    """
    queue = list(st.session_state.get("_rec_doing") or [])
    if not queue:
        return
    rid = queue[0]
    store = drive_store()
    started = st.session_state.get("_rec_doing_started") or time.time()

    ok = False
    try:
        ok = store.delete(rid)
    except Exception as e:
        errlog.add(st.session_state, "drive", "delete threw",
                   "%s: %s" % (rid, e))
    if not ok:
        errlog.add(st.session_state, "drive", "could not delete a recording",
                   "%s: %s" % (rid, store.last_error or "no reason given"))

    tally = st.session_state.setdefault("_rec_tally", {"gone": 0, "failed": 0})
    tally["gone" if ok else "failed"] += 1

    # THE TICK GOES WITH THE FILE. Leaving it set would offer to delete
    # something already gone.
    st.session_state.pop("_rp_%s" % rid, None)
    st.session_state["_rec_doing"] = queue[1:]
    st.session_state["_rec_doing_started"] = started

    if not queue[1:]:
        took = time.time() - started
        # EACH OUTCOME COUNTED SEPARATELY. A single "done" over a batch
        # where one failed is a lie by omission.
        st.session_state["_rec_msg"] = (
            ("bad", t("rec_del_part") % (tally["gone"], tally["failed"], took))
            if tally["failed"]
            else ("good", t("rec_del_done") % (tally["gone"], took)))
        for k in ("_rec_doing", "_rec_doing_total", "_rec_doing_started",
                  "_rec_tally"):
            st.session_state.pop(k, None)
        st.session_state.pop("_recs", None)      # stale now; refetch

    st.rerun()

def _note_actions(picked, all_ids, where):
    """select all · read · delete — the recordings panel's row, for notes.

    Baba: "notes need the same way of deleting and selecting as the
    audio part just below it."

    MIRRORED, NOT INVENTED. The recordings panel already settled every
    question this row asks — where select-all lives, that it doubles as
    select-none, that delete arms before it fires, and that the links are
    ALWAYS DRAWN and grey out rather than vanishing. Two lists on one
    screen that behave differently is two things to learn.

    READ IS ONE NOTE ONLY, and greyed for many, for the same reason
    `play` is in the recordings row: reading two notes at once is not a
    thing. Deleting many is the one act that genuinely means the same
    thing repeated.
    """
    n = len(picked)
    everything = len(all_ids) and n == len(all_ids)

    with st.container(key="nactrow_%s" % where):
        c0, c1, c2 = st.columns([1.1, 0.9, 1.1])

        def _toggle_all():
            for i in all_ids:
                st.session_state["_np_%s" % i] = not everything
            st.session_state.pop("_note_del_armed_many", None)

        c0.button(t("note_none_sel") if everything else t("note_all"),
                  key="nact_all_%s" % where, on_click=_toggle_all,
                  use_container_width=True)

        one = (n == 1)
        c1.button(t("note_read"), key="nact_read_%s" % where,
                  disabled=not one,
                  help=None if one else t("note_one_only"),
                  on_click=lambda: read_note(picked[0]) if picked else None,
                  use_container_width=True)

        if st.session_state.get("_note_del_armed_many") and n:
            c2.button(t("note_del_n_sure") % n, key="nact_deln2_%s" % where,
                      on_click=lambda: st.session_state.update(
                          {"_note_del_many": list(picked),
                           "_note_del_armed_many": False}),
                      use_container_width=True)
        else:
            c2.button(t("note_del_n"), key="nact_deln_%s" % where,
                      disabled=not n,
                      on_click=lambda: st.session_state.update(
                          {"_note_del_armed_many": True}),
                      use_container_width=True)


def _note_delete_pending():
    """Carry out an armed multi-delete, once, at the top of a rerun.

    NOT INSIDE THE on_click. Removing notes while the list that draws
    them is mid-render is how a widget key disappears under Streamlit's
    feet; the recordings panel learned the same lesson (_rec_doing).
    The ticks are cleared too, or a deleted note's tick would survive
    and select whatever note later took its place in the list.
    """
    doomed = st.session_state.pop("_note_del_many", None)
    if not doomed:
        return
    for nid in doomed:
        NOTES.remove(st.session_state, nid)
        st.session_state.pop("_np_%s" % nid, None)
    # A note that was open and has just been deleted must not stay open.
    if st.session_state.get(OPEN_KEY) in doomed:
        close_note()
    # NO persist_notes() HERE. The foot of the module already writes the
    # notebook whenever it differs from the saved copy — that guard exists
    # precisely so the tenth place that changes a note cannot forget to
    # save, and this is the tenth place.


def notes_panel():
    """The list: a search field, then the notes. Folded, like recordings.

    Baba: "make notes collapsible, same as recordings."

    FIVE NOTES FILLED HIS WHOLE SCREEN, and the recordings below them
    were off the bottom edge. The count is on the fold's own line, so
    closed it still answers "how many" — the same shape the recordings
    and the People list already use, which means one thing to learn
    rather than three.

    THE SEARCH FIELD MOVED INSIDE. That is the one real cost: you have
    to open the fold to search. It is the right trade, because a search
    box for a list you cannot see is furniture, and somebody who wants
    to search is already opening the list.
    """
    # BEFORE THE LIST IS READ, not after. A delete carried out mid-render
    # would leave the rows drawn from a notebook that no longer matches
    # the ticks.
    _note_delete_pending()

    all_notes = NOTES.items(st.session_state)
    if not all_notes:
        return                      # nothing yet, and no empty furniture

    with st.expander("%s · %d" % (t("notes_title"), len(all_notes))):
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

        # SELECT ALL WORKS ON WHAT IS ON SCREEN, not on the whole
        # notebook. With a search term typed, "select all" meaning the
        # 200 notes you cannot see is how somebody deletes their
        # notebook while looking at three results.
        ids = [x["id"] for x in shown]
        picked = [i_ for i_ in ids if st.session_state.get("_np_%s" % i_)]
        _note_actions(picked, ids, "top")

        for i, n in enumerate(shown):
            # ONE CARD, ONE PRESS, WHOLE WIDTH. A card with a tick, a
            # title and a menu is three targets in a row on a phone. Here
            # the card IS the target, and everything else lives inside
            # the note once it is open.
            #
            # NUMBERED. Baba: "please add a serial number next to each
            # note." It is the position in the list, not an id — it
            # changes when notes are deleted, which is right: it exists
            # to point at ("open number three"), and a number that no
            # longer matches what somebody is counting is worse than
            # none.
            # THE INDEX IS IN THE KEY, not just the id.
            #
            # A duplicate id crashed the app outright —
            # StreamlitDuplicateElementKey, a red wall of Python where a
            # list of notes should be. ttt/notes.py no longer MAKES a
            # duplicate, and that is the real fix; this is the second
            # line of defence, because the notebook can also arrive from
            # the browser or from Drive, and data that came from
            # somewhere else must never be able to take the app down.
            #
            # The position makes it unique whatever the ids say. Clicking
            # still uses the id, so the right note opens.
            # THE TICK SITS BESIDE THE CARD, not inside it. A checkbox
            # inside a button is not a thing Streamlit can draw, and the
            # recordings list already answered this the same way: the
            # tick is its own control, small, to the left.
            tick, card = st.columns([0.14, 1.0])
            tick.checkbox("", key="_np_%s" % n["id"],
                          help=t("note_sel_help"),
                          label_visibility="collapsed")
            card.button(
                "%s %s\n\n%s" % (note_number(i), NOTES.heading(n),
                                  NOTES.body_preview(n, 70)),
                key="note_%d_%s" % (i, n["id"]), use_container_width=True,
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
        # THE ACTIONS MOVED TO THE FOOT. Baba: "our visual language is
        # that actions are written below the text boxes; in the notes
        # they are above, so move this below the recorder."
        #
        # He is right and it is the last place that disagreed. Every
        # other module puts what you can DO under what you are looking
        # at — copy, clear, add to notes in T; clear in R — because you
        # read first and act second. The open note had its date, delete
        # and close above the words, which is where a title bar goes,
        # not where an action goes.

        st.text_input("title", key="note_title_%s" % note_id,
                      value=NOTES.heading(note),
                      label_visibility="collapsed", on_change=_save_title)

        # SAY WHEN A TAKE FAILED. _note_error was written in two places
        # and displayed in none, so a failed transcription inside a note
        # was completely silent — record, wait, nothing. The §47 shape
        # again: a failure that looks exactly like nothing happening.
        _err = st.session_state.pop("_note_error", None)
        if _err:
            st.error(_err)

        if _note_component is not None:
            ev = _note_component(
                text=note.get("text", ""),
                scale=a11y.clamp(st.session_state.get("text_scale",
                                                      a11y.DEFAULT_SCALE)),
                labels={"rec": t("rec_btn"), "stop": t("rec_stop"),
                        "pause": t("rec_pause")},
                recording=False,
                key="note_ed_%s" % note_id, default=None)

            if isinstance(ev, dict):
                # The editor sends on every keystroke, so the stamp is
                # what stops one edit being re-applied on every rerun.
                if st.session_state.get("_note_seen") != ev.get("at"):
                    st.session_state["_note_seen"] = ev.get("at")
                    if isinstance(ev.get("text"), str):
                        NOTES.update(st.session_state, note_id, text=ev["text"])

                    # A TAKE RECORDED INSIDE THE NOTE. It arrives in the
                    # same shape the deck posts, so it goes down the same
                    # pipeline — router, ffmpeg, Whisper — and only the
                    # destination differs: it joins THIS note instead of
                    # making a new one.
                    if ev.get("b64"):
                        st.session_state["_note_take"] = {
                            "b64": ev["b64"],
                            "mime": ev.get("mime", ""),
                            "seconds": ev.get("seconds", 0),
                            "note_id": note_id,
                            # WHERE HIS CURSOR WAS. Only the frame knows;
                            # it reads it the moment rec is pressed,
                            # before the press can move it.
                            "caret": ev.get("caret"),
                        }
                        st.rerun()
        else:
            # No component: still editable, only without the arrows.
            st.text_area("note", value=note.get("text", ""),
                         key="note_plain_%s" % note_id, height=260,
                         label_visibility="collapsed",
                         on_change=lambda: NOTES.update(
                             st.session_state, note_id,
                             text=st.session_state.get(
                                 "note_plain_%s" % note_id, "")))

        with st.container(key="noteacts"):
            # THE DATE SITS WITH THEM, on the left of the pair. Baba:
            # "made date could go on the top on the left side of delete
            # and close... do not make it, it is clear that it is made."
            # The word "made" was explaining what a date already says.
            # NO SPACER SHARE. The columns hold only what is in them
            # now — the stylesheet packs them to the left, and a wide
            # first column would push the pair back under the badge
            # this move was to escape.
            # READ JOINS THE ROW. Baba: "user can open any note and press
            # a Read action link, and this note goes to the generation
            # and plays automatically through the player above."
            #
            # An ACTION LINK in the row where the note's other actions
            # already are — not a button of its own somewhere else. The
            # note's whole vocabulary is this one line at the foot.
            when, read, dele, back = st.columns([1, 1, 1, 1])
            _body = (note.get("text") or "").strip()
            read.button(t("note_read"), key="nact_read_open",
                        disabled=not _body,
                        help=None if _body else t("notes_none"),
                        on_click=read_note, args=(note_id,),
                        use_container_width=True)
            when.markdown('<div class="notewhen">%s</div>'
                          % NOTES.when_of(note), unsafe_allow_html=True)
        # STILL TWO PRESSES. One press on a whole note, in an app with no
        # undo anywhere, is not a risk worth taking — and moving it next
        # to `close` makes a mis-tap MORE likely, not less.
            if st.session_state.get("_note_del_armed") == note_id:
                # NOT type="primary". That is why it stayed dark after
                # v141 took the red away: Streamlit gives a primary
                # button its own colour rules and they win over the
                # link styling beside it. Baba asked twice; I fixed the
                # red the first time and this the second.
                dele.button(t("note_del_sure"), key="note_del2",
                            on_click=_del_do, use_container_width=True)
            else:
                dele.button(t("note_del"), key="note_del",
                            on_click=_del_arm, use_container_width=True)
            back.button(t("note_close"), key="note_close",
                        on_click=close_note, use_container_width=True)

        # "to the box" and "new note" are gone. Baba: "I don't know what
        # that means or what it does, it's not clear. Remove it. New
        # note, remove it — we only make new notes of it."
        #
        # He is right on both. "to the box" copied a note back into the
        # transcript box, which was the old archive's habit surviving
        # into a place where the note IS the document. And "new note"
        # only closed this one, so it was `close` wearing a second name.

        # The "made … · edited …" caption lived here and is gone: the
        # date is up beside delete and close now, and one date is
        # enough. An edited note shows the time it was last touched,
        # which is the useful one.
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
        # THREE LANGUAGES: HR, ENG, AUTO.
        #
        # AUTO lets the engine work it out, which is what somebody who
        # switches between Croatian and English mid-thought actually
        # wants. It is not free — naming the language is more accurate
        # than detecting it, and detection can hear one sentence of
        # English inside Croatian and change its mind — so it is offered
        # rather than made the default.
        #
        # The app stores "auto" and each provider says it its own way:
        # AssemblyAI takes language_detection=True, Whisper wants the
        # parameter left out altogether.
        # TWO ROWS, EACH A WHOLE GROUP. Five pills do not fit one line
        # below 412px, and Streamlit wrapped them 4 + 1 — which left
        # `multi` alone underneath, looking orphaned rather than paired
        # with `single`. Splitting them deliberately keeps each pair
        # together: the language on one line, the mode on the next.
        # ALL FIVE ON ONE LINE. Baba: "auto HR ENG single multi,
        # everything in one line, not two."
        #
        # This reverses v118, which split them precisely because five
        # pills clipped below 412px. §27 is the rule that decides it and
        # it allows this: the CELLS may shrink and the TYPE may shrink;
        # what may never happen is a word being cut. So the type comes
        # down and the row holds, verified at 320 and 360px.
        #
        # The shares follow the word lengths — AUTO and single are the
        # long ones.
        lcol1, lcol2, lcol3, divcol, mcol1, mcol2 = st.columns(
            [0.8, 0.9, 1.15, 0.25, 1.25, 1.05])
        speech_now = st.session_state.get("speech_lang", "hr")
        # HR · ENG · AUTO, and a divider before single/multi. Baba's
        # order, and the reason is AssemblyAI: it is very good at a
        # named language and its AUTO is not, so the two certainties
        # come first and the guess goes last. This reverses v118, where
        # AUTO led — that was the right order for Whisper alone.
        lcol1.button(t("lang_hr"), key="tr_hr",
                     type="primary" if speech_now == "hr" else "secondary",
                     on_click=set_speech_lang, args=("hr",))
        lcol2.button(t("lang_en"), key="tr_en",
                     type="primary" if speech_now == "en" else "secondary",
                     on_click=set_speech_lang, args=("en",))
        lcol3.button(t("lang_auto"), key="tr_auto",
                     type="primary" if speech_now == "auto" else "secondary",
                     on_click=set_speech_lang, args=("auto",))
        # A PIPE BETWEEN THE TWO IDEAS. Language and mode answer
        # different questions — "what am I speaking" and "what happens
        # to what is already in the box" — and five pills in a row read
        # as one list of five choices.
        divcol.markdown('<div class="pilldiv">|</div>', unsafe_allow_html=True)
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
    # NOTHING IS KEPT HERE ANY MORE.
    #
    # This block used to archive every take, and then to make a note of
    # every take. Both are gone: the archive became notes in v98, and
    # notes became a DECISION in v114 — Baba: "under the textbox just an
    # orange line, add to notes."
    #
    # `keep` is therefore no longer read. It stays in the signature
    # because three callers pass it and because the distinction it names
    # is still real: loading something back into the box is not the same
    # act as a new take arriving. If anything ever needs to tell those
    # apart again, this is where it goes.
    #
    # Nothing is lost by not keeping: the audio and its text.txt are
    # already in Drive (§60), so an unkept take is still recoverable.
    # What changed is that the notebook holds only what he chose.

    # A NOTE IS OPEN: THE WORDS GO INTO IT, NOT INTO THE BOX.
    #
    # This is the bug Baba reported as "it does not insert what I say to
    # note", and it was mine. v98's comment says the deck is "the note's
    # own record button" — the code never made that true. It wrote to
    # _t1_text as always, and with a note open the box is NOT DRAWN
    # (that is the takeover working), so the words landed on a surface
    # nobody could see. Not lost, just invisible, which is worse: the
    # app looked broken rather than wrong.
    open_id = st.session_state.get(OPEN_KEY)
    if open_id and NOTES.get(st.session_state, open_id):
        NOTES.append(st.session_state, open_id, new_text)
        return

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
        USAGE.log("read", spoken_chars, UNIT_CHARS, talking_engine())

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


# What each pill says. Three letters where two would be cryptic beside
# the rest; the dict rather than code.upper() so the label and the code
# can differ without a second list to keep in step.
LANG_PILL = {"hr": "HR", "en": "ENG", "it": "IT", "de": "DE",
             "fr": "FR", "es": "SPA"}


# ---------------------------------------------------------------------
# THE TR CASSETTE DECK. Baba: "we are missing the cassette deck on the
# TR page — same look as on the read tab. But this one is special: it
# reads TWO text boxes. The upper box takes its language from the upper
# row of the matrix, the lower box from the lower row."
#
# TWO SETTINGS ONLY: female or male. Baba: "user does not choose a voice
# by name, only female or male — we don't want to overburden them, they
# are old people." So the ten Edge voices stay an implementation detail
# and the tab offers one binary choice.
#
# WHOLE TEXT IN ONE PIECE, unlike R. R splits into parts because it
# reads pasted articles; a translation box holds a paragraph. One piece
# means no part-handoff, no prefetch, and no chance of the seam bugs
# that machinery exists to prevent.
# ---------------------------------------------------------------------
TR_DECK_CAP = 4000          # characters. Beyond this the wait is unkind.


def tr_voice_key(lang: str) -> str:
    """Which Edge voice reads `lang`, given the one setting there is."""
    return tk.vkey_for(lang, st.session_state.get("tr_gender", "F"))


def tr_make_audio(text: str, lang: str):
    """(mp3 bytes, seconds) for a whole box, or (None, reason).

    Synthesised block by block and joined, because edge-tts answers per
    utterance. Joining MP3 frames end to end is what the format allows
    and what R already relies on inside a part.
    """
    body = (text or "").strip()
    if not body:
        return None, t("nothing_to_read")
    if len(body) > TR_DECK_CAP:
        body = body[:TR_DECK_CAP]
    vkey = tr_voice_key(lang)
    chunks = []
    total = 0.0
    for block in SPEECH.plan_blocks(tk.sentences_of(body)):
        piece = block if isinstance(block, str) else " ".join(block)
        if not piece.strip():
            continue
        audio, secs = tk.synth_sentence(piece, vkey)
        if audio:
            chunks.append(audio)
            total += float(secs or 0)
    if not chunks:
        return None, t("translate_fail")
    return b"".join(chunks), total


def tr_deck():
    """The deck at the top of TR, and the female/male setting under it.

    ALWAYS DRAWN, loaded or not — the same furniture rule the action
    links follow. A transport that appears only once something is
    playing is a control nobody can find before they need it.
    """
    loaded = st.session_state.get("_tr_audio")
    scale = a11y.clamp(st.session_state.get("text_scale", a11y.DEFAULT_SCALE))
    if _wave_component is not None:
        _wave_component(
            src=("data:audio/mpeg;base64," + _b64.b64encode(loaded).decode()
                 if loaded else ""),
            cues=[], words=[], wtimes=[],
            labels={"play": t("wave_play"), "pause": t("wave_pause"),
                    "back": t("wave_back"), "next": t("wave_next"),
                    "save": t("wave_save")},
            part=1 if loaded else 0, parts=1 if loaded else 0,
            startable=bool(loaded), scale=scale,
            autoplay=bool(st.session_state.pop("_tr_autoplay", False)),
            key="tr_player", default=None)

    # THE ONE SETTING. Two pills, because this is a choice being offered
    # rather than an action being taken — the distinction the file
    # manager's links are the other half of.
    g = str(st.session_state.get("tr_gender", "F")).upper()
    with st.container(key="trgender"):
        gc1, gc2 = st.columns(2)
        gc1.button(t("tr_voice_f"), key="tr_gf",
                   type="primary" if g == "F" else "secondary",
                   on_click=lambda: st.session_state.update({"tr_gender": "F"}),
                   use_container_width=True)
        gc2.button(t("tr_voice_m"), key="tr_gm",
                   type="primary" if g == "M" else "secondary",
                   on_click=lambda: st.session_state.update({"tr_gender": "M"}),
                   use_container_width=True)


def tr_read(which: str):
    """Load one box into the deck and start it.

    `which` is "src" or "out" — and THAT is what decides the language:
    the upper box speaks the upper row's pick, the lower box the lower
    row's. Reading a translation in the language it was translated FROM
    is the mistake this function exists to make impossible.
    """
    if which == "src":
        text = st.session_state.get("translate_src_text", "")
        lang = st.session_state.get("translate_src", "hr")
    else:
        text = st.session_state.get("translate_out", "")
        lang = st.session_state.get("translate_tgt", "en")
    audio, why = tr_make_audio(text, lang)
    if audio is None:
        st.session_state["_tr_error"] = why
        return
    st.session_state["_tr_audio"] = audio
    st.session_state["_tr_autoplay"] = True
    USAGE.log("read", len((text or "").strip()), UNIT_CHARS, "edge")


def lang_pills(prefix: str, which: str, current: str):
    cols = st.columns(len(LANGS_TR))
    for col, code in zip(cols, LANGS_TR):
        col.button(
            LANG_PILL.get(code, code.upper()), key=f"{prefix}_{code}",
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
owner_edge()


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
    # READ THEM BACK BEFORE ANYTHING LOOKS AT THEM. Once per session,
    # and only when memory is empty — see restore_notes for why the
    # guard matters.
    restore_notes()
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

    def lang_now():
        """The language AT THE MOMENT OF USE, never a captured copy.

        Baba, three times over in one message: "After recording, not
        before recording. I cannot emphasize this more."
        
        He is right about the requirement and this is the line that
        guarantees it. `lang_code` used to be read HERE, at the top of
        the module, and used a hundred and thirty lines further down when
        the take arrived. In the ordinary case those are the same render
        and the same value — which is why it looked correct — but the
        value was fixed before the deck was even drawn, so any reasoning
        about "which language was chosen when" had to trace a variable
        across the whole module.
        
        A function instead of a variable makes it unarguable: every
        caller reads the pill as it stands the instant it needs it. If he
        changes HR to ENG while speaking, the take that arrives after
        stop is transcribed as English.
        """
        return st.session_state.get("speech_lang", "hr")

    def append_now():
        """And single/multi at the moment of use, for the same reason.
        
        His words: "If I change to multi during recording, I have my note
        appended. If I say single during recording, it was multi before,
        my note gets deleted and replaced with new one." The mode that
        matters is the one showing when the words arrive.
        """
        return bool(st.session_state.get("append_mode"))

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
        transcribe_note_take()
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
                        flac_path = maybe_trim(to_flac16k(raw))
                    stage["convert_s"] = time.time() - _t0
                    stage["out"] = "16 kHz mono FLAC"
                    stage["out_kb"] = os.path.getsize(flac_path) // 1024
                    stage["mins"] = audio_seconds(flac_path) / 60.0
                    # BOTH PATHS AT ONCE. The audio starts going to Drive
                    # here, and Whisper gets it on the next line. Neither
                    # waits for the other.
                    _keeper = start_keeping(flac_path,
                                            audio_seconds(flac_path), lang_now())
                    _t1 = time.time()
                    # ALWAYS through transcribe_any_size. This path used
                    # to call the provider directly, so a long take or a
                    # big upload died at Groq's 25 MB limit with nothing
                    # to show for it. The module already knows how to cut
                    # a file into ten-minute pieces, feed them one at a
                    # time and stitch the results back into one
                    # transcript, with a marker where a piece failed
                    # rather than a silent hole.
                    # THE STATUS WINDOW BELOW THE RECORDER. A Braille
                    # spinner, the engine in parentheses, and — once
                    # there is enough history — how long this is likely
                    # to take. The spinner advances on each part that
                    # finishes rather than on a timer: Streamlit has no
                    # loop to animate from here, and a frame that moves
                    # when something real happened is worth more than one
                    # that spins while nothing does.
                    _eng = stt.id
                    _audio_s = audio_seconds(flac_path)
                    _eta = eta_seconds(_eng, _audio_s)
                    _eta_txt = (ETA.human(_eta) if _eta is not None
                                else t("eta_learning"))
                    prog = st.progress(0.0, text=braille_line(_eng, 0, _eta_txt))

                    def _cb(done, total):
                        try:
                            prog.progress(
                                min(1.0, done / max(total, 1)),
                                text=braille_line(_eng, done, _eta_txt)
                                + (f" · {done}/{total}" if total > 1 else ""))
                        except Exception:
                            pass

                    text, method, reusable = transcribe_any_size(
                        flac_path, chosen_model(stt.provider) or model_for(lang_now()),
                        lang_now(), progress_cb=_cb)
                    prog.empty()
                    stage["transcribe_s"] = time.time() - _t1
                    # ONE SAMPLE, WRITTEN AFTER THE FACT. Never before
                    # deliver_text and never on the critical path: a
                    # sheet that is slow or gone must cost an estimate,
                    # never a transcript.
                    remember_timing(_eng, _audio_s, stage["transcribe_s"],
                                    parts=int(stage.get("parts") or 1),
                                    ok=bool((text or "").strip()))
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
                        # THE LIST IS STALE THE MOMENT A RECORDING IS
                        # MADE. Baba: "I'm just recording audio and it
                        # doesn't automatically come on the recording
                        # after every record stop."
                        #
                        # `_recs` is fetched once per session, because
                        # the panel redraws on every tick of a checkbox
                        # and a round trip each time would make it
                        # unusable. That was right and it was only half
                        # the rule: the cache was dropped after a DELETE
                        # and never after a STORE, so the newest
                        # recording — the one he had just made and would
                        # most want to see — was the one thing the list
                        # could not show.
                        st.session_state.pop("_recs", None)
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
                            # AND THROW IT AWAY IF THAT IS WHAT HE ASKED
                            # FOR. Baba's setting: keep audio, or delete
                            # it once the words are out.
                            #
                            # The whole recording goes, text and all —
                            # audio_del takes the folder and the row
                            # together, and half a pair is the one thing
                            # §60 exists to prevent. The words are in the
                            # box either way, which is the point: this
                            # setting trades "I can hear it again" for
                            # "my Drive does not fill up".
                            if not st.session_state.get("keep_recordings", True):
                                _st.delete(_rec_id)
                                st.session_state.pop("_recs", None)
                    # And let the recording go: a 7 MB take is ~7 MB of
                    # bytes plus ~9 MB of base64 still held by the
                    # component, which is memory this instance cannot
                    # spare once the words are out.
                    st.session_state.pop(hold_key, None)
                    st.session_state["flac_path"] = reusable
                    st.session_state["last_lang"] = lang_now()
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

                        text = stt.transcribe(tmp.name, lang_now(), progress_cb=_cb)
                        method, reusable = "direct", tmp.name
                    else:
                        def _cb(i, n):
                            progress_bar.progress((i + 1) / n,
                                                  text=f"{t('chunk_progress')} {i + 1}/{n}")

                        def _on_wait(idx, attempt, secs, err):
                            progress_bar.progress(
                                0.5, text=t("chunk_waiting").format(s=secs, i=idx + 1))

                        text, method, reusable = transcribe_any_size(
                            tmp.name,
                            chosen_model(stt.provider) or model_for(lang_now()),
                            lang_now(), progress_cb=_cb, on_wait=_on_wait)
                    progress_bar.empty()
                    # THROUGH deliver_text, like every other route. This
                    # path set the box directly, so an uploaded big file
                    # was never archived and ignored single/multi — the
                    # exact drift the one-helper rule exists to prevent.
                    deliver_text(text)
                    st.session_state["last_lang"] = lang_now()
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

    def _ask_custom():
        st.session_state["_tx_custom_open"] = True

    def _run_custom():
        """Whatever he asked for, done to the text in the box.

        The instruction goes through the SAME transform path as grammar
        and reshape — the only difference is that the words come from
        him instead of from a preset. One implementation, three doors.
        """
        want = str(st.session_state.get("_tx_custom_ask", "")).strip()
        if not want:
            return
        # NO PRESET. Naming one makes _apply_transform fetch that
        # preset's wording from the sheet and then discard it, because
        # an explicit instruction wins. Empty says what is true: there
        # is no preset here, only his words.
        _apply_transform("", want)
        st.session_state["_tx_custom_open"] = False
        st.session_state["_tx_custom_ask"] = ""
        flash("tx_custom")

    # THE TIER DECIDES WHAT IS ON THIS ROW.
    #
    # Baba: "grammar and reshape only in the tier of Studio. We remove
    # this from the free user... they do not pay."
    #
    # And it is not only a price: grammar and reshape send the text to a
    # language model, which on the free tier means Baba's own Groq keys
    # paying for somebody else's rewriting. Transcription is the service;
    # rewriting is the extra.
    #
    # NOT HIDDEN FROM THE OWNER — he is on whatever tier he chose, like
    # everybody else, so he sees exactly what that tier gives.
    _eng = EN.current(st.session_state)
    _studio = bool(_eng and _eng.tier == "studio")

    # COPY AND CLEAR LEFT THIS ROW (v132). They live under the box now,
    # with every other box's copy and clear, so the row holds only what
    # is particular to T: a new take, and the studio tools.
    # THE COMMAND ROW IS GONE FROM T TOO.
    #
    # Baba: "it should appear under the text box, not above, and it is
    # not a button, it is an action link."
    #
    # `new` was the last thing in it, and a bordered row holding one
    # word was the widest, emptiest thing on the screen. Everything T
    # does to its text now sits under the box with copy and clear, in
    # the order they are reached: read what came back, then act on it.
    #
    # The studio tools ride there too — they act on the same text, so
    # they belong in the same place, and the row that used to hold them
    # was a second home for one idea.
    # `new` IS GONE. Baba: "we do not need new — copy copies, clear
    # clears for new transcription, add to notes if it is empty creates
    # a new note. New goes out."
    #
    # He is right that it was two words for one act. `new` cleared the
    # box for a fresh take; `clear` already does that. What `new` also
    # did — start a fresh note — is what `add to notes` now does when
    # the box is empty.
    _extra = []
    if _studio:
        _extra += [(t("grammar_word"), ("tx_grammar", _grammar)),
                   (t("reshape_word"), ("tx_reshape", _reshape)),
                   (t("custom_word"), ("tx_custom", _ask_custom))]

    # CUSTOM: say what you want done, and it is done to the text that is
    # already in the box. Studio only, for the same reason as the other
    # two, and it opens rather than sitting open — a prompt box on a
    # screen that is mostly a recorder would be the loudest thing on it.
    if _studio and st.session_state.get("_tx_custom_open"):
        with st.container(key="customrow"):
            st.text_input(t("custom_word"), key="_tx_custom_ask",
                          placeholder=t("custom_hint"),
                          label_visibility="collapsed")
            _c1, _c2 = st.columns([1, 1])
            _c1.button(t("custom_do"), key="tx_custom_go",
                       type="primary", use_container_width=True,
                       on_click=_run_custom)
            _c2.button(t("custom_cancel"), key="tx_custom_no",
                       use_container_width=True,
                       on_click=lambda: st.session_state.update(
                           {"_tx_custom_open": False}))

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
    # ---- WHAT YOU CAN DO WITH THE TEXT --------------------------
    #
    # copy · clear · add to notes, under the box, as links. The order is
    # the order they are reached: read what came back, then act on it.
    #
    # NO OUTER GUARD. An `if _body:` lived here from v114, when the only
    # thing on this row was "add to notes" and an empty box had nothing
    # to keep. It has outlived that: `add to notes` on an empty box now
    # makes a blank note to speak into, which is what `new` used to do.
    # The guard was invisible from inside box_links and quietly undid
    # the change — the row simply never appeared.
    # WHAT THE TRIM ACTUALLY DID, once, under the box. This is the only
    # setting in the app whose effect is invisible in the result — the
    # words come back the same and only the bill changes — so somebody
    # experimenting with it has nothing to look at unless it says so.
    _tn = st.session_state.pop("_trim_note", None)
    if _tn:
        st.markdown('<div class="readhint">%s</div>' % html.escape(_tn),
                    unsafe_allow_html=True)

    box_links("tx", t1_text(), on_clear=_clear_all,
              extra=_extra + [(t("tx_tonote"),
                               ("tx_tonote", keep_as_note))])
    if st.session_state.pop("_note_kept", None):
        st.caption(t("tx_tonote_done"))

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

    # AND THE RECORDINGS UNDER THEM. Baba moved this here from Settings:
    # a recording is made on this screen and belongs on it. Notes first
    # because they are what somebody came to write; recordings after,
    # because they are what was kept.
    recordings_panel()

    # WRITE THEM IF THEY DIFFER FROM WHAT WAS LAST SAVED.
    #
    # Compared against the SAVED copy, not against what was in memory at
    # the top of this module. My first version did the latter and would
    # have missed every change made by a CALLBACK — add to notes, delete,
    # the title box — because callbacks run BEFORE the script body, so
    # by the time the top of the module read the notebook the change had
    # already happened and there was nothing to notice.
    #
    # Comparing to the saved copy is also cheaper than wrapping all nine
    # places that write a note, and it cannot be forgotten by the tenth.
    persist_notes()

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
    engine = talking_engine()

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
            # A VOICE THAT REFUSES IS A SENTENCE, NEVER A TRACEBACK.
            #
            # Baba photographed edge_tts.exceptions.NoAudioReceived
            # taking the whole app down — a red wall of Python on his
            # phone, on the tab he opened to hear something read.
            #
            # The BACKGROUND worker two functions up already swallows its
            # errors, "so one failed block cannot cancel the others".
            # This is the same call in the foreground and it had no
            # guard at all: the block he is actually waiting for was the
            # one that could kill the run.
            #
            # Edge is free and unauthenticated, so it refuses sometimes
            # for reasons nobody here can control — a rate limit, a bad
            # minute. The honest answer is to say so and leave the app
            # standing, with the studio voices as the way past it.
            try:
                with st.spinner(t("gen_part").format(i=idx + 1, n=len(parts))):
                    cached = _make(idx)
            except Exception as e:
                errlog.add(st.session_state, "read",
                           "the voice could not read this block",
                           "{}: {}".format(type(e).__name__, e))
                st.error(t("read_failed"))
                cached = None
            save_rings()

        # AND IF IT COULD NOT BE BUILT, STOP HERE. Everything below wants
        # audio and marks; without them it would fail again, one line
        # further down, with a less useful message.
        if cached is None:
            # st.stop(), not return: this is module level, not a
            # function. pyflakes caught the `return` immediately, which
            # is exactly what it is for.
            tab_signature(t("sig_read"))
            st.stop()

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

        # "New text" is gone. Baba: "we do not need new text — there is
        # text box." He is right: the box is always there and typing in
        # it is how a new text begins. A button that only cleared the
        # player was a second way to say "I have finished with this
        # one", which the next press of play says by itself.

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
        # THE VOICES FIRST. Baba: "these language buttons go above this
        # wave player, they are at the top." Choosing who reads comes
        # before pressing play, so the screen reads in that order.
        synth_fn = _voice_row(engine, sp_ring_talk)

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


        def _clear_talk():
            st.session_state["talk_text"] = ""
            flash("rd_clear")

        # _keep_text lived here and is gone with the `archive` button it
        # served. It wrote into the OLD archive, which became notes in
        # v98 and is displayed nowhere — a drawer nobody opens. The
        # second copy further down belongs to the reader's own archive
        # panel and is left alone.

        # THE COMMAND ROW IS GONE FROM R. Baba: "archive and clear goes
        # away — it should be only clear, as an action link under the
        # text box."
        #
        # `archive` kept a copy of the text in the OLD archive, which
        # became notes in v98 and is not shown anywhere any more, so the
        # button wrote into a drawer nobody opens. And a bordered row of
        # two commands above the box was heavier than the two words in
        # it deserve.
        #
        # The same shape as T's "add to notes": one quiet link, under
        # the box, where you look after reading what is in it.
        st.text_area(t("tab_talk"), key="talk_text", height=150,
                     label_visibility="collapsed", placeholder=t("talk_placeholder"))
        box_links("rd", st.session_state.get("talk_text", ""),
                  on_clear=_clear_talk)
        # A GREY LINE SAYING WHAT TO DO NEXT. Baba: "in gray letters
        # under the text box put little note — press play to read."
        #
        # The play that starts a reading is the player's own, up at the
        # top, and nothing on this screen said so. A person who pastes
        # text and then looks for a "read" button finds none, because it
        # was deliberately removed (§64) — this is the one line that
        # makes that removal make sense.
        st.markdown('<div class="readhint">%s</div>' % html.escape(t("rd_hint")),
                    unsafe_allow_html=True)

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

    # THE CASSETTE DECK, AT THE TOP, AS ON EVERY OTHER TAB. Baba: "we are
    # missing the cassette deck on the TR page — same logic and same
    # interface on every tab." It was the one tab without a transport,
    # and a hand that has learned where play lives found nothing there.
    tr_deck()
    _tr_err = st.session_state.pop("_tr_error", None)
    if _tr_err:
        st.error(_tr_err)

    def _clear_src():
        st.session_state["translate_src_text"] = ""
        st.session_state["translate_out"] = ""
        flash("tr_src")

    def _do_translate():
        do_translate()
        flash("tr_go")

    st.text_area("src", key="translate_src_text", height=120,
                 label_visibility="collapsed", placeholder=t("translate_src_ph"))
    box_links("trsrc", st.session_state.get("translate_src_text", ""),
              on_clear=_clear_src)
    # READ, UNDER THE BOX IT READS. The upper box speaks the UPPER row's
    # language — that pairing is the whole point of two rows and two
    # boxes, and getting it backwards would read a translation in the
    # language it came from.
    with st.container(key="nact_trsrc"):
        st.button(t("tr_read_src"), key="nact_read_trsrc",
                  disabled=not (st.session_state.get("translate_src_text")
                                or "").strip(),
                  on_click=tr_read, args=("src",))

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

    st.text_area("out", key="translate_out", height=150,
                 label_visibility="collapsed", placeholder=t("translate_out_ph"))
    box_links("trout", st.session_state.get("translate_out", ""),
              on_clear=_clear_out)
    with st.container(key="nact_trout"):
        st.button(t("tr_read_src"), key="nact_read_trout",
                  disabled=not (st.session_state.get("translate_out")
                                or "").strip(),
                  on_click=tr_read, args=("out",))

    tab_signature(t("sig_translate"))


elif active == "vr":
    # VR — VIRTUAL REHEARSAL. Baba: "this one is to experiment with human
    # emotions. Pills for each emotion, a deck that reads, a box to paste
    # into. Many voices — one pill per voice. We don't save on pills."
    #
    # THE SAME SHAPE AS EVERY OTHER TAB: transport at the top, the thing
    # you are working on under it, actions under that. A fourth tab that
    # invented its own arrangement would be a fourth thing to learn.
    st.session_state.setdefault("vr_voice", VR.DEFAULT_VOICE)
    st.session_state.setdefault("vr_text", "")

    _vr_audio = st.session_state.get("_vr_audio")
    if _wave_component is not None:
        _wave_component(
            src=("data:audio/wav;base64," + _b64.b64encode(_vr_audio).decode()
                 if _vr_audio else ""),
            cues=[], words=[], wtimes=[],
            labels={"play": t("wave_play"), "pause": t("wave_pause"),
                    "back": t("wave_back"), "next": t("wave_next"),
                    "save": t("wave_save")},
            part=1 if _vr_audio else 0, parts=1 if _vr_audio else 0,
            startable=bool(_vr_audio),
            scale=a11y.clamp(st.session_state.get("text_scale",
                                                 a11y.DEFAULT_SCALE)),
            autoplay=bool(st.session_state.pop("_vr_autoplay", False)),
            key="vr_player", default=None)

    _vr_err = st.session_state.pop("_vr_error", None)
    if _vr_err:
        st.error(_vr_err)
    _vr_said = st.session_state.pop("_vr_said", None)
    if _vr_said:
        st.caption(t("vr_now") % _vr_said)

    st.text_area("vr", key="vr_text", height=120,
                 label_visibility="collapsed", placeholder=t("vr_text_ph"))

    def _vr_clear():
        st.session_state["vr_text"] = ""

    box_links("vrbox", st.session_state.get("vr_text", ""), on_clear=_vr_clear)

    # THE CAST. One pill per voice, twelve women and twelve men, each
    # showing its accent so a name that means nothing still tells you
    # something. Baba asked for many and this is many on purpose.
    st.markdown('<div class="vtag">%s</div>' % html.escape(t("vr_voices")),
                unsafe_allow_html=True)
    _cur_voice = st.session_state.get("vr_voice", VR.DEFAULT_VOICE)
    for _g in ("F", "M"):
        _rows = VR.VOICES[_g]
        for _start in range(0, len(_rows), 3):
            _cols = st.columns(3)
            for _col, (_vn, _acc, _age) in zip(_cols, _rows[_start:_start + 3]):
                _col.button(
                    _vn, key="vrv_%s" % _vn.replace(" ", "_").replace("'", ""),
                    type="primary" if _vn == _cur_voice else "secondary",
                    help="%s · %s" % (_acc, _age),
                    on_click=lambda v=_vn: st.session_state.update(
                        {"vr_voice": v}),
                    use_container_width=True)

    # THE DIRECTION. Checkboxes, not one choice: Baba asked for "one
    # emotion or a combination", and that is also what acting is — grief
    # that is angry reads differently from either alone.
    st.markdown('<div class="vtag">%s</div>' % html.escape(t("vr_emotions")),
                unsafe_allow_html=True)
    for _start in range(0, len(VR.EMOTIONS), 3):
        _cols = st.columns(3)
        for _col, (_eid, _lbl, _phr) in zip(_cols,
                                            VR.EMOTIONS[_start:_start + 3]):
            _col.checkbox(_lbl, key="vre_%s" % _eid, help=_phr)

    _picked = [e for e in VR.EMOTION_IDS if st.session_state.get("vre_%s" % e)]
    if len(_picked) > VR.MAX_EMOTIONS:
        st.caption(t("vr_too_many"))

    st.text_input("vrnote", key="vr_note", placeholder=t("vr_note_ph"),
                  label_visibility="collapsed")

    # THE PACE, STATED IN SECONDS. Baba: "if I need to wait 30 seconds
    # between two reads, no problem — just write, please wait, Hume AI is
    # drinking coffee." Measured in his own brief: 3s is refused, 12s
    # holds. So the button is disabled and says how long, rather than
    # firing into a 429 and blaming the person.
    _left = VR.wait_left(st.session_state.get("_vr_last_at"), time.time())
    _has = bool((st.session_state.get("vr_text") or "").strip())

    def _vr_go():
        raw = (st.session_state.get("vr_text") or "").strip()
        if not raw:
            st.session_state["_vr_error"] = t("vr_nothing")
            return
        if VR.wait_left(st.session_state.get("_vr_last_at"), time.time()):
            return          # the button was disabled; belt and braces
        picked = [e for e in VR.EMOTION_IDS
                  if st.session_state.get("vre_%s" % e)]
        direction = VR.build_direction(picked, st.session_state.get("vr_note", ""))
        ring = get_ring("hume")
        # STAMPED BEFORE THE CALL, not after. A call that takes 20
        # seconds and is stamped afterwards lets the next press come 12
        # seconds after it FINISHED, which is 32 seconds of real spacing
        # — slower than asked. Stamping first paces the REQUESTS.
        st.session_state["_vr_last_at"] = time.time()
        got, err = hume_speak(ring, raw, st.session_state.get(
            "vr_voice", VR.DEFAULT_VOICE), direction)
        save_rings()
        if err:
            st.session_state["_vr_error"] = err
            return
        audio, secs = got
        st.session_state["_vr_audio"] = audio
        st.session_state["_vr_autoplay"] = True
        st.session_state["_vr_said"] = VR.summarise(picked)
        USAGE.log("read", len(raw), UNIT_CHARS, "hume")

    with st.container(key="nact_vr"):
        st.button(t("vr_coffee") % _left if _left else t("vr_speak"),
                  key="nact_vr_go", disabled=bool(_left) or not _has,
                  on_click=_vr_go)

    tab_signature(t("sig_vr"))


elif active == "looks":
    # QUICK SETTINGS FIRST. Baba: "at the top of the settings." The
    # things changed in the middle of working, above the things set once.
    quick_settings()

    # HOW THE APP LOOKS — everyone gets this. Size, typeface, colour.
    # Deliberately separate from engines and keys: what a person sees is
    # theirs to set, what the app talks to is the owner's.
    # EACH SETTING IN ITS OWN FRAME. Baba: "visually group different
    # settings so we know they belong to different groups — put the
    # frame, the visual language from the rest of the interface."
    #
    # Three rows of pills with a word above each read as one long list
    # of eighteen buttons. The same fill the deck and the note sit in
    # says "these belong together" without another colour or another
    # line.
    # TEXT SIZE IS A NUMBER YOU TYPE. Baba: "add entry box, user can
    # enter any size... and then put default action link there."
    #
    # Eight pills covered 80 to 185 in fixed steps and could not reach
    # 200 or 250, which are the sizes WCAG actually asks about. A box
    # takes any of them.
    #
    # THE DEFAULT IS 100, NOT 80. 80 is the SMALLEST the app allows —
    # it looked like the default only because it is the first pill and
    # the one Baba had chosen. Making the smallest text the default in
    # an app built for people who cannot see well would be exactly
    # backwards.
    with st.container(key="looksgroup_size"):
        _sl, _sb, _sd, _il, _ib = st.columns([1.15, 0.85, 0.8, 1.25, 0.8])
        _sl.markdown('<div class="setlabel">%s</div>' % html.escape(
            t("looks_size")), unsafe_allow_html=True)
        _now_pct = int(round(a11y.clamp(st.session_state.get(
            "text_scale", a11y.DEFAULT_SCALE)) * 100))

        def _size_typed():
            raw = st.session_state.get("_size_pct", _now_pct)
            try:
                st.session_state["text_scale"] = a11y.clamp(float(raw) / 100.0)
            except (TypeError, ValueError):
                pass
            persist_settings()

        def _size_default():
            st.session_state["text_scale"] = a11y.DEFAULT_SCALE
            st.session_state["_size_pct"] = int(a11y.DEFAULT_SCALE * 100)
            persist_settings()

        _sb.number_input(
            t("looks_size"), key="_size_pct", value=_now_pct,
            min_value=int(a11y.MIN_SCALE * 100),
            max_value=int(a11y.MAX_SCALE * 100), step=5,
            label_visibility="collapsed", on_change=_size_typed)
        _sd.button(t("looks_default"), key="size_default",
                   on_click=_size_default, use_container_width=True)

        # INTERFACE SIZE, on the same line. Baba: "text size affects only
        # text — add another property in the same line, interface size,
        # so the whole interface can be shrunk or enlarged."
        #
        # TWO DIFFERENT THINGS, DELIBERATELY SEPARATE. Text size is for
        # somebody who can see the app but not read the transcript;
        # interface size is for somebody who finds the whole thing too
        # small, or wants more of it on the screen at once. One control
        # doing both would force a compromise on both.
        _iface = int(round(float(st.session_state.get("ui_scale", 1.0)) * 100))

        def _iface_typed():
            raw = st.session_state.get("_iface_pct", _iface)
            try:
                st.session_state["ui_scale"] = max(0.5, min(float(raw) / 100.0, 2.0))
            except (TypeError, ValueError):
                pass
            persist_settings()

        _il.markdown('<div class="setlabel">%s</div>' % html.escape(
            t("looks_iface")), unsafe_allow_html=True)
        _ib.number_input(
            t("looks_iface"), key="_iface_pct", value=_iface,
            min_value=50, max_value=200, step=5,
            label_visibility="collapsed", on_change=_iface_typed)

    # LABEL ON THE LINE, like the interface language. Above the buttons
    # it was a row for one word, and under this screen's spacing it kept
    # touching them.
    with st.container(key="looksgroup_font"):
        _fl, f1, f2, f3 = st.columns([1.3, 1, 1, 1])
        _fl.markdown('<div class="setlabel">%s</div>' % html.escape(
            t("looks_font")), unsafe_allow_html=True)
        fcols = [f1, f2, f3]
        for col, (fid, label) in zip(fcols, [("mono", "mono"), ("sans", "sans"),
                                             ("serif", "serif")]):
            def _pick_font(f=fid):
                st.session_state["font_family"] = f
                persist_settings()
            col.button(label, key=f"font_{fid}", use_container_width=True,
                       type="primary" if st.session_state.get("font_family", "mono") == fid
                       else "secondary", on_click=_pick_font)

    with st.container(key="looksgroup_scheme"):
        _cl, k1, k2, k3, k4 = st.columns([1.3, 1, 1, 1, 1])
        _cl.markdown('<div class="setlabel">%s</div>' % html.escape(
            t("looks_scheme")), unsafe_allow_html=True)
        scols = [k1, k2, k3, k4]
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

    # THE INTERFACE LANGUAGE BELONGS HERE, not in the owner's panel.
    #
    # It was moved into the amber gear in v90 and then removed in v91 on
    # the reasoning that the interface would simply be English. That was
    # wrong for the people this app is FOR — Baba: "this is for the
    # users, my grandfather and mother, they do not speak English."
    #
    # It is a personal setting, like text size, so it sits in the grey
    # gear where a person can reach their own things. The owner's panel
    # keeps engines and keys.
    # A LABEL LIKE THE OTHERS ON THIS SCREEN. Baba: "interface language
    # is behind the buttons and it is not reading nicely — should not be
    # bold, thin letters, save the space."
    #
    # st.caption is bold-ish and carries its own margins, and under the
    # tight spacing here it printed THROUGH the buttons under it — the
    # same collision as the engine test result, one screen over. TXT, TY
    # and C above it are already thin dim marks; this is now one of them.
    # THE LABEL SITS ON THE SAME LINE AS THE PILLS. Baba: "check the
    # overlapping text, interface language — you can put interface
    # language HR ENG in one line, not in two lines."
    #
    # Above them it was a whole row for two words, and under this
    # screen's tight spacing it kept colliding with what came next. On
    # the line it costs nothing and cannot overlap anything.
    with st.container(key="uilangrow"):
        _llab, _lc1, _lc2, _ = st.columns([1.6, 0.8, 0.8, 1.4])
        _llab.markdown('<div class="setlabel">%s</div>' % html.escape(
            t("settings_lang")), unsafe_allow_html=True)
    _lang_now = st.session_state.get("ui_lang", "en")
    _lc1.button("HR", key="ui_hr",
                type="primary" if _lang_now == "hr" else "secondary",
                on_click=set_ui_lang, args=("hr",),
                use_container_width=True)
    _lc2.button("ENG", key="ui_en",
                type="primary" if _lang_now == "en" else "secondary",
                on_click=set_ui_lang, args=("en",),
                use_container_width=True)

    # LOG OUT IS UNCONDITIONAL. Whatever got you in — a password, a
    # remembered token, the emergency door — must have a way out, or a
    # shared phone cannot be handed over. It is the one control on this
    # page that must never be hidden by a condition.
    st.button(t("log_out"), key="log_out_btn", on_click=log_out,
              use_container_width=True)


    # ---- YOUR OWN ASSEMBLYAI KEY --------------------------------------
    assemblyai_panel()

    # ---- YOUR OWN SPEECHIFY KEY ---------------------------------------
    speechify_panel()

    # ---- SILENCE ------------------------------------------------------
    #
    # Baba asked for this as something to "choose and experiment with",
    # which is exactly right for a feature whose effect you cannot see in
    # the transcript — the words come back the same and only the bill is
    # different.
    st.markdown('<div class="setlabel">%s</div>' % html.escape(
        t("trim_label")), unsafe_allow_html=True)

    def _set_trim():
        st.session_state["trim_silence"] = bool(
            st.session_state.get("_trim_pick"))
        persist_settings()

    st.toggle(" ", key="_trim_pick",
              value=bool(st.session_state.get("trim_silence")),
              label_visibility="collapsed", on_change=_set_trim)
    st.markdown('<div class="readhint">%s</div>' % html.escape(
        t("trim_why_on") if st.session_state.get("trim_silence")
        else t("trim_why_off")), unsafe_allow_html=True)

    # ---- WHAT HAPPENS TO THE AUDIO -----------------------------------
    #
    # THE SETTING STAYS IN SETTINGS, and the FILES moved to T. That is
    # the line between the two screens: this is a standing choice about
    # how the app behaves, made once; the recordings are things you go
    # through. Moving the panel to T was right and moving this with it
    # would not have been.
    if drive_store().enabled:
        st.markdown('<div class="setlabel">%s</div>' % html.escape(
            t("rec_keep_label")), unsafe_allow_html=True)

        _keep_now = bool(st.session_state.get("keep_recordings", True))

        def _set_keep():
            st.session_state["keep_recordings"] = (
                st.session_state.get("_keep_pick") == t("rec_keep"))
            persist_settings()

        # A SPACE FOR THE LABEL, not the label again. Baba's screenshot
        # shows "AFTER TRANSCRIBING" twice: once as the heading above and
        # once from the radio itself, because label_visibility="collapsed"
        # hides a label from SIGHT and Streamlit renders it anyway. The
        # same fault as the recordings heading in v156, in the same file,
        # two hundred lines apart.
        st.radio(" ", [t("rec_keep"), t("rec_bin")],
                 index=0 if _keep_now else 1, key="_keep_pick",
                 horizontal=True, label_visibility="collapsed",
                 on_change=_set_keep)
        # SAY WHAT THE CHOICE COSTS. "Delete automatically" sounds like
        # tidiness and is actually a decision about whether these words
        # can ever be recovered.
        st.markdown('<div class="readhint">%s</div>' % html.escape(
            t("rec_keep_why") if _keep_now else t("rec_bin_why")),
            unsafe_allow_html=True)

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
        # THE WHOLE MODULE IS THE OWNER'S, so the whole module is dense.
        # It was only the People half at first, which left round pills
        # above square ones on one screen — worse than either.
        admin_dense()
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
            # TEST SITS WITH THE ENGINES. Baba: "put test next to the
            # engines in one line, so we do not have this hanging
            # button or orphan button." It acts on whichever engine is
            # chosen, so it belongs beside them rather than underneath.
            elab, ecol1, ecol2, ecol3 = st.columns([0.9, 2.0, 2.6, 0.9])
            elab.text(t("settings_engine"))
            _now = engine_now()
            _now_id = _now.id if _now else ""
            for col, eng in zip((ecol1, ecol2), EN.ENGINES):
                col.button(eng.label, key="eng_%s" % eng.id,
                           type="primary" if eng.id == _now_id else "secondary",
                           help=eng.note,
                           on_click=pick_engine, args=(eng.id,),
                           use_container_width=True)
            ecol3.button(t("eng_check"), key="eng_check",
                         on_click=run_engine_check, use_container_width=True)

            # Did the global save land? A global setting that quietly
            # did not save is worse than one that never claimed to.
            if "_engine_saved" in st.session_state:
                st.caption(t("eng_saved") if st.session_state["_engine_saved"]
                           else t("eng_notsaved"))



            _res = st.session_state.get("_engine_check")
            if _res:
                # A verdict about a DIFFERENT engine is worse than none —
                # it is read as applying to the one on screen.
                if _res.get("engine") != _now_id:
                    st.caption(t("eng_stale"))
                else:
                    # ONE BLOCK, NOT A CAPTION AND THEN LINES.
                    #
                    # The verdict was an st.caption and the parts were
                    # st.text, and under this panel's tight spacing the
                    # two OVERLAPPED — "all parts answered" printed
                    # across the line beneath it. Baba: "it is really
                    # not clear what this is."
                    #
                    # A single code block cannot overlap itself, lines
                    # up in a column, and is the same shape as the
                    # people table above it.
                    _bad = _res.get("state") == EN.FAIL
                    _lines = ["%s %s   %s" % (
                        "✗" if _bad else "✓",
                        t("eng_bad") if _bad else t("eng_good"),
                        _res.get("at", ""))]
                    for _row in _res.get("rows", []):
                        _p = PROVIDERS.get(_row["provider"])
                        _name = getattr(_p, "label", None) or _row["provider"]
                        _jobs = ", ".join(
                            t("eng_task_" + j) for j in
                            EN.tasks_for(EN.get(_now_id), _row["provider"])
                        ) if _now_id else ""
                        _mark = {EN.OK: "✓", EN.FAIL: "✗", EN.SKIP: "–"}.get(
                            _row["state"], "?")
                        _lines.append("  %s %-10s %-22s %s" % (
                            _mark, _name, _jobs, _row.get("detail", "")))
                    st.code("\n".join(_lines), language=None)

            # ---- ONE ENGINE PER PERSON ----------------------------
            # The keyed container is what admin_dense() styles. Nothing
            # outside it changes, which is how the exception to rule 6
            # stays scoped to the one screen it belongs on.
            st.text(t("adm_title"))
            user_admin_panel()

        # Help lived here as an expander AND as its own module. Two copies
        # of the same text drift apart, and the module is the one people
        # find. Removed rather than kept in sync.

    tab_signature("")
