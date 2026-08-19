"""DriveStore's text half — the client side of the paired archive.

Runs against a tiny stub of the Apps Script over real HTTP on localhost,
so the transport, the JSON shapes and the never-raises contract are all
exercised without Streamlit, without Google and without a key.

    python3 tests/test_drive_text.py
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ttt import drive  # noqa: E402

STORE = {}          # (user, rec_id) -> text
REGISTERED = set()  # (user, rec_id)
SEEN = []           # every request body the script received
MODE = {"fail": False, "no_file_id": False}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _reply(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n).decode())
        SEEN.append(body)

        if body.get("token") != "TOK":
            return self._reply({"ok": False, "error": "bad token"})
        if MODE["fail"]:
            return self._reply({"ok": False, "error": "boom"})

        what = body.get("what")
        key = (body.get("user"), body.get("rec_id"))

        if what == "audio_reg":
            REGISTERED.add(key)
            return self._reply({"ok": True})
        if what == "text_put":
            if key not in REGISTERED:
                return self._reply({"ok": False, "error": "no such recording"})
            STORE[key] = body.get("text", "")
            out = {"ok": True, "chars": len(STORE[key])}
            if not MODE["no_file_id"]:
                out["file_id"] = "f1"
            return self._reply(out)
        if what == "text_get":
            if key not in STORE:
                return self._reply({"ok": False, "error": "no text stored"})
            return self._reply({"ok": True, "text": STORE[key],
                                "chars": len(STORE[key])})
        return self._reply({"ok": False, "error": "unknown"})


srv = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:{}/".format(srv.server_port)

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   " + name)
    else:
        failed += 1
        print("  FAIL " + name + ("  — " + str(detail) if detail else ""))


def store(**kw):
    kw.setdefault("url", URL)
    kw.setdefault("token", "TOK")
    kw.setdefault("secret", "SEC")
    kw.setdefault("user", "baba")
    return drive.DriveStore(**kw)


print("DRIVE TEXT — client half\n")

# --- the round trip ---------------------------------------------------
d = store()
d._post({"what": "audio_reg", "rec_id": "r1"}, 15)
check("1 put_text succeeds", bool(d.put_text("r1", "Dobar dan")))
check("2 get_text returns it exactly", d.get_text("r1") == "Dobar dan",
      d.get_text("r1"))

hr = "ČčĆćŠšŽžĐđ — čekaj me u šumi"
d.put_text("r1", hr)
check("3 Croatian survives the HTTP round trip", d.get_text("r1") == hr)

# --- the rec_id is sanitised the same way as the audio path -----------
d._post({"what": "audio_reg", "rec_id": drive.safe_name("R2!!")}, 15)
d.put_text("R2!!", "x")
check("4 rec_id is safe_name'd, matching the audio path",
      SEEN[-1]["rec_id"] == "r2", SEEN[-1]["rec_id"])

# --- the ugly cases ---------------------------------------------------
check("5 get_text on a recording with no text returns None",
      d.get_text("never-existed") is None)

d.put_text("r1", "")
check("6 empty text is stored, not skipped", d.get_text("r1") == "")

d._post({"what": "audio_reg", "rec_id": "r3"}, 15)
d.put_text("r3", None)
check("7 None text becomes empty string, does not crash",
      d.get_text("r3") == "")

big = "x" * 200000
d._post({"what": "audio_reg", "rec_id": "r4"}, 15)
d.put_text("r4", big)
check("8 a 200,000-char transcript round trips", d.get_text("r4") == big)

check("9 unregistered recording is refused, and returns None",
      d.put_text("nope", "x") is None)

# --- never raises, never a dependency ---------------------------------
MODE["fail"] = True
check("10 a refusing script returns None, does not raise",
      d.put_text("r1", "x") is None and d.get_text("r1") is None)
MODE["fail"] = False

dead = store(url="http://127.0.0.1:1/")
check("11 an unreachable script returns None, does not raise",
      dead.put_text("r1", "x") is None and dead.get_text("r1") is None)
check("12 the failure is recorded for the log", bool(dead.last_error))

off = store(secret="")
check("13 a disabled store is a silent no-op",
      off.enabled is False and off.put_text("r1", "x") is None
      and off.get_text("r1") is None)

bad = store(token="WRONG")
check("14 a bad token cannot write", bad.put_text("r1", "x") is None)

# --- store() writes the text as part of the recording -----------------
before = len([b for b in SEEN if b.get("what") == "text_put"])


class FakeStore(drive.DriveStore):
    """Only the audio half is faked, so the ORDER under test is real."""

    def put_part(self, rec_id, part, raw):
        return {"ok": True, "file_id": "x", "folder_id": "fid"}


import tempfile  # noqa: E402

fs = FakeStore(url=URL, token="TOK", secret="SEC", user="baba")
tmp = tempfile.mkdtemp()
flac = os.path.join(tmp, "a.flac")
open(flac, "wb").write(b"\0" * 1000)

_orig_split = drive._audio.split_into_chunks
_orig_dur = drive._audio.duration_seconds
drive._audio.split_into_chunks = lambda p, **k: ([flac], None)
drive._audio.duration_seconds = lambda p: 1.0

rec = fs.store(flac, seconds=1.0, language="hr", text="stored with audio")
check("15 store() returns a rec_id", bool(rec), rec)
after = [b for b in SEEN if b.get("what") == "text_put"]
check("16 store() wrote the text too", len(after) > before)
check("17 the text landed under the SAME rec_id as the audio",
      after[-1]["rec_id"] == rec, "{} vs {}".format(after[-1]["rec_id"], rec))

order = [b["what"] for b in SEEN if b.get("what") in ("audio_reg", "text_put")]
check("18 registration comes BEFORE the text write",
      order[-2] == "audio_reg" and order[-1] == "text_put", order[-2:])

check("19 store() with no text writes no text_put",
      fs.store(flac, text="") and
      [b["what"] for b in SEEN][-1] == "audio_reg")

# A failing text write must NOT cost the audio.
MODE["fail"] = False
rec2 = None


class TextFails(FakeStore):
    def put_text(self, rec_id, text):
        return None


tf = TextFails(url=URL, token="TOK", secret="SEC", user="baba")
rec2 = tf.store(flac, text="this will fail to write")
check("20 a failed text write still returns the rec_id — audio is safe",
      bool(rec2), rec2)

drive._audio.split_into_chunks = _orig_split
drive._audio.duration_seconds = _orig_dur

print("\n{} passed, {} failed".format(passed, failed))
srv.shutdown()
sys.exit(1 if failed else 0)
