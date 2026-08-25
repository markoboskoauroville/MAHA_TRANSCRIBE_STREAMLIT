"""ONE PRESS STARTS A READING.

    python3 tests/test_double_play.py

Fault 4 of Baba's brief, 03:20 on 25.8.2026:

  "THE DOUBLE PLAY. Every reader deck needs two presses — the first does
   nothing. Never investigated."

INVESTIGATED. The idle deck was keyed `talk_player_idle` and the playing
deck `talk_player` — TWO KEYS, so Streamlit mounts TWO IFRAMES. The press
landed on the idle one; Python built the first block and rendered the
OTHER one with autoplay=True. A browser only permits audio.play() in a
document that has had a user gesture, and that fresh iframe had never
been touched. The play was refused, the refusal was swallowed by a bare
.catch(), and nothing happened.

The second press worked because by then the person was pressing the
playing deck itself — a gesture in the right document.

ONE KEY IS ONE IFRAME: it survives the rerun, keeps its gesture, and
autoplay is allowed. TR and VR never had this, because they only ever had
one key each — which is exactly why Baba said "every READER deck".

WHAT THIS CANNOT CATCH: whether a real browser now plays on one press.
Autoplay policy is the browser's and no test here runs one. What is
checked is that the two documents became one, and that a refusal can
never be silent again.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = failed = 0
def check(n, c, d=""):
    global passed, failed
    if c: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ("  — " + str(d) if d else ""))

app = open(os.path.join(os.path.dirname(__file__), "..", "app.py"),
           encoding="utf-8").read()
front = open(os.path.join(os.path.dirname(__file__), "..",
                          "waveform_frontend", "index.html"),
             encoding="utf-8").read()
def _js_code(src):
    """The JavaScript with /* */ and // comments removed.

    My first version dropped lines STARTING with a comment marker, which
    misses the middle of a multi-line /* */ block — and one of those
    lines quotes `catch(function(){})` while explaining that it was
    removed. Fifth time today a check matched its own explanation.
    """
    out, inblock = [], False
    for line in src.splitlines():
        t = line.strip()
        if inblock:
            if "*/" in t:
                inblock = False
            continue
        if t.startswith("/*"):
            if "*/" not in t:
                inblock = True
            continue
        if t.startswith("//"):
            continue
        out.append(line)
    return "\n".join(out)


fcode = _js_code(front)

print("1 ONE DECK, ONE IFRAME")
check("1a the idle deck no longer has a key of its own",
      'key="talk_player_idle"' not in app)
check("1b both R branches use the same key",
      app.count('key="talk_player"') == 2, app.count('key="talk_player"'))
i = app.index('key="talk_player"')
j = app.index('key="talk_player"', i + 10)
check("1c and they are in MUTUALLY EXCLUSIVE branches, or Streamlit "
      "would refuse a duplicate key",
      (app[:i].rfind("    if job:") > app[:i].rfind("    else:"))
      != (app[:j].rfind("    if job:") > app[:j].rfind("    else:")))
check("1d the playing branch autoplays", "autoplay=True" in app[i - 200:i])
check("1e the idle branch does not — it is waiting to be pressed",
      "autoplay=False" in app[j - 200:j])

print("\n1b THE OTHER DECKS WERE NEVER AFFECTED")
for key in ("tr_player", "vr_player"):
    check("1f %s has exactly one key, which is why it never needed two "
          "presses" % key, app.count('key="%s"' % key) == 1,
          app.count('key="%s"' % key))

print("\n2 A REFUSED PLAY IS NEVER SILENT")
# The empty catch is how this stayed invisible. A browser refusing
# audio.play() is a diagnosable policy decision; swallowing it turns it
# into "the app does nothing when I press play".
check("2a there is no bare .catch() left in the code",
      "catch(function(){})" not in fcode,
      [l for l in fcode.splitlines() if "catch(function(){})" in l])
check("2b the autoplay path reports a refusal",
      "autoplay refused:" in front)
check("2c and tells the person what to do about it",
      "press play to start" in front)
check("2d a DIRECT press that is refused says so too — the most "
      "surprising case, because they definitely made a gesture",
      "this browser would not play it" in front)
check("2e both put the transport back to PLAY, so a second press is an "
      "obvious thing to do rather than a guess",
      front.count("setPlaying(false);\n      if(!PYMSG)") == 2,
      front.count("setPlaying(false);\n      if(!PYMSG)"))
check("2f and neither stamps on a message Python is showing",
      front.count("if(!PYMSG) msg.textContent") >= 2)

print("\n3 THE START HANDSHAKE IS UNCHANGED")
# One press is still one start: the stamp guards against the component
# re-reporting across reruns.
check("3a the idle press still reports a start",
      "{at: Date.now(), start: true}" in front)
check("3b only when there is something to start",
      "classList.contains('startable')" in front)
check("3c Python still guards it with a stamp", '"_talk_start_seen"' in app)
check("3d so one press cannot become two starts",
      '_ev0.get("at")' in app and "_start = True" in app)

print("\n{} passed, {} failed".format(passed, failed))
sys.exit(1 if failed else 0)
