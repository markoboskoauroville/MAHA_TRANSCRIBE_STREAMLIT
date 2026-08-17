"""Read the text out of a picture.

A photo of a letter, a screenshot of an email, a page of a form — the
person points at it and gets text they can enlarge, have read aloud, or
translate. For someone who cannot read a printed page, this is arguably
the most useful thing in the app.

THE MODEL IS DISCOVERED, NEVER HARDCODED. Groq's own model list reports
`input_modalities` per model, so the vision-capable one is found by asking
for a model that accepts images. Today exactly one does
(qwen/qwen3.6-27b); when Groq adds another, or renames that one, this
keeps working with no edit. Hardcoding the name would have it break
silently on a model rename, which is the failure this project keeps
learning about.

TWO TRAPS, both measured against the live API rather than assumed:

  1. THE THINKING BLOCK EATS THE ANSWER. That model is a reasoning model
     and wraps its output in <think>…</think>. With a normal token budget
     the reasoning consumed ALL of it and the reply came back containing
     nothing but an unterminated think block — stripping it client-side
     left an empty string. The fix is server-side:
     `reasoning_format: "hidden"`, which Groq applies before the response
     is built. Verified: same request with it returns clean text.
     `strip_think()` is kept anyway as a belt-and-braces for any model
     that ignores the parameter.
  2. IT INVENTS REPEATS. Asked loosely to "transcribe all text", it
     reported the same letter three times, describing imaginary "blocks"
     and cut-off fragments that were not in the image. The prompt says
     ONCE, in reading order, and forbids guessing at anything unclear —
     a transcript that quietly doubles itself is worse than one that
     stops short, because nobody proof-reads what they cannot read.
"""

import base64
import re

# What an image-capable model is asked to do. Deliberately an OCR
# instruction rather than "describe this": the person wants the words on
# the page, not a summary of the picture.
OCR_PROMPT = (
    "Transcribe the printed or handwritten text in this image. "
    "Output the text ONCE, in reading order, exactly as it appears. "
    "Do not repeat any line. Do not describe the image. Do not add "
    "commentary, headings or explanation. If part of the text is unclear, "
    "leave it out rather than guessing."
)

DESCRIBE_PROMPT = (
    "Describe what is in this image, plainly and briefly, for someone who "
    "cannot see it. Two or three sentences. No preamble."
)

MAX_BYTES = 4 * 1024 * 1024      # keep the base64 payload sane
_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
_THINK_OPEN = re.compile(r"<think>.*", re.S | re.I)


def strip_think(text: str) -> str:
    """Remove a reasoning block if one survives the API parameter."""
    s = _THINK.sub("", text or "")
    s = _THINK_OPEN.sub("", s)
    return s.strip()


def find_vision_models(models) -> list:
    """Models that accept images, from whatever the provider reported.

    `models` is the list of dicts as Groq returns them, so this reads the
    provider's own declaration rather than a name we chose.
    """
    out = []
    for m in models or []:
        if "image" in (m.get("input_modalities") or []):
            if m.get("active") is not False and m.get("id"):
                out.append(m["id"])
    return out


def data_url(raw: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def mime_for(filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if name.endswith(".webp"):
        return "image/webp"
    if name.endswith(".gif"):
        return "image/gif"
    return "image/png"


def build_payload(model: str, image_bytes: bytes, mime: str,
                  prompt: str = OCR_PROMPT, max_tokens: int = 2000) -> dict:
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        # The parameter that makes this usable at all — see the module note.
        "reasoning_format": "hidden",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url",
             "image_url": {"url": data_url(image_bytes, mime)}},
        ]}],
    }


def read_image(call, model: str, image_bytes: bytes, filename: str = "",
               prompt: str = OCR_PROMPT) -> str:
    """`call(payload) -> (data, error)` is supplied by the caller, so this
    module never touches a key or a key ring."""
    if not image_bytes:
        raise ValueError("no image")
    if len(image_bytes) > MAX_BYTES:
        raise ValueError(
            f"image too large ({len(image_bytes) // 1024} KB, limit "
            f"{MAX_BYTES // 1024} KB)")
    payload = build_payload(model, image_bytes, mime_for(filename), prompt)
    data, err = call(payload)
    if err:
        raise RuntimeError(err)
    text = (data["choices"][0]["message"]["content"] or "")
    return strip_think(text)
