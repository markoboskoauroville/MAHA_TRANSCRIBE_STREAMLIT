"""A copy button that says what it is doing.

Lives in its own iframe (that is how Streamlit embeds raw HTML), so it
cannot inherit the app's stylesheet and carries its own. Keep the two in
step if the palette ever changes.

Why a button at all, when every browser can already copy a selection:
selecting text precisely needs a steady hand and good eyesight, which is
exactly what this app's readers do not have. One large round target that
takes the whole box is the accessible equivalent.

The states matter as much as the copying. Baba asked for it plainly —
"it needs to confirm it's copied... so we can see everything is live" —
and for someone who cannot read a small confirmation, a button that
visibly becomes something else is the confirmation.

    Copy      resting
    Copying…  pressed, the write is in flight
    Copied ✓  it worked; returns to resting after a moment
    Failed    it did not, and says so rather than lying

Copy uses navigator.clipboard.writeText, which IS permitted here: the
component iframe's Permissions Policy grants clipboard-write. Paste is a
different matter entirely — clipboard-read is NOT granted, so pasting has
to come from the native paste event instead. See HANDOVER §14.
"""

import json

BG = "#0b0d10"
# The same dim the app uses for a link at rest. Written here rather than
# imported, because this module renders inside an IFRAME and cannot see
# the page's CSS variables — a var(--dim) here resolves to nothing.
DIM = "#b1a389"   # measured off the page: rgb(177,163,137)
FG = "#f2ddb4"
GOLD = "#f59e0b"
EDGE = "rgba(232,220,192,0.25)"

# Enough for a 44px target plus breathing room; Streamlit reserves this
# height in the page whether or not the button fills it.
HEIGHT = 58
# His CP button is an 86px amber circle. Kept as a circle here because it
# is the one control people reach for constantly, and a round target is
# easier to hit than a bar when your hand is not steady.
CP_SIZE = 86
CP_HEIGHT = CP_SIZE + 8


def _js(value) -> str:
    """JSON for embedding inside a <script> block.

    json.dumps alone is NOT safe here: it does not escape "</script>", so
    a transcript containing that string would close the script element
    early and break the button — and in the general case that is an
    injection point. A transcript is arbitrary text a person dictated or
    pasted, so it must be assumed hostile. Escaping the "<" of any "</"
    (and the HTML comment openers, which can also end a script block)
    keeps the value byte-identical in JavaScript while making it inert to
    the HTML parser.
    """
    out = json.dumps(value, ensure_ascii=False)
    return (out.replace("</", "<\\/")
               .replace("<!--", "<\\!--")
               .replace("\u2028", "\\u2028")
               .replace("\u2029", "\\u2029"))


def html(text: str, label: str, busy: str, done: str, failed: str,
         scale: float = 1.0, fg: str = FG, font: str = "") -> str:
    """The whole component. `text` is embedded as JSON, never interpolated
    raw — a transcript containing quotes, backslashes or newlines would
    otherwise break the script, and a transcript is arbitrary text by
    definition."""
    payload = _js(text or "")
    labels = _js({"idle": label, "busy": busy, "done": done, "failed": failed})
    size = round(0.95 * max(0.8, min(float(scale or 1.0), 2.5)), 3)

    return f"""
<!doctype html>
<meta charset="utf-8">
<style>
  html, body {{ margin:0; padding:0; background:transparent; }}
  button {{
    width:100%; min-height:44px;               /* WCAG 2.5.5 target size */
    /* Font and colour are PASSED IN, not fixed here. This component is an
       iframe, so it inherits none of the page's CSS variables — which is
       why 'copy' sat in a different typeface and a different cream from
       the cells either side of it, in a row whose whole point is that
       every cell looks the same. Baba spotted it immediately. */
    font-family: {font or 'ui-monospace, monospace'};
    font-size: {size}rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: {fg}; background: {BG};
    border: 1px solid {EDGE}; border-radius: 999px;
    padding: 0.5rem 1rem; cursor: pointer;
    transition: transform 90ms ease-out, background-color 90ms ease-out,
                border-color 90ms ease-out;
  }}
  button:hover:not(:disabled) {{
    border-color: {GOLD}; background: rgba(224,163,64,0.10); transform: scale(1.03);
  }}
  button:active:not(:disabled) {{ transform: scale(0.97); }}
  button:focus-visible {{ outline: 3px solid {GOLD}; outline-offset: 2px; }}
  button.done {{ color: {GOLD}; }}
  button.failed {{ border-color: #d9534f; color: #ffb3b0; }}
  @media (prefers-reduced-motion: reduce) {{
    button {{ transition: none; }}
    button:hover:not(:disabled), button:active:not(:disabled) {{ transform: none; }}
  }}
</style>
<button id="b" type="button" aria-live="polite"></button>
<script>
  const TEXT = {payload};
  const L = {labels};
  const b = document.getElementById('b');
  let timer = null;

  function set(state) {{
    b.textContent = L[state];
    b.className = (state === 'done') ? 'done' : (state === 'failed' ? 'failed' : '');
  }}
  set('idle');

  b.addEventListener('click', async () => {{
    if (timer) {{ clearTimeout(timer); timer = null; }}
    set('busy');
    b.disabled = true;
    let ok = false;
    try {{
      await navigator.clipboard.writeText(TEXT);
      ok = true;
    }} catch (e) {{
      // Older browsers, and any case where the async API is refused.
      try {{
        const ta = document.createElement('textarea');
        ta.value = TEXT;
        ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.focus(); ta.select();
        ok = document.execCommand('copy');
        ta.remove();
      }} catch (e2) {{ ok = false; }}
    }}
    set(ok ? 'done' : 'failed');
    b.disabled = false;
    // Return to resting so the button is obviously ready again, rather
    // than sitting on a stale "Copied" that no longer means anything.
    timer = setTimeout(() => set('idle'), 2200);
  }});
</script>
"""


def cp_html(text: str, done_label: str = "OK", failed_label: str = "X",
            label: str = "CP", size: int = CP_SIZE,
            link: bool = False) -> str:
    """size=0 means a WORD pill rather than a circle — for command rows
    where the label has to be readable ("copy") instead of an initialism.
    Same behaviour and the same state changes either way."""
    """The round amber CP button from Baba's own app.

    Same behaviour as the wide one — it announces what it is doing — but
    the states have to fit inside a circle, so they are short: CP, a
    spinner, OK, X. The circle is 86px, well beyond the 44px floor,
    because this is the control people reach for most and a round target
    is the easiest thing to hit with an unsteady hand.
    """
    payload = _js(text or "")
    labels = _js({"idle": label, "busy": "\u00b7\u00b7\u00b7",
                  "done": done_label, "failed": failed_label})

    # LINK MODE. The copy control has to be a component — nothing else
    # can reach the clipboard — so it cannot be a Streamlit button
    # styled into a link like the ones beside it. This makes it LOOK
    # like one, so a row of copy · clear reads as one kind of thing
    # rather than a button standing next to two links.
    # LINK MODE, IN PIXELS — NOT rem. AND NOT SCALED.
    #
    # WHY THE LINKS LOOKED DIFFERENT SIZES: this said `0.72rem`, and rem
    # inside an IFRAME resolves against the iframe's own root font-size,
    # which is whatever the browser defaults to — not the page's. Two
    # numbers that read the same in two stylesheets and mean different
    # things in two documents.
    #
    # 11.5px IS 0.72rem AT THE PAGE'S ROOT, which is 16px and stays 16px:
    # Baba's text-size setting resizes the TEXT AREAS and the reading
    # surfaces, not the root. I first made this scale with that setting
    # and it was wrong in the other direction — the copy link would have
    # grown while `clear` beside it stayed put. Checked before shipping,
    # not after.
    #
    # The wide copy button at the top of this file already knew the
    # lesson: "font and colour are PASSED IN, not fixed here. This
    # component is an iframe, so it inherits none of the page's CSS
    # variables." Forty lines above the mistake.
    # 14px AND THIS EXACT GREY, both MEASURED off the real page rather
    # than derived. `clear` computes to 14px / rgb(177,163,137) in a
    # browser — not the 11.5px the stylesheet's 0.72rem suggests, and
    # not the --dim this file was guessing at. Two stylesheets cannot be
    # kept in step by reasoning about them; they can be measured.
    px = 14
    LINKCSS = ("""
  button {
    height: %dpx !important; font-weight: 400 !important;
    font-size: %dpx !important; letter-spacing: 0 !important;
    text-decoration: underline; text-underline-offset: 3px;
    color: %s !important; justify-content: flex-end !important;
    padding: 0 12px 0 0 !important; min-height: 0 !important;
  }
  html, body { justify-content: flex-end !important; align-items: flex-start; }
""" % (px + 8, px, DIM)) if link else ""

    return f"""
<!doctype html>
<meta charset="utf-8">
<style>
  html, body {{ margin:0; padding:0; background:transparent;
                display:flex; align-items:center;
                justify-content:center; }}
  button {{
    {"width:100%; height:44px; border:none; background:transparent;"
     " justify-content:center; padding:0; font-weight:600;"
     " letter-spacing:0.04em;"
     if not size else
     f"width:{size}px; height:{size}px; border-radius:50%;"}
    {"color:" + FG + ";" if not size else
     "border:1px solid " + GOLD + "; background:" + GOLD + "; color:" + BG + ";"}
    font-family: ui-monospace, monospace; font-weight:800;
    font-size:{"0.92rem" if not size else str(max(13, int(size * 0.30))) + "px"};
    letter-spacing:0.06em; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    transition: transform 90ms ease-out, filter 90ms ease-out;
  }}
  {LINKCSS}
  button:active:not(:disabled) {{ color:{GOLD}; }}
  button:focus-visible {{ outline:3px solid {GOLD}; outline-offset:3px; }}
  button.failed {{ color:#f48383; }}
  @media (prefers-reduced-motion: reduce) {{
    button {{ transition:none; }}
    button:active:not(:disabled) {{ transform:none; }}
  }}
</style>
<button id="b" type="button" aria-live="polite" aria-label="{label}"></button>
<script>
  const TEXT = {payload};
  const L = {labels};
  const b = document.getElementById('b');
  let timer = null;
  function set(s) {{ b.textContent = L[s]; b.className = (s === 'failed') ? 'failed' : ''; }}
  set('idle');
  b.addEventListener('click', async () => {{
    if (timer) {{ clearTimeout(timer); timer = null; }}
    set('busy'); b.disabled = true;
    let ok = false;
    try {{ await navigator.clipboard.writeText(TEXT); ok = true; }}
    catch (e) {{
      try {{
        const ta = document.createElement('textarea');
        ta.value = TEXT; ta.style.position='fixed'; ta.style.opacity='0';
        document.body.appendChild(ta); ta.focus(); ta.select();
        ok = document.execCommand('copy'); ta.remove();
      }} catch (e2) {{ ok = false; }}
    }}
    set(ok ? 'done' : 'failed'); b.disabled = false;
    timer = setTimeout(() => set('idle'), 2200);
  }});
</script>
"""


# ---------------------------------------------------------------------
# A GRID OF PILLS THAT COPY — one component, not one per pill
#
# Baba, 25.8.2026: "make both views look identical... action buttons, and
# they can be written in multiple columns depending how wide the user
# interface is. And they should be aligned left, not right. So checkmark,
# no checkmark, it looks identical."
#
# WHY ONE COMPONENT AND NOT TWELVE. The first version put each pill in
# its own iframe inside an st.columns row. Two things went wrong at once
# and his screenshot showed both: every pill landed on its own line,
# because an iframe is a block and twelve of them cannot share a row; and
# every one was right-aligned, because `link=True` forces
# justify-content: flex-end — correct for `copy` sitting at the end of a
# box row, wrong for a grid.
#
# One iframe holding the whole grid fixes both, and it answers the worry
# recorded in v204's delivery note: twelve clipboard components on one
# page was never tested and now does not exist.
#
# IT WRAPS BY ITSELF. Flex with a min width per pill, so the number of
# columns follows the width of the phone rather than a number chosen
# here. Baba: "depends how wide the user interface is."
#
# THE COLOURS ARE PASSED IN, never guessed. An iframe inherits none of
# the page's CSS variables — the lesson already written twice in this
# file. The caller reads them from the theme and hands them over, so a
# scheme change follows.
# ---------------------------------------------------------------------

GRID_MIN_PX = 96          # a pill narrower than this is hard to hit
GRID_ROW_PX = 42          # one row of pills, including its gap


def grid_height(count: int, per_row: int = 3) -> int:
    """How tall the iframe must be. An iframe does not grow to fit its
    content — it is given a height and clips whatever else there is, so
    a wrong number here silently hides the last row of directions."""
    rows = max(1, (max(0, int(count)) + per_row - 1) // per_row)
    return rows * GRID_ROW_PX + 8


def pill_grid(items, done_label: str = "copied", failed_label: str = "—",
              bg: str = "#141a21", fg: str = "#f2ddb4",
              line: str = "#23303d", lit: str = "#f59e0b") -> str:
    """`items` is [(label, text_to_copy, tooltip)]. One press copies one.

    THE PILL IS THE SAME PILL as the Streamlit buttons beside it —
    999px, the same surface, the same border, the same ink — because the
    whole point is that ticking the box changes what a press DOES and
    nothing about what the row looks like.
    """
    rows = _js([{"label": str(a), "text": str(b), "tip": str(c or "")}
                for a, b, c in (items or [])])
    labels = _js({"done": done_label, "failed": failed_label})
    return f"""
<!doctype html><meta charset="utf-8">
<style>
  html, body {{ margin:0; padding:0; background:transparent; }}
  #wrap {{
    display:flex; flex-wrap:wrap; gap:6px;
    justify-content:flex-start; align-items:flex-start;
  }}
  button {{
    flex: 1 1 {GRID_MIN_PX}px; min-width:{GRID_MIN_PX}px; max-width:100%;
    min-height:34px; border-radius:999px; cursor:pointer;
    background:{bg}; color:{fg}; border:1px solid {line};
    font-family:ui-monospace,Menlo,monospace; font-size:13px;
    letter-spacing:.03em; padding:.28rem .7rem; white-space:nowrap;
    overflow:hidden; text-overflow:ellipsis;
  }}
  button:active {{ transform:translateY(1px); }}
  button.done {{ background:{lit}; color:{bg}; border-color:{lit}; }}
</style>
<div id="wrap"></div>
<script>
const ITEMS = {rows}, L = {labels};
const wrap = document.getElementById('wrap');
ITEMS.forEach(function(it){{
  const b = document.createElement('button');
  b.type = 'button';
  b.textContent = it.label;
  if (it.tip) b.title = it.tip;
  b.onclick = async function(){{
    const was = it.label;
    try {{
      await navigator.clipboard.writeText(it.text);
      b.textContent = L.done; b.classList.add('done');
    }} catch (e) {{
      // A CLIPBOARD CALL THAT NEVER ANSWERS is the fault four-tests.md
      // names by name, so there is a fallback and not a dead button:
      // select the text in a temporary field so it can be copied by
      // hand, and say so on the pill itself.
      try {{
        const ta = document.createElement('textarea');
        ta.value = it.text; document.body.appendChild(ta);
        ta.select(); document.execCommand('copy'); ta.remove();
        b.textContent = L.done; b.classList.add('done');
      }} catch (e2) {{
        b.textContent = L.failed;
      }}
    }}
    setTimeout(function(){{
      b.textContent = was; b.classList.remove('done');
    }}, 1200);
  }};
  wrap.appendChild(b);
}});
</script>
"""
