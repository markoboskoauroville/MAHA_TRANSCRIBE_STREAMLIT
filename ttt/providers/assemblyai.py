"""AssemblyAI speech-to-text. Keyed, handles large files natively.

Because it takes a file of any size on its own, it does NOT need the
tiered chunking in ttt/audio.py — that machinery exists for Groq's 25MB
limit and stays where the limit is.
"""

import time

from .base import Model, Provider, http_json

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
        known = [
            Model("universal-3-pro", "Universal 3 Pro", for_task="stt",
                  recommended=True, note="most accurate"),
            Model("universal", "Universal", for_task="stt", note="faster"),
        ]
        return known, False, None

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
