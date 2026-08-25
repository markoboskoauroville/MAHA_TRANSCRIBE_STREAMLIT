import re
"""The help page.

ONE DOCUMENT, BOTH LANGUAGES, NO RELOAD. Croatian and English are both in
the page at once and the toggle only changes which is displayed. That is
why switching is instant and why it keeps your place in the text — a
Streamlit rerun would rebuild the page and throw you back to the top,
which is exactly what Baba asked not to happen.

The content lives here rather than in the component so both halves are
edited side by side and cannot drift apart.
"""

CSS = """
:root{--bg:#0b0d10;--card:#12161c;--line:rgba(232,220,192,.16);
      --prose:#f2ddb4;--dim:#9aa3af;--amber:#f59e0b;--dark:#0b0d10;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--prose);
     font:15px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;}
#top{position:sticky;top:0;z-index:5;background:var(--bg);
     border-bottom:1px solid var(--line);padding:8px 12px;display:flex;
     gap:0;align-items:center}
.lang{flex:0 0 auto;height:38px;min-width:64px;padding:0 14px;
      background:var(--card);color:var(--prose);border:1px solid var(--line);
      border-right-width:0;font:inherit;font-size:13px;cursor:pointer}
.lang:last-of-type{border-right-width:1px;border-radius:0 3px 3px 0}
.lang:first-of-type{border-radius:3px 0 0 3px}
.lang.on{background:var(--amber);color:var(--dark)}
.lang:focus-visible{outline:3px solid var(--amber);outline-offset:-3px}
#wrap{padding:14px 14px 40px}
h2{font-size:16px;margin:26px 0 8px;color:var(--amber);
   border-bottom:1px solid var(--line);padding-bottom:5px}
h3{font-size:14px;margin:18px 0 6px;color:var(--prose)}
p,li{color:var(--prose);font-size:14px}
ul{padding-left:20px;margin:8px 0}
li{margin:5px 0}
code{background:#0b0d10;border:1px solid var(--line);border-radius:3px;
     padding:1px 5px;font-size:13px;color:var(--amber)}
.note{border-left:3px solid var(--amber);padding:8px 12px;margin:12px 0;
      background:rgba(245,158,11,.06);font-size:13.5px}
.warn{border-left:3px solid #d9534f;padding:8px 12px;margin:12px 0;
      background:rgba(217,83,79,.07);font-size:13.5px}
.soon{border-left:3px solid var(--dim);padding:8px 12px;margin:12px 0;
      background:rgba(154,163,175,.07);font-size:13.5px;color:var(--dim)}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13px}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;
      vertical-align:top}
th{color:var(--amber);font-weight:600}
dt{color:var(--amber);margin-top:12px;font-size:13.5px}
dd{margin:3px 0 0 0;color:var(--prose);font-size:13.5px}
[data-lang]{display:none}
[data-lang].show{display:block}
"""

HR = """
<h2>Što je TTT-LLL?</h2>
<p><b>TTT</b> je <i>Talk To Type</i> — govoriš, a aplikacija ispisuje.
<b>LLL</b> je <i>Look, Listen, Learn</i> — aplikacija čita naglas dok ti
istu rečenicu vidiš na ekranu.</p>

<h2>Moduli</h2>
<table>
<tr><th>T1</th><td><b>Modul za transkripciju.</b> Snima mikrofon i pretvara govor u tekst.</td></tr>
<tr><th>T2</th><td><b>Modul za zvuk s računala.</b> Nadolazeće.</td></tr>
<tr><th>R</th><td><b>Modul za čitanje.</b> Čita tekst naglas i označava riječ koju izgovara.</td></tr>
<tr><th>TR</th><td><b>Modul za prijevod.</b></td></tr>
<tr><th>⚙ sivi</th><td><b>Modul izgleda.</b> Font, veličina, boje.</td></tr>
<tr><th>⚙ jantarni</th><td><b>Modul postavki.</b> Motori i ključevi. Vidi ga samo vlasnik.</td></tr>
<tr><th>H</th><td><b>Modul pomoći.</b> Ova stranica.</td></tr>
</table>

<h2>Kasetofon</h2>
<p>Četiri tipke u jednom redu:</p>
<ul>
<li><b>rec</b> — počinje snimati. Val na ekranu pokazuje pravi signal.</li>
<li><b>pause</b> — stane i nastavlja u istoj snimci. Sat se zaustavlja.</li>
<li><b>stop</b> — završava snimku i <b>odmah je šalje</b> na prijepis.
Nema dodatnog koraka.</li>
<li><b>open</b> — otvara datoteku s telefona ili računala.</li>
</ul>
<div class="note"><b>Ako je val ravna crta, mikrofon ne prima zvuk.</b>
To je najkorisnija stvar koju ti snimač može reći prije nego što govoriš
deset minuta u ništa.</div>

<h3>Lijepljenje</h3>
<p>Pritisni <code>Ctrl+V</code>, ili dugi pritisak → Zalijepi na Androidu.
Slika s međuspremnika ide kao slika, sve ostalo kao tekst. Ne treba
nikakav dodatak ni proširenje za preglednik.</p>

<h2>single i multi</h2>
<ul>
<li><b>single</b> — novi prijepis <b>zamjenjuje</b> ono što je u okviru.</li>
<li><b>multi</b> — novi prijepis se <b>dodaje</b> ispod, odvojen praznim
redom.</li>
</ul>
<div class="note">Kako se jede slon? Žlicu po žlicu. U <b>multi</b> načinu
snimaš pet minuta, staneš, pojedeš kičari, pa nastaviš. Svaki dio je
spremljen prije nego što počne sljedeći — pa ako veza pukne, gubiš najviše
zadnjih pet minuta, a ne pola sata.</div>

<h2>HR i ENG</h2>
<p>Ovo je <b>naredba, ne prijedlog</b>. Jezik se nikada ne pogađa
automatski. Izmjereno: bez zadanog jezika model razbacuje zareze i
izmišlja riječi. Ako govoriš hrvatski, stisni HR prije snimanja.</p>

<h2>Red naredbi</h2>
<table>
<tr><th>new</th><td>Nova snimka, briše staru.</td></tr>
<tr><th>copy</th><td>Kopira tekst u međuspremnik.</td></tr>
<tr><th>grammar</th><td>Popravlja pravopis i očite omaške.</td></tr>
<tr><th>reshape</th><td>Slaže tekst u uredne odlomke.</td></tr>
<tr><th>clear</th><td>Prazni okvir.</td></tr>
</table>

<h2>Kad nešto ne radi</h2>
<p>Ispod kasetofona je <b>status</b>. Sklopljen je dok je sve u redu, a
<b>sam se otvara kada nešto pođe po zlu</b>. U njemu piše:</p>
<ul>
<li>što je stiglo i u što je pretvoreno — npr.
<code>WebM (Opus) 6.997 KB → 16 kHz mono FLAC</code></li>
<li>koliko je trajalo pretvaranje i koliko prijepis</li>
<li>koliko je znakova vraćeno</li>
<li><b>Whisper odbio:</b> — pravi razlog odbijanja, ako ga je bilo</li>
</ul>
<div class="warn"><b>0 znakova</b> znači da je zvuk stigao, ali u njemu
nije pronađen govor. Provjeri je li val bio ravan dok si snimao.</div>

<h3>Slanje kad veza puca</h3>
<p>Snimka se <b>ne zaboravlja dok se ne potvrdi da je stigla</b>. Ako ne
stigne, pokušava pet puta (2, 4, 8, 15, 25 sekundi), a onda stane i
četvrta ćelija postane <b>ponovi</b>. Kad se veza vrati, šalje sama od
sebe.</p>
<div class="warn">Snimka živi u memoriji preglednika. <b>Ako zatvoriš
karticu prije nego što je poslana, izgubljena je.</b> Zato u lošoj vezi
snimaj kraće dijelove u <b>multi</b> načinu.</div>

<h2>T1 i T2</h2>
<p><b>T1</b>, modul za transkripciju, je ono što sada radi: snima <b>mikrofon</b>. Radi svugdje —
Android, macOS, Windows, u pregledniku.</p>
<div class="soon"><b>T2 — zvuk sustava. Još nije napravljeno.</b><br>
Ideja: snimati ono što računalo <i>svira</i>, a ne ono što mikrofon čuje.
Za prijepis video poziva, snimke sastanka, podcasta ili videa.
<ul>
<li><b>Windows</b> — preglednik to može sam, uz dijeljenje zvuka sustava.</li>
<li><b>macOS</b> — treba besplatni BlackHole, koji se pojavi kao običan
mikrofon.</li>
<li><b>Android</b> — <b>nije moguće.</b> Sustav to ne dopušta.</li>
</ul>
<b>Prije snimanja poziva provjeri zakon.</b> U Hrvatskoj snimanje razgovora
bez pristanka nije uvijek dopušteno.</div>

<h2>Rječnik</h2>
<dl>
<dt>prijepis (transcript)</dt><dd>Tekst nastao iz govora.</dd>
<dt>Whisper</dt><dd>Model koji pretvara govor u tekst.</dd>
<dt>Groq</dt><dd>Servis na kojem Whisper radi. Brz.</dd>
<dt>FLAC</dt><dd>Format zvuka bez gubitaka. Aplikacija sve pretvara u
16 kHz mono FLAC jer Whisper to očekuje.</dd>
<dt>Opus / WebM</dt><dd>Format u kojem preglednik snima. Jedini koji
preglednik nudi — WAV nije moguć.</dd>
<dt>16 kHz mono</dt><dd>16.000 uzoraka u sekundi, jedan kanal. Dovoljno za
govor, a datoteka je puno manja.</dd>
<dt>loudnorm</dt><dd>Izjednačavanje glasnoće prije prijepisa. Spašava tihe
snimke.</dd>
<dt>chunk / komad</dt><dd>Dugi zvuk se reže na desetominutne komade, šalje
jedan po jedan i spaja natrag u jedan tekst.</dd>
<dt>ključ (API key)</dt><dd>Lozinka kojom se aplikacija predstavlja
servisu. Ima ih više pa jedan umorni odmara.</dd>
<dt>međuspremnik (clipboard)</dt><dd>Mjesto gdje živi ono što si kopirao.</dd>
</dl>
"""

EN = """
<h2>What is TTT-LLL?</h2>
<p><b>TTT</b> is <i>Talk To Type</i> — you speak, the app writes.
<b>LLL</b> is <i>Look, Listen, Learn</i> — the app reads aloud while you
see the same sentence on screen.</p>

<h2>The modules</h2>
<table>
<tr><th>T1</th><td><b>The transcription module.</b> Records the microphone and turns speech into text.</td></tr>
<tr><th>T2</th><td><b>The computer-audio module.</b> Coming.</td></tr>
<tr><th>R</th><td><b>The read module.</b> Reads text aloud and highlights the word being spoken.</td></tr>
<tr><th>TR</th><td><b>The translate module.</b></td></tr>
<tr><th>⚙ grey</th><td><b>The looks module.</b> Font, size, colours.</td></tr>
<tr><th>⚙ amber</th><td><b>The settings module.</b> Engines and keys. Only the owner sees it.</td></tr>
<tr><th>H</th><td><b>The help module.</b> This page.</td></tr>
</table>

<h2>The cassette deck</h2>
<p>Four keys in one row:</p>
<ul>
<li><b>rec</b> — starts recording. The trace shows the real signal.</li>
<li><b>pause</b> — stops and resumes within the same take. The clock
freezes.</li>
<li><b>stop</b> — ends the take and <b>sends it straight away</b>. There is
no second step.</li>
<li><b>open</b> — opens a file from your phone or computer.</li>
</ul>
<div class="note"><b>If the trace is a flat line, the microphone is not
receiving.</b> That is the single most useful thing a recorder can tell you
before you talk for ten minutes into nothing.</div>

<h3>Pasting</h3>
<p>Press <code>Ctrl+V</code>, or long-press → Paste on Android. A picture
on the clipboard arrives as a picture, anything else as text. No extension
or add-on is needed for this, and none would help.</p>

<h2>single and multi</h2>
<ul>
<li><b>single</b> — the new transcript <b>replaces</b> what is in the
box.</li>
<li><b>multi</b> — the new transcript is <b>added underneath</b>, separated
by a blank line.</li>
</ul>
<div class="note">How do you eat an elephant? Spoon by spoon. In
<b>multi</b> you record for five minutes, stop, eat, and carry on. Each
piece is safely stored before the next begins — so if the connection
breaks you lose the last five minutes, not half an hour.</div>

<h2>HR and ENG</h2>
<p>This is an <b>instruction, not a hint</b>. The language is never guessed.
Measured: without a language set, the model scatters commas and invents
words. If you are speaking Croatian, press HR before recording.</p>

<h2>The command row</h2>
<table>
<tr><th>new</th><td>Fresh take, discards the old one.</td></tr>
<tr><th>copy</th><td>Copies the text to the clipboard.</td></tr>
<tr><th>grammar</th><td>Fixes spelling and obvious slips.</td></tr>
<tr><th>reshape</th><td>Tidies the text into clear paragraphs.</td></tr>
<tr><th>clear</th><td>Empties the box.</td></tr>
</table>

<h2>When something does not work</h2>
<p>Under the deck there is a <b>status</b> box. It stays folded while all is
well and <b>opens by itself when something goes wrong</b>. It shows:</p>
<ul>
<li>what arrived and what it became — e.g.
<code>WebM (Opus) 6,997 KB → 16 kHz mono FLAC</code></li>
<li>how long converting took, and how long transcribing took</li>
<li>how many characters came back</li>
<li><b>Whisper refused:</b> — the real reason, when there was one</li>
</ul>
<div class="warn"><b>0 chars</b> means the audio arrived but no speech was
found in it. Check whether the trace was flat while you were recording.</div>

<h3>Sending on a broken connection</h3>
<p>A recording is <b>not forgotten until it is proven to have landed</b>. If
it does not, it tries five times (2, 4, 8, 15, 25 seconds), then stops and
the fourth cell becomes <b>retry</b>. When the signal returns it resends by
itself.</p>
<div class="warn">The recording lives in the browser's memory. <b>If you
close the tab before it has been sent, it is lost.</b> On a weak connection,
record shorter pieces in <b>multi</b> mode.</div>

<h2>T1 and T2</h2>
<p><b>T1</b>, the transcription module, is what works today: it records the <b>microphone</b>. It works
everywhere — Android, macOS, Windows, in the browser.</p>
<div class="soon"><b>T2 — system audio. NOT BUILT YET.</b><br>
The idea: record what the computer is <i>playing</i> rather than what the
microphone hears. For transcribing a video call, a recorded meeting, a
podcast or a video.
<ul>
<li><b>Windows</b> — the browser can do this itself, by sharing system
audio.</li>
<li><b>macOS</b> — needs the free BlackHole, which then appears as an
ordinary microphone.</li>
<li><b>Android</b> — <b>not possible.</b> The system does not allow it.</li>
</ul>
<b>Check the law before recording a call.</b> In Croatia, recording a
conversation without consent is not always permitted.</div>

<h2>Dictionary</h2>
<dl>
<dt>transcript</dt><dd>The text made from speech.</dd>
<dt>Whisper</dt><dd>The model that turns speech into text.</dd>
<dt>Groq</dt><dd>The service Whisper runs on. Fast.</dd>
<dt>FLAC</dt><dd>Lossless audio format. Everything is converted to
16 kHz mono FLAC because that is what Whisper expects.</dd>
<dt>Opus / WebM</dt><dd>What the browser records in. The only thing a
browser offers — WAV is not possible.</dd>
<dt>16 kHz mono</dt><dd>16,000 samples a second, one channel. Enough for
speech, and a far smaller file.</dd>
<dt>loudnorm</dt><dd>Levelling the loudness before transcribing. It rescues
quiet recordings.</dd>
<dt>chunk</dt><dd>Long audio is cut into ten-minute pieces, sent one at a
time, and stitched back into one transcript.</dd>
<dt>API key</dt><dd>The password the app uses to identify itself to a
service. There are several, so a tired one can rest.</dd>
<dt>clipboard</dt><dd>Where whatever you copied lives.</dd>
</dl>
"""


def page(lang: str = "hr", show_toggle: bool = True,
         level: str = None) -> str:
    """One document holding both languages.

    `show_toggle=False` hides the buttons INSIDE the page, for when the
    language is chosen outside it.

    WHY THAT OPTION EXISTS. The toggle in here is client-side: it flips
    which div is shown and writes localStorage, and Python never hears
    about it. Once the help could be READ ALOUD that became a trap — Baba
    switched to Croatian with this toggle, pressed read, and got English,
    because the voice was following `ui_lang` while the screen was
    following localStorage. Two controls for one idea, disagreeing
    silently.

    So when the tab offers its own language buttons, these are hidden and
    there is exactly one place to choose. The cost is a rerun on each
    switch instead of an instant flip; the gain is that what you see is
    what you hear.
    """
    start = "hr" if str(lang).lower().startswith("hr") else "en"
    # FOUR DEPTHS, ONE PAGE. `level` picks which telling — see
    # ttt/help_levels.py for why four and what each is for. None keeps
    # the original single document, so nothing that called this before
    # has to change.
    if level:
        from ttt import help_levels as _L
        return _one_level(_L.body(start, level), start)
    _toggle = "" if not show_toggle else """
  <button class="lang" id="bHR" type="button">HR</button>
  <button class="lang" id="bEN" type="button">ENG</button>"""
    return f"""<!doctype html><meta charset="utf-8">
<style>{CSS}</style>
<div id="top">{_toggle}
</div>
<div id="wrap">
  <div data-lang="hr">{HR}</div>
  <div data-lang="en">{EN}</div>
</div>
<script>
// Both languages are already in the page. Switching only changes which
// one is shown, so it is instant and — the part Baba asked for — it does
// not move you in the text. A Streamlit rerun would rebuild the page and
// throw you back to the top.
var cur = "{start}";
function show(l){{
  cur = l;
  document.querySelectorAll('[data-lang]').forEach(function(d){{
    d.classList.toggle('show', d.getAttribute('data-lang') === l);
  }});
  // GUARDED, because the buttons are optional now. An unguarded
  // getElementById on a hidden toggle returns null, and .classList on
  // null throws — which would take the WHOLE page down and leave a
  // blank help tab, not a missing button.
  var _h = document.getElementById('bHR'), _e = document.getElementById('bEN');
  if (_h) _h.classList.toggle('on', l === 'hr');
  if (_e) _e.classList.toggle('on', l === 'en');
  try {{ localStorage.setItem('ttt_help_lang', l); }} catch(e) {{}}
}}
if (_h) _h.onclick = function(){{ show('hr'); }};
if (_e) _e.onclick = function(){{ show('en'); }};
try {{
  var saved = localStorage.getItem('ttt_help_lang');
  if (saved === 'hr' || saved === 'en') cur = saved;
}} catch(e) {{}}
show(cur);
</script>"""


# ---------------------------------------------------------------------
#  T2 — the tab that says what it will be
# ---------------------------------------------------------------------
# Deliberately NOT a stub. There is no rec key here that quietly does
# nothing: a control that looks alive and is not is worse than an empty
# room, because it costs someone a real recording to find out. It says
# what it will do, what it will need on each platform, and what it can
# never do.

SOON_HR = """
<h2>T2 — modul za zvuk s računala</h2>
<p class="lead">Nadolazeća mogućnost.</p>

<p>Ovo će snimati ono što <b>računalo svira</b>, a ne ono što mikrofon čuje
— pa ćeš moći prepisati:</p>
<ul>
<li>video poziv ili sastanak dok traje,</li>
<li>snimku sastanka koju ti je netko poslao,</li>
<li>podcast, predavanje ili video s interneta,</li>
<li>bilo koji zvuk koji svira na uređaju, bez mikrofona u sobi.</li>
</ul>

<p>Sučelje će biti <b>isto kao u modulu T1</b>: iste četiri tipke, isti val, isti
sat, isti <b>single</b> i <b>multi</b>, isti status. Razlika je samo odakle
zvuk dolazi.</p>

<h3>Što će trebati</h3>
<table>
<tr><th>Windows</th><td>Ništa. Preglednik to već može — pri dijeljenju
zaslona označiš <i>dijeli zvuk sustava</i>.</td></tr>
<tr><th>macOS</th><td>Besplatni <b>BlackHole</b>. Nakon instalacije se
pojavi kao običan mikrofon i aplikacija ga jednostavno odabere.</td></tr>
<tr><th>Android</th><td><b>Nije moguće.</b> Sustav ne dopušta snimanje
zvuka drugih aplikacija. Na telefonu ostaje modul T1.</td></tr>
</table>

<div class="warn"><b>Prije snimanja razgovora provjeri zakon.</b>
U Hrvatskoj snimanje razgovora bez pristanka sugovornika nije uvijek
dopušteno. Ovo je alat za prijepis, a ne dozvola.</div>

<div class="note">Do tada: sve što možeš spremiti kao datoteku možeš
prepisati već sada — u modulu <b>T1</b> pritisni <b>open</b> i odaberi je.</div>
"""

SOON_EN = """
<h2>T2 — the computer-audio module</h2>
<p class="lead">An upcoming feature.</p>

<p>This will record what the <b>computer is playing</b> rather than what
the microphone hears — so you will be able to transcribe:</p>
<ul>
<li>a video call or meeting as it happens,</li>
<li>a recorded meeting somebody sent you,</li>
<li>a podcast, a lecture, or a video from the internet,</li>
<li>any sound playing on the device, with no microphone in the room.</li>
</ul>

<p>The interface will be <b>the same as the T1 module</b>: the same four keys, the
same trace, the same clock, the same <b>single</b> and <b>multi</b>, the
same status box. Only where the sound comes from is different.</p>

<h3>What it will need</h3>
<table>
<tr><th>Windows</th><td>Nothing. The browser can already do this — tick
<i>share system audio</i> when sharing the screen.</td></tr>
<tr><th>macOS</th><td>The free <b>BlackHole</b>. Once installed it appears
as an ordinary microphone and the app simply selects it.</td></tr>
<tr><th>Android</th><td><b>Not possible.</b> The system does not allow
recording other apps' audio. On the phone, the T1 module remains.</td></tr>
</table>

<div class="warn"><b>Check the law before recording a conversation.</b>
In Croatia, recording a conversation without the other person's consent is
not always permitted. This is a transcription tool, not a permission.</div>

<div class="note">Until then: anything you can save as a file can be
transcribed today — in the <b>T1</b> module press <b>open</b> and choose it.</div>
"""


def soon(lang: str = "hr") -> str:
    """The T2 tab: both languages, same instant toggle as the help page."""
    start = "hr" if str(lang).lower().startswith("hr") else "en"
    return f"""<!doctype html><meta charset="utf-8">
<style>{CSS}
.lead{{color:var(--amber);font-size:13px;letter-spacing:.08em;
      text-transform:uppercase;margin:2px 0 14px}}
</style>
<div id="top">
  <button class="lang" id="bHR" type="button">HR</button>
  <button class="lang" id="bEN" type="button">ENG</button>
</div>
<div id="wrap">
  <div data-lang="hr">{SOON_HR}</div>
  <div data-lang="en">{SOON_EN}</div>
</div>
<script>
var cur = "{start}";
function show(l){{
  cur = l;
  document.querySelectorAll('[data-lang]').forEach(function(d){{
    d.classList.toggle('show', d.getAttribute('data-lang') === l);
  }});
  document.getElementById('bHR').classList.toggle('on', l === 'hr');
  document.getElementById('bEN').classList.toggle('on', l === 'en');
  try {{ localStorage.setItem('ttt_help_lang', l); }} catch(e) {{}}
}}
document.getElementById('bHR').onclick = function(){{ show('hr'); }};
document.getElementById('bEN').onclick = function(){{ show('en'); }};
try {{
  var saved = localStorage.getItem('ttt_help_lang');
  if (saved === 'hr' || saved === 'en') cur = saved;
}} catch(e) {{}}
show(cur);
</script>"""


# ---------------------------------------------------------------------
# THE SAME HELP, AS SPEECH
#
# Baba, 25.8.2026: "add in the help file to read. So there will be at the
# top female, male, and read... the user doesn't need to close the eyes
# and listen."
#
# THIS IS THE POINT OF THE WHOLE APP APPLIED TO ITS OWN INSTRUCTIONS. The
# people this is written for do not read easily — that is why R exists.
# Help that can only be READ is help that is hardest for exactly the
# person most likely to need it.
#
# HTML IS NOT SPEECH. The page is one document holding both languages,
# and handing that to a voice would have it read tag names, both
# languages end to end, and every table cell as a sentence. So the text
# is pulled out: one language, headings kept because they are the shape
# of the thing, everything else as prose.
#
# A PURE FUNCTION ON A STRING, so it can be run and checked without
# Streamlit and without a voice — four-tests.md: if the logic cannot be
# exercised without starting the app, that is itself the finding.
# ---------------------------------------------------------------------

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]+")


def plain(lang: str = "hr") -> str:
    """The help of ONE language as speakable prose.

    Block elements become sentence breaks rather than disappearing: a
    heading run together with the paragraph under it is a sentence the
    voice reads as one long clause, and the listener loses the shape.
    """
    body = HR if str(lang).lower().startswith("hr") else EN
    return _to_prose(body)


def _to_prose(body: str) -> str:
    """The stripper, once. plain() and plain_level() both use it.

    Pulled out rather than copied when levels arrived: two strippers
    would drift, and the drift would be a voice reading markup aloud in
    one place and not the other.
    """
    # SOURCE LINE BREAKS ARE NOT SENTENCE BREAKS. The HTML is hand-wrapped
    # at about 76 columns, so a paragraph is several source lines — and
    # keeping them made the voice read "the app reads aloud while you."
    # as a finished sentence and "see the same sentence on screen." as
    # another. Only a closing block tag ends a sentence, so every newline
    # in the source becomes an ordinary space FIRST and the block rules
    # below put the breaks back where they belong.
    txt = re.sub(r"\s*\n\s*", " ", body)
    # A cell boundary is a pause, not a join — otherwise a table reads as
    # one enormous run-on word list.
    txt = re.sub(r"</t[dh]>\s*<t[dh][^>]*>", " — ", txt, flags=re.I)
    # Anything that ends a block ends a sentence.
    txt = re.sub(r"</(p|h[1-6]|li|tr|div|table|ul|ol)>", ".\n", txt,
                 flags=re.I)
    txt = re.sub(r"<br\s*/?>", "\n", txt, flags=re.I)
    txt = _TAG.sub("", txt)
    txt = (txt.replace("&nbsp;", " ").replace("&amp;", "and")
              .replace("&lt;", "<").replace("&gt;", ">")
              .replace("&quot;", '"').replace("&#39;", "'"))
    out = []
    for line in txt.splitlines():
        line = _WS.sub(" ", line).strip()
        if not line:
            continue
        # DO NOT ADD A STOP TO SOMETHING ALREADY STOPPED. The block rule
        # above appends "." to every closing tag, so a heading that ended
        # in "?" came out as "Što je TTT-LLL?." — which a voice reads as
        # a question and then a pause it did not earn. Strip any trailing
        # stops that pile up, then add exactly one if it is still needed.
        line = re.sub(r"[.\s]+$", "", line)
        if not line:
            continue
        if not line.endswith(("!", "?", ":", "—")):
            line += "."
        out.append(line)
    return "\n".join(out)


def _one_level(html_body: str, start: str) -> str:
    """A single level, wrapped in the same stylesheet as the full page.

    NO LANGUAGE TOGGLE INSIDE. The tab owns both the language and the
    level now, and a second control in here is exactly the trap v197
    fixed: the screen followed localStorage while the voice followed
    something else.
    """
    return ("<!doctype html><meta charset=\"utf-8\">"
            "<style>%s</style><div id=\"top\"></div>"
            "<div data-lang=\"%s\">%s</div>" % (CSS, start, html_body))


def plain_level(lang: str = "hr", level: str = "adult") -> str:
    """One level, as words for a voice. Same stripper as plain()."""
    from ttt import help_levels as _L
    start = "hr" if str(lang).lower().startswith("hr") else "en"
    return _to_prose(_L.body(start, level))
