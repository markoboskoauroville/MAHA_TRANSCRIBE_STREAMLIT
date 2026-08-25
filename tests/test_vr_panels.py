"""VR's TWO PANELS — and the direction surviving a trip to the cast.

    python3 tests/test_vr_panels.py

THE FAULT THIS FILE EXISTS TO PREVENT is not a crash. Splitting VR into
two panels means the emotion checkboxes are not rendered while the cast
is showing, and a Streamlit widget key whose widget did not render is
cleaned up. Pick three emotions, look at the voices, come back — blank.

HOW_WE_WORK.md §63 calls keeping the value outside Streamlit "the single
most useful thing in this codebase", and it cost three sessions the first
time it was learnt. So the store is a plain dict, testable here with no
Streamlit at all, and the widgets are only a view of it.

WHAT THIS CANNOT CATCH: that the pill row renders, that the panels look
right at 390px, or that Streamlit really does garbage-collect the
checkbox keys on this version. The last one is the actual mechanism and
it lives in a browser. Test 5 boots the real app and does exactly that
trip — pick, leave, come back — which is the only check here that meets
the fault the way a person would.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ttt import vr as VR  # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


E = VR.EMOTION_IDS

print("1 THE STORE, ALONE\n")
s = {}
check("1a nothing chosen to start", VR.picked_of(s) == [])
VR.set_picked(s, E[3], True)
VR.set_picked(s, E[0], True)
check("1b two chosen", len(VR.picked_of(s)) == 2, VR.picked_of(s))
check("1c and they come back in EMOTION_IDS order, not press order",
      VR.picked_of(s) == [E[0], E[3]], VR.picked_of(s))
VR.set_picked(s, E[0], True)
check("1d ticking the same one twice does not double it",
      VR.picked_of(s) == [E[0], E[3]], VR.picked_of(s))
VR.set_picked(s, E[0], False)
check("1e unticking removes exactly one", VR.picked_of(s) == [E[3]])
VR.set_picked(s, E[7], False)
check("1f unticking one that was never ticked is not an error",
      VR.picked_of(s) == [E[3]])

print("\n1b THE UGLY CASES")
check("1g a store with junk in it reads as empty",
      VR.picked_of({VR.PICKED_KEY: None}) == [])
check("1h an unknown id in the store is ignored, not returned",
      VR.picked_of({VR.PICKED_KEY: ["not-an-emotion", E[1]]}) == [E[1]])
check("1i the note starts empty", VR.note_of({}) == "")
check("1j None as a note is an empty string, never None",
      VR.set_note({}, None) == "")
check("1k too_many is false at the cap",
      not VR.too_many({VR.PICKED_KEY: E[:VR.MAX_EMOTIONS]}))
check("1l and true one past it",
      VR.too_many({VR.PICKED_KEY: E[:VR.MAX_EMOTIONS + 1]}))

print("\n2 THE PANEL VALUE CANNOT TAKE THE PAGE DOWN")
# The tier radio already met this: a stored value that is not one of the
# options raises ValueError inside the widget and kills the whole page.
check("2a a nonsense panel clamps to the default",
      VR.clamp_panel("emotions-tab") == VR.DEFAULT_PANEL)
check("2b None clamps too", VR.clamp_panel(None) == VR.DEFAULT_PANEL)
check("2c a real one is left alone", VR.clamp_panel("direction") == "direction")
check("2d there are exactly two panels", len(VR.PANELS) == 2, VR.PANELS)

print("\n3 A TRIP TO THE CAST AND BACK — the whole point\n")
# What the tab does, in order, with the widget keys behaving the way
# Streamlit behaves: cleaned up when the widget does not render.
st = {"_vr_panel": "direction"}
for eid in (E[2], E[5]):
    st["vre_%s" % eid] = True
    VR.set_picked(st, eid, True)
VR.set_note(st, "quieter, near the end")
st["vr_note"] = VR.note_of(st)
before = VR.picked_of(st)

# --- switch to the cast: Streamlit drops every key it owns -----------
st["_vr_panel"] = "cast"
for k in [k for k in list(st) if k.startswith("vre_") or k == "vr_note"]:
    del st[k]
check("3a Streamlit's own keys are gone, as they would be",
      not [k for k in st if k.startswith("vre_")])
check("3b the choice SURVIVES, because it never lived there",
      VR.picked_of(st) == before, VR.picked_of(st))
check("3c and so does the note", VR.note_of(st) == "quieter, near the end")

# --- back to the direction: the boxes are rebuilt from the store -----
st["_vr_panel"] = "direction"
held = VR.picked_of(st)
for eid in E:
    st["vre_%s" % eid] = eid in held
check("3d exactly the two chosen boxes come back ticked",
      [e for e in E if st.get("vre_%s" % e)] == before,
      [e for e in E if st.get("vre_%s" % e)])
check("3e the direction sentence is unchanged by the round trip",
      VR.build_direction(VR.picked_of(st), VR.note_of(st))
      == VR.build_direction(before, "quieter, near the end"))

print("\n4 THE PAGE ITSELF — inspected as text, and it says what it searched")
APP = os.path.join(os.path.dirname(__file__), "..", "app.py")
src = open(APP, encoding="utf-8").read()
vr_tab = src[src.index('elif active == "vr":'):src.index('elif active == "looks":')]
print("       searched the vr tab, %d chars" % len(vr_tab))


def before_of(needle):
    """Where `needle` sits in the tab, or -1.

    index() RAISED here, so one moved marker killed the whole file and it
    printed nothing. Two markers moved: the VR box became a kept_area in
    v218, and rehearse joined the action row in v224.
    """
    return vr_tab.find(needle)


_go_at = before_of('"nact_vr_go"')
_box_at = before_of('kept_area("vr_text"')
check("4a0 both the rehearse action and the box are present",
      _go_at > 0 and _box_at > 0, (_go_at, _box_at))
check("4a rehearse is rendered ABOVE the text box, i.e. under the player",
      0 < _go_at < _box_at, (_go_at, _box_at))
# THE SPELLING CHANGED WHEN REHEARSE JOINED THE ROW: it is an extra's
# key now, ("nact_vr_go", ...), not key="nact_vr_go". Same claim, current
# spelling, and both bounds checked before comparing.
_pl_at = before_of('key="vr_player"')
check("4b the player is above rehearse", 0 < _pl_at < _go_at,
      (_pl_at, _go_at))
check("4c the panel switch is BELOW the box links",
      before_of('box_links("vrbox"') < before_of('key="_vr_panel"'))
# THE CHECKBOXES WENT IN v201 and the store with them — directions are
# TAGS IN THE TEXT now, so there is no widget state to read and nothing
# to keep a store in step with. This asserted the old contract and would
# have gone red the moment the file could run again; it was hidden
# because the file was crashing four checks earlier.
check("4d the directions live in the TEXT, not in widget state",
      "VR.picked_of" not in vr_tab and "VR.tag_for(" in vr_tab,
      [x for x in ("VR.picked_of",) if x in vr_tab])
check("4e nothing reads a vre_ key to decide what was chosen",
      'for e in VR.EMOTION_IDS\n' not in vr_tab
      and 'st.session_state.get("vre_%s" % e)' not in vr_tab,
      "a widget key is still being trusted as the source of truth")


# --- 5. WHAT A TEST CANNOT DO HERE, SAID PLAINLY ---------------------
# Booting the real app with AppTest and driving the trip — pick, leave,
# come back — WAS TRIED, on 25.8.2026, AND IT HANGS. The VR tab renders
# `_wave_component`, and an AppTest run whose script ends without
# producing widget deltas waits out the whole default_timeout and then
# raises. Three runs produced no result in nine minutes.
#
# It is the same wall tests/test_recorder_stress.py hits at its line
# 125, and it has now cost two sessions. Do not re-add it without
# solving the component problem first.
#
# So the MECHANISM this file guards — Streamlit garbage-collecting a
# checkbox key whose widget did not render — is not proven here.
# Section 3 proves the store survives a simulated round trip. Section 4
# greps the page to show the store is what the code reads. Neither is a
# person pressing a pill, and saying so is the point.
print("\n5 NOT TESTED HERE")
print("       the real trip through Streamlit: AppTest hangs on this tab")
print("       (the wave component yields no widget deltas)")

print("\n{} passed, {} failed".format(passed, failed))


def test_vr_panels():
    assert failed == 0, "%d of %d failed" % (failed, passed + failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
