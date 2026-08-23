"""AssemblyAI speech-to-text. Keyed, handles large files natively.

Because it takes a file of any size on its own, it does NOT need the
tiered chunking in ttt/audio.py — that machinery exists for Groq's 25MB
limit and stays where the limit is.
"""

import os
import time

from .base import Model, Provider, http_json


# ---- WHAT ASSEMBLYAI COSTS -------------------------------------------
#
# Baba's own figures, and they check out against the $50 a new account
# starts with: 50 / 0.21 = 238 hours, 50 / 0.15 = 333 hours. Both match
# the numbers he quoted, which is why these are written down as fact
# rather than left editable — the earlier plan was a settings box for the
# rate, and that was me hedging because I had found three different
# prices on the web. He has the real ones.
#
# THEY STILL LIVE IN ONE PLACE. If AssemblyAI changes a price, this is
# the only line to change, and the picker note, the hours-left figure and
# the cost-so-far all follow it.
ASYNC_MODEL = "universal-3-5-pro"      # pre-recorded, the slow safe path
SYNC_MODEL_ID = "universal-streaming"   # real-time, the fast short path

RATE_PER_HOUR = {
    ASYNC_MODEL: 0.21,
    SYNC_MODEL_ID: 0.15,
}

# What a new AssemblyAI account is given. Used only to fill the box the
# first time — once somebody has topped up, what they have is theirs to
# say, not ours to assume.
FREE_CREDIT_USD = 50.0


def hours_for(usd: float, model: str = ASYNC_MODEL) -> float:
    """How many hours `usd` buys on this model. The whole arithmetic."""
    rate = RATE_PER_HOUR.get(model, RATE_PER_HOUR[ASYNC_MODEL])
    try:
        return max(0.0, float(usd)) / rate
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def cost_of(seconds: float, model: str = ASYNC_MODEL) -> float:
    """What `seconds` of audio cost on this model."""
    rate = RATE_PER_HOUR.get(model, RATE_PER_HOUR[ASYNC_MODEL])
    try:
        return max(0.0, float(seconds)) / 3600.0 * rate
    except (TypeError, ValueError):
        return 0.0

API = "https://api.assemblyai.com"


def _classify(status: int) -> str:
    if status in (401, 403):
        return "dead"
    if status == 429:
        return "cool"
    return "soft"


class AssemblyAI(Provider):
    id = "assemblyai"
    label = "AssemblyAI"
    capabilities = ("stt",)
    needs_key = True
    # 32 hex characters, no distinctive prefix (Key_Tester's KeyParser:
    # "HEX32 -> assemblyai"). An empty tuple sends every candidate down the
    # key ring's generic fallback path, which is correct here.
    key_prefixes = ()

    def _call(self, key, path, payload=None, method="GET", data=None, timeout=60):
        headers = {"authorization": key}
        if data is not None:
            headers["content-type"] = "application/octet-stream"
        return http_json(API + path, headers, payload=payload, data=data,
                         method=method, timeout=timeout, classify=_classify)

    def models(self, task: str = "", fetch=None):
        """AssemblyAI has NO model-list endpoint — /v2/models,
        /v2/transcript/models and /lemur/v3/models were all checked
        against the live API and answer 404 or an unrelated error. So this
        list is written down, and returns live=False so the picker says
        so instead of implying it was fetched. If they add an endpoint,
        this is the one method to change.
        """
        # TWO MODELS AND NO OTHERS. Baba: "we're going to use only these
        # 2 models. You need to restrict on these 2 models only."
        #
        # `universal-3-pro` and plain `universal` were here and are gone.
        # A picker that offers models nobody has priced is a picker that
        # can produce a bill nobody expected — and the whole point of the
        # hours-left figure is that every path has a known rate.
        known = [
            Model(ASYNC_MODEL, "Universal 3.5 Pro", for_task="stt",
                  recommended=True,
                  note="pre-recorded · $%.2f/hr" % RATE_PER_HOUR[ASYNC_MODEL]),
            Model(SYNC_MODEL_ID, "Universal Streaming", for_task="stt",
                  note="fast, short clips · $%.2f/hr"
                       % RATE_PER_HOUR[SYNC_MODEL_ID]),
        ]
        return known, False, None

    # ---- THE SYNC PATH ---------------------------------------------
    #
    # Ported from TTT mini's MaProviders, on Baba's instruction to use it
    # as the model. Its reasoning is better than anything I would have
    # arrived at here, so the rules come across intact and so do the
    # reasons.
    #
    # AN ALLOW-LIST, NOT A DENY-LIST, and that direction is the whole
    # point. AssemblyAI's own sync endpoint does not accept `hr` at all —
    # its language list is en, es, de, fr, it, pt, tr, nl, sv, no, da,
    # fi, hi, vi, ar, he, ja, ur, zh — so Croatian sent up that path
    # comes back as FLUENT CROATIAN THAT IS THE WRONG WORDS. Not
    # garbled, not empty, not obviously broken: plausible sentences
    # nobody would question without knowing what was said.
    #
    # A wrong answer that looks right is worse than an error, because
    # there is nothing to notice. So only a language whose sync output
    # somebody has actually READ belongs on this list, and today that is
    # English alone.
    SYNC_SAFE_LANGUAGES = frozenset({"en"})

    SYNC_URL = "https://sync.assemblyai.com/transcribe"
    # THE SYNC ENDPOINT SENDS Universal 3.5 Pro — that is what TTT mini
    # puts in its X-AAI-Model header, read from its source rather than
    # assumed. Which of the two RATES that endpoint bills at is the one
    # thing here I have not been able to verify, so `cost_of` is called
    # with the model actually sent, and a real invoice should be checked
    # against it once. Guessing quietly would put a wrong number under
    # "hours left", which is the number he asked for.
    SYNC_MODEL = ASYNC_MODEL
    SYNC_MAX_SECONDS = 120.0
    SYNC_MAX_BYTES = 40 * 1024 * 1024
    # The endpoint rejects anything under 80 ms as too short, so half a
    # second is a comfortable floor for something meant to be speech.
    MIN_SYNC_SECONDS = 0.5
    # The service rejects at 120 s and our figure is CALCULATED from the
    # file while theirs is measured, so the last two seconds are left as
    # room for the two to disagree.
    SYNC_SECONDS_MARGIN = 2.0

    def use_sync(self, language: str, path: str, seconds=None) -> bool:
        """Whether this recording goes up the sync path.

        EVERY CONDITION HERE IS A REASON TO SAY NO, and that asymmetry is
        deliberate — TTT mini's words, and they are right: "Fast is a
        preference; arriving is not." A recording that cannot take the
        fast path takes the slow one and nobody is told, because the only
        difference anybody can see is how long the words take.

        AUTO COLLAPSES TO NO. A language this app has not been told is
        English is treated as one that might be Croatian, and the safe
        answer to "might be" is async. That is the same choice TTT mini
        makes for an install still carrying an old "detect" setting.
        """
        if str(language or "").lower() not in self.SYNC_SAFE_LANGUAGES:
            return False
        try:
            if os.path.getsize(path) > self.SYNC_MAX_BYTES:
                return False
        except OSError:
            return False
        # NOT KNOWING HOW LONG THE AUDIO IS COUNTS AS TOO LONG. A header
        # that will not parse is not a thing to gamble a dictation on.
        if seconds is None:
            return False
        try:
            secs = float(seconds)
        except (TypeError, ValueError):
            return False
        return (secs >= self.MIN_SYNC_SECONDS
                and secs <= self.SYNC_MAX_SECONDS - self.SYNC_SECONDS_MARGIN)

    def test_key(self, key: str):
        _, err, kind = self._call(key, "/v2/transcript?limit=1", timeout=30)
        return err, kind

    def transcribe(self, rotate, path: str, language: str = "hr",
                   model: str = "universal-3-pro", progress_cb=None,
                   poll_timeout: int = 7200):
        """Upload, submit, poll. Each step goes through the ring, so a key
        that dies mid-job hands over to the next one."""
        with open(path, "rb") as f:
            audio_bytes = f.read()

        if progress_cb:
            progress_cb("upload")
        up, err = rotate(lambda k: self._call(k, "/v2/upload", method="POST",
                                              data=audio_bytes, timeout=1800))
        if err:
            raise RuntimeError(err)

        cfg = {"audio_url": up["upload_url"], "speech_models": [model]}
        if language == "auto":
            cfg["language_detection"] = True
        else:
            cfg["language_code"] = language

        if progress_cb:
            progress_cb("queue")
        job, err = rotate(lambda k: self._call(k, "/v2/transcript", payload=cfg,
                                               method="POST"))
        if err:
            raise RuntimeError(err)
        tid = job["id"]

        if progress_cb:
            progress_cb("process")
        t0 = time.time()
        while time.time() - t0 < poll_timeout:
            # Back off gently: snappy at first, calm once it is clearly a
            # long job, so a short clip returns fast without hammering.
            elapsed = time.time() - t0
            time.sleep(0.6 if elapsed < 4 else (1.2 if elapsed < 12 else 3.0))
            data, err = rotate(lambda k: self._call(k, "/v2/transcript/" + tid))
            if err:
                raise RuntimeError(err)
            status = data.get("status")
            if status == "completed":
                return (data.get("text") or "").strip()
            if status == "error":
                raise RuntimeError(data.get("error") or "AssemblyAI reported an error")
        raise RuntimeError("AssemblyAI took too long.")
