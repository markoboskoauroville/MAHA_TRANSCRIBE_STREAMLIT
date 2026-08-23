"""Drive audio storage — the client half.

Keeps the levelled 16 kHz audio in Baba's Drive so that changing the
language and transcribing again costs no upload from the phone. The
phone uploads once; everything after that is Streamlit's datacentre
talking to Google's.

THIS MODULE NEVER RAISES AND IS NEVER A DEPENDENCY. Storage failing must
never cost someone their transcript, so every call returns None or [] on
failure and the caller carries on with the audio it already has in hand.

WHY THE AUDIO COMES BACK AS BASE64. Apps Script's ContentService can only
serve text — there is no way to hand raw bytes back from a web app. So the
part is base64 in the JSON, decoded here, and passed to Whisper by this
process. Checked against the ContentService docs before building; it is a
platform limit, not a preference.

WHY TWO SECRETS. SHEETS_TOKEN unlocks the settings and the API keys.
Download links are the part most likely to end up in a log, so they carry
a separate short-lived signature made with DRIVE_SECRET. Losing one must
never cost the other.

MEASURED LIMITS, 18.8.2026, against the live deployment:
  * the platform refuses a request body over 52,428,800 bytes (50 MiB)
    exactly — 50 MiB passes, one KB more is HTTP 400
  * 16-bit 16 kHz FLAC runs about 17,200 bytes per second of speech
  * so one 10-minute part is ~10.3 MB, ~13.7 MB as base64, about a
    quarter of the envelope — which is why parts are 10 minutes and why
    there is no chunk-reassembly protocol to get wrong
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from . import audio as _audio

# Deadlines. Every wait on anything outside this process needs one, or a
# call that neither answers nor refuses hangs the app forever — no catch
# handler is ever reached, because nothing was ever thrown.
TIMEOUT_SMALL = 15      # list, register, delete
TIMEOUT_PART = 180      # one part up or down, on a bad phone network

LINK_SECONDS = 300      # how long a signed link we mint stays good
MAX_PART_B64 = 40 * 1024 * 1024   # matches MAX_PART_BYTES in the script


def safe_name(s) -> str:
    """MUST match safeName_ in drive_addition.gs character for character.

    The signature is computed over the SANITISED rec_id, so if these two
    disagree the script answers "bad signature" for a recording that
    plainly exists — which reads like a broken secret and is not. There
    is a test that runs both implementations over the same inputs.
    """
    return re.sub(r"[^a-z0-9_\-]", "", str(s or "").lower())[:60]


def new_rec_id() -> str:
    """Lowercase hex and a timestamp: already safe, so safe_name() is the
    identity on it and the signing trap above cannot arise in practice."""
    return time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4)


def sign_part(secret: str, rec_id: str, part, exp: int) -> str:
    msg = "{}|{}|{}".format(safe_name(rec_id), part, exp)
    return hmac.new(str(secret).encode("utf-8"), msg.encode("utf-8"),
                    hashlib.sha256).hexdigest()


class DriveStore:
    """Talks to the Apps Script. Construct it even when storage is off —
    `enabled` is False and every method becomes a cheap no-op, so callers
    never need an `if` around it."""

    def __init__(self, url: str = "", token: str = "", secret: str = "",
                 user: str = "", enabled: bool = True):
        self.url = str(url or "")
        self.token = str(token or "")
        self.secret = str(secret or "")
        self.user = safe_name(user) or "unknown"
        self.enabled = bool(enabled and self.url and self.token and self.secret)
        self.last_error = ""

    # -- transport ------------------------------------------------------

    def _post(self, payload: dict, timeout: int):
        if not self.enabled:
            return None
        payload = dict(payload)
        payload["token"] = self.token
        payload["user"] = self.user
        try:
            req = urllib.request.Request(
                self.url, data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read().decode("utf-8"))
            if not out.get("ok"):
                self.last_error = str(out.get("error", "refused"))
                return None
            return out
        except Exception as err:                      # never raises
            self.last_error = "{}: {}".format(type(err).__name__, err)[:200]
            return None

    def _get(self, params: dict, timeout: int):
        if not self.enabled:
            return None
        try:
            qs = urllib.parse.urlencode(params)
            with urllib.request.urlopen(self.url + "?" + qs, timeout=timeout) as r:
                out = json.loads(r.read().decode("utf-8"))
            if not out.get("ok"):
                self.last_error = str(out.get("error", "refused"))
                return None
            return out
        except Exception as err:
            self.last_error = "{}: {}".format(type(err).__name__, err)[:200]
            return None

    # -- one part -------------------------------------------------------

    def put_part(self, rec_id: str, part: int, raw: bytes):
        b64 = base64.b64encode(raw).decode("ascii")
        if len(b64) > MAX_PART_B64:
            # Refuse here rather than let the platform return an opaque
            # HTTP 400 after pushing 40 MB up a phone connection.
            self.last_error = "part too large: {} bytes as base64".format(len(b64))
            return None
        out = self._post({"what": "audio_put", "rec_id": safe_name(rec_id),
                          "part": int(part), "data": b64}, TIMEOUT_PART)
        # PROVE IT WAS ACTUALLY STORED, do not settle for ok:true.
        #
        # A deployment WITHOUT the audio routing does not reject an
        # audio_put — it falls through to the usage-logging appendRow and
        # answers {ok:true}. So the app believed a recording was safe in
        # Drive while the script had written a junk usage row and thrown
        # the audio away. Measured against the live script, 19.8.2026.
        #
        # A real store returns a file_id. Nothing else does.
        if out is not None and not out.get("file_id"):
            self.last_error = ("the deployed script has no audio storage — "
                               "push and deploy a New version")
            return None
        return out

    def get_part(self, rec_id: str, part: int):
        """Returns the part's bytes, or None."""
        rec = safe_name(rec_id)
        exp = int(time.time()) + LINK_SECONDS
        out = self._get({"what": "audio", "user": self.user, "rec_id": rec,
                         "part": int(part), "exp": exp,
                         "sig": sign_part(self.secret, rec, int(part), exp)},
                        TIMEOUT_PART)
        if not out:
            return None
        try:
            return base64.b64decode(out.get("data", ""), validate=True)
        except (binascii.Error, ValueError) as err:
            self.last_error = "corrupt part: {}".format(err)
            return None

    # -- the transcript, stored beside the audio -------------------------
    #
    # THEY GO IN PAIRS. The text is a file inside the recording's own
    # folder, not a sheet cell, so trashing the folder removes both at
    # once and they cannot come apart. A cell would also truncate a long
    # transcript at the sheet's 50,000-character ceiling.
    #
    # No signature here, unlike get_part. A signed link exists because a
    # download URL is the thing most likely to end up in a log; this goes
    # through doPost under SHEETS_TOKEN like every other write, so losing
    # DRIVE_SECRET still cannot open anyone's text.

    def put_text(self, rec_id: str, text: str):
        """Write the transcript. Replaces any earlier one, so a
        retranscribe leaves exactly one text.txt. Returns the response or
        None."""
        return self._post({"what": "text_put", "rec_id": safe_name(rec_id),
                           "text": "" if text is None else str(text)},
                          TIMEOUT_SMALL)

    # -- the notebook ----------------------------------------------------
    #
    # NOT put_text. That one refuses a rec_id with no row in the index,
    # deliberately: text for an unknown recording would be half of a
    # pair that must never exist. A notebook is not half of a pair — it
    # belongs to the PERSON, so it sits beside their recordings rather
    # than inside one, as a plain notes.txt anybody can open.

    def put_notes(self, text: str):
        """Write the whole notebook. Replaces what was there."""
        return self._post({"what": "notes_put",
                           "text": "" if text is None else str(text)},
                          TIMEOUT_SMALL)

    def get_notes(self):
        """Read it back. None means no notebook stored — which is not the
        same as a failure, and both look like None here, so the caller
        must treat a missing notebook as 'nothing yet' either way."""
        out = self._post({"what": "notes_get"}, TIMEOUT_SMALL)
        if not out:
            return None
        text = out.get("text")
        return None if text is None else str(text)

    def get_text(self, rec_id: str):
        """Read the transcript back — instant and free, against a
        retranscribe which costs a fetch and a Whisper call. Returns the
        text, or None when there is none stored."""
        out = self._post({"what": "text_get", "rec_id": safe_name(rec_id)},
                         TIMEOUT_SMALL)
        if not out:
            return None
        text = out.get("text")
        return None if text is None else str(text)

    # -- whole recordings -----------------------------------------------

    def store(self, flac_path: str, seconds: float = 0.0,
              language: str = "", note: str = "", text: str = ""):
        """Split the levelled FLAC into parts, upload each, then register.

        Registration happens LAST and on purpose: a recording that appears
        in the archive must be one whose audio is actually all there. A
        half-uploaded recording leaves orphan files in Drive and no row,
        which is the harmless direction to fail in.

        Returns the rec_id, or None.
        """
        if not self.enabled:
            return None
        rec_id = new_rec_id()
        parts, tmp = [], None
        try:
            parts, tmp = _audio.split_into_chunks(flac_path)
            if not parts:
                self.last_error = "nothing to store"
                return None
            folder_id = ""
            for i, p in enumerate(parts):
                with open(p, "rb") as fh:
                    res = self.put_part(rec_id, i, fh.read())
                if not res:
                    return None            # last_error already set
                folder_id = res.get("folder_id", folder_id)
            ok = self._post({"what": "audio_reg", "rec_id": rec_id,
                             "seconds": float(seconds or
                                              _audio.duration_seconds(flac_path)),
                             "parts": len(parts), "folder_id": folder_id,
                             "language": language, "note": note},
                            TIMEOUT_SMALL)
            if not ok:
                return None
            # AFTER registration, because putText_ updates has_text and
            # chars on the row and the row must exist for it to find.
            #
            # A failed text write does NOT fail the store. The audio is
            # safe, the row is correct, and has_text stays FALSE — so the
            # list offers "retranscribe" for this recording instead of
            # "pull", which is the honest answer rather than a row that
            # promises text nobody can fetch.
            if text:
                self.put_text(rec_id, text)
            return rec_id
        except Exception as err:
            self.last_error = "{}: {}".format(type(err).__name__, err)[:200]
            return None
        finally:
            if tmp:
                _audio.cleanup(tmp)

    def fetch(self, rec_id: str, parts: int, out_dir: str, on_part=None):
        """Pull every part back down as files. Returns paths in order, or
        [] — never a partial list, because a partial list transcribes to a
        confident transcript with a hole in the middle, and nothing in the
        result would show that anything was missing."""
        got = []
        total = int(parts or 0)
        for i in range(total):
            # SAY WHICH PART IS COMING BEFORE IT COMES. A caller that
            # wants to narrate needs the number BEFORE the wait, not
            # after — announcing "part 2 of 3" once part 2 has already
            # arrived tells somebody about a wait that is over.
            if on_part:
                # THE PART ABOUT TO BE FETCHED IS 1-BASED AND ITS SIZE IS
                # UNKNOWN. Passing `i` and 0 read on screen as "part 0 of
                # 3 · 0 KB" — a number nobody counts from and a size that
                # looks like a failure. `i + 1` with size None says
                # "starting this one", and the caller can tell the two
                # apart because only the finished call carries a size.
                on_part(i + 1, total, None)
            raw = self.get_part(rec_id, i)
            if raw is None:
                for p in got:
                    try:
                        os.remove(p)
                    except OSError:
                        pass
                return []
            p = os.path.join(out_dir, "part_{:04d}.flac".format(i))
            with open(p, "wb") as fh:
                fh.write(raw)
            got.append(p)
            # And again with the size, now that it is known.
            if on_part:
                on_part(i + 1, total, len(raw))
        return got

    def list(self):
        out = self._post({"what": "audio_list"}, TIMEOUT_SMALL)
        return (out or {}).get("recordings", []) or []

    def delete(self, rec_id: str) -> bool:
        return bool(self._post({"what": "audio_del",
                                "rec_id": safe_name(rec_id)}, TIMEOUT_SMALL))
