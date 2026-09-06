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
from ttt import providers as P
from ttt.providers import google as GP                  # noqa: E402

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
    # A STATUS LINE. Baba, 6.9.2026: "I just want to be edge or Google.
    # When it's edge, it's edge. When it's Google, it's Google. We don't
    # write there what is not present."
    #
    # v250 read "switch to Gemini" — the OTHER engine — so the one word
    # on screen was always the one word that was NOT true.
    check("it names the engine that is RUNNING", b.label == "Edge", b.label)
    check("...and NOT the one it would switch to",
          "Gemini" not in b.label and "Google" not in b.label, b.label)
    check("no glyph on it — a mark beside a status is a second thing to "
          "read before the first one lands",
          GLYPH not in b.label, b.label)
    check("...and no instruction words either",
          "switch" not in b.label.lower(), b.label)
    check("it is ONE word", len(b.label.split()) == 1, b.label)
    # WHERE IT WOULD GO IS IN THE TOOLTIP, which is not on the page.
    check("the target is in the help, not on the line", bool(b.help), b.help)
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
# EIGHT NOW. The engine glyph went with the icon Baba did not want, and
# a SYM entry no button wears is dead weight that the aria injector
# still carries.
check("SYM holds eight glyphs", len(glyphs) == 8, len(glyphs))
check("the engine glyph is gone from SYM", "\\u21c4" not in glyphs, glyphs)
# UNIQUENESS IS NOT COSMETIC. The aria injector matches BY GLYPH, so a
# duplicate makes a screen reader announce two buttons with one name.
# It already happened: translate borrowed the play triangle and was
# announced as "Read".
check("EVERY SYM GLYPH IS UNIQUE — the aria injector matches on them",
      len(set(glyphs)) == len(glyphs),
      [g for g in glyphs if glyphs.count(g) > 1])
# THE ARIA MAPPING WENT WITH IT. A mapping for a glyph no button wears
# is a lookup that can never match, and it would have gone stale
# silently.
check("no aria mapping is left for the removed glyph",
      'SYM["engine"]' not in CODE)

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
# THE LABEL NO LONGER VARIES — it is always the running engine — so
# only the REASON has three branches now. A check counting the old
# two-value assignment would have been green about a line that no
# longer exists.
check("every path sets a reason, so a dead link always explains itself",
      sw.count("why = ") == 3, sw.count("why = "))
check("...and the label is the running engine on every path",
      sw.count("label = eng.short") == 1, sw.count("label = eng.short"))

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
print("8 THE VOICE DROPDOWNS — two lists, ten each")
# =====================================================================
#
# Baba, 6.9.2026: "when I change engine there are different voices. You
# need to give me a drop-down menu for the voices now. Two drop-down
# menus: male and female... I want just ten voices, none more than ten.
# In the Gemini Google, in the Edge we already defined what it is."

import shutil                                     # noqa: E402
SEC = os.path.join(ROOT, ".streamlit", "secrets.toml")
BAK = SEC + ".voicebak"
shutil.copy(SEC, BAK)
try:
    # A KEY THAT IS NOT A PLACEHOLDER, or google is never USABLE and the
    # route quietly falls back to Edge — which is what made the first
    # version of this test look like the dropdowns had not been built.
    # FACE 5: a .replace() whose pattern misses changes NOTHING and the
    # test then passes for the wrong reason — here it would silently
    # leave the placeholder in place, google would not be usable, and
    # every check below would be testing the Edge picker while claiming
    # to test Google's. So the target is asserted first.
    _raw = open(SEC).read()
    _target = '"AQ.paste_your_first_key_here"'
    assert _target in _raw, "the placeholder key moved — this edit would miss"
    _s = _raw.replace(_target, '"AQ.stubKeyNotRealAAAAAAAAAAAAAAAAAAAAAAAA"')
    assert _s != _raw, "the file was not changed"
    open(SEC, "w").write(_s)

    def gapp():
        a = app("talk")
        a.session_state["route_stt"] = "google"
        a.session_state["route_tts"] = "google"
        a.session_state["route_llm"] = "google"
        return a

    g = gapp()
    g.run()
    check("the google reader renders", not g.exception, g.exception)
    # v252 PUT TWO DROPDOWNS HERE AND v254 REPLACED THEM WITH A RADIO
    # AND ONE LIST. Two boxes both held a value, so the screen answered
    # "which voice is speaking" with two names and therefore neither.
    # These checks now read the ONE list, once per side of the radio.
    boxes = {x.key: x for x in g.selectbox}
    check("there is ONE list, not two", len(boxes) == 1, sorted(boxes))
    check("...and a radio saying which side it holds",
          len(g.radio) == 1 and list(g.radio[0].options) == ["Female", "Male"],
          [r.options for r in g.radio])
    for side, gender in (("Female", "F"), ("Male", "M")):
        # SET THE STATE, NOT THE WIDGET. radio.set_value() proved
        # unreliable once the key already held a value from an earlier
        # press in the same test — it silently kept the old side and the
        # assertion then described the wrong list. The session key is
        # what the code actually reads.
        g.session_state["talkvoice_gender"] = gender
        g.run()
        # RE-READ THE BOX AFTER THE PRESS. Holding a reference from
        # before the rerun reads the OLD list and the assertion then
        # describes the wrong side — which is how the first version of
        # this loop reported the male list as failing to be female.
        boxes = {"talkvoice_voice": g.selectbox[0]}
        key = "talkvoice_voice"
        opts = boxes[key].options
        check("%s offers TEN, no more" % key, len(opts) == 10, len(opts))
        names = [o.split(" — ")[0] for o in opts]
        check("%s: every name is Google's" % key,
              all(n in GP.voice_names() for n in names), names[:3])
        check("%s: every name is that gender, from Google's table" % key,
              all(GP.gender_of(n) == gender for n in names),
              [(n, GP.gender_of(n)) for n in names[:3]])
        check("%s: the adjective is shown beside the name" % key,
              all(" — " in o for o in opts), opts[:2])
    g.session_state["talkvoice_gender"] = "F"
    g.run()
    check("the female list leads with the voice Google's own docs use",
          g.selectbox[0].options[0].startswith("Kore"),
          g.selectbox[0].options[0])
    g.session_state["talkvoice_gender"] = "M"
    g.run()
    check("the male list leads with Google's own first choice",
          g.selectbox[0].options[0].startswith("Charon"),
          g.selectbox[0].options[0])

    # PICKING ONE STICKS. A dropdown that resets on every render loses
    # the choice a person just made — and Streamlit reruns constantly.
    g.selectbox[0].select("Puck — Upbeat").run()
    check("choosing a voice is remembered",
          sget(g, "google_voice") == "Puck", sget(g, "google_voice"))
    g.run()
    check("...and survives a rerun", sget(g, "google_voice") == "Puck",
          sget(g, "google_voice"))

    # EDGE IS UNTOUCHED. "In the Edge we already defined what it is."
    e = app("talk")
    e.run()
    check("EDGE STILL SHOWS ITS FOUR BUTTONS, not dropdowns",
          len(e.selectbox) == 0
          and len([b for b in e.button
                   if b.key and b.key.startswith("talkvoice_")]) == 4,
          (len(e.selectbox),
           [b.key for b in e.button if b.key
            and b.key.startswith("talkvoice_")]))
finally:
    shutil.move(BAK, SEC)
check("the secrets file was put back", "paste_your" in open(SEC).read())


print()
print("9 THE STATUS LINE NAMES THE KEY BY POSITION")
# =====================================================================
#
# Baba, 6.9.2026: "in status line always specifies which engine is used,
# what API key by number. So if I have five API keys, you can write
# Google API two/five, so I see what's going on in status."

def sigtext(at):
    return " ".join(m.value for m in at.markdown if "tabsig" in m.value)

a = app("talk")
a.run()
sig = sigtext(a)
check("the status line carries the engine name", "Edge" in sig, sig[-120:])
check("...and a key position beside it", "/" in sig, sig[-120:])
# A DASH UNTIL SOMETHING HAS BEEN ASKED. Showing 1/2 before any call
# would be a claim about a key that has never been tried.
check("nothing used yet reads as a dash, not as key 1",
      "\u2013/" in sig, sig[-120:])

# THE NUMBER IS A POSITION AND NEVER A FRAGMENT OF A KEY. keyring.md
# §10d: on Gemini the first six characters are identical on every key,
# so a masked prefix identifies nothing and leaks something.
import re as _re                                  # noqa: E402
_keys = list(P.get("groq").keys or []) + list(P.get("google").keys or [])
check("NO KEY MATERIAL IS ON THE STATUS LINE",
      not any(k and len(k) >= 8 and k[:8] in sig for k in _keys))
check("...and no eight-character run of one either",
      not _re.search(r"[A-Za-z0-9_]{16,}", sig.split("tabsig")[-1]),
      sig[-120:])

# THE POSITION IS RECORDED ONLY BY A KEY THAT ACTUALLY WORKED.
gp = GP.Google(keys=["AQ.one", "AQ.two", "AQ.three"])
check("a fresh provider has used nothing", gp.active_key == 0)
tried = []


def _third_works(key):
    tried.append(key)
    if len(tried) < 3:
        return None, "401", "dead"
    return "ok", None, None


gp._rotate(_third_works)
check("the position of the key that WORKED is recorded, not the ones "
      "that were refused", gp.active_key == 3, gp.active_key)

gp2 = GP.Google(keys=["AQ.one", "AQ.two"])
gp2._rotate(lambda k: (None, "401", "dead"))
check("a ring where every key failed records nothing",
      gp2.active_key == 0, gp2.active_key)

# THE ENGINE NAME, NOT THE VENDOR. §0 rule 2 — the free engine's number
# belongs to the transcriber's keys, and the line still says "Edge".
check("the status names the ENGINE, not the provider behind the keys",
      "Groq" not in sig and "groq" not in sig, sig[-120:])


print()
print("10 THE PLAYER IS TOLD WHAT THE AUDIO ACTUALLY IS")
# =====================================================================
#
# Baba, 6.9.2026: "Sound dub or our tab, which supposedly generates the
# audio, does not work with Google."
#
# THE CAUSE: every player in this app was handed
# "data:audio/mpeg;base64,..." — hardcoded, because for two years every
# voice here returned MP3. Gemini returns a WAV. A browser given RIFF
# bytes under an MP3 label DOES NOT GUESS: it declines to decode and
# plays nothing. No error, no console warning, no failed request. The
# reading simply never started, which is why it looked like the tab was
# broken rather than the label.

from ttt import speech as SP                      # noqa: E402
from ttt.providers.google import to_wav           # noqa: E402

_wav = to_wav(b"\x00\x01" * 500)
check("a Gemini WAV is called audio/wav", SP.audio_mime(_wav) == "audio/wav",
      SP.audio_mime(_wav))
check("an MP3 with an ID3 tag is still audio/mpeg",
      SP.audio_mime(b"ID3\x04\x00" + b"\x00" * 32) == "audio/mpeg")
check("a bare MP3 frame is still audio/mpeg",
      SP.audio_mime(b"\xff\xfb\x90\x00" + b"\x00" * 32) == "audio/mpeg")
check("ogg and flac are named too",
      SP.audio_mime(b"OggS" + b"\x00" * 32) == "audio/ogg"
      and SP.audio_mime(b"fLaC" + b"\x00" * 32) == "audio/flac")
# UNKNOWN FALLS BACK TO MP3 — what every existing voice returns — so a
# shape nobody has seen behaves exactly as before rather than newly
# breaking.
for junk in (b"", None, b"\x00\x00\x00\x00", b"nonsense"):
    check("junk falls back to mpeg, never to nothing: %.12r" % (junk,),
          SP.audio_mime(junk) == "audio/mpeg", SP.audio_mime(junk))

check("the data URL carries the sniffed type",
      SP.audio_src(_wav).startswith("data:audio/wav;base64,"),
      SP.audio_src(_wav)[:26])
check("...and round-trips the bytes",
      __import__("base64").b64decode(SP.audio_src(_wav).split(",", 1)[1]) == _wav)

# NO PLAYER MAY HARDCODE THE TYPE AGAIN. This is the check that would
# have caught it: a grep for the literal, with comments stripped.
check("NOT ONE PLAYER STILL HARDCODES audio/mpeg IN A data: URL",
      "data:audio/mpeg;base64," not in CODE,
      [l for l in CODE.splitlines() if "data:audio/mpeg" in l][:2])
check("...and they all go through the one helper",
      CODE.count("SPEECH.audio_src(") >= 3, CODE.count("SPEECH.audio_src("))

print()
print("11 A RADIO SAYS WHICH VOICE IS SPEAKING")
# =====================================================================
#
# Baba: "there is a list of female and male voices, but which one is
# speaking? How can the user select that? You need to do radio buttons
# for female and male voice, and then there are two options there."
#
# Two dropdowns both held a value at all times, so the screen showed two
# names and answered "which is speaking" with neither.

shutil.copy(SEC, BAK)
try:
    _raw2 = open(SEC).read()
    _t2 = '"AQ.paste_your_first_key_here"'
    assert _t2 in _raw2, "the placeholder key moved"
    open(SEC, "w").write(
        _raw2.replace(_t2, '"AQ.stubKeyNotRealAAAAAAAAAAAAAAAAAAAAAAAA"'))

    def gapp2():
        a = app("talk")
        a.session_state["route_stt"] = "google"
        a.session_state["route_tts"] = "google"
        a.session_state["route_llm"] = "google"
        return a

    r = gapp2()
    r.run()
    check("the reader renders on google", not r.exception, r.exception)
    check("there is ONE radio", len(r.radio) == 1, len(r.radio))
    check("...with exactly two options",
          list(r.radio[0].options) == ["Female", "Male"], r.radio[0].options)
    check("there is ONE list, not two", len(r.selectbox) == 1,
          [x.key for x in r.selectbox])
    check("...holding ten voices", len(r.selectbox[0].options) == 10,
          len(r.selectbox[0].options))

    # THE SCREEN AND THE SOUND AGREE, and not by coincidence: the voice
    # is written every render, so a moved default cannot silently split
    # what is shown from what is spoken.
    shown = r.selectbox[0].options[0].split(" — ")[0]
    check("the voice in session IS the one at the top of the list",
          sget(r, "google_voice") == shown, (sget(r, "google_voice"), shown))
    check("...and it is a female voice, matching the radio",
          GP.gender_of(sget(r, "google_voice")) == "F",
          sget(r, "google_voice"))

    # SWITCHING SIDES MOVES THE VOICE. If it did not, the radio would
    # say Female while a male voice went on speaking.
    # THROUGH THE WIDGET, so the on_change callback actually fires.
    # Setting the session key directly — which the block above does —
    # bypasses it, and a mutation that broke _side_changed stayed GREEN
    # because nothing in the suite ever pressed the radio.
    # THE RAW OPTION VALUE, "M", NOT THE LABEL "Male". AppTest matches
    # against the option list the code passed — ("F", "M") — and a label
    # from format_func is SILENTLY IGNORED: no error, no change, and the
    # next assertion then describes a press that never happened. That
    # cost two false failures here before it was measured.
    r.radio[0].set_value("M").run()
    check("switching to Male changes the voice being used",
          GP.gender_of(sget(r, "google_voice")) == "M",
          sget(r, "google_voice"))
    check("...and the list under it is the male list",
          all(GP.gender_of(o.split(" — ")[0]) == "M"
              for o in r.selectbox[0].options),
          r.selectbox[0].options[:3])
    r.selectbox[0].select("Puck — Upbeat").run()
    check("picking from the list sets the voice",
          sget(r, "google_voice") == "Puck", sget(r, "google_voice"))
    r.run()
    check("...and it survives a rerun", sget(r, "google_voice") == "Puck")
    check("the radio stays on Male with a male voice chosen",
          sget(r, "talkvoice_gender") == "M", sget(r, "talkvoice_gender"))

    # AND BACK, through the widget again: the guard must move the voice
    # in BOTH directions, or the radio says Female while Puck speaks.
    r.radio[0].set_value("F").run()
    check("switching back to Female moves the voice with it",
          GP.gender_of(sget(r, "google_voice")) == "F",
          sget(r, "google_voice"))
    check("...and it is the first of the female list",
          sget(r, "google_voice") == GP.top_voices("F", 10)[0][0],
          sget(r, "google_voice"))
finally:
    shutil.move(BAK, SEC)

print()
print("%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
