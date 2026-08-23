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

      /* ---- ONE RHYTHM -------------------------------------------------
         Baba, from a phone screenshot: "the space between all these
         frames is not equal. Above, below the recorder there is too much
         space." Every frame — deck, command row, box, archive, language
         row — now sits on this single gap, so the spacing cannot drift
         apart one rule at a time. Change it here and the whole column
         re-spaces together. */
      --frame-gap: 0.55rem;
    }}

    /* ---- TYPE SCALE ---------------------------------------------------
       "Everything too large." The whole interface steps down together
       rather than rule by rule, so the proportions between the parts are
       preserved and nothing has to be re-tuned against anything else.

       This is a scale on the CHROME, not on the reading surfaces. The
       transcript, the reader and the subtitle are governed by the text
       size control (hard rule 6: the control sits above each reading
       surface) and are deliberately NOT touched here — shrinking the
       words someone came to read would break the one thing this app
       exists to do. In rem throughout, so a reader's own OS font setting
       still scales all of it. */
    .stButton button, .stCheckbox, [data-testid="stExpander"] summary {{
      font-size: 0.82rem !important;
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
      /* The top padding was 14px and Streamlit adds its own above that,
         which on a phone put an empty band between the browser bar and
         the tabs — the first thing anybody sees and the least useful.
         Trimmed at the top only; the bottom keeps its room so the last
         control is not against the edge. */
      padding: 4px 14px 20px !important;
      max-width: 640px;
      margin-top: 0.2rem;
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

    /* THE LOGIN FOLD-OUT HAS NO FRAME. Everywhere else an expander holds
       real content and the panel around it is right. Here it is one
       closed line on an otherwise bare screen, and the box made it read
       as a section with something inside rather than as a quiet way in.
       Just the arrow and the words. */
    /* The border is drawn on the inner <details>, not on the expander
       itself — measured, after the first attempt styled the wrong
       element and changed nothing visible. */
    [class*="st-key-loginmore"] [data-testid="stExpander"],
    [class*="st-key-loginmore"] [data-testid="stExpander"] details {{
      background: transparent !important;
      border: 0 !important;
      border-radius: 0 !important;
    }}
    [class*="st-key-loginmore"] [data-testid="stExpander"] summary {{
      padding-left: 0;
      color: var(--dim);
    }}
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
    /* NO NEGATIVE MARGIN. This was -0.5rem, which pulled the command row
       up against the box below it and left every other frame sitting in
       more air — measured at 1.8px here against 17.6px under the deck.
       The rhythm is --frame-gap and nothing opts out of it. */
    [class*="st-key-cmdrow_"] div[data-testid="stHorizontalBlock"] {{
      display: grid !important;
      /* FLEX, not grid-auto-flow: column. A column grid cannot wrap, so
         once the words were long enough the last cell ran off the right
         edge of the phone — Baba caught "+" hanging outside the screen.
         Anything leaving the screen is a bug, always. Flex with wrap
         keeps every cell its own width AND keeps them all on screen. */
      display: flex !important;
      /* ONE ROW, ALWAYS. This used to be flex-wrap:wrap, added because a
         column grid pushed the last cell off the right edge of the phone.
         Wrapping fixed that and introduced a worse thing: "clear" dropped
         onto a second line and the strip became two rows of different
         widths. Baba: "no new rows, it can only remove letters."
         So the row never wraps, the cells SHRINK, and the words are
         clipped from the right — reshape becomes resh, grammar becomes
         gra — before anything is ever allowed to leave the screen or
         start a second line. */
      flex-wrap: nowrap !important;
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
      /* 0 1 auto, not 0 0 auto: the cell must be ALLOWED to shrink, or
         nowrap simply pushes the last one off the screen again. */
      flex: 0 1 auto !important;
      overflow: hidden;
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
      /* Padding and type both give way as the screen narrows, so the
         letters survive as long as possible before any are clipped. */
      padding: 0 clamp(0.2rem, 1.7vw, 0.85rem) !important;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: clip;
      justify-content: center;
      font-size: clamp(0.60rem, 2.5vw, 0.92rem) !important;
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
    div[data-testid="stVerticalBlock"] {{ gap: var(--frame-gap); }}
    div[data-testid="stHorizontalBlock"] {{ gap: 0.28rem !important; }}

    /* EVERY FRAME ON THE SAME GAP.
       The gap is set ONCE, by the vertical block's flex gap above. These
       containers carry NO margin of their own — a margin here ADDS to
       that gap instead of replacing it, which measured 17.6px under the
       deck against 1.8px under the command row: the exact inequality
       that was photographed. Anything that wants to sit closer or
       further away has to change --frame-gap, not add a margin.

       The component iframe is inline by default, which leaves a text
       baseline gap underneath it that looks like padding nobody wrote. */
    [class*="st-key-deckbox"], [class*="st-key-statusbox"],
    [class*="st-key-archivebox"], [class*="st-key-langrow"],
    [class*="st-key-cmdrow_"] {{
      margin-top: 0 !important;
      margin-bottom: 0 !important;
    }}
    iframe {{ display: block; }}
    [data-testid="stIFrame"] {{ margin-bottom: 0 !important; }}

    /* The source dropdown's CSS lived here. It is a gear inside the
       deck now (v95), styled in the component's own stylesheet, so
       there is nothing on the page left to style. */

    /* THE VOICES, ON ONE ROW. Four pills wrapping to a second line cost
       a whole row of a phone screen and say nothing extra. Same nowrap
       override as the command row: the cells may SHRINK, and the type
       gives way before any name is clipped. */
    [class*="st-key-voicerow"] div[data-testid="stHorizontalBlock"] {{
      flex-wrap: nowrap !important;
      gap: 0.25rem !important;
    }}
    [class*="st-key-voicerow"] div[data-testid="stColumn"] {{
      flex: 0 1 auto !important; min-width: 0 !important; width: auto !important;
    }}
    [class*="st-key-voicerow"] .stButton button {{
      font-size: clamp(0.60rem, 2.6vw, 0.82rem) !important;
      padding: 0.34rem 0.5rem !important;
      width: 100%;
    }}

    /* ADD TO NOTES — a line, not a button.
       Baba asked for "just an orange line link". The box already carries
       five command keys above it; a sixth full-width button would
       compete with them for an action that is an afterthought — you read
       what came back, THEN you decide to keep it. */
    /* GLUED TO THE BOTTOM OF THE BOX. The negative margin closes the
       gap Streamlit puts between two elements; without it the line
       floated loose and read as a status report rather than an action.
       Left-aligned to the box's own text inset so the words line up
       with the transcript above them. */
    /* THE WRAPPER IS THE FLEX ROW. Its width is the one that is known —
       the button's is not, and neither is its inner paragraph's. Making
       the wrapper a row and pushing its end is the only version of this
       that measured right. */
    /* WIDTH FIRST, THEN ALIGNMENT. The element container was itself
       only 128px wide inside a 390px parent, so every attempt to push
       its contents right was pushing them to the right of 128px — which
       is where they already were. Four rounds of CSS went past this
       because I kept styling the thing being moved instead of measuring
       the thing that held it.

       Read the ancestor chain when a rule "does nothing": the answer was
       one line of computed widths. */
    [class*="st-key-tx_tonote"] {{
      margin-top: -0.75rem !important;
      width: 100% !important;
      /* NOTHING TO ALIGN AT THIS LEVEL. Measured, after five rounds of
         guessing at it: the container is a ROW and its child .stButton
         already fills all 330px of it. So there is no free space here
         for justify-content or align-items to distribute — the words
         sit left because the BUTTON's own label sits left inside a
         full-width button. That is the only place left to fix, below. */
    }}
    [class*="st-key-tx_tonote"] .stButton {{ width: 100% !important; }}
    [class*="st-key-tx_tonote"] button {{
      background: transparent !important;
      border: 0 !important;
      color: var(--amber) !important;
      padding: 0.1rem 0.75rem !important;
      min-height: 0 !important;
      font-size: 0.76rem !important;
      text-decoration: underline;
      text-underline-offset: 3px;
      /* RIGHT-ALIGNED, where `copy` and the tab signature sit, so the
         panel's actions line up down the right margin. The button is
         full width; these two lines are what put its LABEL at the right
         end of it, and the <p> Streamlit wraps the label in needs
         telling as well as the button. */
      /* ONE width, not two. This read `width: 100%` and then
         `width: auto` on the next line — left over from an earlier
         attempt — so the last one won and the button stayed 128px wide
         while every rule after it argued with a line I had forgotten to
         delete. THAT is why five rounds of alignment moved nothing. */
      width: 100% !important;
    }}
    /* AND THE DIV INSIDE THE BUTTON. Streamlit puts a flex div between
       the button and its label, with justify-content: center — so a
       full-width button still centred a 104px paragraph. Measured, not
       guessed: button 330, inner div 306, paragraph 104 sitting in the
       middle of it. */
    [class*="st-key-tx_tonote"] button > div {{
      width: 100% !important;
      justify-content: flex-end !important;
    }}
    [class*="st-key-tx_tonote"] button p {{
      text-align: right !important;
    }}
    [class*="st-key-tx_tonote"] button:hover {{ color: var(--amber-hi) !important; }}

    /* THE NOTES — cards, in the app's own quiet register.
       Baba asked for Keep, but "dull colours, not too bright". So the
       card is the same surface as every other panel and gets NO colour
       of its own: colour is reserved for state, and a note at rest has
       no state. The heading is gold only because it is the thing the eye
       is looking for. */
    [class*="st-key-notesbox"] .stButton button {{
      text-align: left;
      justify-content: flex-start;
      align-items: flex-start;
      flex-direction: column;
      gap: 0.25rem;
      padding: 0.6rem 0.7rem !important;
      min-height: 0 !important;
      border-radius: 12px !important;
      white-space: pre-line;         /* the heading and the taste, two lines */
      line-height: 1.45;
      font-size: 0.72rem !important;
      font-weight: 400;
    }}
    /* The first line is the heading. :first-line is the only way to
       reach it — the two lines are one text node, deliberately, so the
       whole card stays a single press. */
    [class*="st-key-notesbox"] .stButton button p::first-line {{
      color: var(--amber);
      font-weight: 600;
      font-size: 0.82rem;
    }}
    [class*="st-key-notesbox"] .stButton button:hover {{
      border-color: var(--amber) !important;
    }}
    /* The search field is a field, not a shout. */
    [class*="st-key-notesbox"] input {{
      font-size: 0.8rem !important;
    }}

    /* THE OPEN NOTE. It has taken the module over, so it gets the room:
       no extra frame around the component, which draws its own. */
    [class*="st-key-noteopen"] [data-testid="stIFrame"] {{
      margin: 0 !important;
    }}
    /* THE ACTION ROW SITS AT THE RIGHT. The row is what gets aligned —
       an empty spacer column collapsed and left both buttons on the
       left, measured at x=54 in a 380px panel. Its columns become
       auto-width so they take only what the words need. */
    [class*="st-key-noteacts"] div[data-testid="stHorizontalBlock"] {{
      justify-content: flex-end !important;
      flex-wrap: nowrap !important;
      gap: 0.3rem !important;
    }}
    [class*="st-key-noteacts"] div[data-testid="stColumn"] {{
      flex: 0 0 auto !important;
      width: auto !important;
      min-width: 0 !important;
    }}

    /* The old note about a spacer, so it needs no
       nowrap: there is no text_input in it to demand a minimum width.
       Forcing nowrap with the title in the row ran `close` past the
       panel edge, which is why the title moved to its own line. */
    /* DELETE AND CLOSE, small, at the top right. Same size as the note's
       own meta line, so they read as part of the frame rather than as
       two more things to do. */
    [class*="st-key-note_del"] button,
    [class*="st-key-note_close"] button {{
      font-size: 0.7rem !important;
      min-height: 0 !important;
      padding: 0.3rem 0.4rem !important;
    }}
    [class*="st-key-noteopen"] input {{
      font-size: 0.95rem !important;
      color: var(--amber) !important;
    }}

    /* THE ARCHIVE. Small type: it is a list to scan, not to read, and it
       sits under the thing that matters. The rows are quiet so the
       transcript above stays the loudest thing on screen. */
    [class*="st-key-archivebox"] summary,
    [class*="st-key-archivebox"] summary p {{
      font-size: 0.72rem !important; color: var(--amber) !important;
      letter-spacing: 0.04em;
    }}

    /* THE TICK STAYS BESIDE THE NAME.
       Streamlit stacks columns below ~640px, so on a phone the checkbox
       landed on its own line ABOVE the row — which is the same default
       §7 calls a bug rather than something to accept. Forced horizontal,
       exactly as the command row already is. */
    [class*="st-key-archivebox"] div[data-testid="stHorizontalBlock"] {{
      flex-wrap: nowrap !important;
      align-items: center;
      gap: 0.3rem !important;
    }}
    [class*="st-key-archivebox"] div[data-testid="stHorizontalBlock"]
      > div[data-testid="stColumn"] {{
      flex: 0 1 auto !important;
      min-width: 0 !important;
      width: auto !important;
    }}
    [class*="st-key-archivebox"] div[data-testid="stHorizontalBlock"]
      > div[data-testid="stColumn"]:last-child {{
      flex: 1 1 auto !important;
    }}

    [class*="st-key-archivebox"] .stButton button {{
      font-size: 0.66rem !important;
      padding: 0.22rem 0.5rem !important;
      min-height: 0 !important;
      text-align: left;
      justify-content: flex-start;
      font-weight: 500;
      letter-spacing: 0.02em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    /* The two actions are pills, not slabs: a button is the size of its
       text (hard rule 7), and these two are the smallest thing here
       because deleting is not what anyone came to do. */
    [class*="st-key-arc_del_sel"] button,
    [class*="st-key-arc_clear_all"] button {{
      font-size: 0.64rem !important;
      padding: 0.2rem 0.6rem !important;
      text-align: center !important;
      justify-content: center !important;
    }}
    /* The tick keeps a usable target even though the row is small.
       Target size does not shrink with type — but inside a dense list
       44px would make every row a slab, so it takes the row's height and
       the whole row is tappable to LOAD, which is the common action. */
    [class*="st-key-archivebox"] [data-testid="stCheckbox"] {{
      min-height: 0 !important; display: flex; align-items: center;
      margin: 0 !important;
    }}
    [class*="st-key-archivebox"] [data-testid="stCheckbox"] label {{
      min-height: 0 !important; padding: 0 !important;
    }}

    /* THE STATUS BOX. Small type, the same dim monospace as the deck's
       own line, so it reads as a continuation of it rather than as a new
       piece of furniture. Folded away until something goes wrong. */
    [class*="st-key-statusbox"] summary,
    [class*="st-key-statusbox"] summary p {{
      font-size: 0.72rem !important; color: var(--dim) !important;
      letter-spacing: 0.04em;
    }}
    [class*="st-key-statusbox"] div[data-testid="stText"],
    [class*="st-key-statusbox"] pre, [class*="st-key-statusbox"] code {{
      font-size: 0.68rem !important; line-height: 1.45 !important;
      color: var(--dim) !important; background: transparent !important;
      white-space: pre-wrap !important; overflow-wrap: anywhere !important;
      border: none !important; padding: 0 !important; margin: 0 !important;
    }}
    [class*="st-key-statusbox"] div[data-testid="stExpander"] {{
      border-color: var(--line) !important; background: transparent !important;
    }}
    [data-testid="stHeader"] {{ background: transparent; }}
    hr {{ border-color: var(--line); margin: 0.6rem 0; }}
    </style>
    """
