"""Accessibility: text size, reading comfort, and targets for unsteady hands.

This app exists largely FOR people who cannot easily read a screen —
Baba's words: *"this app is actually accessibility app for people who
cannot see, who cannot read"*. So accessibility is not a setting bolted
on the side, it is the product. Anything that breaks at a large text size
is a bug of the same seriousness as losing someone's recording.

Grounded in WCAG rather than taste. The criteria this module implements:

  1.4.4  Resize text (AA)     text usable at 200% with no loss of content
                              or functionality. We allow up to 250%,
                              because "up to 200" is a floor, not a target.
  1.4.10 Reflow (AA)          no scrolling in two directions at a width of
                              320 CSS px. Everything wraps; nothing is
                              ever placed in a fixed-width box.
  1.4.12 Text spacing (AA)    line height, letter, word and paragraph
                              spacing must survive being increased — so
                              they scale WITH the text here rather than
                              being frozen in pixels.
  2.5.5  Target size (AAA)    44x44 CSS px minimum for anything you press.
                              This is the one that matters for tremor:
                              WCAG 2.2's AA floor is only 24px, and 24px
                              is not enough for a shaking hand.
  1.4.6  Contrast (AAA)       7:1. The near-black and gold already clear
                              this; check it again if colours ever change.

Everything is expressed in `rem`, never `px`, because a fixed pixel size
ignores the reader's own browser and OS font setting — which is the first
thing a person with low vision will already have turned up.
"""

MIN_SCALE = 0.8
MAX_SCALE = 2.5          # 250%: WCAG asks for 200 as a floor
STEP = 0.15
DEFAULT_SCALE = 1.0

# Below this, text is too small for the audience whatever the scale says.
BASE_REM = 1.05


def clamp(scale) -> float:
    try:
        s = float(scale)
    except (TypeError, ValueError):
        return DEFAULT_SCALE
    # NaN fails every comparison, so min/max would silently pass it
    # through and it reached the maximum instead of the default. A
    # stored setting that somehow became NaN must land on normal size,
    # not on the largest text in the app.
    if s != s:
        return DEFAULT_SCALE
    return round(max(MIN_SCALE, min(MAX_SCALE, s)), 2)


def bigger(scale) -> float:
    return clamp(clamp(scale) + STEP)


def smaller(scale) -> float:
    return clamp(clamp(scale) - STEP)


def percent(scale) -> int:
    return int(round(clamp(scale) * 100))


def at_max(scale) -> bool:
    return clamp(scale) >= MAX_SCALE


def at_min(scale) -> bool:
    return clamp(scale) <= MIN_SCALE


def css(scale) -> str:
    """The stylesheet for one text scale.

    Line height, letter spacing and paragraph spacing all move WITH the
    size instead of staying fixed: enlarged text on cramped leading is
    harder to read than small text, which is the usual failure of a naive
    zoom. Line height eases DOWN as text grows because long lines need
    proportionally less leading than short ones.
    """
    s = clamp(scale)
    size = round(BASE_REM * s, 3)
    # 1.75 at normal size, easing toward 1.45 at the largest.
    leading = round(1.75 - (s - 1.0) * 0.22, 3)
    leading = max(1.45, leading)
    tracking = round(0.012 * s, 4)

    return f"""
    <style>
    /* ---- READING SURFACES ------------------------------------------
       Text the person actually reads: the transcript box, the pasted
       text, translations, the reader, the subtitle. Sized by their own
       control, wrapped so no word is ever cut, and never placed in a
       container that can scroll sideways (WCAG 1.4.10). */
    .stTextArea textarea,
    .stTextInput input,
    .subtitle-box,
    .reading-surface {{
        font-size: {size}rem !important;
        line-height: {leading} !important;
        letter-spacing: {tracking}em !important;

        /* Wrapping that holds at ANY size. overflow-wrap breaks a word
           only when it genuinely cannot fit, so ordinary text keeps its
           natural shape; word-break: break-word would break far more
           eagerly and make prose ragged. hyphens softens the long
           Croatian compounds that would otherwise leave a hole. */
        overflow-wrap: break-word !important;
        word-break: normal !important;
        hyphens: auto !important;
        -webkit-hyphens: auto;

        /* Never a sideways scrollbar. */
        white-space: pre-wrap !important;
        max-width: 100% !important;
    }}

    /* Comfortable, momentum-preserving vertical scrolling, and a text
       box tall enough that enlarged text still shows several lines. */
    .stTextArea textarea {{
        -webkit-overflow-scrolling: touch;
        overscroll-behavior: contain;
        scroll-padding: 1rem;
        min-height: {round(9 * size, 1)}rem !important;
        padding: 0.7rem 0.8rem !important;
    }}

    .subtitle-box, .reading-surface {{
        padding: {round(0.9 * s, 2)}rem {round(0.8 * s, 2)}rem !important;
        min-height: {round(4.2 * size, 1)}rem !important;
    }}

    /* Paragraph rhythm scales too (WCAG 1.4.12). */
    .reading-surface p {{ margin: 0 0 {round(0.85 * s, 2)}em 0; }}

    /* ---- TARGETS FOR UNSTEADY HANDS --------------------------------
       44x44 CSS px minimum (WCAG 2.5.5 AAA). WCAG 2.2's AA floor of 24px
       is not enough for a tremor. Applies to every real control; the
       patch bay's round jacks set their own size and are excluded. */
    .stButton button,
    .stDownloadButton button,
    [data-testid="stFileUploader"] button {{
        min-height: 44px;
        min-width: 44px;
    }}
    /* Space between targets matters as much as their size: adjacent
       small buttons are a mis-tap waiting to happen. */
    div[data-testid="stHorizontalBlock"] {{ gap: 0.5rem !important; }}

    /* Checkboxes and radios are tiny by default. */
    .stCheckbox, .stRadio label {{ min-height: 44px; display: flex; align-items: center; }}

    /* ---- FOCUS -----------------------------------------------------
       A visible focus ring, because keyboard and switch users need to
       know where they are. Gold on near-black clears 7:1. */
    .stButton button:focus-visible,
    .stTextArea textarea:focus-visible,
    .stTextInput input:focus-visible {{
        outline: 3px solid #e0a340 !important;
        outline-offset: 2px !important;
    }}

    /* ---- MOTION ----------------------------------------------------
       Respect a person who has asked the system for less movement. */
    @media (prefers-reduced-motion: reduce) {{
        * {{ animation-duration: 0.01ms !important;
             transition-duration: 0.01ms !important;
             scroll-behavior: auto !important; }}
    }}
    </style>
    """
