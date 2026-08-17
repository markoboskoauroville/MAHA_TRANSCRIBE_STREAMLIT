"""One player for the whole text, with the subtitle following along.

Replaces the old reader, which synthesised a sentence, played it, waited,
and synthesised the next. That put an audio bar on screen per sentence, a
silent gap at every full stop, and gave no idea how long was left. Baba:
*"users should not be aware of the engine beneath. It's just a player for
the whole text."*

So: one file, one player, and a subtitle box that shows the sentence being
spoken. Elapsed and remaining time come free from the audio element, and
seeking anywhere works because it really is one file.

The highlight is driven by the audio's own `timeupdate`, so it follows
the sound rather than a timer running alongside it. If the person seeks,
pauses, or their phone throttles the tab, the subtitle is still correct —
which a Python-side sleep loop could never manage.

One-way on purpose: this component never needs to send anything back to
Python, so it is plain `components.html` rather than a declared
component. Less to go wrong, and nothing to go stale.
"""

import base64
import json


def _js(value) -> str:
    out = json.dumps(value, ensure_ascii=False)
    return (out.replace("</", "<\\/")
               .replace("<!--", "<\\!--")
               .replace("\u2028", "\\u2028")
               .replace("\u2029", "\\u2029"))


def height_for(scale: float = 1.0) -> int:
    """Room for the player, the subtitle and the skip row. Grows with the
    reader's text size, or the subtitle would be clipped exactly for the
    people who enlarged it."""
    return int(250 + 90 * max(0.0, float(scale) - 1.0))


def html(audio_bytes: bytes, marks, scale: float = 1.0,
         autoplay: bool = True, labels=None) -> str:
    """`marks` is [{start,end,text,start_time,end_time}] over the whole
    text, as produced by ttt.speech.build()."""
    labels = labels or {}
    src = "data:audio/mpeg;base64," + base64.b64encode(audio_bytes).decode()
    size = round(1.35 * max(0.8, min(float(scale or 1.0), 2.5)), 3)

    return f"""
<!doctype html>
<meta charset="utf-8">
<style>
  html, body {{ margin:0; padding:0; background:transparent;
                font-family: ui-monospace, "JetBrains Mono", monospace;
                color:#f2ddb4; }}
  .sub {{
    border:1px solid #23303d; border-radius:12px; background:#141a21;
    padding:0.9rem 0.8rem; min-height:{round(4.4 * size, 1)}rem;
    font-size:{size}rem; line-height:1.5; letter-spacing:0.012em;
    overflow-wrap:break-word; display:flex; align-items:center;
  }}
  .sub b {{ background:#f59e0b; color:#0b0d10; border-radius:4px;
            padding:1px 4px; font-weight:600; }}
  audio {{ width:100%; margin:0.5rem 0 0.35rem; height:44px; }}
  .row {{ display:flex; gap:0.35rem; align-items:center; }}
  .row button {{
    min-width:44px; min-height:44px; border-radius:999px;
    background:#141a21; border:1px solid #23303d; color:#f2ddb4;
    font-family:inherit; font-size:1rem; cursor:pointer;
    transition: border-color 90ms ease-out, background-color 90ms ease-out;
  }}
  .row button:hover {{ border-color:#f59e0b; background:rgba(245,158,11,0.10); }}
  .row button:active {{ transform:scale(0.97); }}
  .row button:focus-visible {{ outline:3px solid #f59e0b; outline-offset:2px; }}
  .count {{ margin-left:auto; color:#b1a389; font-size:0.85rem;
            font-variant-numeric:tabular-nums; }}
  @media (prefers-reduced-motion: reduce) {{ .row button {{ transition:none; }} }}
</style>

<div class="sub" id="sub" aria-live="polite"></div>
<audio id="a" controls preload="auto" src="{src}"></audio>
<div class="row">
  <button id="prev" title="{labels.get('prev', 'previous sentence')}"
          aria-label="{labels.get('prev', 'previous sentence')}">&#9198;</button>
  <button id="next" title="{labels.get('next', 'next sentence')}"
          aria-label="{labels.get('next', 'next sentence')}">&#9197;</button>
  <span class="count" id="count"></span>
</div>

<script>
  const M = {_js(marks)};
  const a = document.getElementById('a');
  const sub = document.getElementById('sub');
  const count = document.getElementById('count');
  let cur = -1;

  function indexAt(t) {{
    for (let i = 0; i < M.length; i++) {{
      if (t >= M[i].start_time && t < M[i].end_time) return i;
    }}
    // Between two sentences: stay on the one just finished rather than
    // blanking, so the box never flickers empty mid-reading.
    for (let i = M.length - 1; i >= 0; i--) if (t >= M[i].start_time) return i;
    return 0;
  }}

  function show(i) {{
    if (i === cur || !M.length) return;
    cur = i;
    sub.innerHTML = '<b></b>';
    sub.firstChild.textContent = M[i].text;
    count.textContent = (i + 1) + ' / ' + M.length;
  }}

  a.addEventListener('timeupdate', () => show(indexAt(a.currentTime)));
  a.addEventListener('seeked',     () => show(indexAt(a.currentTime)));
  a.addEventListener('loadedmetadata', () => show(0));

  document.getElementById('prev').addEventListener('click', () => {{
    const i = Math.max(0, indexAt(a.currentTime) - 1);
    a.currentTime = M[i].start_time; show(i);
  }});
  document.getElementById('next').addEventListener('click', () => {{
    const i = Math.min(M.length - 1, indexAt(a.currentTime) + 1);
    a.currentTime = M[i].start_time; show(i);
  }});

  show(0);
  {"a.play().catch(function(){});" if autoplay else ""}
</script>
"""
