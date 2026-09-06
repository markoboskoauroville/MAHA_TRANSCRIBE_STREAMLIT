"""THE ENGINE TOGGLE — one press, the whole engine, on every tab.

    python3 tests/test_engine_toggle.py

Baba, 6.9.2026: "I want to be able to give free users ability to change
engines. So on all the tabs they have access to, put one toggle, engine 1
or engine 2, so they can try both and see what works better."
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from streamlit.testing.v1 import AppTest        # noqa: E402

from ttt import engines as EN                   # noqa: E402
from ttt import providers as P                  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RAW = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
# COMMENTS STRIPPED. Face 2: a check that greps raw source matches its
# own explanation and passes for ever. Every comment above is ABOUT this
# feature and names every string this suite looks for.
def code_only(src: str) -> str:
    """Comments AND docstrings gone.

    Face 2, and I walked into it writing this suite: _engine_switch's own
    docstring says the words "Gemini" and "Edge" appear in engines.py and
    not here — so a check greping for those vendors matched my
    explanation of why they are absent. Stripping only "#" lines is not
    enough in Python, where most prose lives in triple quotes.
    """
    body = "\n".join(l for l in src.splitlines()
                     if not l.lstrip().startswith("#"))
    body = re.sub(r'(?<!["\'])#.*$', "", body, flags=re.M)
    return re.sub(r'"""(?:.|\n)*?"""', "", body)


CODE = code_only(RAW)

GLYPH = "\u21c4"

# =====================================================================
print("1 THE MECHANISM, ALONE")
# =====================================================================

free = EN.for_tier("free")
check("two free engines today", len(free) == 2, [e.id for e in free])
check("they are the free-tier ones, read off the data",
      {e.id for e in free} == {"normal", "google"}, [e.id for e in free])
check("every one of them really declares tier free",
      all(e.tier == "free" for e in free))
check("studio is not in the free set",
      "studio" not in {e.id for e in free})
check("for_tier reads the tier and does not hold a list",
      EN.for_tier("studio") == [EN.get("studio")])
check("an unknown tier gives nothing, rather than everything",
      EN.for_tier("nonsense") == [])

check("normal flips to google", EN.next_in(free, "normal").id == "google")
check("google flips back to normal", EN.next_in(free, "google").id == "normal")
check("it is a CYCLE, so two presses return to the start",
      EN.next_in(free, EN.next_in(free, "normal").id).id == "normal")
check("a board on no known engine goes to the first",
      EN.next_in(free, "").id == free[0].id)
check("an unknown id goes to the first rather than raising",
      EN.next_in(free, "nonsense").id == free[0].id)
check("ONE engine has nowhere to go — this is what greys the button",
      EN.next_in(free[:1], "normal") is None)
check("no engines has nowhere to go either", EN.next_in([], "x") is None)

# A THIRD FREE ENGINE MUST APPEAR WITHOUT ANY CODE CHANGING. This is the
# whole reason for_tier derives instead of listing.
third = EN.Engine("pretend", "Pretend", {"stt": "groq", "tts": "edge",
                                         "llm": "groq"}, tier="free")
trio = free + [third]
check("a third free engine joins the cycle by existing",
      EN.next_in(trio, "google").id == "pretend"
      and EN.next_in(trio, "pretend").id == "normal",
      [e.id for e in trio])
check("...and every engine in a trio is reachable",
      {EN.next_in(trio, e.id).id for e in trio} == {e.id for e in trio})

# ROUTES, NOT A NAME. What the button writes has to be what the corner
# reads back, or the label lies about what is running.
for e in free:
    rs = EN.route_settings(e)
    check("choosing %s writes all three routes" % e.id, len(rs) == 3, rs)
    check("...and current() reads %s back out of them" % e.id,
          EN.current(rs) is e, EN.current(rs))

# =====================================================================
print()
print("2 THE REAL THING — the app, rendered")
# =====================================================================

# THE SAME DOOR-BYPASS EVERY OTHER AppTest SUITE USES. Not a shortcut
# past the login: the login has its own suite (test_door), and driving it
# again here would make this test fail for reasons that have nothing to
# do with an engine toggle.
def sget(at, key, default=None):
    """AppTest's session_state is not a dict — no .get(), and a missing
    key raises. Every other AppTest suite here carries this helper."""
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def app(tab="talk"):
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=90)
    at.session_state["_authed"] = True
    at.session_state["_user"] = "stub"
    # "active_tab", NOT "active". app.py reads
    #     active = st.session_state.get("active_tab") or "transcribe"
    # so setting "active" set a key nothing reads, every tab fell
    # through to the default, and this loop tested ONE tab six times
    # while reporting six passes. It was committed that way.
    at.session_state["active_tab"] = tab
    return at


at = app()
at.run()
keys = [b.key for b in at.button]
check("the app renders without raising", not at.exception, at.exception)
check("the toggle is ON THE PAGE, by key", "eng_flip" in keys, keys[:12])

btn = [b for b in at.button if b.key == "eng_flip"]
if btn:
    b = btn[0]
    # IT IS A LINK NOW, NOT A GLYPH-ONLY BUTTON. Baba, 6.9.2026: "For
    # switching engine, put also an action link." The glyph rides with
    # the words: alone at the foot of a page it was a puzzle, and the
    # words alone lose the mark he has already learned.
    check("it wears the glyph", b.label.startswith(GLYPH), b.label)
    check("...and says in words what it will do",
          len(b.label) > len(GLYPH) + 3, b.label)
    check("it carries help text saying what it will do", bool(b.help), b.help)
    # NOT READY, AND SAYING SO. This clone has placeholder Google keys in
    # secrets, so the target engine is offered and cannot work — and the
    # button must be dead and must explain itself rather than silently
    # failing over route by route.
    check("with placeholder keys it is disabled rather than lying",
          b.disabled is True, b.disabled)
    check("...and the help names WHICH engine is not ready",
          "Gemini" in (b.help or ""), b.help)
else:
    check("it wears the glyph", False, "no eng_flip button")

# "ON ALL THE TABS THEY HAVE ACCESS TO" — his words, so every tab is
# rendered and asked, not just one. This is the check that would catch a
# tab whose body returns early and never reaches tab_signature.
for tab in ("transcribe", "talk", "translate", "vr", "looks", "help"):
    a = app(tab)
    a.run()
    found = [b for b in a.button if b.key == "eng_flip"]
    check("tab %-10s renders without raising" % tab, not a.exception,
          a.exception)
    check("tab %-10s carries the toggle" % tab, len(found) == 1,
          [b.key for b in a.button][:10])

# =====================================================================
print()
print("3 THE UGLY CASES")
# =====================================================================

check("the glyph is not a letter or a digit", not GLYPH.isalnum())

blk = re.search(r"^SYM = \{.*?^\}", CODE, re.S | re.M)
check("the SYM table is found", blk is not None)
glyphs = re.findall(r'"[a-z]+":\s*"(\\u[0-9a-f]{4})"', blk.group(0) if blk else "")
check("SYM holds nine glyphs", len(glyphs) == 9, len(glyphs))
# UNIQUENESS IS NOT COSMETIC. The aria injector matches BY GLYPH, so a
# duplicate makes a screen reader announce two buttons with one name.
# It already happened: translate borrowed the play triangle and was
# announced as "Read".
check("EVERY SYM GLYPH IS UNIQUE — the aria injector matches on them",
      len(set(glyphs)) == len(glyphs),
      [g for g in glyphs if glyphs.count(g) > 1])
check("the switch glyph is in SYM", "\\u21c4" in glyphs, glyphs)
check("the switch is given a spoken name for assistive technology",
      'SYM["engine"]: t("eng_switch")' in CODE)

# NOTHING APPEARS, NOTHING DISAPPEARS. The failure this guards is a
# button rendered only when it is usable, which moves the page.
# THE CONTROL MOVED into _foot_links when it became an action link, so
# the region these checks read moves with it. A check left pointing at
# a function that no longer exists reads as a failure of the feature
# rather than of the check — and one pointing at a function that no
# longer DECIDES anything is worse, because it stays green.
sw = CODE[CODE.find("def _foot_links"):]
sw = sw[:sw.find("\ndef ", 10)] if "\ndef " in sw[10:] else sw
check("the switch region was found and is a sensible size (%d chars)"
      % len(sw), 400 < len(sw) < 4000, len(sw))
# TWO BUTTONS NOW: the engine link and the way out. Both rendered
# unconditionally — nothing appears, nothing disappears.
check("both footer links are rendered UNCONDITIONALLY",
      sw.count("st.button(") == 2, sw.count("st.button("))
check("it is greyed with disabled=, not hidden",
      "disabled=not ready" in sw, sw[-200:])
check("every path sets a reason, so a dead link always explains itself",
      sw.count("why, label = ") == 3, sw.count("why, label = "))

# §0 RULE 2 — the tab must not know a vendor.
for vendor in ("gemini", "edge", "speechify", "groq", "hume", "anthropic",
               "assemblyai"):
    check("the switch does not name %r" % vendor, vendor not in sw.lower())

# THE FLIP CLEARS THE OLD VERDICT. A tick belongs to the engine that
# earned it; carried over, it puts a ✓ beside something never tested.
check("flipping forgets the previous engine check",
      '_engine_check' in sw and 'pop("_engine_check"' in sw)
check("the flip writes ROUTES, not just a name",
      "EN.route_settings(nxt)" in sw)
check("...and the name too, so both views agree",
      "EN.SETTING_KEY] = nxt.id" in sw)

# GOOGLE'S KEYS ACTUALLY REACH THE PROVIDER. Without this the toggle is
# a pill that can never light: google_keys() read the secret and nothing
# handed it on.
check("the app hands Google's keys to the registry",
      "PROVIDERS.set_google_keys(" in CODE)
check("the registry knows how to receive them",
      hasattr(P, "set_google_keys"))
check("usability for google asks the APP's keys, not a person's ring",
      'if provider.id == "google":' in CODE and "bool(GOOGLE_KEYS)" in CODE)

P.set_google_keys([])
check("no keys means the provider holds none", P.get("google").keys == [])
P.set_google_keys(["AQ.a", "AQ.b"])
check("keys arrive intact and uncounted-on", P.get("google").keys ==
      ["AQ.a", "AQ.b"])
P.set_google_keys(None)
check("None is not a crash", P.get("google").keys == [])

# =====================================================================
print()
print("4 THE UPGRADE — somebody who already had the old version")
# =====================================================================

check("the free engine is still the default", EN.DEFAULT == "normal")
check("a session that never touched an engine still reads as normal",
      EN.current({}) is EN.get("normal"), EN.current({}))
check("the old 'free' id still resolves", EN.get("free") is EN.get("normal"))

# A STUDIO USER LOSES NOTHING AND GAINS NO SURPRISE. One engine in the
# tier, so the button is present and dead — the same furniture, greyed.
check("studio has one engine, so its toggle is dead by construction",
      EN.next_in(EN.for_tier("studio"), "studio") is None)
check("studio's routes are untouched",
      EN.get("studio").routes == {"stt": "assemblyai", "tts": "speechify",
                                  "llm": "anthropic"})

# A HALF-PATCHED BOARD IS NOT A DEAD END. Somebody who patched one
# crosspoint by hand must still have a way back to a whole engine.
mixed = {"route_stt": "google", "route_tts": "edge", "route_llm": "google"}
check("a mixed board reads as mixed", EN.current(mixed) is None)
check("...and is offered the free set as the way back",
      EN.next_in(EN.for_tier("free"), "") is not None)

check("three engines, no more and no fewer", len(EN.ENGINES) == 3,
      [e.id for e in EN.ENGINES])
check("adding the toggle did not change any engine's routes",
      [e.routes for e in EN.ENGINES] ==
      [{"stt": "groq", "tts": "edge", "llm": "groq"},
       {"stt": "assemblyai", "tts": "speechify", "llm": "anthropic"},
       {"stt": "google", "tts": "google", "llm": "google"}])



print()
print("5 THE FOOT OF THE PAGE — where am I, and the way out")
# =====================================================================

for tab in ("transcribe", "talk", "translate", "vr", "looks", "help",
            "settings"):
    a = app(tab)
    a.run()
    md = " ".join(m.value for m in a.markdown)
    keys = [b.key for b in a.button]
    check("tab %-10s asks 'Where am I?'" % tab, "Where am I?" in md)
    check("tab %-10s offers the way out" % tab, "foot_logout" in keys,
          keys[:8])
    check("tab %-10s offers the engine link" % tab, "eng_flip" in keys)
    check("tab %-10s renders without raising" % tab, not a.exception,
          a.exception)

# ONE CONTROL, NOT TWO. The glyph-only button it replaced is gone; two
# implementations of one control are two places to drift.
check("the old glyph-only switch is gone", "def _engine_switch" not in CODE)
check("there is exactly one engine control", CODE.count('key="eng_flip"') == 1,
      CODE.count('key="eng_flip"'))

# THE LINK LOOK IS THE EXISTING ONE. The container key begins
# "boxlinks_", which the stylesheet already turns into right-aligned
# dim underlined text that follows the reader's size dial. No second
# stylesheet to drift from the first.
check("the footer reuses the action-link container",
      'key="boxlinks_foot"' in CODE)

print()
print("6 LOGGING OUT LEAVES NOTHING BEHIND")
# =====================================================================
#
# This app is shared with his family on one phone. Clearing the
# credential alone would leave the transcript, the reader's text, the
# notes and the key rings sitting behind a fresh login screen.
# log_out_btn has been listed as a MISSING FEATURE since v237.

at = app("talk")
at.run()
at.session_state["talk_text"] = "private text"
at.session_state["_t1_text"] = "a transcript"
at.session_state["_rings"] = {"hume": {"keys": [{"key": "SECRET"}], "active": 0}}
at.session_state["text_scale"] = 1.4
at.session_state["ui_lang"] = "hr"
at.run()
check("the work is there before logging out",
      sget(at, "talk_text") == "private text")

at.button(key="foot_logout").click().run()
check("the credential is gone", sget(at, "_authed") is None)
check("the name is gone", sget(at, "_user") is None)
check("THE READER'S TEXT IS GONE — the next person must not read it",
      sget(at, "talk_text") is None, sget(at, "talk_text"))
check("the transcript is gone", sget(at, "_t1_text") is None)
check("THE KEY RINGS ARE GONE", not sget(at, "_rings"), sget(at, "_rings"))

# BUT HOW THE SCREEN IS SET UP SURVIVES. Logging out is not a reason to
# make somebody with low vision find the text-size dial again.
check("the reading size survives", sget(at, "text_scale") == 1.4,
      sget(at, "text_scale"))
check("the language survives", sget(at, "ui_lang") == "hr",
      sget(at, "ui_lang"))
check("logging out does not raise", not at.exception, at.exception)

# AN ALLOWLIST, NOT A REMOVE-LIST. A remove-list is the one that goes
# stale: every feature added after it stores something new and nobody
# remembers to add it.
check("what survives is an allowlist", "KEEP_ON_LOGOUT" in CODE)
check("...and it is short", len(re.findall(r'"\w+"', CODE.split(
      "KEEP_ON_LOGOUT = (")[1].split(")")[0])) <= 6)
check("the loop removes everything NOT on it",
      "if key not in KEEP_ON_LOGOUT" in CODE)

# THE REMEMBER-ME TOKEN. Asserted on the source: the localStorage bridge
# consumes _pending_ls on the very next render, so by the time an
# AppTest can look, it has already been cleared — the observable proof
# lives in a browser and this is the honest substitute.
_lo = CODE.split("def log_out")[1].split("\ndef ")[0]
check("the log-out region was found (%d chars)" % len(_lo),
      60 < len(_lo) < 900, len(_lo))
check("logging out also drops the remembered login, or the next run "
      "walks straight back in",
      "queue_ls(removes=[AUTH_LS_KEY])" in _lo, _lo)

print()
print("%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
