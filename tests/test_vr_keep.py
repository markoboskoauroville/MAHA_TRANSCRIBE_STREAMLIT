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

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
