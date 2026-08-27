"""HIS OWN TAGS: A PANEL, A STORE, AND A DOOR.

    python3 tests/test_vr_tags_panel.py

Baba, 25.8.2026: "Create a new tab inside VR. Custom tags. Where I'm
going to create my tags, for my emotions I need, and I can export them as
a file and load them back if they are gone. But basically that needs to
be stored in browser memory."

THE EXPORT IS NOT A FEATURE, IT IS THE SAFETY NET. Browser storage is
real storage until somebody clears their history, changes device, or
opens a private window — and then a vocabulary built over months is gone
with no warning and no undo. He asked for the file in the same breath as
the store, which is the right instinct.
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import vr as V  # noqa: E402

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
vr = app[app.find('elif active == "vr":'):app.find('elif active == "looks":')]

print("1 THE FILE SAYS WHAT IT IS")
out = V.export_own(["like a priest", "half asleep"])
blob = json.loads(out)
check("1a it is JSON, so it survives being opened and edited", isinstance(blob, dict))
check("1b it names itself — a file found in a downloads folder in two "
      "years still says what read it",
      blob["kind"] == V.TAGS_FILE_KIND, blob.get("kind"))
check("1c and carries a version", blob["version"] == V.TAGS_FILE_VERSION)
check("1d and when it was saved", "saved" in blob)
check("1e the tags are in it", blob["tags"] == ["like a priest", "half asleep"])
check("1f Croatian survives the round trip",
      json.loads(V.export_own(["tužno", "ljutito"]))["tags"] == ["tužno", "ljutito"])
check("1g an empty list still makes a valid file",
      json.loads(V.export_own([]))["tags"] == [])

print("\n2 LOADING ADDS, IT DOES NOT REPLACE")
# Loading a file is almost always "put my tags back", not "throw away
# what I have now" — and the second is not undoable while the first is.
got, note = V.import_own(out, ["mine"])
check("2a what he has now is kept", got[0] == "mine", got)
check("2b and the file is added after it",
      got == ["mine", "like a priest", "half asleep"], got)
got, _ = V.import_own(out, ["like a priest"])
check("2c a tag he already has is not doubled",
      got.count("like a priest") == 1, got)
got, _ = V.import_own(out, ["LIKE A PRIEST"])
check("2d and the match ignores case, keeping HIS spelling",
      got == ["LIKE A PRIEST", "half asleep"], got)
big = V.export_own(["t%d" % i for i in range(60)])
check("2e the cap still holds — a panel, not an archive",
      len(V.import_own(big, [])[0]) == V.MAX_OWN)

print("\n3 IT TAKES WHAT A PERSON WOULD ACTUALLY HAND IT")
check("3a a bare JSON list", V.import_own('["one","two"]', [])[0] == ["one", "two"])
check("3b one per line, which is what somebody writes by hand",
      V.import_own("one\ntwo\nthree", [])[0] == ["one", "two", "three"])
check("3c blank lines are not tags",
      V.import_own("one\n\n\ntwo", [])[0] == ["one", "two"])
check("3d and padding is trimmed", V.import_own("  spaced  ", [])[0] == ["spaced"])

print("\n3b AND REFUSES WHAT IT SHOULD")
check("3e a file of symbols is not a vocabulary — these end up INSIDE "
      "his script as <like this>, and a line of punctuation there is a "
      "rehearsal that reads symbols aloud",
      V.import_own("%%%", [])[0] == [], V.import_own("%%%", []))
check("3f the same rule for a JSON list, or it is half a rule",
      V.import_own('["ok","###"]', [])[0] == ["ok"],
      V.import_own('["ok","###"]', []))
check("3g somebody else's JSON is named, not silently raided",
      "not a VR tags file" in V.import_own('{"kind":"other","tags":["x"]}', [])[1])
check("3h an empty file says so", "empty" in V.import_own("", [])[1])
check("3i and None does not raise", V.import_own(None, ["keep"])[0] == ["keep"])
check("3j bytes are decoded, because that is what an upload gives",
      V.import_own(out.encode("utf-8"), [])[0] == ["like a priest", "half asleep"])
check("3k undecodable bytes are refused, not crashed on",
      V.import_own(b"\xff\xfe\x00", ["keep"])[0] == ["keep"])
check("3l a file with nothing new says so rather than claiming success",
      "nothing new" in V.import_own(out, ["like a priest", "half asleep"])[1])

print("\n4 THE PANEL")
check("4a there are three panels now", V.PANELS == ("cast", "direction", "tags"),
      V.PANELS)
check("4b the switch names the third", 't("vr_mytags")' in vr)
check("4c the panel exists", 'st.session_state["_vr_panel"] == "tags"' in vr)
check("4d he can add one", "VR.add_own(st.session_state, word)" in vr)
check("4e the box empties in the CALLBACK, not after the widget draws",
      '"vr_tag_new"] = ""' in vr
      and vr.find('"vr_tag_new"] = ""') < vr.find("_tc1.text_input"))
check("4f each tag can be removed — a list you can only add to fills "
      "with typos", "VR.remove_own(" in vr)
check("4g an empty panel says what to do rather than sitting blank",
      't("vr_tags_none")' in vr)
check("4h they are shown as the TAG he will paste, not the bare word",
      "VR.tag_for([_w])" in vr)

print("\n4b THE DOOR")
check("4i there is an export", "download_button" in vr and "vr-tags.json" in vr)
check("4j disabled when there is nothing to save", "disabled=not _own_now" in vr)
check("4k there is an import", "file_uploader" in vr and "vr_tags_up" in vr)
check("4l it takes json AND txt", 'type=["json", "txt"]' in vr)
# THE GUARD, NOT THE NAME. My first version asked whether the string
# "_vr_tags_seen" appeared anywhere in the tab — and it still does, in
# the line that SETS it, so deleting the comparison left this green.
# A stamp that is written and never read is not a stamp.
check("4m the upload is STAMPED — Streamlit re-offers the same file on "
      "every rerun and it would import for ever",
      'st.session_state.get("_vr_tags_seen") != _up.name' in vr,
      [l for l in vr.splitlines() if "_vr_tags_seen" in l])
check("4n and it says what it did", '"_vr_tags_note"' in vr)

print("\n5 THEY WERE ALREADY IN BROWSER STORAGE")
# He asked for browser memory. VR.OWN_KEY went into KEPT_CHOICES in v227,
# so this panel gives them a home rather than inventing a second store.
_kc = app[app.find("KEPT_CHOICES"):app.find("def _kept_restore")]
check("5a the store is persisted with every other choice",
      "VR.OWN_KEY" in _kc, _kc[-160:])
check("5b and the panel does not invent a second one",
      "_vr_own" not in vr or "VR.OWN_KEY" in vr)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
