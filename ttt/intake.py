"""Where does this file go?

Everything now arrives through one door — the deck's fourth cell and the
recorder both hand back the same shape — so something has to decide what
a file IS before anything tries to read it. Getting that wrong is loud and
confusing: a PNG handed to ffmpeg produces a codec error about audio
streams, which tells the person nothing about what they actually did.

DECIDED BY CONTENT FIRST, NAME SECOND. A phone will happily hand over
`recording.wav` that is really an m4a, and Android's share sheet sometimes
supplies no extension at all. Magic bytes do not lie; extensions do.

This module knows nothing about Streamlit or about any provider. It says
what a thing is and what should happen to it, and the caller does it —
which is what makes the rules testable without a browser or a key.
"""

# What the pipelines are called. The caller maps these to real work.
AUDIO = "audio"        # transcode, then transcribe (chunking if large)
VIDEO = "video"        # same, ffmpeg takes the audio track out
IMAGE = "image"        # read the text out of the picture
TEXT = "text"          # already words; straight into the box
UNKNOWN = "unknown"    # say so plainly rather than guess

# Magic numbers, longest first so a more specific match wins.
_MAGIC = [
    (b"\x00\x00\x00\x18ftyp", VIDEO), (b"\x00\x00\x00\x20ftyp", VIDEO),
    (b"OggS", AUDIO), (b"fLaC", AUDIO), (b"RIFF", AUDIO), (b"ID3", AUDIO),
    (b"\x1aE\xdf\xa3", VIDEO),          # matroska/webm — could be either
    (b"\xff\xd8\xff", IMAGE), (b"\x89PNG", IMAGE), (b"GIF8", IMAGE),
    (b"BM", IMAGE), (b"II*\x00", IMAGE), (b"MM\x00*", IMAGE),
    (b"%PDF", TEXT),
]

_EXT = {
    "mp3": AUDIO, "wav": AUDIO, "m4a": AUDIO, "aac": AUDIO, "ogg": AUDIO,
    "oga": AUDIO, "opus": AUDIO, "flac": AUDIO, "wma": AUDIO, "amr": AUDIO,
    "aiff": AUDIO, "caf": AUDIO, "3gp": AUDIO,
    "mp4": VIDEO, "mov": VIDEO, "mkv": VIDEO, "avi": VIDEO, "webm": VIDEO,
    "m4v": VIDEO, "mpg": VIDEO, "mpeg": VIDEO, "wmv": VIDEO,
    "jpg": IMAGE, "jpeg": IMAGE, "png": IMAGE, "gif": IMAGE, "bmp": IMAGE,
    "webp": IMAGE, "heic": IMAGE, "heif": IMAGE, "tif": IMAGE, "tiff": IMAGE,
    "txt": TEXT, "md": TEXT, "csv": TEXT, "json": TEXT, "srt": TEXT,
    "vtt": TEXT, "rtf": TEXT, "pdf": TEXT,
}


def _ext_of(name):
    n = str(name or "").strip().lower()
    return n.rsplit(".", 1)[-1] if "." in n else ""


def kind_of(name="", mime="", head=b""):
    """AUDIO / VIDEO / IMAGE / TEXT / UNKNOWN.

    Order matters: content, then declared mime, then the extension. A webm
    from the deck is a container that could hold either, so it is resolved
    by mime when the browser told us, and treated as audio otherwise —
    which is right, because the deck only ever records sound into it.
    """
    head = bytes(head or b"")
    mime = str(mime or "").lower()

    if head.startswith(b"\x1aE\xdf\xa3"):        # matroska/webm
        if mime.startswith("video/"):
            return VIDEO
        return AUDIO
    for sig, kind in _MAGIC:
        if head.startswith(sig):
            # RIFF is also AVI and WEBP; look further in
            if sig == b"RIFF" and len(head) >= 12:
                tag = head[8:12]
                if tag == b"AVI ":
                    return VIDEO
                if tag == b"WEBP":
                    return IMAGE
            return kind

    if mime.startswith("audio/"):
        return AUDIO
    if mime.startswith("video/"):
        return VIDEO
    if mime.startswith("image/"):
        return IMAGE
    if mime.startswith("text/"):
        return TEXT

    by_ext = _EXT.get(_ext_of(name))
    if by_ext:
        return by_ext

    # Nothing declared it. If it reads as text, it is text.
    if head:
        sample = head[:512]
        if b"\x00" not in sample:
            try:
                sample.decode("utf-8")
                return TEXT
            except UnicodeDecodeError:
                pass
    return UNKNOWN


def route(name="", mime="", head=b"", size=0, spoken_limit=0):
    """What should happen to this file.

    Returns a dict the caller acts on:
        kind       one of the constants above
        pipeline   'transcribe' | 'ocr' | 'read' | None
        chunk      True when it must be fed in pieces
        reason     a short phrase for the person, when nothing can be done

    `chunk` is advisory and deliberately errs toward True: the transcriber
    checks the real size after transcoding anyway, and being told to
    expect chunks and then not needing them costs nothing, while the
    reverse means an upload that fails at the provider's limit.
    """
    kind = kind_of(name, mime, head)
    limit = int(spoken_limit or 0)
    big = bool(limit and size and size > limit)

    if kind in (AUDIO, VIDEO):
        return {"kind": kind, "pipeline": "transcribe", "chunk": big,
                "reason": ""}
    if kind == IMAGE:
        return {"kind": kind, "pipeline": "ocr", "chunk": False, "reason": ""}
    if kind == TEXT:
        return {"kind": kind, "pipeline": "read", "chunk": False, "reason": ""}
    return {"kind": UNKNOWN, "pipeline": None, "chunk": False,
            "reason": "not a sound, a picture or text"}
