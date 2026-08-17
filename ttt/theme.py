"""The visual language, lifted from Baba's own maha_transcribe app.

Read out of that app's stylesheet rather than eyeballed from screenshots,
so the tokens here ARE his tokens. One module, so a colour is changed in
one place and the whole app follows.

    --bg        #0b0d10   the page behind everything
    --surface   #0d1117   the card the app sits in
    --surface-2 #141a21   any control or box on that card
    --line      #23303d   every border
    --amber     #f59e0b   the single accent; active = amber fill, dark text
    --prose     #f2ddb4   body text, warm rather than white
    --dim       lifted    quiet text (see below)
    --red       lifted    errors and recording

TWO COLOURS WERE DELIBERATELY CHANGED, and only these two. His `--dim`
(#8a7a5c) measures 4.18:1 against surface-2 and his `--red` (#ef4444)
measures 4.65:1 — the first fails even AA, and both fail the 7:1 this app
holds itself to (hard rule 6). They carry inactive pill labels, field
labels and error text, which are exactly the things a person with poor
eyesight needs to read. Both were lifted in LIGHTNESS ONLY, keeping hue
and saturation, until they cleared 7:1: #b1a389 (7.06) and #f48383 (7.02).
Same colours, same feel, actually readable.

Everything else clears AAA as it stands: prose on surface 14.22, amber on
surface-2 8.15, dark text on an amber pill 9.06.

The shape language, also his:
  * one card holding the app — surface, 1px line, 10px radius, 14px padding
  * pills for every choice — 999px radius, surface-2 when idle, amber fill
    when active with the page colour as text
  * main actions full width — amber, 14px radius, bold, letter-spaced
  * boxes — surface-2, 12px radius
  * labels — 10px, uppercase, letter-spaced, dim
  * tight rhythm — 4px between controls in a row, 6px between rows

WHAT IS NOT COPIED: his fixed pixel font sizes. Text size here is the
reader's own choice and lives in ttt/a11y.py, which must win. This module
sets colour, border, radius, weight, spacing and letter-spacing; a11y.py
sets size, line height and targets. Keep that split — if this file starts
setting font-size on reading surfaces, the text-size control breaks.
"""

TOKENS = {
    "bg": "#0b0d10",
    "surface": "#0d1117",
    "surface2": "#141a21",
    "line": "#23303d",
    "amber": "#f59e0b",
    "amber_hi": "#fbbf24",
    "amber_lo": "#b45309",
    "prose": "#f2ddb4",
    "dim": "#b1a389",       # lifted from #8a7a5c for 7:1
    "red": "#f48383",       # lifted from #ef4444 for 7:1
    "green": "#22c55e",
}

MONO = ('ui-monospace, "JetBrains Mono", "Cascadia Mono", "SF Mono", '
        'Menlo, Consolas, monospace')


def css() -> str:
    t = TOKENS
    return f"""
    <style>
    :root {{
      --bg: {t['bg']};
      --surface: {t['surface']};
      --surface-2: {t['surface2']};
      --line: {t['line']};
      --amber: {t['amber']};
      --amber-hi: {t['amber_hi']};
      --prose: {t['prose']};
      --dim: {t['dim']};
      --red: {t['red']};
      --mono: {MONO};
    }}

    .stApp, [data-testid="stAppViewContainer"] {{
      background: var(--bg);
      font-family: var(--mono);
    }}

    /* ---- THE CARD -------------------------------------------------
       His whole app lives inside one bordered panel rather than floating
       on the page. It is what makes it read as an instrument instead of
       a web form. */
    .block-container {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 14px 14px 20px !important;
      max-width: 640px;
      margin-top: 0.6rem;
    }}

    /* ---- PILLS ----------------------------------------------------
       Every choice is a pill: quiet by default, amber-filled when
       chosen, with the page colour as its text so the contrast reverses
       and the active one is unmistakable. */
    .stButton button {{
      background: var(--surface-2);
      border: 1px solid var(--line);
      color: var(--prose);
      font-family: var(--mono);
      font-weight: 600;
      letter-spacing: 0.05em;
      border-radius: 999px;
      box-shadow: none;
    }}
    .stButton button p {{ font-weight: 600; letter-spacing: 0.05em; }}

    .stButton button[kind="primary"] {{
      background: var(--amber);
      border-color: var(--amber);
      color: var(--bg);
      font-weight: 700;
    }}
    .stButton button[kind="primary"] p {{ color: var(--bg); font-weight: 700; }}
    .stButton button[kind="primary"]:hover {{
      background: var(--amber-hi);
      border-color: var(--amber-hi);
    }}

    /* ---- BOXES ----------------------------------------------------- */
    .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {{
      background: var(--surface-2) !important;
      border: 1px solid var(--line) !important;
      border-radius: 12px !important;
      color: var(--prose) !important;
      font-family: var(--mono) !important;
    }}
    .stTextArea textarea:focus, .stTextInput input:focus {{
      border-color: var(--amber) !important;
    }}

    /* ---- LABELS ---------------------------------------------------
       Small, uppercase, letter-spaced and quiet — they name a control
       without competing with it. */
    div[data-testid="stCaptionContainer"] p {{
      color: var(--dim);
      letter-spacing: 0.09em;
      font-weight: 700;
      margin-bottom: 2px;
    }}

    /* ---- TAB BAR --------------------------------------------------
       Streamlit's segmented control becomes his pill row. The real
       markup is [data-testid="stButtonGroup"] holding role="radio"
       buttons — NOT data-baseweb, which was my first guess and matched
       nothing. Confirmed by reading the live DOM.

       Streamlit joins the segments into one bar with square inner
       corners; his are separate pills, so each is rounded individually.

       ONE DELIBERATE DEPARTURE from his app: his tab row scrolls
       sideways and never wraps. That works with three short English
       labels; here there are four Croatian ones and the fourth
       (Čitaonica) is pushed off the edge. A tab you cannot see is a tab
       that does not exist for someone who does not know to swipe a row
       sideways — and the whole audience for this app is people who do
       not. So it wraps instead. Two tidy rows of pills beat one row with
       a feature hidden past the fold. */
    [data-testid="stButtonGroup"] > div[role="radiogroup"] {{
      display: flex;
      gap: 4px;
      flex-wrap: wrap;
      row-gap: 4px;
    }}
    [data-testid="stButtonGroup"] > div[role="radiogroup"]::-webkit-scrollbar {{
      display: none;
    }}
    [data-testid="stButtonGroup"] button[role="radio"] {{
      background: var(--surface-2) !important;
      border: 1px solid var(--line) !important;
      border-radius: 999px !important;
      color: var(--dim) !important;
      font-family: var(--mono) !important;
      letter-spacing: 0.03em;
      white-space: nowrap;
      flex: 0 1 auto;
    }}
    [data-testid="stButtonGroup"] button[role="radio"] p {{
      color: var(--dim);
    }}
    [data-testid="stButtonGroup"] button[role="radio"][aria-checked="true"] {{
      background: var(--amber) !important;
      border-color: var(--amber) !important;
      color: var(--bg) !important;
      font-weight: 700;
    }}
    [data-testid="stButtonGroup"] button[role="radio"][aria-checked="true"] p {{
      color: var(--bg);
      font-weight: 700;
    }}

    /* ---- EXPANDERS AND PANELS -------------------------------------- */
    [data-testid="stExpander"] {{
      background: var(--surface-2);
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
    }}
    [data-testid="stExpander"] summary {{ color: var(--prose); }}
    [data-testid="stExpander"] summary:hover {{ color: var(--amber); }}

    [data-testid="stPopoverBody"] {{
      background: var(--surface) !important;
      border: 1px solid var(--line) !important;
      border-radius: 12px !important;
    }}

    /* ---- SLIDERS AND CHECKBOXES ------------------------------------ */
    .stSlider [data-baseweb="slider"] div[role="slider"] {{ background: var(--amber); }}
    .stCheckbox [data-baseweb="checkbox"] span {{ border-color: var(--line); }}

    /* ---- FILE UPLOADER --------------------------------------------
       Streamlit prints "Drag and drop file here / Limit 500MB per file •
       MP3, WAV, M4A, …" inside every uploader. On a phone that is the
       longest text on the screen, it is technical, and it tells someone
       who just wants to hand over a file nothing they can act on. The
       Browse button stays; the essay goes. */
    [data-testid="stFileUploaderDropzoneInstructions"] {{ display: none !important; }}
    [data-testid="stFileUploaderDropzone"] {{
      padding: 0.4rem 0.5rem !important;
      min-height: 0 !important;
    }}
    /* The caption above each uploader was landing ON the dashed border,
       because the caption rule pulls its margin in tight and the
       shrunken dropzone left nothing between them. */
    [data-testid="stFileUploader"] {{ margin-top: 0.25rem; }}
    [data-testid="stFileUploaderDropzone"] button {{ margin: 0 auto; }}


    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploaderDropzone"] {{
      background: var(--surface-2);
      border: 1px dashed var(--line);
      border-radius: 12px;
    }}
    [data-testid="stAudioInput"] {{
      background: var(--surface-2);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 4px 8px;
    }}

    /* ---- MESSAGES -------------------------------------------------- */
    [data-testid="stAlert"] {{
      background: var(--surface-2);
      border: 1px solid var(--line);
      border-radius: 12px;
      color: var(--prose);
    }}

    /* ---- ROWS THAT MUST KEEP THEIR PROPORTIONS ---------------------
       The pill rules let columns size to their content, which is right
       for a row of choices and WRONG wherever a ratio was asked for.
       It is why the gear sat on the LEFT: st.columns([6, 1]) collapsed
       to two content-width columns, so the empty spacer had no width.
       Any row wrapped in one of these keyed containers keeps the ratio
       it was given. */
    /* Equal shares would be just as wrong as content-width: st.columns
       was asked for 6:1 and 1:2:1, so the ratio is restated here rather
       than flattened. First attempt used flex:1 1 0 for all of them and
       parked the gear dead centre. */
    .st-key-topbar div[data-testid="stColumn"] {{
      width: auto !important; min-width: 0 !important;
    }}
    .st-key-topbar div[data-testid="stColumn"]:first-child {{ flex: 6 1 0 !important; }}
    .st-key-topbar div[data-testid="stColumn"]:last-child  {{ flex: 0 0 auto !important; }}

    [class*="st-key-cprow"] div[data-testid="stColumn"] {{
      width: auto !important; min-width: 0 !important;
    }}
    [class*="st-key-cprow"] div[data-testid="stColumn"]:nth-child(1) {{ flex: 1 1 0 !important; }}
    [class*="st-key-cprow"] div[data-testid="stColumn"]:nth-child(2) {{ flex: 2 1 0 !important; }}
    [class*="st-key-cprow"] div[data-testid="stColumn"]:nth-child(3) {{ flex: 1 1 0 !important; }}
    .st-key-topbar div[data-testid="stHorizontalBlock"],
    [class*="st-key-cprow"] div[data-testid="stHorizontalBlock"] {{
      justify-content: space-between;
      flex-wrap: nowrap !important;
      align-items: center;
    }}

    /* The gear itself: quiet until touched, like his. */
    .st-key-topbar .stPopover button {{
      background: transparent !important;
      border: none !important;
      color: var(--dim) !important;
      font-size: 1.35rem;
      padding: 4px 6px !important;
    }}
    .st-key-topbar .stPopover button:hover {{ color: var(--amber) !important; }}

    /* Language switch: short labels, so nearly round. */
    .st-key-langrow .stButton button {{
      border-radius: 999px;
      min-width: 56px;
      padding: 0.45rem 0.6rem !important;
    }}

    /* ---- RHYTHM ---------------------------------------------------
       His spacing is tight: 4px inside a row, 6px between rows. Streamlit
       is far airier by default, which is what makes it look like a form
       rather than a panel. */
    div[data-testid="stVerticalBlock"] {{ gap: 0.42rem; }}
    div[data-testid="stHorizontalBlock"] {{ gap: 0.28rem !important; }}
    [data-testid="stHeader"] {{ background: transparent; }}
    hr {{ border-color: var(--line); margin: 0.6rem 0; }}
    </style>
    """
