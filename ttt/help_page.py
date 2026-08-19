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

<h2>Kartice na vrhu</h2>
<table>
<tr><th>T</th><td>Snimanje i prijepis govora u tekst.</td></tr>
<tr><th>R</th><td>Čitanje teksta naglas, uz označavanje riječi.</td></tr>
<tr><th>TR</th><td>Prijevod.</td></tr>
<tr><th>⚙ sivi</th><td>Izgled — font, veličina, boje.</td></tr>
<tr><th>⚙ jantarni</th><td>Motori i ključevi. Vidi ga samo vlasnik.</td></tr>
<tr><th>H</th><td>Ova stranica.</td></tr>
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
<p><b>T1</b> je ono što sada radi: snima <b>mikrofon</b>. Radi svugdje —
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

<h2>The tabs along the top</h2>
<table>
<tr><th>T</th><td>Record and turn speech into text.</td></tr>
<tr><th>R</th><td>Read text aloud, highlighting each word.</td></tr>
<tr><th>TR</th><td>Translate.</td></tr>
<tr><th>⚙ grey</th><td>Looks — font, size, colours.</td></tr>
<tr><th>⚙ amber</th><td>Engines and keys. Only the owner sees it.</td></tr>
<tr><th>H</th><td>This page.</td></tr>
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
<p><b>T1</b> is what works today: it records the <b>microphone</b>. It works
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


def page(lang: str = "hr") -> str:
    """One document holding both languages, with an instant toggle."""
    start = "hr" if str(lang).lower().startswith("hr") else "en"
    return f"""<!doctype html><meta charset="utf-8">
<style>{CSS}</style>
<div id="top">
  <button class="lang" id="bHR" type="button">HR</button>
  <button class="lang" id="bEN" type="button">ENG</button>
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
