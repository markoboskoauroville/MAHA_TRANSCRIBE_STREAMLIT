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

# Colour schemes. All four keep the same STRUCTURE — near-black ground,
# one accent, warm prose — and differ only in hue, so the app never stops
# looking like itself. Every one was checked to clear 7:1 for prose on
# surface before being offered.
SCHEMES = {
    "amber": {"accent": "#f59e0b", "accent_hi": "#fbbf24", "prose": "#f2ddb4"},
    "green": {"accent": "#4ade80", "accent_hi": "#86efac", "prose": "#dbf0e0"},
    "cyan":  {"accent": "#38bdf8", "accent_hi": "#7dd3fc", "prose": "#d6ecf7"},
    "paper": {"accent": "#e6e0d4", "accent_hi": "#ffffff", "prose": "#ece7dc"},
}

FONTS = {
    "mono":  'ui-monospace, "JetBrains Mono", "Cascadia Mono", "SF Mono", Menlo, Consolas, monospace',
    "sans":  '-apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    "serif": 'Georgia, "Times New Roman", serif',
}

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


def css(scheme: str = "amber", font: str = "mono") -> str:
    t = dict(TOKENS)
    sc = SCHEMES.get(scheme) or SCHEMES["amber"]
    t["amber"] = sc["accent"]
    t["amber_hi"] = sc["accent_hi"]
    t["prose"] = sc["prose"]
    mono = FONTS.get(font) or FONTS["mono"]
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
      --mono: {mono};
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
    /* The OWNER's gear is amber even when unselected: it is the one that
       changes things for everybody, and it should look like it. The
       user's own looks-gear stays quiet grey. Last tab = owner's. */
    [data-testid="stButtonGroup"] button[role="radio"]:last-child p {{
      color: var(--amber) !important;
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
    /* Just the button. The dashed box was a large empty rectangle that
       said nothing — on a phone it was the biggest thing on the tab. */
    [data-testid="stFileUploaderDropzone"] {{
      padding: 0 !important;
      background: transparent !important;
      border: none !important;
      justify-content: flex-start;
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

    /* ---- COMMAND ROWS ---------------------------------------------
       A real grid, which is what Baba meant by "an underlying invisible
       table". grid-auto-columns:1fr makes every cell identical whatever
       the word inside it, so nothing can drift out of line — the problem
       the pipes were there to hide.

       With cells, the pipes are gone: a thin shared border separates
       them better and gives a far larger target to press, which matters
       more here than the typography did. Corners are nearly square, so
       the row reads as a terminal table rather than a strip of pills. */
    [class*="st-key-cmdrow_"] {{ margin-bottom: -0.5rem; }}
    [class*="st-key-cmdrow_"] div[data-testid="stHorizontalBlock"] {{
      display: grid !important;
      /* FLEX, not grid-auto-flow: column. A column grid cannot wrap, so
         once the words were long enough the last cell ran off the right
         edge of the phone — Baba caught "+" hanging outside the screen.
         Anything leaving the screen is a bug, always. Flex with wrap
         keeps every cell its own width AND keeps them all on screen. */
      display: flex !important;
      flex-wrap: wrap;
      align-content: flex-start;
      /* The row is a closed strip, not a set of boxes ending in mid-air.
         The LAST cell takes whatever width is left, so the border runs
         to the edge and every cell keeps its own text-sized width.
         Baba: "if there is space to be filled up, we can make empty
         button" — this fills it without adding a control nobody asked
         for and nobody should press. */
      gap: 0 !important;
      border: 1px solid var(--line);
      border-radius: 4px;
      overflow: hidden;
    }}
    [class*="st-key-cmdrow_"] div[data-testid="stHorizontalBlock"]
      > div[data-testid="stColumn"] {{
      width: max-content !important;
      min-width: 0 !important;
      flex: 0 0 auto !important;
      border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
    }}
    [class*="st-key-cmdrow_"] div[data-testid="stHorizontalBlock"]
      > div[data-testid="stColumn"]:last-child {{
      border-right: none;
      flex: 1 1 auto !important;
      width: auto !important;
    }}
    /* ...and its button must not stretch with it: the control stays the
       size of its word, sitting at the left of the space it closes. */
    [class*="st-key-cmdrow_"] div[data-testid="stHorizontalBlock"]
      > div[data-testid="stColumn"]:last-child .stButton button {{
      width: auto !important;
      min-width: 44px;
    }}
    [class*="st-key-cmdrow_"] div[data-testid="stVerticalBlock"] {{ gap: 0; }}
    [class*="st-key-cmdrow_"] div[data-testid="stElementContainer"] {{ width: 100%; }}

    [class*="st-key-cmdrow_"] .stButton button {{
      width: 100% !important;
      height: 44px !important;
      min-height: 44px !important;
      min-width: 0 !important;
      padding: 0 0.85rem !important;
      white-space: nowrap;
      justify-content: center;
      font-size: 0.92rem !important;
      font-weight: 600;
      letter-spacing: 0.04em;
      border: none !important;
      border-radius: 0 !important;
      background: transparent !important;
      color: var(--prose) !important;
    }}
    [class*="st-key-cmdrow_"] .stButton button p {{
      color: inherit !important; font-weight: 600; letter-spacing: 0.04em;
    }}
    /* Pressed: the whole cell fills, so the feedback is unmissable. */
    [class*="st-key-cmdrow_"] .stButton button[kind="primary"] {{
      background: var(--amber) !important;
      color: var(--bg) !important;
    }}
    [class*="st-key-cmdrow_"] .stButton button[kind="primary"] p {{
      color: var(--bg) !important;
    }}
    /* NOT width:100% here. A component is given an explicit pixel width
       computed from its word, and 100% resolves against a max-content
       column — which then sizes to the iframe's intrinsic 300px and the
       cell becomes four times too wide. Let the attribute stand. */
    /* Streamlit does not honour the width passed to components.html
       here, and an iframe's intrinsic 300px then wins a max-content
       column. So the CELL is constrained instead and the iframe fills
       it. 84px matches "paste" and "copy" at this font — the two words
       that ever appear in a component cell. */
    [class*="st-key-cmdrow_"] div[data-testid="stHorizontalBlock"]
      > div[data-testid="stColumn"]:has(iframe) {{
      width: 84px !important;
      max-width: 84px !important;
    }}
    [class*="st-key-cmdrow_"] iframe {{
      width: 84px !important; height: 44px !important; display: block;
    }}
    /* Streamlit wraps a component iframe in its own container which
       reports a slightly different height than a button cell, leaving a
       few pixels of ragged edge in an otherwise exact grid. */
    [class*="st-key-cmdrow_"] div[data-testid="stColumn"] {{
      display: flex; align-items: stretch;
    }}
    [class*="st-key-cmdrow_"] [data-testid="stIFrame"],
    [class*="st-key-cmdrow_"] div[data-testid="stElementContainer"] {{
      height: 44px !important; display: flex; align-items: stretch;
    }}

    /* The bare − and + above a box: same terminal language, pushed to
       the right so it does not compete with the commands on the left. */
    [class*="st-key-sizerow_"] {{ margin-bottom: -0.6rem; margin-top: -0.35rem; }}
    [class*="st-key-sizerow_"] div[data-testid="stHorizontalBlock"] {{
      gap: 0 !important; flex-wrap: nowrap !important;
    }}
    [class*="st-key-sizerow_"] div[data-testid="stHorizontalBlock"]
      > div[data-testid="stColumn"] {{
      flex: 0 0 auto !important; width: auto !important;
    }}
    [class*="st-key-sizerow_"] div[data-testid="stHorizontalBlock"]
      > div[data-testid="stColumn"]:first-child {{ flex: 1 1 auto !important; }}
    [class*="st-key-sizerow_"] .stButton button {{
      background: transparent !important;
      border: none !important;
      color: var(--dim) !important;
      font-size: 1.05rem !important;
      height: 30px !important;
      min-height: 30px !important;
      padding: 0 !important;
      width: 100% !important;
    }}
    [class*="st-key-sizerow_"] .stButton button:disabled {{ opacity: 0.3 !important; }}

    /* The txttools row that used to live here is gone: every command
       row in the app is now the grid defined above. A second, older
       definition of the SAME selectors survived here for a while and
       silently won — it set 38px cells and re-added hover, so the grid
       above appeared not to work. Deleting rules is part of changing
       them. */

    /* The translate action sits beside the two language rows.

       SCOPED TO THE BUTTON ONLY. The previous version styled every
       .stButton inside the matrix, which caught the language pills too:
       they lost their amber fill and grew to fill the row, so a selected
       language looked the same as an unselected one and the whole block
       became a wall of tall boxes. A rule aimed at one control must say
       which control. */
    .st-key-trmatrix .st-key-do_translate_btn button {{
      height: 96px !important;
      border-radius: 10px !important;
      background: var(--surface-2) !important;
      border: 1px solid var(--line) !important;
      color: var(--amber) !important;
      font-weight: 700;
      letter-spacing: 0.04em;
      white-space: normal !important;
      line-height: 1.25;
      padding: 0 0.4rem !important;
    }}
    .st-key-trmatrix .st-key-do_translate_btn button p {{
      color: var(--amber) !important; white-space: normal !important;
    }}
    /* The pills stay pill-height: a control should never be much taller
       than the word inside it. */
    .st-key-trmatrix div[data-testid="stColumn"] .stButton button {{
      height: 44px !important;
      min-height: 44px !important;
    }}

    /* Language switch: short labels, so nearly round. */
    .st-key-langrow .stButton button {{
      border-radius: 999px;
      min-width: 56px;
      padding: 0.45rem 0.6rem !important;
    }}

    /* The tab signature: bottom right, in the same quiet monospace as
       the recorder's 00:00 counter, so it reads as a mark on the panel
       rather than as another control competing for attention. */
    .tabsig {{
      text-align: right;
      /* Gold, on Baba's instruction: it should catch the eye enough to
         answer "where am I?" without being read on purpose. */
      color: var(--amber);
      font-family: var(--mono);
      /* 20% down from 0.95rem, on Baba's eye. It is a mark on the
         frame, not a label that needs reading. */
      font-size: 0.76rem;
      letter-spacing: 0.10em;
      opacity: 0.75;
      margin: 0.5rem 0 0.1rem;
      user-select: none;
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
