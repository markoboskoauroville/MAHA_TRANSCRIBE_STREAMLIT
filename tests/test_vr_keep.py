"""THE BOX IS NEVER EMPTIED BY THE APP, the script is shown, one file out.

    python3 tests/test_vr_keep.py

Baba, 25.8.2026: "When I press Rehearse or Play, the text box is cleared.
I cannot go back and read with another voice, or to fix something, it's
gone. Make anything pasted in any text box persistent until a user clears
it. It's only user action, the system doesn't clear it."

WHY IT EMPTIED. VR's block advance calls st.rerun() a hundred lines ABOVE
the text box, so the script stopped before the box was drawn — and
Streamlit garbage-collects a widget key whose widget did not render.
HOW_WE_WORK §63, and the same trap already fixed for VR's emotion
checkboxes three versions earlier. The symptom was fixed there and the
cause left here.

TEST 1 drives the store on a plain dict. TEST 2 reads the tab.
"""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
vr = app[app.index('elif active == "vr":'):app.index('elif active == "looks":')]


def text(st_, slot):
    return st_.get("_keep_" + slot, "") or ""


def kset(st_, slot, v):
    st_["_keep_" + slot] = v or ""
    st_["_keepgen_" + slot] = int(st_.get("_keepgen_" + slot, 0)) + 1


def key(st_, slot):
    return "kept_%s_%d" % (slot, int(st_.get("_keepgen_" + slot, 0)))


print("1 THE STORE OUTLIVES THE WIDGET")
st = {}
kset(st, "vr_text", "the line to rehearse")
check("1a what was set is what comes back",
      text(st, "vr_text") == "the line to rehearse")
# Streamlit cleaning up a key that did not render is exactly this: the
# widget entry vanishes and the store does not.
st.pop(key(st, "vr_text"), None)
check("1b losing the WIDGET entry does not lose the text",
      text(st, "vr_text") == "the line to rehearse")
check("1c the store key is not the widget key",
      "_keep_vr_text" != key(st, "vr_text"))

print("\n1b THE GENERATION IS WHAT MAKES A CHANGE VISIBLE")
# A text_area that already exists keeps whatever the browser last sent
# it. Only a key it has never seen takes a fresh value=.
k1 = key(st, "vr_text")
kset(st, "vr_text", "a different line")
check("1d setting the text remounts the box", key(st, "vr_text") != k1,
      (k1, key(st, "vr_text")))
check("1e and the new text is what it will show",
      text(st, "vr_text") == "a different line")

print("\n1c ONLY A PERSON EMPTIES IT")
kset(st, "vr_text", "")
check("1f clear empties it", text(st, "vr_text") == "")
check("1g and that is a set like any other, not a special path",
      "_keep_vr_text" in st)

print("\n2 THE TAB USES THE STORE, NOT THE WIDGET")
print("       searched the vr tab, %d chars" % len(vr))
check("2a the box is a kept_area", "kept_area(\"vr_text\"" in vr)
check("2b nothing writes the widget key directly",
      'st.session_state["vr_text"]' not in vr,
      'st.session_state["vr_text"]' in vr)
check("2c rehearse reads the STORE", 'kept_text("vr_text")' in vr)
check("2d inserting a tag goes through the store",
      'kept_set("vr_text", body)' in vr)
check("2e clear is the only thing that empties it",
      vr.count('kept_set("vr_text", "")') == 1,
      vr.count('kept_set("vr_text", "")'))
check("2f and the rerun that used to lose it is still above the box — "
      "the fix is the store, not moving the rerun",
      vr.index("st.rerun()") < vr.index('kept_area("vr_text"'))

print("\n3 THE SCRIPT IS ON SCREEN")
check("3a there is a script view", "def _vr_script" in vr)
check("3b the block being spoken is marked apart from the rest",
      "vrnow" in vr and "vrthen" in vr)
check("3c the direction is named beside its block",
      "vrdir" in vr)
check("3d it is drawn from the JOB, so it follows the hand-off",
      "_vr_script(_vr_job)" in vr)
check("3e the tags themselves are not printed — they are markup, not "
      "lines",
      "tag_for" not in vr[vr.index("def _vr_script"):
                          vr.index("_vr_script(_vr_job)")])
theme = open(os.path.join(os.path.dirname(__file__), "..", "ttt",
                          "theme.py"), encoding="utf-8").read()
check("3f the spoken block is lit and the rest is quiet, not hidden",
      ".vrnow" in theme and ".vrthen" in theme)

print("\n4 ONE FILE OF THE WHOLE READING")
check("4a there is a stitcher", "def _vr_stitch" in vr)
# 4b, 4c, 4g and 4h moved to section 6. They described the stitcher when
# it lived INSIDE the vr tab; it is shared with R now, so checking for it
# in the tab is checking the wrong place. The behaviour is still checked,
# just where the code is.
# THE SECOND CONTROL IS GONE. v216 made the deck's own `save` key BE the
# stitcher, because two download controls meant Baba pressed the obvious
# one and got a single block. There is no st.download_button to be drawn
# after any more — the finished file is handed back DOWN to the player.
check("4e the finished file is handed back to the deck, not to a second "
      "button", 'dl=(' in vr and "_vr_whole" in vr)
check("4e2 and there is no second download control to press by mistake",
      "st.download_button" not in vr, "st.download_button" in vr)
# THE NAME MOVED WITH THE CONTROL. It was st.download_button's
# file_name; now the deck saves the file, so the name goes DOWN as a prop
# and the mime is in the data URI.
check("4f the file is named for what it actually is",
      'dl_name="rehearsal.mp3"' in vr and "data:audio/mpeg;base64" in vr)
check("4g VR hands its own block builder to the shared stitcher",
      "stitch_reading(len(job.get" in vr and "_vr_block" in vr)
check("4h and reports a refusing block on screen rather than silently",
      '"_vr_error"' in vr[vr.index("def _vr_stitch"):
                          vr.index("_vr_audio = st.session_state")])

print("\n4b THE JOIN REALLY MAKES ONE FILE")
if __import__("shutil").which("ffmpeg"):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from ttt import speech as S
    paths = []
    for f in (220, 330, 440):
        pth = tempfile.mktemp(suffix=".wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "sine=frequency=%d:duration=1" % f,
                        "-ar", "48000", "-ac", "1", pth], check=True)
        paths.append(pth)
    out = S.join_audio(paths)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration", "-of", "csv=p=0", out],
                         capture_output=True, text=True).stdout.strip()
    fmt = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=format_name", "-of", "csv=p=0", out],
                         capture_output=True, text=True).stdout.strip()
    print("       three 1s clips joined -> %s, %ss" % (fmt, dur))
    check("4i three parts become ONE file", fmt == "mp3", fmt)
    check("4j and it is as long as all three together",
          abs(float(dur) - 3.0) < 0.3, dur)
    for pth in paths + [out]:
        try:
            os.unlink(pth)
        except OSError:
            pass
else:
    print("  skip  ffmpeg is not here")

print("\n5 EVERY BOX KEEPS ITS TEXT, NOT JUST VR'S")
# Baba: "make anything pasted in any text box persistent until a user
# clears it." R and TR do not rerun mid-render today, so they do not lose
# text — but the trap is one feature away and VR showed what it costs.
for slot, tabname in (("talk_text", "R"), ("translate_src_text", "TR src"),
                      ("translate_out", "TR out")):
    check("5a %s is a kept box" % tabname,
          'kept_area("%s"' % slot in app, slot)
    check("5b %s never writes the widget key" % tabname,
          'st.session_state["%s"]' % slot not in app, slot)
    check("5c %s never reads the widget key" % tabname,
          'st.session_state.get("%s"' % slot not in app, slot)

print("\n6 ONE STITCHER, NOT ONE PER TAB")
check("6a there is a shared stitcher", "def stitch_reading(" in app)
check("6b VR uses it", "stitch_reading(len(job.get" in app)
check("6c R uses it too", "stitch_reading(len(parts), _make)" in app)
check("6d neither tab grew its own join",
      app.count("SPEECH.join_audio(") == 1, app.count("SPEECH.join_audio("))
check("6e it builds every block, so a half-played reading still saves whole",
      "for i in range(int(count or 0)):" in app)
check("6f a failing block stops it rather than saving a hole",
      'got.get("err")' in app[app.index("def stitch_reading"):])
check("6g temporary files go on every path",
      "finally:" in app[app.index("def stitch_reading"):
                        app.index("def tab_signature")])
check("6h R offers the whole reading as its own file",
      'file_name="reading.mp3"' in app)
check("6i and VR its own", 'dl_name="rehearsal.mp3"' in app)
check("6j both say how many parts are left rather than hanging",
      app.count("vr_stitch_wait") >= 2, app.count("vr_stitch_wait"))

print("\n7 SAVE STILL WORKS WHEN THE READING HAS FINISHED")
# Baba, 25.8.2026: "you broke VR save. When I press save, nothing's
# happening." His screenshot showed 1/1 and 0:01 / 0:01 — the reading had
# ENDED. The job was popped on completion, and save needs the job,
# because the job holds the parts and the cache the file is made from.
# So save worked while playing and did nothing the moment it finished,
# which is exactly when somebody wants to keep what they just heard.
check("7a a finished reading MARKS the job done", '_vr_job["done"] = True' in vr)
check("7b rather than popping it, which is what broke save",
      'pop("_vr_job", None)' not in vr[vr.index("THE READING IS OVER"):
                                       vr.index("THE READING IS OVER") + 900])
check("7c the save guard can still find a finished job — it asks for the "
      "job, not for it to be playing",
      '_vr_job and isinstance(_vr_ev, dict) and _vr_ev.get("save")' in vr)
check("7d a finished reading does not claim to be making a part",
      'not _vr_job.get("done") and _vr_job["index"] < _n' in vr)
check("7e and does not autoplay itself on every rerun, now that the job "
      "outlives it",
      '_vr_job and not _vr_job.get("done")' in vr)

print("\n8 SAVE FROM A STANDING START — text in the box, nothing played")
# Baba, 25.8.2026: "if there is something in the text box and the user
# presses download instead of play, the text should be generated and
# downloaded, not be dead."
#
# TWO DEAD ENDS ON ONE PRESS. The component returned early on !audio.src,
# and Python required a job. So a person who typed a line and pressed
# save got nothing at either end — and a control that does nothing
# teaches that the app is broken, not that an order of operations was
# expected.
front = open(os.path.join(os.path.dirname(__file__), "..",
                          "waveform_frontend", "index.html"),
             encoding="utf-8").read()
check("8a the component no longer refuses just because nothing is loaded",
      "if(!audio.src) return;" not in front,
      [l for l in front.splitlines() if "if(!audio.src) return;" in l])
# v228 MOVED THE GUARD OUT OF THE COMPONENT. It used to check the
# `startable` class, which lags a render behind, so on a phone it refused
# the very press it was written to allow. Section 9 checks the new
# arrangement; these two describe the one it replaced.
check("8b it reports the press unconditionally, because a prop that "
      "lags cannot guard one",
      "{at: Date.now(), save: true}" in front)
check("8c and PYTHON is where an empty box gets answered",
      'not kept_text("vr_text").strip()' in vr and '"vr_nothing"' in vr)

check("8d Python answers a save press with NO job, if there is text",
      'not _vr_job and kept_text("vr_text").strip()' in vr)
check("8e by planning through _vr_go — the same planning rehearse does, "
      "not a second way to plan", "_vr_go()" in vr)
check("8f then going straight to stitching, because he asked to SAVE",
      '_vr_stitching"] = True' in vr)
check("8g and NOT starting to talk at him",
      'pop("_vr_autoplay", None)' in vr)
check("8h the press is stamped, so one press is one file",
      vr.count('"_vr_save_seen"] = _vr_ev.get("at")') >= 2,
      vr.count('"_vr_save_seen"] = _vr_ev.get("at")'))
# find(), NOT index() — the sweep BLOCKED on this line as new lint debt
# and it was right: I wrote the fault the linter exists to catch, in the
# same commit, one hour after the sweep started enforcing it.
_def_at = app.find("def _vr_go")
_call_at = app.find("            _vr_go()")
check("8i _vr_go is defined ABOVE the save handler that calls it — "
      "pyflakes caught this as an undefined name",
      0 < _def_at < _call_at, (_def_at, _call_at))
check("8j and moving it did not move what the person SEES: player, then "
      "rehearse, then the box",
      0 < vr.find('key="vr_player"') < vr.find('"nact_vr_go"')
      < vr.find('kept_area("vr_text"'),
      (vr.find('key="vr_player"'), vr.find('"nact_vr_go"'),
       vr.find('kept_area("vr_text"')))

print("\n9 THE DECK KNOWS THERE IS TEXT, EVEN WITH NO AUDIO")
# Baba, after v225: "I need to press rehearsal and then I can save. I
# cannot skip rehearsal."
#
# v225 was written for exactly that and DID NOT REACH HIM. VR passed
# startable=bool(_vr_audio) — FALSE with a line typed and nothing played,
# which is the only case that mattered. So the component's new guard
# bailed on precisely the press it was written to allow. I built the road
# and left the gate shut, and shipped it without pressing the button.
# v227 GATED THE PRESS ON A PROP AND HE STILL COULD NOT SAVE.
#
# `startable` comes from the LAST render. On a phone the text he has just
# typed has not reached Python yet, because a Streamlit text_area does
# not commit until it loses focus — and tapping a button inside the
# iframe is what blurs it. So at the instant of the click the class is
# always one step behind reality.
#
# A PROP THAT LAGS CANNOT GUARD A PRESS. The press is reported always and
# Python decides, by which time the blur has committed the text.
front = open(os.path.join(os.path.dirname(__file__), "..",
                          "waveform_frontend", "index.html"),
             encoding="utf-8").read()


def _js_code(src):
    """The JavaScript with /* */ and // comments stripped.

    The comment explaining that `startable` was REMOVED contains the
    word, so a check reading raw source matches its own explanation and
    can only be made green by deleting the reason.
    checking-the-checks.md face 2, met for the sixth time today.
    """
    out, inblock = [], False
    for line in src.splitlines():
        t = line.strip()
        if inblock:
            if "*/" in t:
                inblock = False
            continue
        if t.startswith("/*"):
            if "*/" not in t:
                inblock = True
            continue
        if t.startswith("//"):
            continue
        out.append(line)
    return "\n".join(out)


_fc = _js_code(front)
_sv_a, _sv_b = _fc.find("bSave.onclick"), _fc.find("audio.onplay")
check("9a0 the save handler is findable", 0 < _sv_a < _sv_b, (_sv_a, _sv_b))
_sv = _fc[_sv_a:_sv_b] if 0 < _sv_a < _sv_b else ""
check("9a save reports the press without consulting a stale prop",
      "startable" not in _sv, [l for l in _sv.splitlines()
                               if "startable" in l])
check("9b and it still reports it", '{at: Date.now(), save: true}' in _sv)
_pl_a = _fc.find("bPlay.onclick")
_pl = _fc[_pl_a:_sv_a] if 0 < _pl_a < _sv_a else ""
check("9b2 play does the same — the lag is identical",
      "startable" not in _pl and "{at: Date.now(), start: true}" in _pl,
      [l for l in _pl.splitlines() if "startable" in l])
check("9b3 an empty box gets a SENTENCE, not silence — the guard moved "
      "to Python, it did not vanish",
      'not kept_text("vr_text").strip()' in vr and '"vr_nothing"' in vr)

print("\n9b AND PLAY IS NOT DEAD EITHER")
# The same dead end one button along: once startable is true the deck
# REPORTS a play press on an empty deck, and nothing was listening. That
# is how save shipped broken in v225 — the report existed, the handler
# did not.
check("9c VR handles a start press", '_vr_ev.get("start")' in vr)
check("9d only when there is text to start FROM",
      'and not _vr_job and kept_text("vr_text").strip()' in vr)
check("9e stamped, so one press is one reading", '"_vr_start_seen"' in vr)
check("9f it plans through _vr_go, like everything else",
      vr.count("_vr_go()") >= 2, vr.count("_vr_go()"))
check("9g play DOES autoplay — unlike save, he asked to hear it",
      '_vr_autoplay"] = True' in vr)
check("9h and _vr_go is defined above both handlers",
      0 < vr.find("def _vr_go") < vr.find('_vr_ev.get("start")')
      < vr.find('_vr_ev.get("save")'),
      (vr.find("def _vr_go"), vr.find('_vr_ev.get("start")'),
       vr.find('_vr_ev.get("save")')))

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
