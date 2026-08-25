"""THE HELP, AT FOUR DEPTHS.

Baba asked for this on 25.8.2026 and it waited a long time:

  "Four-level free-user help file: a child of five, mid-school, a
   non-technical adult, a first-year IT student. In Croatian and English,
   written to be HEARD."

WHY FOUR AND NOT ONE. The people using this app are a five-year-old's
grandfather, a working actress, a dyslexic filmmaker and whoever picks it
up next. One document written for the middle of that range is too much
for one end and too little for the other, and the end it fails is always
the end that most needed help.

WRITTEN TO BE HEARD. `help_page.plain()` strips the markup and hands the
words to a voice, so these are written as SPEECH first: short sentences,
one idea each, no bullet lists read aloud as "dash, dash, dash", and no
sentence whose meaning depends on seeing where it sits on the page.

WHAT EACH LEVEL IS FOR
    child   a five-year-old, or anyone who wants to know what it DOES
            and nothing else. Sixty seconds, no nouns from computing.
    school  a curious eleven-year-old. What each tab is for, plainly.
    adult   someone with work to do and no interest in machinery. The
            level most people actually want.
    tech    a first-year IT student. What is really happening: where
            things run, what is stored, where the limits are.

THE FACTS ARE THE SAME AT EVERY LEVEL. A simpler telling may leave things
out; it must never say anything the more technical one contradicts. That
is the rule that makes four documents honest rather than four opinions.
"""

LEVELS = ("child", "school", "adult", "tech")

LEVEL_NAMES = {
    "hr": {"child": "za dijete", "school": "za školarca",
           "adult": "jednostavno", "tech": "tehnički"},
    "en": {"child": "for a child", "school": "for a schoolchild",
           "adult": "plain", "tech": "technical"},
}


# ---------------------------------------------------------------------
# ENGLISH
# ---------------------------------------------------------------------

EN = {}

EN["child"] = """
<h2>What this does</h2>
<p>You talk, and the words appear on the screen.</p>
<p>That is the whole thing. You press the round button that says rec, you
say something, you press stop. A moment later your words are written
down.</p>
<p>It can do the other way round too. You give it words, and it reads
them out loud in a real voice. It shows you which word it is saying while
it says it.</p>
<p>It knows Croatian and English. It does not mind which one you use.</p>
<p>If something goes wrong, nothing is broken. Press the button again.</p>
"""

EN["school"] = """
<h2>What is TTT-LLL?</h2>
<p>TTT means Talk To Type. You speak and it writes.</p>
<p>LLL means Look, Listen, Learn. It reads out loud while you follow
along on the screen.</p>

<h2>The six rooms</h2>
<p>Along the top there are six round buttons. Each one is a room.</p>
<p>T is for talking. Press rec, say what you want, press stop. The words
arrive in the box underneath. You can also press open and give it a sound
file or a video you already have, and it will do the same thing.</p>
<p>R is for listening. Put any text in the box and press play. It reads
it aloud and lights up each word as it says it, so your eyes and your
ears go together.</p>
<p>TR is for translating. Put in text, choose a language, and get it
back. It can read the translation out loud too.</p>
<p>VR is for playing with voices. There are twenty-four actors in there.
You can tell them to sound calm, or angry, or afraid.</p>
<p>The grey circle with the star is for how things look. Bigger letters,
different colours.</p>
<p>H is this page.</p>

<h2>One thing to remember</h2>
<p>The words in the box stay while the page is open. If you want to keep
them, copy them out and send them to yourself.</p>
"""

EN["adult"] = """
<h2>What it is for</h2>
<p>Two things. It turns speech into text, and it turns text into speech.
Everything else is a detail of those two.</p>

<h2>Getting words in</h2>
<p>Open the T tab. Press rec and talk. Press stop. The words appear
below, usually within a few seconds.</p>
<p>You can also press open and choose a file you already have. It takes
audio and it takes video — if you give it a video it uses the sound and
ignores the picture. There is no need to convert anything first.</p>
<p>Choose HR, ENG or AUTO before you record. AUTO works, but naming the
language is more accurate.</p>
<p>Single replaces what is in the box each time. Multi adds to the end,
so you can work in sittings.</p>

<h2>Getting words out</h2>
<p>The R tab reads text aloud. Paste anything in and press play. It
highlights the word being spoken and scrolls itself, so you can follow a
long piece without touching the screen.</p>
<p>There are four voices. Two Croatian, two English. Changing voice
starts the reading again from the top, so you can compare them on the
same words.</p>

<h2>Translating</h2>
<p>TR takes text in one language and gives it back in another. Six
languages. The translation can be read aloud as well.</p>

<h2>Rehearsing a line</h2>
<p>VR is for hearing a line performed. Twenty-four voices, each with an
accent and an age. Press a name and it says its own name so you can hear
it.</p>
<p>You can mark up the text with directions. Press a word like calm and
it writes a small tag into your line. The voice reads that way from that
point until the next tag.</p>

<h2>Your notes</h2>
<p>Under the T tab there are notes. These are yours and they stay in this
browser on this device. You can speak into a note as well as type in it.</p>

<h2>What is kept and what is not</h2>
<p>The text in the boxes and your choices are kept in this browser, so
switching to another app and coming back does not lose your work.</p>
<p>The audio is not kept in the browser — it is too big. If you want a
recording, use save on the player and it gives you one file of the whole
reading.</p>
<p>Nothing is sent to Google Drive unless you have that switched on.</p>
"""

EN["tech"] = """
<h2>What it is</h2>
<p>A Streamlit application. Python runs on a server; the browser holds
the interface. Every button press sends a message to the server, the
whole script runs again from the top, and the page is redrawn. That one
fact explains most of the behaviour below.</p>

<h2>Speech to text</h2>
<p>The recorder is a custom component — a small web page inside an iframe
that uses MediaRecorder. It sends the audio to Python as base64 in a
message.</p>
<p>The file, whatever it is, goes through ffmpeg first. Content is
sniffed before the file name is trusted, because phones routinely hand
over a file called recording dot wav that is really an m4a. Video is
accepted and the audio track is taken out of it.</p>
<p>ffmpeg produces a mono FLAC at sixteen kilohertz, levelled with
loudnorm to minus sixteen LUFS. That is what Whisper wants. Quiet or
uneven audio makes Whisper drop short words rather than guess at them,
which is worse than an obvious error because the transcript still reads
fluently.</p>
<p>Anything longer than the provider will take is split into chunks and
reassembled. Failed chunks are retried on a schedule that backs off and
adds jitter, because several chunks failing at once would otherwise all
retry at the same instant and deliver the same burst that caused the
refusal.</p>

<h2>Text to speech</h2>
<p>Readings are built in blocks, not all at once. The first block is one
sentence, so sound starts almost immediately; every block after it is
four. While one block plays, the next two are built. For any length of
text the wait before the first word is about the same.</p>
<p>In the rehearsal tab a block can never span two directions, because
one request to the voice provider carries one description.</p>

<h2>Keys and failures</h2>
<p>API keys are held in a ring. When a key fails, the failure is
classified: dead, resting, or our own fault. A dead key is buried and the
next one is tried. A resting key is parked for as long as the provider
asked, not for a number we chose. Our own fault stops the whole ring,
because no other key can fix a malformed request.</p>
<p>Two things a status code alone cannot tell you. A four zero three
carrying error code one zero one zero is Cloudflare refusing the client,
not the provider refusing the key, and it hits every key at once. And an
account with no credit left may answer four hundred rather than four zero
two. Both are read out of the response body.</p>

<h2>State and storage</h2>
<p>Session state lives in the server's memory and dies when the websocket
drops, which is what happens when a phone suspends the tab. So the text
boxes and the choices are mirrored into the browser's localStorage and
restored on the way back.</p>
<p>Audio is deliberately not mirrored. localStorage is about five
megabytes for the whole origin and base64 adds a third on top; a few
minutes of speech would fill it, and filling it raises an error that
would take the notes down with it.</p>
<p>The rendered audio cache is capped at twenty megabytes per person,
evicting the oldest already-heard block. The whole application has one
gigabyte of memory, shared by everyone using it at the same time.</p>

<h2>Limits worth knowing</h2>
<p>A widget key belongs to Streamlit, not to you. If a rerun happens
before a widget renders, its key is garbage-collected and the value is
gone — which is why the text boxes keep their contents somewhere else.</p>
<p>An iframe inherits none of the page's styles or variables, and a user
gesture in one iframe does not authorise audio playback in another.</p>
"""


# ---------------------------------------------------------------------
# CROATIAN
# ---------------------------------------------------------------------

HR = {}

HR["child"] = """
<h2>Što ovo radi</h2>
<p>Ti govoriš, a riječi se pojave na ekranu.</p>
<p>To je sve. Pritisneš okrugli gumb na kojem piše rec, kažeš nešto, pa
pritisneš stop. Za koji trenutak tvoje su riječi zapisane.</p>
<p>Može i obrnuto. Ti daš riječi, a ono ih pročita naglas pravim glasom.
Dok govori, pokazuje ti koju riječ upravo izgovara.</p>
<p>Zna hrvatski i engleski. Svejedno mu je koji koristiš.</p>
<p>Ako nešto pođe po zlu, ništa nije pokvareno. Pritisni gumb ponovno.</p>
"""

HR["school"] = """
<h2>Što je TTT-LLL?</h2>
<p>TTT znači Talk To Type. Ti govoriš, a ono piše.</p>
<p>LLL znači Look, Listen, Learn. Čita naglas dok ti pratiš na ekranu.</p>

<h2>Šest soba</h2>
<p>Gore se nalazi šest okruglih gumba. Svaki je jedna soba.</p>
<p>T je za govor. Pritisneš rec, kažeš što želiš, pritisneš stop. Riječi
stignu u okvir ispod. Možeš i pritisnuti open i dati mu zvučnu datoteku
ili video koji već imaš, i napravit će isto.</p>
<p>R je za slušanje. Staviš bilo kakav tekst u okvir i pritisneš play.
Čita ga naglas i pali svaku riječ dok je izgovara, pa oči i uši idu
zajedno.</p>
<p>TR je za prevođenje. Staviš tekst, odabereš jezik, i dobiješ ga
natrag. Može i prijevod pročitati naglas.</p>
<p>VR je za igru s glasovima. Unutra je dvadeset i četiri glumca. Možeš
im reći da zvuče mirno, ili ljutito, ili uplašeno.</p>
<p>Sivi krug sa zvjezdicom je za izgled. Veća slova, druge boje.</p>
<p>H je ova stranica.</p>

<h2>Jedno zapamti</h2>
<p>Riječi u okviru ostaju dok je stranica otvorena. Ako ih želiš
sačuvati, kopiraj ih van i pošalji sebi.</p>
"""

HR["adult"] = """
<h2>Čemu služi</h2>
<p>Dvjema stvarima. Pretvara govor u tekst i pretvara tekst u govor. Sve
ostalo je detalj tih dviju stvari.</p>

<h2>Kako unijeti riječi</h2>
<p>Otvori karticu T. Pritisni rec i govori. Pritisni stop. Riječi se
pojave ispod, obično za nekoliko sekundi.</p>
<p>Možeš i pritisnuti open i odabrati datoteku koju već imaš. Prima zvuk
i prima video — ako mu daš video, uzet će zvuk i zanemariti sliku. Ništa
ne moraš prije pretvarati.</p>
<p>Prije snimanja odaberi HR, ENG ili AUTO. AUTO radi, ali kad jezik
imenuješ, točnije je.</p>
<p>Single svaki put zamijeni ono što je u okviru. Multi dodaje na kraj,
pa možeš raditi u nekoliko navrata.</p>

<h2>Kako izvući riječi</h2>
<p>Kartica R čita tekst naglas. Zalijepi bilo što i pritisni play.
Označava riječ koju izgovara i sama se pomiče, pa možeš pratiti dugi
tekst bez diranja ekrana.</p>
<p>Ima četiri glasa. Dva hrvatska, dva engleska. Promjena glasa kreće
čitanje ispočetka, da ih možeš usporediti na istim riječima.</p>

<h2>Prevođenje</h2>
<p>TR uzima tekst na jednom jeziku i vraća ga na drugom. Šest jezika.
Prijevod se također može pročitati naglas.</p>

<h2>Proba replike</h2>
<p>VR je za slušanje odigrane replike. Dvadeset i četiri glasa, svaki sa
svojim naglaskom i godinama. Pritisni ime i glas će reći svoje ime da ga
čuješ.</p>
<p>Tekst možeš označiti uputama. Pritisni riječ poput mirno i u tvoju se
repliku upiše mala oznaka. Glas od tog mjesta čita tako, sve do sljedeće
oznake.</p>

<h2>Tvoje bilješke</h2>
<p>Ispod kartice T su bilješke. One su tvoje i ostaju u ovom pregledniku
na ovom uređaju. U bilješku možeš i govoriti, ne samo tipkati.</p>

<h2>Što se čuva, a što ne</h2>
<p>Tekst u okvirima i tvoji odabiri čuvaju se u ovom pregledniku, pa
prelazak u drugu aplikaciju i povratak ne gubi tvoj rad.</p>
<p>Zvuk se u pregledniku ne čuva — prevelik je. Ako želiš snimku,
pritisni save na playeru i dobit ćeš jednu datoteku cijelog čitanja.</p>
<p>Na Google Drive ne ide ništa osim ako to nisi uključio.</p>
"""

HR["tech"] = """
<h2>Što je ovo</h2>
<p>Streamlit aplikacija. Python se izvodi na poslužitelju, a preglednik
drži sučelje. Svaki pritisak gumba šalje poruku poslužitelju, cijela se
skripta izvede ponovno od početka, i stranica se iscrta iznova. Ta jedna
činjenica objašnjava većinu ponašanja koje slijedi.</p>

<h2>Govor u tekst</h2>
<p>Snimač je vlastita komponenta — mala web stranica unutar iframea koja
koristi MediaRecorder. Zvuk šalje Pythonu kao base64 u poruci.</p>
<p>Datoteka, kakva god bila, prvo prolazi kroz ffmpeg. Sadržaj se
prepoznaje prije nego što se povjeruje imenu datoteke, jer telefoni
redovito predaju datoteku imena recording točka wav koja je zapravo m4a.
Video se prima i iz njega se izvuče zvučni zapis.</p>
<p>ffmpeg proizvodi mono FLAC na šesnaest kiloherca, izjednačen s
loudnorm na minus šesnaest LUFS. To je ono što Whisper voli. Tih ili
neujednačen zvuk tjera Whisper da ispušta kratke riječi umjesto da ih
pogađa, što je gore od očite greške jer transkript i dalje zvuči
tečno.</p>
<p>Sve duže od onoga što pružatelj prima dijeli se na dijelove i ponovno
sastavlja. Neuspjeli dijelovi ponavljaju se po rasporedu koji se
produljuje i dodaje slučajni pomak, jer bi inače nekoliko dijelova koji
padnu zajedno pokušalo ponovno u istom trenutku i isporučilo isti nalet
koji je i izazvao odbijanje.</p>

<h2>Tekst u govor</h2>
<p>Čitanja se grade u blokovima, ne odjednom. Prvi je blok jedna
rečenica, pa zvuk kreće gotovo odmah; svaki sljedeći su četiri. Dok jedan
blok svira, grade se sljedeća dva. Za tekst bilo koje duljine čekanje do
prve riječi približno je isto.</p>
<p>U kartici za probu blok nikada ne može obuhvatiti dvije upute, jer
jedan zahtjev pružatelju glasa nosi jedan opis.</p>

<h2>Ključevi i kvarovi</h2>
<p>API ključevi drže se u prstenu. Kad ključ padne, kvar se razvrstava:
mrtav, na odmoru, ili naša vlastita greška. Mrtav ključ se zakopa i
pokuša sljedeći. Ključ na odmoru parkira se onoliko dugo koliko je
pružatelj tražio, a ne na broj koji smo mi odabrali. Naša greška
zaustavlja cijeli prsten, jer nijedan drugi ključ ne može popraviti
neispravan zahtjev.</p>
<p>Dvije stvari koje sam statusni kod ne može reći. Četiri nula tri s
kodom greške jedan nula jedan nula je Cloudflare koji odbija klijenta, a
ne pružatelj koji odbija ključ, i pogađa sve ključeve odjednom. A račun
bez kredita može odgovoriti četiristo umjesto četiri nula dva. Oboje se
čita iz tijela odgovora.</p>

<h2>Stanje i pohrana</h2>
<p>Stanje sesije živi u memoriji poslužitelja i umire kad padne
websocket, a to se događa kad telefon uspava karticu. Zato se okviri s
tekstom i odabiri zrcale u localStorage preglednika i vraćaju pri
povratku.</p>
<p>Zvuk se namjerno ne zrcali. localStorage ima oko pet megabajta za
cijelo podrijetlo, a base64 dodaje još trećinu; nekoliko minuta govora
napunilo bi ga, a punjenje diže grešku koja bi povukla i bilješke sa
sobom.</p>
<p>Predmemorija izrađenog zvuka ograničena je na dvadeset megabajta po
osobi i izbacuje najstariji već odslušani blok. Cijela aplikacija ima
jedan gigabajt memorije, dijeljen sa svima koji je koriste istovremeno.</p>

<h2>Ograničenja koja vrijedi znati</h2>
<p>Ključ widgeta pripada Streamlitu, ne tebi. Ako se ponovno izvođenje
dogodi prije nego što se widget iscrta, njegov se ključ pobriše i
vrijednost je nestala — zato okviri s tekstom svoj sadržaj drže
drugdje.</p>
<p>Iframe ne nasljeđuje nijedan stil ni varijablu sa stranice, a korisnik
kretnjom u jednom iframeu ne odobrava reprodukciju zvuka u drugom.</p>
"""


def body(lang: str = "hr", level: str = "adult") -> str:
    """One document. Falls back rather than raising on an unknown name."""
    table = HR if str(lang).lower().startswith("hr") else EN
    return table.get(level) or table["adult"]


def level_name(lang: str, level: str) -> str:
    names = LEVEL_NAMES.get(
        "hr" if str(lang).lower().startswith("hr") else "en", LEVEL_NAMES["en"])
    return names.get(level, level)
