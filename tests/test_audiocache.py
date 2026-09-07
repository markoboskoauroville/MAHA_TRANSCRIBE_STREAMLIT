"""THE AUDIO KEPT ON THE MACHINE, PER PERSON (7.9.2026).

    python3 tests/test_audiocache.py

Marko: "audio kept on the machine per user with MB and delete for the user
(looks tab) and for the admin (portal)."

1  the store alone, in a temp folder: put, get, usage, count, clear, the cap
2  the app really consults it: _make looks the block up BEFORE building it
   and stores it AFTER (read off the source, comments stripped), and the
   looks tab draws the line and the delete only where the store is on
3  ugly: switched off (no path) everything is a quiet no; a user name with
   slashes cannot leave the folder; a broken .json is a miss, not a crash
4  upgrade: a person who never had a cache sees 0 bytes, 0 files, and the
   delete is dimmed rather than absent
"""
import importlib
import json
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def fresh(path, cap_mb="77"):
    os.environ["TTT_AUDIO_CACHE"] = path
    os.environ["TTT_AUDIO_CACHE_MB"] = cap_mb
    from ttt import audiocache
    return importlib.reload(audiocache)


tmp = tempfile.mkdtemp(prefix="ttt_ac_")
try:
    print("1 THE MECHANISM, ALONE")
    AC = fresh(os.path.join(tmp, "audio"))
    check("switched on when the path is set", AC.enabled())
    k1 = AC.key("marko", "google|Kore", "One sentence.")
    k2 = AC.key("marko", "google|Kore", "One sentence")
    k3 = AC.key("marko", "google|Puck", "One sentence.")
    k4 = AC.key("emina", "google|Kore", "One sentence.")
    check("a key is 64 hex characters", re.fullmatch(r"[0-9a-f]{64}", k1) is not None, k1)
    check("a changed word is another key", k1 != k2)
    check("another voice is another key", k1 != k3)
    check("another person is another key", k1 != k4)
    check("the same input is the same key", AC.key("marko", "google|Kore", "One sentence.") == k1)
    check("a miss is None", AC.get("marko", k1) is None)
    check("put returns True", AC.put("marko", k1, b"\x00" * 1000, [{"word": "One", "start": 0}]))
    got = AC.get("marko", k1)
    check("get returns audio and marks", got and got["audio"] == b"\x00" * 1000 and got["marks"][0]["word"] == "One", got)
    check("usage counts the bytes", AC.usage("marko") == 1000, AC.usage("marko"))
    check("count counts the files", AC.count("marko") == 1)
    check("another person holds nothing", AC.usage("emina") == 0 and AC.count("emina") == 0)
    AC.put("marko", k3, b"\x01" * 500, [])
    check("two blocks, 1500 bytes", AC.usage("marko") == 1500 and AC.count("marko") == 2)
    allu = AC.usage_all()
    check("usage_all lists the person with bytes and files", allu.get("marko") == {"bytes": 1500, "files": 2}, allu)
    freed = AC.clear("marko")
    check("clear frees the bytes", freed == 1500, freed)
    check("and nothing is left", AC.usage("marko") == 0 and AC.count("marko") == 0 and AC.get("marko", k1) is None)
    check("clearing twice is a quiet 0", AC.clear("marko") == 0)

    # THE CAP: 77 MB by default; here 0.002 MB so three 1000-byte blocks overflow
    AC = fresh(os.path.join(tmp, "audio2"), cap_mb="0.002")
    AC.put("p", "a" * 64, b"x" * 1000, [])
    AC.put("p", "b" * 64, b"x" * 1000, [])
    check("under the cap both stay", AC.count("p") == 2)
    import time
    time.sleep(0.05)
    os.utime(os.path.join(AC._dir("p"), "a" * 64 + ".bin"), (1, 1))     # a is the oldest
    AC.put("p", "c" * 64, b"x" * 1000, [])
    check("over the cap the oldest goes", AC.count("p") == 2 and AC.get("p", "a" * 64) is None, AC.count("p"))
    check("and the newest stays", AC.get("p", "c" * 64) is not None)

    print("2 THE APP USES IT")
    ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    raw = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    code = "\n".join(l for l in raw.splitlines() if not l.lstrip().startswith("#"))
    code = re.sub(r'"""(?:.|\n)*?"""', "", code)
    m = re.search(r"def _make\(i\):(?:.|\n)*?return job\[\"cache\"\]\[i\]", code)
    check("_make(i) is there", m is not None)
    body = m.group(0) if m else ""
    look = body.find("AUDIOCACHE.get(")
    build = body.find("SPEECH.build_part(")
    store = body.find("AUDIOCACHE.put(")
    check("the cache is looked up BEFORE the block is built", 0 <= look < build, (look, build))
    check("and the block is stored AFTER it is built", build < store, (build, store))
    check("the key is the person, the voice signature and the words",
          "AUDIOCACHE.key(_who, _voice_signature(engine)" in body)
    sig = re.search(r"def _voice_signature\(engine\)(?:.|\n)*?\n\n", code)
    check("the voice signature carries every voice setting",
          sig and all(k in sig.group(0) for k in ("google_voice", "sp_voice", "sp_model", '"voice"')))
    looks = code[code.find('elif active == "looks":'):code.find('elif active == "help":')]
    check("the looks tab draws the line only where the store is on and there is a person",
          "if AUDIOCACHE.enabled() and _ac_user:" in looks)
    check("the line says the MB and the files", 'AUDIOCACHE.usage(_ac_user)' in looks and 'AUDIOCACHE.count(_ac_user)' in looks)
    check("the delete calls clear for that person", "AUDIOCACHE.clear(u)" in looks)
    check("the delete is dimmed, not absent, when there is nothing",
          "disabled=AUDIOCACHE.count(_ac_user) == 0" in looks)
    labels = raw[raw.find('"looks_audio"'):raw.find('"looks_audio_gone"') + 200]
    check("the labels exist in both languages", labels.count('"hr"') >= 3 and labels.count('"en"') >= 3)

    print("3 THE UGLY CASES")
    AC = fresh("")
    check("switched off: enabled is False", not AC.enabled())
    check("switched off: put is a quiet False", AC.put("marko", "k", b"x", []) is False)
    check("switched off: get is None, usage 0, clear 0, usage_all {}",
          AC.get("marko", "k") is None and AC.usage("marko") == 0 and AC.clear("marko") == 0 and AC.usage_all() == {})
    AC = fresh(os.path.join(tmp, "audio3"))
    AC.put("../../evil", "k" * 64, b"x", [])
    check("a name with slashes cannot leave the folder",
          os.path.isdir(os.path.join(tmp, "audio3")) and not os.path.exists(os.path.join(tmp, "evil"))
          and all(os.path.commonpath([os.path.join(tmp, "audio3"), os.path.join(tmp, "audio3", d)]) == os.path.join(tmp, "audio3")
                  for d in os.listdir(os.path.join(tmp, "audio3"))))
    AC.put("marko", "j" * 64, b"x" * 10, [])
    with open(os.path.join(AC._dir("marko"), "j" * 64 + ".json"), "w") as fh:
        fh.write("{not json")
    check("a broken marks file is a miss, not a crash", AC.get("marko", "j" * 64) is None)
    check("an empty audio is not stored", AC.put("marko", "e" * 64, b"", []) is False)
    check("no person: nothing stored", AC.put("", "e" * 64, b"x", []) is False)
    check("usage_all survives a stray file in the root", (open(os.path.join(tmp, "audio3", "stray.txt"), "w").write("x") or True)
          and "stray.txt" not in AC.usage_all())

    print("4 UPGRADE")
    check("a person who never had a cache: 0 bytes, 0 files", AC.usage("newbie") == 0 and AC.count("newbie") == 0)
    check("and the json stored is a list even when marks were None",
          AC.put("n", "m" * 64, b"x", None) and json.load(open(os.path.join(AC._dir("n"), "m" * 64 + ".json"))) == [])
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("TTT_AUDIO_CACHE", None)
    os.environ.pop("TTT_AUDIO_CACHE_MB", None)

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
