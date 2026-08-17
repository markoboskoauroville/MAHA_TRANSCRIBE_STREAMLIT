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

BG = "#0d0d0d"
FG = "#e8dcc0"
GOLD = "#e0a340"
EDGE = "rgba(232,220,192,0.25)"

# Enough for a 44px target plus breathing room; Streamlit reserves this
# height in the page whether or not the button fills it.
HEIGHT = 58


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
         scale: float = 1.0) -> str:
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
    font-family: ui-monospace, monospace;
    font-size: {size}rem;
    color: {FG}; background: {BG};
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
  button.done {{ border-color: {GOLD}; background: {GOLD}; color: {BG}; }}
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
