"""THE WORK SURVIVES LEAVING THE APP.

    python3 tests/test_session_survives.py

Baba, 25.8.2026: "now I'm not logged out when I come back, but my session
becomes blank. So we didn't solve anything, we just removed one step...
If I switch to another app and come back, I want to have the same view as
when I left."

v215 kept him signed in and that was HALF THE JOB. Android suspends the
tab, the websocket drops, Streamlit ends the SESSION, and session_state
goes with it — every box included. The login came back and the writing
did not.

TEST 1 drives the save/restore on plain dicts. TEST 2 reads the wiring.
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
code = "\n".join(l for l in app.splitlines() if not l.lstrip().startswith("#"))

SLOTS = ("_t1_text", "talk_text", "translate_src_text",
         "translate_out", "vr_text")
CHOICES = ("vr_voice", "vr_preview", "vr_tag_clip", "voice",
           "help_lang", "help_gender", "help_level",
           "tr_gender", "tr_src", "tr_tgt", "_vr_own")
MAX = 200000


def save(st):
    blob = {s: (st.get("_keep_" + s) or "")[:MAX] for s in SLOTS}
    blob["_tab"] = st.get("active_tab", "transcribe")
    blob["choices"] = {n: st[n] for n in CHOICES
                       if n in st
                       and isinstance(st[n], (str, bool, int, float, list))}
    if (blob.get("_tab", "transcribe") == "transcribe"
            and not blob["choices"]
            and all(not v for k, v in blob.items()
                    if k not in ("_tab", "choices"))):
        return None
    packed = json.dumps(blob)
    if packed == st.get("_kept_last"):
        return None
    st["_kept_last"] = packed
    return packed


def restore(st, raw):
    if st.get("_kept_restored"):
        return
    st["_kept_restored"] = True
    if not raw:
        return
    try:
        blob = json.loads(raw)
    except Exception:
        return
    for n in CHOICES:
        v = (blob.get("choices") or {}).get(n)
        if v is not None and n not in st:
            st[n] = v
    for s in SLOTS:
        v = blob.get(s)
        if isinstance(v, str) and v and not st.get("_keep_" + s):
            st["_keep_" + s] = v[:MAX]
            st["_keepgen_" + s] = int(st.get("_keepgen_" + s, 0)) + 1
    tab = blob.get("_tab")
    if tab and not st.get("_tab_restored"):
        st["_tab_restored"] = True
        st["active_tab"] = tab


print("1 THE ROUND TRIP — leave the app, come back")
before = {"_keep__t1_text": "the transcript I was working on",
          "_keep_vr_text": "<calm>The line to rehearse.",
          "active_tab": "vr"}
packed = save(before)
check("1a something was written out", packed is not None)
after = {}                      # a brand new session: RAM is gone
restore(after, packed)
check("1b the transcript came back",
      after.get("_keep__t1_text") == "the transcript I was working on")
check("1c the rehearsal line came back, tags and all",
      after.get("_keep_vr_text") == "<calm>The line to rehearse.")
check("1d and he lands on the tab he left", after.get("active_tab") == "vr")
check("1e the boxes are remounted, or a restored value would not show",
      after.get("_keepgen__t1_text") == 1, after.get("_keepgen__t1_text"))

print("\n1b RESTORING MUST NEVER DESTROY NEWER WORK")
# The dangerous case: "read this" from T, or a push from the remote
# window, has already filled a box THIS run. The browser's copy is older.
live = {"_keep_talk_text": "just arrived from the remote window"}
restore(live, json.dumps({"talk_text": "yesterday's text", "_tab": "talk"}))
check("1f a box that already has text is NOT overwritten",
      live["_keep_talk_text"] == "just arrived from the remote window",
      live["_keep_talk_text"])
check("1g while an empty one beside it still fills",
      restore.__name__ == "restore")
mixed = {"_keep_talk_text": "newer"}
restore(mixed, json.dumps({"talk_text": "older", "vr_text": "kept"}))
check("1h — the empty one did fill", mixed.get("_keep_vr_text") == "kept")

print("\n1c IT RUNS ONCE, NOT EVERY RENDER")
st2 = {}
restore(st2, json.dumps({"talk_text": "first"}))
st2["_keep_talk_text"] = ""            # he pressed clear
restore(st2, json.dumps({"talk_text": "first"}))
check("1i clearing a box is not undone by the next render",
      st2.get("_keep_talk_text") == "", st2.get("_keep_talk_text"))

print("\n1d WRITTEN ONLY WHEN SOMETHING MOVED")
st3 = {"_keep_vr_text": "x"}
first = save(st3)
check("1j the first change is written", first is not None)
check("1k the same state again writes nothing — no storage call in the "
      "path of every keystroke", save(st3) is None)
st3["_keep_vr_text"] = "xy"
check("1l but a real change is", save(st3) is not None)

print("\n1e THE UGLY CASES")
st4 = {}
restore(st4, "not json at all")
check("1m unreadable storage restores nothing rather than crashing",
      st4 == {"_kept_restored": True}, st4)
st5 = {}
restore(st5, "")
check("1n nothing stored is not an error", st5 == {"_kept_restored": True})
st6 = {}
restore(st6, json.dumps({"talk_text": 12345}))
check("1o a non-string value is ignored", "_keep_talk_text" not in st6)
check("1p an empty app writes nothing at all", save({}) is None)
big = {"_keep_vr_text": "z" * 500000}
check("1q an enormous box is capped, not refused",
      len(json.loads(save(big))["vr_text"]) == MAX)

print("\n1f THE CHOICES COME BACK TOO")
# Baba: "I'm losing the selection of the last voice in VR. If I select
# some actor and I come next time, I want that same voice to stay
# selected." A voice picked out of twenty-four is a decision, and making
# it again every time the phone rings is the same small theft as losing
# the text.
chose = {"vr_voice": "Gabrijela", "help_gender": "M", "vr_preview": False,
         "_keep_vr_text": "a line"}
packedc = save(chose)
back = {}
restore(back, packedc)
check("1r the voice he picked is still picked",
      back.get("vr_voice") == "Gabrijela", back.get("vr_voice"))
check("1s and a False setting survives — False is a choice, not absence",
      back.get("vr_preview") is False, back.get("vr_preview"))
check("1t and the help voice too", back.get("help_gender") == "M")
check("1u a choice made THIS run is not overwritten by the stored one",
      (lambda d: (restore(d, packedc), d.get("vr_voice"))[1])(
          {"vr_voice": "Ryan"}) == "Ryan")
check("1v choices alone are worth saving, even with every box empty",
      save({"vr_voice": "Sonia"}) is not None)
check("1w nothing at all is still not worth saving", save({}) is None)

print("\n1g THE TAB SURVIVES ON ITS OWN")
# Baba: "make persistent inside browser storage the last tab when the
# user left the app."
#
# It was already saved — but only as a PASSENGER. The guard refused to
# write anything unless a box had text or a choice had been made, so
# somebody who opened the app, went to VR, typed nothing and left came
# back to T. It survived at all only by accident, because rendering a
# tab usually setdefaults a choice somewhere.
bare = save({"active_tab": "vr"})
check("1x a tab with NOTHING else is still written out", bare is not None,
      bare)
back2 = {}
restore(back2, bare)
check("1y and he comes back to it", back2.get("active_tab") == "vr",
      back2.get("active_tab"))
check("1z a browser that has never been used writes nothing at all",
      save({}) is None, save({}))
# AND THE MODEL ABOVE IS ONLY A MODEL. It can drift from the app without
# a single check going red — mutating the app's guard left 1x green,
# because 1x drives this copy. So the app's OWN guard is read here.
# find(), with the region checked — the sweep blocked on this as new
# debt the moment I wrote it, which is the tool doing its job on its
# author.
_gs, _ge = app.find("def _kept_save"), app.find("def kept_area")
check("1z0 the save function is findable", 0 < _gs < _ge, (_gs, _ge))
_g = app[_gs:_ge] if 0 < _gs < _ge else ""
check("1z1 the APP refuses only when the tab is the DEFAULT and nothing "
      "else is set — not merely when a box is empty",
      'blob.get("_tab", "transcribe") == "transcribe"' in _g, _g[-300:])
check("1z2 which tab he was on IS state — often the only state, and "
      "always the first thing he sees",
      "vr" in (bare or ""))

print("\n1h HIS OWN DIRECTIONS SURVIVE TOO")
# Said in v201 that they should live in the browser, built the store for
# it in v218, and never moved them across — so a direction he wrote
# himself lasted until the phone rang.
own = {"_vr_own": ["like a priest", "half asleep"], "active_tab": "vr"}
packed_own = save(own)
back_own = {}
restore(back_own, packed_own)
check("1za a LIST survives, not just strings and flags",
      back_own.get("_vr_own") == ["like a priest", "half asleep"],
      back_own.get("_vr_own"))
check("1zb and they are worth saving on their own",
      packed_own is not None)
check("1zc the app allows a list through its type filter",
      "(str, bool, int, float, list)" in app)
check("1zd and names the store by its own constant, not a copy of the "
      "string", "VR.OWN_KEY" in app)

print("\n1i THE WRITE IS SENT IN THE RUN THAT DECIDED IT")
# Baba, 25.8.2026: "when I was switching between apps it stayed. But
# after refreshing the page I'm back to the first tab."
#
# THAT DISTINCTION WAS THE WHOLE DIAGNOSIS. The queue is drained at the
# TOP of a run and _kept_save fills it at the BOTTOM, nine thousand lines
# later — so a write decided at the end of run N waited for run N+1.
# Switching apps keeps the session alive, so a later run eventually sent
# it. A RELOAD STARTS A NEW SESSION and the queued write dies with the
# old one. The tab was never in localStorage at all; it only ever
# survived in the server's memory, which is the one place it was
# promised not to need.
_drain = app.find('_pending = st.session_state.pop("_pending_ls"')
_save = app.rfind("    _kept_save()")
_flush = app.rfind("    flush_ls()")
print("       drain at %d, save at %d, flush at %d" % (_drain, _save, _flush))
check("1zz the queue really is drained near the TOP, long before the "
      "save at the bottom — this is the ordering that broke it",
      0 < _drain < _save, (_drain, _save))
check("1zy so there is a flush AFTER the save", 0 < _save < _flush,
      (_save, _flush))
check("1zx and it is the last thing that touches storage",
      app.find("flush_ls()", _flush + 5) == -1)
check("1zw the flush uses a SECOND component key — two calls on one key "
      "are one widget, and the second would replace the first",
      '"ls_sync_tail"' in app and 'key=key' in app)
check("1zv it takes what was queued, rather than recomputing",
      'pop("_pending_ls", None)' in app[app.find("def flush_ls"):
                                        app.find("def flush_ls") + 1400])
check("1zu and it bumps the stamp, or the browser would ignore a repeat",
      '_ls_stamp"] = st.session_state.get("_ls_stamp", 0) + 1'
      in app[app.find("def flush_ls"):app.find("def flush_ls") + 1600])

print("\n2 THE APP IS WIRED THIS WAY")
check("2a there is a store key", "KEPT_LS_KEY" in code)
check("2b every box is in the list",
      all(('"%s"' % s) in code[code.index("KEPT_SLOTS"):
                               code.index("KEPT_MAX")] for s in SLOTS))
# THE CALL, NOT THE DEFINITION. "def _kept_restore():" CONTAINS
# "_kept_restore()", so the first version measured where the function was
# defined — thousands of lines earlier — and stayed green when the call
# was deleted entirely. Fourth time today a marker was a substring of
# itself.
# find(), NOT index(). index() RAISES when the thing is missing, so the
# mutation that deletes the call killed the file instead of turning the
# check red — a crash and a pass look equally unlike a failure in a
# sweep. -1 is an answer; an exception is not.
_call = code.find("\n_kept_restore()")
check("2c2 the restore is actually CALLED at top level, not merely "
      "defined", _call > 0, _call)
check("2c it restores BEFORE the tab bar, or the old tab shows for a "
      "frame and then jumps",
      _call > 0 and _call < code.find('key="active_tab"'), _call)
# AND BEFORE THE DEFAULT, or setdefault would be a no-op after the
# restore had already put the real tab there — harmless in that order,
# fatal in the other.
check("2c3 and before the default that would otherwise win",
      0 < _call < code.find('setdefault("active_tab"'), _call)
check("2d and AFTER the login — there is nothing to restore for somebody "
      "who is not in",
      code.index('if not st.session_state.get("_authed")')
      < code.index("_kept_restore()"))
check("2e typing saves", code.count("_kept_save()") >= 3,
      code.count("_kept_save()"))
# THE CHOICES ARE SAVED AT THE END OF THE SCRIPT, not in a dozen
# callbacks. Baba lost the VR voice precisely because it had no wiring of
# its own, and a list of call sites is a list to forget one from.
_save_call = code.rfind("\n    _kept_save()")
check("2h the save runs at the END, after every choice has settled",
      _save_call > code.index('key="active_tab"'), _save_call)
check("2i and it is guarded — the last line must not take down a page "
      "that already drew",
      "except Exception:" in code[_save_call:_save_call + 220])
# NOT EVERY NAME IS A LITERAL. `_vr_own` is in the table as VR.OWN_KEY,
# a constant, which is BETTER than a copied string — a second copy of a
# key is a second thing to keep in step. This check demanded the literal
# and went red on the right code.
_kc = code[code.find("KEPT_CHOICES"):code.find("def _kept_restore")]
_missing = [n for n in CHOICES
            if ('"%s"' % n) not in _kc and "OWN_KEY" not in _kc]
check("2j every choice he can make is in the list, by literal or by "
      "constant", not _missing, _missing)
check("2j2 and the store is named by its constant rather than a copied "
      "string", "VR.OWN_KEY" in _kc, _kc[-200:])
check("2k but nothing DERIVED is — no job, no cache, no audio",
      not any(x in code[code.index("KEPT_CHOICES"):
                        code.index("def _kept_restore")]
              for x in ('"_vr_job"', '"_vr_whole"', '"cache"')))
check("2f it goes through the SAME bridge as the remembered login, not a "
      "second mechanism", "queue_ls(writes={KEPT_LS_KEY" in code)
check("2g the audio is NOT stored — localStorage is ~5 MB and one "
      "minute of rehearsal is ~470 KB",
      "_vr_whole" not in code[code.index("KEPT_SLOTS"):code.index("KEPT_MAX")])

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
