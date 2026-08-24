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


def css(scheme: str = "amber", font: str = "mono",
        ui_scale: float = 1.0) -> str:
    t = dict(TOKENS)
    sc = SCHEMES.get(scheme) or SCHEMES["amber"]
    t["amber"] = sc["accent"]
    t["amber_hi"] = sc["accent_hi"]
    t["prose"] = sc["prose"]
    mono = FONTS.get(font) or FONTS["mono"]
    # 16px is the browser default every rem here was written against.
    ui_px = round(16.0 * max(0.5, min(float(ui_scale or 1.0), 2.0)), 2)
    return f"""
    <style>
    /* INTERFACE SIZE. Baba: "so the whole interface can be shrunk or
       enlarged."
       It moves the ROOT font size, which is what every rem in this
       stylesheet is measured against — so the pills, the labels, the
       links and the padding all move together and the layout keeps its
       proportions. Text size is separate and multiplies on top of it,
       because they answer different questions: "I cannot read the
       transcript" and "the whole thing is too small".

       NOT on the component iframes, which cannot see this — see
       HOW_WE_WORK.md on why a component never quite matches the page. */
    html {{ font-size: {ui_px}px; }}

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
      /* Baba: "the first row is too far away from the top, put it at
         the top." Streamlit's own top padding plus this one left an
         empty band above the tabs — the first thing anybody sees and
         the least useful. The bottom keeps its room so the last control
         is not against the edge. */
      padding: 0 12px 16px !important;
      max-width: 640px;
      margin-top: 0;
    }}

    /* THE PAGE ABOVE THE PANEL. Streamlit reserves room for a header
       that this app does not use, which is where most of the band came
       from — the panel's own padding was only part of it. */
    /* THE ROOT OF EVERY "OVERLAPPING AT THE TOP".
       ================================================================
       This set the header's height to zero in v122, to close the empty
       band above the tabs. (Written in words on purpose: this
       stylesheet is an f-string, so a brace in a COMMENT is still read
       as code — the first draft of this very note crashed the app with
       NameError: name 'height' is not defined.)
       It does not remove the
       header. Streamlit's header is POSITION: FIXED, so zeroing its
       height leaves the toolbar exactly where it was and lets the page
       scroll UNDERNEATH it — and whatever happens to be at the top of
       the page is printed through.

       That is why it kept coming back and why every fix was a patch:
       the thing being overlapped was never the problem. The tabs, the
       interface-language label, the engine test result, the password
       notice — four different elements, one cause, four symptom fixes.

       The header stays, invisible, and the page is given room for it.
       Anything that wants to be higher up the screen must shrink THIS
       padding, never the header. */
    [data-testid="stHeader"] {{
      background: transparent !important;
      pointer-events: none;
    }}
    [data-testid="stHeader"] * {{ pointer-events: auto; }}

    /* THE TOOLBAR GOES. Share, the star, the pencil, the GitHub mark and
       the three dots are Streamlit's, not this app's — and on a phone
       they land ON TOP of the tab row, because the header they live in
       is fixed and narrow enough that the icons and the tabs occupy the
       same band. Baba photographed "Share" printed across TR.
       Nobody here has ever pressed one of them: this is his family's
       transcriber, not a Streamlit demo to fork. Removing them also
       removes the collision entirely, rather than negotiating with it —
       which is what padding-top was doing, and what it kept losing. */
    /* THE TAB BAR HOLDS ONE LINE, whoever is looking at it. The owner
       has seven and a family member five, and at 360px the seventh
       wrapped — `log` alone underneath, which is the orphan shape Baba
       objected to for `multi` and which I noted at v130 and left.
       §27's trade: the cells may shrink and the type may shrink, and no
       word may be cut. `log` is three letters and survives it. */
    /* .stButtonGroup's INNER div is the flex row that wraps — not
       stSegmentedControl, which is the block around it. Found by
       walking up from the `log` tab and reading each ancestor's
       computed display and flex-wrap, rather than guessing at a
       test-id. The same lesson as the add-to-notes link: when a rule
       does nothing, print the chain. */
    .stButtonGroup > div {{
      flex-wrap: nowrap !important;
      gap: 0.2rem !important;
    }}
    .stButtonGroup button {{
      padding-left: 0.5rem !important;
      padding-right: 0.5rem !important;
      min-width: 0 !important;
      white-space: nowrap !important;
    }}
    .stButtonGroup button p {{ white-space: nowrap !important; }}

    [data-testid="stToolbar"] {{ display: none !important; }}
    [data-testid="stToolbarActions"] {{ display: none !important; }}
    [data-testid="stAppDeployButton"] {{ display: none !important; }}
    /* The running indicator STAYS. It is the only thing up there that
       says the app is working, and on a slow phone that is the
       difference between waiting and pressing again. */
    [data-testid="stStatusWidget"] {{ display: block !important; }}
    [data-testid="stMainBlockContainer"] {{
      /* 64px WAS FOR A TOOLBAR THAT IS NO LONGER THERE. With it hidden
         the header holds nothing that can be printed through, so the
         page can start where Baba wanted it in the first place — at the
         top. Measured again after hiding it, not assumed. */
      padding-top: 12px !important;
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
      /* AND IT KEEPS CLEAR OF THE BADGE TOO. This is the very last
         thing on the page and it was right-aligned, which on Streamlit
         Cloud puts it directly under "Manage app" — Baba's screenshot
         shows it cut to "transcrib". The line stays on the right,
         because that is where he asked for it and it reads well there,
         but it now leaves room for the thing sitting on top of it. */
      padding-right: 5.5rem;
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

    /* A SHADE DARKER INSIDE EACH FRAME. Baba: "fill up the frame with
       some very dark color, just to have some visual distinction
       between sections."

       Barely a shade — the frames already divide the sections, and this
       only stops them reading as one long surface with lines drawn on
       it. Colour still means STATE in this app; this is depth, not
       colour, which is why it is a step of the same hue rather than a
       tint of another one. */
    /* NO SECOND EDGE. Baba: "recording has its edge, and there is some
       other edge around it — when I said colour I meant the edge which
       is already there, not to add an additional one."
       The deck draws its own frame inside the iframe and the note editor
       draws its own too, so v122's border put a line around a line. The
       FILL is what he asked for and the fill is all that stays. */
    [class*="st-key-deckbox"], [class*="st-key-noteopen"] {{
      background: var(--surface-2);
      border-radius: 10px;
      padding: 0.35rem !important;
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

    /* THE PASSWORD NUDGE. Quiet, one line, with a way past it. It used
       to be a full screen that stopped the app — Baba: "we are not
       torturing the user." It is not red and it is not gold: it is not
       an error and it is not the owner's. */
    [class*="st-key-mustnotice"] {{
      background: var(--surface-2);
      border-radius: 8px;
      /* ROOM TO BREATHE, INSIDE AND BELOW. Baba: "it is again too close
         to the buttons, it looks unprofessional and amateurish."
         He is right, and the cause is the same one that made the
         sections read as one long list before v135: this app's default
         gap is tight, which is correct BETWEEN things that belong
         together and wrong between things that do not. The notice and
         the tab row are strangers, so the space between them has to say
         so. The padding grew with it — a card whose text touches its
         own edge looks like a mistake even when the spacing below it is
         right. */
      padding: 0.6rem 0.7rem !important;
      margin-bottom: 1.1rem !important;
    }}
    /* THE SPACE GOES ON THE CONTAINER, not on my div.
       margin-bottom on `.mustsay` measured 2px in a browser: Streamlit
       wraps every st.markdown in its own element container, and MY
       margin sits inside that wrapper where the next element cannot see
       it. The wrapper is the thing with a neighbour, so the wrapper is
       the thing that needs the space.
       Measured before and after — 2px, then 14. */
    /* A LINE'S WORTH, NOT A GULF. 0.7rem measured 41px once Streamlit's
       own container margin was added to it, which is as wrong in the
       other direction — Baba: "you create another mess." The gap wanted
       is about one line of text. */
    [class*="st-key-mustnotice"] div[data-testid="stMarkdownContainer"] {{
      margin-bottom: 0.15rem !important;
    }}
    [class*="st-key-mustnotice"] div[data-testid="stHorizontalBlock"] {{
      align-items: center !important;
      gap: 0.3rem !important;
    }}
    [class*="st-key-mustnotice"] div[data-testid="stColumn"] {{
      min-width: 0 !important;
    }}
    [class*="st-key-mustnotice"] .stButton button {{
      min-height: 0 !important;
      padding: 0.2rem 0.4rem !important;
      font-size: 0.7rem !important;
    }}
    .mustsay {{
      color: var(--dim);
      font-size: 0.72rem;
      line-height: 1.45;
      white-space: normal;
      /* THE SPACE BABA HAS ASKED FOR THREE TIMES, and the three times
         are my fault: he kept saying "it is sitting on the buttons" and
         I kept widening the gap BELOW THE CARD. The gap he meant was
         inside it — between his sentence and the two buttons under it,
         which was 0.25rem, about four pixels. A sentence four pixels
         above a button reads as one object, and that is what looked
         amateurish.
         Read what somebody is pointing AT, not what is nearby. */
      margin: 0 0 0.6rem 0;
    }}

    /* EACH COLOUR BUTTON WEARS ITS OWN COLOUR. Baba: "each button can
       be already colored to represent its color — people can see and
       understand everything."
       Four words in identical pills asked somebody to imagine what
       `cyan` would look like. Now the button IS the answer, and the
       chosen one fills, exactly as every other chosen pill does.

       WRITTEN OUT RATHER THAN LOOPED because this stylesheet is one
       f-string: a loop here would have to be built before it and read
       further from the thing it describes. Four schemes, four blocks,
       and they change together or not at all. */
    [class*="st-key-scheme_amber"] button {{
      border-color: #f59e0b !important;
      color: #f59e0b !important;
    }}
    [class*="st-key-scheme_amber"] button[kind="primary"] {{
      background: #f59e0b !important;
      border-color: #f59e0b !important;
      color: #14181d !important;
    }}
    [class*="st-key-scheme_green"] button {{
      border-color: #4ade80 !important;
      color: #4ade80 !important;
    }}
    [class*="st-key-scheme_green"] button[kind="primary"] {{
      background: #4ade80 !important;
      border-color: #4ade80 !important;
      color: #14181d !important;
    }}
    [class*="st-key-scheme_cyan"] button {{
      border-color: #38bdf8 !important;
      color: #38bdf8 !important;
    }}
    [class*="st-key-scheme_cyan"] button[kind="primary"] {{
      background: #38bdf8 !important;
      border-color: #38bdf8 !important;
      color: #14181d !important;
    }}
    [class*="st-key-scheme_paper"] button {{
      border-color: #e6e0d4 !important;
      color: #e6e0d4 !important;
    }}
    [class*="st-key-scheme_paper"] button[kind="primary"] {{
      background: #e6e0d4 !important;
      border-color: #e6e0d4 !important;
      color: #14181d !important;
    }}

    /* EACH SETTING IN ITS OWN FRAME. Baba: "visually group different
       settings so we know they belong to different groups — put the
       frame, the visual language from the rest of the interface."
       The same fill the deck and the note sit in, so the grouping is
       said the way this app already says it. */
    [class*="st-key-looksgroup_"] {{
      background: var(--surface-2);
      border-radius: 10px;
      padding: 0.5rem 0.55rem !important;
      margin-bottom: 0.4rem !important;
    }}

    /* Every settings row keeps its label on the line with its controls. */
    [class*="st-key-looksgroup_"] div[data-testid="stHorizontalBlock"] {{
      align-items: center !important;
      flex-wrap: nowrap !important;
      gap: 0.3rem !important;
    }}
    [class*="st-key-looksgroup_"] div[data-testid="stColumn"] {{
      min-width: 0 !important;
    }}
    [class*="st-key-looksgroup_"] .setlabel {{
      margin: 0 !important;
      white-space: nowrap;
    }}
    /* The size box, small like everything beside it. */
    [class*="st-key-_size_pct"] input {{
      font-size: 0.8rem !important;
      padding: 0.25rem 0.4rem !important;
    }}
    [class*="st-key-size_default"] button {{
      background: transparent !important;
      border: 0 !important;
      color: var(--dim) !important;
      min-height: 0 !important;
      padding: 0.2rem 0 !important;
      font-size: 0.7rem !important;
      text-decoration: underline;
      text-underline-offset: 3px;
    }}

    /* The interface language, label and pills on ONE line. */
    [class*="st-key-uilangrow"] div[data-testid="stHorizontalBlock"] {{
      align-items: center !important;
      flex-wrap: nowrap !important;
      gap: 0.3rem !important;
    }}
    [class*="st-key-uilangrow"] div[data-testid="stColumn"] {{
      min-width: 0 !important;
    }}
    [class*="st-key-uilangrow"] .setlabel {{
      margin: 0 !important;
      white-space: nowrap;
    }}

    /* PROPORTION. Baba: "look at the sizes of text, buttons and
       everything — proportions are not good, make them less different,
       more equal size."
       He is right and the cause is history: every row was tuned on the
       day it was built, so the deck's transport, the pills, the links
       and the settings labels each carry their own idea of small. These
       pull the extremes toward each other — nothing changes by much,
       and the spread narrows. */
    [class*="st-key-quickrow"] button {{
      font-size: 0.78rem !important;
      padding: 0.35rem 0.5rem !important;
      min-height: 0 !important;
    }}
    .setlabel {{ font-size: 0.68rem !important; letter-spacing: 0.04em; }}
    .readhint {{ font-size: 0.72rem !important; line-height: 1.5; }}
    /* The pills and the links were 0.72 and 0.78; both move to 0.75, so
       a row of pills and the links under a box read as one family. */
    .stButtonGroup button p {{ font-size: 0.75rem !important; }}

    /* THE PIPE BETWEEN LANGUAGE AND MODE. Quiet, centred on the pills
       beside it: it is punctuation, not a control, and anything that
       looks pressable there would be pressed. */
    .pilldiv {{
      color: var(--line);
      text-align: center;
      font-size: 1.1rem;
      line-height: 2.2rem;
      user-select: none;
    }}

    /* THE FILE MANAGER IS A SYSTEM TOOL, so its controls are LINKS.
       Baba: "for this kind of interface, when we are doing file
       management, it's like a system tool. Don't make pills, make
       action links."
       A pill is a choice being offered; a link is a thing you do to
       what you have selected. File managers have always looked like the
       second, and this panel is the one place in the app that is about
       files rather than about words. */
    [class*="st-key-rec_"] button,
    [class*="st-key-recacts_"] button,
    /* THE NOTES LIST IS THE SAME KIND OF PANEL. Baba, seeing v178 on a
       phone: "make the action links exactly the same look as in the
       audio file storage — not yellow, grey underlined action links."
       He is right, and the reason is the one written above: this row
       acts on files you have selected, so it is a link, not a pill.
       ADDED TO THE SAME RULE rather than copied into a new one — two
       rules for one look drift, and this app has paid for that. */
    [class*="st-key-nact_"] button,
    [class*="st-key-nactrow_"] button {{
      background: transparent !important;
      border: 0 !important;
      min-height: 0 !important;
      padding: 0.15rem 0 !important;
      font-size: 0.72rem !important;
      color: var(--dim) !important;
      text-decoration: underline;
      text-underline-offset: 3px;
      justify-content: flex-start !important;
      white-space: nowrap;
    }}
    [class*="st-key-rec_"] button:hover:not(:disabled),
    [class*="st-key-nact_"] button:hover:not(:disabled) {{
      color: var(--amber) !important;
    }}
    /* GREYED, AND VISIBLY SO. A disabled link that looks like a live one
       is worse than no link: somebody presses it and learns nothing.
       The underline goes too — that is what says "not now" without a
       word. */
    [class*="st-key-rec_"] button:disabled,
    [class*="st-key-nact_"] button:disabled {{
      color: var(--line) !important;
      text-decoration: none !important;
      cursor: default !important;
    }}
    /* Delete keeps its warning colour on hover, as it does in the note. */
    [class*="st-key-rec_del"] button:hover:not(:disabled),
    [class*="st-key-nact_deln"] button:hover:not(:disabled) {{
      color: var(--rec, #d9484b) !important;
    }}
    /* The rows themselves sit tight — a file list is a list, not a form. */
    [class*="st-key-_rp_"] {{ margin: 0 !important; }}
    [class*="st-key-_np_"] {{ margin: 0 !important; }}

    /* THE NOTE CARDS: a gold edge, and the words in the reading colour.
       Baba: "note does not have nice outline — add golden outline
       around each note, but the text is supposed to be white, same as
       transcription text."
       The edge says a card is a THING you can open; the prose colour
       says what is inside it is the same kind of stuff as the
       transcript. The number stays dim, because it is a label on the
       card rather than part of what was said. */
    [class*="st-key-note_"] button {{
      border: 1px solid var(--amber) !important;
      background: transparent !important;
      color: var(--prose) !important;
      text-align: left !important;
      justify-content: flex-start !important;
      font-weight: 400 !important;
    }}
    [class*="st-key-note_"] button p {{
      text-align: left !important;
      color: var(--prose) !important;
    }}
    [class*="st-key-note_"] button:hover {{
      border-color: var(--amber-hi) !important;
      background: var(--surface-2) !important;
    }}

    /* copy · clear UNDER EVERY BOX. One rule, one look, in T, R and
       both halves of TR. Baba: "under all tabs we have text box, copy
       clear under — as an action link, not an action button."
       Glued to the box like add-to-notes was, and right-aligned so the
       panel's actions line up down the same margin. */
    [class*="st-key-boxlinks_"] {{
      /* GLUED TO THE BOX, which is right when there is text — the links
         read as the bottom edge of the writing surface. Baba noticed it
         is wrong when the box is EMPTY: with nothing in the box the
         single link sits on the border and reads as part of it. The
         empty case gets its own rule below. */
      margin-top: -0.7rem !important;
    }}
    /* AFTER the rule above, so it wins: both selectors match an empty
       row and the later one takes it. */
    [class*="_empty"][class*="st-key-boxlinks_"] {{
      margin-top: 0.25rem !important;
    }}
    [class*="st-key-boxlinks_"] div[data-testid="stHorizontalBlock"] {{
      justify-content: flex-end !important;
      flex-wrap: nowrap !important;
      gap: 0 !important;
      /* ONE BASELINE. Baba: "they are dancing." Without this the cells
         are stretched to equal height and each link sits wherever its
         own box puts it — `copy` is an IFRAME and the others are
         buttons, so their boxes are different heights and their words
         landed at different levels. Aligning the ends makes every word
         sit on the same line whatever it is made of. */
      align-items: flex-end !important;
    }}
    [class*="st-key-boxlinks_"] div[data-testid="stColumn"] {{
      flex: 0 0 auto !important;
      width: auto !important;
      min-width: 0 !important;
    }}
    [class*="st-key-boxlinks_"] .stButton button {{
      background: transparent !important;
      border: 0 !important;
      color: var(--dim) !important;
      padding: 0.1rem 0.75rem !important;
      min-height: 0 !important;
      font-size: 0.72rem !important;
      text-decoration: underline;
      text-underline-offset: 3px;
      white-space: nowrap;
    }}
    [class*="st-key-boxlinks_"] .stButton button:hover {{
      color: var(--amber) !important;
    }}
    [class*="st-key-boxlinks_"] [data-testid="stIFrame"] {{
      margin: 0 !important;
    }}

    /* FIVE PILLS, ONE LINE. nowrap holds the row together and the type
       shrinks to fit — §27's trade, which lets a cell get smaller but
       never lets a word be cut. Measured at 320 and 360px. */
    [class*="st-key-langrow"] div[data-testid="stHorizontalBlock"] {{
      flex-wrap: nowrap !important;
      gap: 0.25rem !important;
    }}
    [class*="st-key-langrow"] div[data-testid="stColumn"] {{
      min-width: 0 !important;
    }}
    [class*="st-key-langrow"] .stButton button {{
      padding-left: 0.35rem !important;
      padding-right: 0.35rem !important;
    }}
    [class*="st-key-langrow"] .stButton button p {{
      font-size: 0.72rem !important;
      white-space: nowrap !important;
    }}

    /* THE COPY BUTTON IS ALWAYS THERE. Baba: "there should be on the
       screen this copy button all the time, not when I am just hovering
       over — if it is hidden, I do not see."
       Streamlit fades it in on hover, which on a phone means it appears
       only after a press that might have done something else. A control
       nobody can see is a control that has to be explained, and the
       line explaining it is gone now. */
    [data-testid="stCode"] button,
    [data-testid="stCodeBlock"] button,
    .stCode button {{
      opacity: 1 !important;
      visibility: visible !important;
      color: var(--amber) !important;
    }}

    /* THE DELETE STRIP WEARS RED. Baba: "confirm should be in a red
       frame, and confirm should be a red button — not too much red, so
       I know I am deleting."
       Only delete: a reset is recoverable, a delete is not, and red
       that appears for both says nothing about either. */
    [class*="st-key-askstrip_danger"] {{
      border: 1px solid var(--rec, #d9484b);
      border-radius: 8px;
      padding: 0.5rem 0.6rem !important;
      background: rgba(217, 72, 75, 0.06);
    }}
    [class*="st-key-ad_yes_danger"] button {{
      background: var(--rec, #d9484b) !important;
      border-color: var(--rec, #d9484b) !important;
      color: #14181d !important;
      font-weight: 600;
    }}

    /* THE PERSON'S ACTIONS ARE LINKS, not buttons. Baba: "these should
       be links at the top, not buttons — we make it a nice and compact
       user interface." Three bordered pills for actions taken once in a
       while were the heaviest thing on a panel that is mostly a list. */
    [class*="st-key-ad_rename"] button,
    [class*="st-key-ad_reset"] button,
    [class*="st-key-ad_del"] button {{
      background: transparent !important;
      border: 0 !important;
      min-height: 0 !important;
      padding: 0.1rem 0 !important;
      font-size: 0.7rem !important;
      color: var(--dim) !important;
      text-decoration: underline;
      text-underline-offset: 3px;
      justify-content: flex-start !important;
    }}
    /* ONE LINE, and the type may shrink to hold it — §27's rule, which
       lets a cell get smaller but never lets a word be cut. */
    [class*="st-key-ad_rename"] button p,
    [class*="st-key-ad_reset"] button p,
    [class*="st-key-ad_del"] button p {{
      white-space: nowrap !important;
      font-size: 0.66rem !important;
    }}
    [class*="st-key-ad_reset"] button:hover {{ color: var(--amber) !important; }}
    /* Delete is the one that ends something. It says so before it is
       pressed, not only in the confirm strip afterwards. */
    [class*="st-key-ad_del"] button:hover {{ color: var(--rec, #d9484b) !important; }}

    /* The label above the interface-language pills. The same thin dim
       mark as TXT, TY and C further up the same screen — st.caption was
       heavier and carried margins that printed it through the buttons
       beneath it. */
    .setlabel {{
      color: var(--dim);
      font-size: 0.62rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin: 0.4rem 0 0.15rem 0.1rem;
    }}

    /* THE LANGUAGE TAG beside its voices. Dim and small, so the row
       still costs one line — which is what removing the headings was
       protecting in the first place. */
    .vtag {{
      color: var(--dim);
      font-size: 0.62rem;
      letter-spacing: 0.08em;
      line-height: 2.6;
      text-align: right;
      padding-right: 0.2rem;
      white-space: nowrap;
    }}

    /* The line under the reading box. Grey, small, and not a control —
       it says where the play is, since the read button was removed on
       purpose and nothing else on the screen mentioned it. */
    .readhint {{
      color: var(--dim);
      font-size: 0.7rem;
      margin: -0.5rem 0 0.2rem 0.2rem;
    }}

    /* THE NOTES — cards, in the app's own quiet register.
       Baba asked for Keep, but "dull colours, not too bright". So the
       card is the same surface as every other panel and gets NO colour
       of its own: colour is reserved for state, and a note at rest has
       no state. The heading is gold only because it is the thing the eye
       is looking for. */
    /* TARGETED AT THE CARDS, not at the container they used to sit in.
       The notes moved into an expander (v160) and `st-key-notesbox` went
       with it — styling that hangs off a container is styling that
       disappears the day the container does. The cards carry their own
       key, and that is the thing that is actually being styled. */
    [class*="st-key-note_"] .stButton button,
    [class*="st-key-note_"] button {{
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
    [class*="st-key-note_"] button p::first-line {{
      color: var(--amber);
      font-weight: 600;
      font-size: 0.82rem;
    }}
    [class*="st-key-note_"] button:hover {{
      border-color: var(--amber) !important;
    }}
    /* The search field is a field, not a shout. */
    [class*="st-key-notes_q"] input {{
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
    /* LEFT, NOT RIGHT. Baba: "delete and close are behind Manage App —
       align everything to the left side."
       Streamlit Cloud plants its own "Manage app" badge in the BOTTOM
       RIGHT of the page, and these actions moved to the foot of the
       note in v149. Right-aligned at the foot is exactly where that
       badge sits, so on his phone they were underneath it and could not
       be pressed.
       Nothing in the app can move that badge. The actions move instead.
       And it is a corner worth remembering: anything right-aligned at
       the bottom of this app is under something Streamlit owns. */
    [class*="st-key-noteacts"] div[data-testid="stHorizontalBlock"] {{
      justify-content: flex-start !important;
      flex-wrap: nowrap !important;
      gap: 0.6rem !important;
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
    /* DELETE AND CLOSE ARE LINKS, not pills. Baba: "forget pills, make
       links, glue it to this outline for that box, tiny."

       A pill says "press me, this is a thing you do". These two are
       ways OUT of a note — reached rarely, and when they are wanted the
       eye is already in that corner. As links they sit on the frame
       instead of on the page. */
    [class*="st-key-note_del"] button,
    [class*="st-key-note_close"] button {{
      background: transparent !important;
      border: 0 !important;
      min-height: 0 !important;
      padding: 0 0.25rem !important;
      font-size: 0.68rem !important;
      color: var(--dim) !important;
      text-decoration: underline;
      text-underline-offset: 3px;
    }}
    [class*="st-key-note_del"] button:hover,
    [class*="st-key-note_close"] button:hover {{
      color: var(--amber) !important;
    }}
    /* Armed delete is the one state that earns colour. */
    /* THE ARMED DELETE KEEPS THE LINK'S OWN COLOUR. Baba: "it has
       changed the color and it is not visible — please do not change
       the colour, keep it the same."
       It was red on a dark panel, which is a colour chosen for a filled
       button and unreadable as text. The WORDS are the signal: `delete
       user` becomes `delete — sure?`, and a person who has just pressed
       delete does not need to be told in red that they pressed delete.
       Nothing here: the base rule above already styles it, because
       `st-key-note_del` matches note_del2 as well. */

    /* The date, thinner and quieter than either. It is a mark on the
       frame, not a label — the word "made" in front of it was
       explaining what a date already says. */
    .notewhen {{
      color: var(--dim);
      font-size: 0.62rem;
      opacity: 0.75;
      line-height: 1.9;
      white-space: nowrap;
    }}

    /* GLUED TO THE BOX. The row sits on the note's top edge rather than
       floating above it, so the three marks read as part of the frame. */
    [class*="st-key-noteacts"] {{
      margin-bottom: -0.55rem !important;
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
