# -*- coding: utf-8 -*-
"""Help text shown under the gear icon, in both languages.

Written for people who are not programmers: what the app is for, what each
button does, in plain words.
"""

HELP = {
    "hr": """
**Što znači ime TTT-LLL?**

To su dvije kratice, po jedna za svaku polovicu aplikacije.

**TTT** je *Talk To Type*, na engleskom "govori da bi se ispisalo". To je prva
polovica: ti govoriš, a aplikacija tvoje riječi ispisuje kao tekst.

**LLL** je *Look, Listen, Learn*, na engleskom "gledaj, slušaj, uči". To je
druga polovica: aplikacija čita tekst naglas, ti ga u isto vrijeme vidiš na
ekranu i čuješ. Gledaš i slušaš istu rečenicu, pa je lakše pratiti.

Zajedno: govor pretvaraš u tekst, i tekst pretvaraš u govor.

---

**Što je ovo?**

Aplikacija radi dvije stvari. Pretvara tvoj govor u tekst, i čita tekst naglas
ljudskim glasom. Ima dva taba na vrhu.

---

**Tab Transkripcija — govori, a ona piše**

1. Odaberi jezik kojim ćeš govoriti, hrvatski ili engleski.
2. Dodirni mikrofon i govori normalno. Kad završiš, dodirni ponovno da zaustaviš.
3. Pričekaj koju sekundu. Tvoje riječi pojave se ispisane u okviru ispod.
4. Tekst možeš dodirnuti i ispraviti rukom ako želiš.

**Ispravi** — ako je neka riječ krivo prepoznata, pritisni ovo. Aplikacija
posluša tvoj isti snimak još jednom, ovaj put sporijim i točnijim postupkom,
i ispiše bolju verziju. Ne moraš ponovno govoriti.

**Pročitaj ovo** — šalje ispisani tekst na tab Čitanje i odmah ga počne čitati
naglas, sam odabere glas koji odgovara jeziku.

---

**Tab Čitanje — zalijepi tekst, a ona čita**

1. Odaberi glas. Prva grupa su hrvatski glasovi, druga engleski.
2. Zalijepi tekst u veliki okvir. Može biti e-mail, poruka, bilješka, bilo što.
3. Pritisni **Čitaj**.

Dok čita, rečenica koja se upravo govori označena je zlatnom bojom u tekstu.
Ispod toga je poseban okvir koji pokazuje samo tu jednu rečenicu, veliko i
čisto, kao titl na filmu. Ako ti je teško pratiti sitna slova, gledaj u taj okvir.

**Zaustavi** — prekida čitanje.

---

**Korisni savjeti**

- Napravi ikonu aplikacije na ekranu telefona i uključi Zapamti me, pa više
  nikad ne moraš upisivati lozinku. Upute su na ekranu za lozinku.
- Postavke ispod zupčanika pamte se za tebe na ovom telefonu. Drugi korisnik
  s drugom lozinkom ima svoje postavke.
- Za tipkanje e-maila: govori na tabu Transkripcija, kopiraj ispisani tekst,
  zalijepi u e-mail.
- Za čitanje e-maila: kopiraj tekst e-maila, zalijepi na tab Čitanje, pritisni Čitaj.

---

**Tab Prevedi — prevodi između pet jezika**

Odaberi jezik teksta koji imaš (hrvatski, engleski, talijanski, njemački ili
francuski), zalijepi tekst u prvi okvir. Odaberi na koji jezik ga želiš
prevesti, pritisni **Prevedi**. Strelica između dva reda jezika brzo zamijeni
smjer prijevoda.

Ispod prijevoda je gumb **Čitaj** koji prevedeni tekst pročita naglas, uvijek
pravim glasom za taj jezik.
""",

    "en": """
**What does the name TTT-LLL mean?**

They are two short names, one for each half of the app.

**TTT** stands for *Talk To Type*. That is the first half: you talk, and the
app types your words out as text.

**LLL** stands for *Look, Listen, Learn*. That is the second half: the app
reads text aloud while you see it on screen at the same time. You look at the
sentence and hear the same sentence, which makes it easier to follow.

Together: speech becomes text, and text becomes speech.

---

**What is this?**

The app does two things. It turns your speech into text, and it reads text
aloud in a human voice. There are two tabs at the top.

---

**Transcribe tab — you speak, it writes**

1. Choose the language you will speak, Croatian or English.
2. Tap the microphone and speak normally. Tap again when you are done.
3. Wait a few seconds. Your words appear written in the box below.
4. You can tap the text and fix it by hand if you like.

**Correct** — if a word came out wrong, press this. The app listens to your
same recording once more, this time with a slower and more accurate method,
and writes a better version. You do not need to speak again.

**Read this** — sends the written text to the Talk tab and starts reading it
aloud straight away, picking the voice that matches the language by itself.

---

**Talk tab — you paste text, it reads**

1. Choose a voice. The first group is Croatian voices, the second English.
2. Paste your text into the big box. An email, a message, a note, anything.
3. Press **Read**.

While it reads, the sentence being spoken is marked in gold in the text.
Below that is a separate box showing only that one sentence, large and clean,
like a subtitle in a film. If small print is hard to follow, watch that box.

**Stop** — interrupts the reading.

---

**Useful tips**

- Put an app icon on your phone screen and turn on Remember me, then you
  never have to type the password again. Instructions are on the password screen.
- The settings under the gear are remembered for you on this phone. Another
  person with a different password has their own settings.
- To write an email: speak on the Transcribe tab, copy the written text,
  paste it into your email.
- To read an email: copy the email text, paste it into the Talk tab, press Read.

---

**Translate tab — translates between five languages**

Choose the language of the text you have (Croatian, English, Italian,
German, or French), paste the text into the first box. Choose which
language to translate it into, press **Translate**. The arrow between the
two language rows quickly swaps the direction.

Below the translation is a **Read** button that reads the translated text
aloud, always in the right voice for that language.
""",
}

# Shown on the password screen, before anyone is logged in. Five languages,
# because a friend who doesn't read Croatian still needs to find the
# shortcut instructions. Translated once via the app's own translate engine
# (openai/gpt-oss-120b on Groq) and checked, then baked in as plain text —
# the login screen must never depend on a live API call to render.
LOGIN_GUIDE = {
    "hr": """
**Savjet: napravi ikonu na ekranu telefona**

Tako ti aplikacija stoji uz ostale aplikacije i otvara se jednim dodirom,
bez upisivanja adrese.

**Chrome:** dodirni tri točkice gore desno, pa *Dodaj na početni zaslon*
(ponekad piše *Instaliraj aplikaciju*), pa potvrdi s *Dodaj*.

**Firefox:** dodirni tri točkice, pa *Instaliraj* ili *Dodaj na početni zaslon*,
pa potvrdi.

Uključi kvačicu **Zapamti me** iznad i aplikacija te više neće pitati lozinku
na ovom telefonu.
""",

    "en": """
**Tip: put an icon on your phone screen**

That way the app sits with your other apps and opens with one tap, without
typing an address.

**Chrome:** tap the three dots at the top right, then *Add to Home screen*
(sometimes it says *Install app*), then confirm with *Add*.

**Firefox:** tap the three dots, then *Install* or *Add to Home screen*,
then confirm.

Tick **Remember me** above and the app will stop asking for the password on
this phone.
""",

    "it": """
**Consiglio: crea un'icona sulla schermata del telefono**

In questo modo l'applicazione si posiziona accanto alle altre app e si apre
con un solo tocco, senza dover inserire l'indirizzo.

**Chrome:** tocca i tre puntini in alto a destra, poi *Aggiungi alla
schermata principale* (a volte dice *Installa l'applicazione*), poi
conferma con *Aggiungi*.

**Firefox:** tocca i tre puntini, poi *Installa* o *Aggiungi alla schermata
principale*, poi conferma.

Attiva la casella **Ricordami** sopra e l'applicazione non ti chiederà più
la password su questo telefono.
""",

    "de": """
**Tipp: Erstelle ein Symbol auf dem Telefonbildschirm**

So steht die App neben den anderen Apps und lässt sich mit einem Fingertipp
öffnen, ohne die Adresse einzugeben.

**Chrome:** tippe auf die drei Punkte oben rechts, dann *Zum Startbildschirm
hinzufügen* (manchmal steht *App installieren*), und bestätige mit
*Hinzufügen*.

**Firefox:** tippe auf die drei Punkte, dann *Installieren* oder *Zum
Startbildschirm hinzufügen*, und bestätige.

Aktiviere das Häkchen **Angemeldet bleiben** oben, und die App wird dich auf
diesem Telefon nicht mehr nach dem Passwort fragen.
""",

    "fr": """
**Conseil : créez une icône sur l'écran du téléphone**

Ainsi, l'application se place parmi les autres applications et s'ouvre d'un
seul toucher, sans saisir d'adresse.

**Chrome :** touchez les trois points en haut à droite, puis *Ajouter à
l'écran d'accueil* (parfois il est indiqué *Installer l'application*), puis
confirmez avec *Ajouter*.

**Firefox :** touchez les trois points, puis *Installer* ou *Ajouter à
l'écran d'accueil*, puis confirmez.

Cochez la case **Se souvenir de moi** ci-dessus et l'application ne vous
demandera plus le mot de passe sur ce téléphone.
""",
}

# Login-screen labels that must match whichever LOGIN_GUIDE language is
# showing, so the guide's instructions point at words that actually appear
# on screen.
LOGIN_LABELS = {
    "hr": {"password": "Lozinka", "remember": "Zapamti me", "wrong": "Pogrešna lozinka."},
    "en": {"password": "Password", "remember": "Remember me", "wrong": "Wrong password."},
    "it": {"password": "Password", "remember": "Ricordami", "wrong": "Password errata."},
    "de": {"password": "Passwort", "remember": "Angemeldet bleiben", "wrong": "Falsches Passwort."},
    "fr": {"password": "Mot de passe", "remember": "Se souvenir de moi", "wrong": "Mot de passe incorrect."},
}

# Shown once, at the very top of the login screen, above everything else —
# a warm first impression plus the name explained, before the practical
# shortcut guide. Translated via the same model as LOGIN_GUIDE, then
# proofread the same way (caught 'Bienvenue à' -> 'Bienvenue sur', a French
# preposition mismatch, and a couple of German comma/redundancy fixes).
WELCOME = {
    "hr": """### Dobro došao u TTT-LLL

TTT znači Talk To Type, "govori da bi se ispisalo". LLL znači Look, Listen, Learn, "gledaj, slušaj, uči". Prva polovica pretvara tvoj govor u tekst, druga čita tekst naglas dok ga u isto vrijeme gledaš i slušaš.""",

    "en": """### Welcome to TTT-LLL

TTT stands for Talk To Type. LLL stands for Look, Listen, Learn. The first half turns your speech into text, the second reads text aloud while you see and hear it at the same time.""",

    "it": """### Benvenuti in TTT-LLL

TTT sta per Talk To Type, cioè «parla per far scrivere il testo». LLL sta per Look, Listen, Learn, cioè «guarda, ascolta, impara». La prima metà converte il tuo discorso in testo; la seconda legge il testo ad alta voce, mentre lo guardi e ascolti la lettura.""",

    "de": """### Willkommen bei TTT-LLL

TTT bedeutet Talk To Type – „sprich, damit es geschrieben wird". LLL bedeutet Look, Listen, Learn – „schau, hör zu, lerne". Die erste Hälfte wandelt deine Sprache in Text um, der zweite Teil liest den Text laut vor, während du ihn siehst und hörst.""",

    "fr": """### Bienvenue sur TTT-LLL

TTT signifie Talk To Type, « parler pour que cela soit écrit ». LLL signifie Look, Listen, Learn, « regarde, écoute, apprends ». La première moitié transforme ta parole en texte, la seconde lit le texte à haute voix, tout en le regardant et en l'écoutant.""",
}


# The label on the fold-out triangle. Deliberately a question rather than
# a noun: someone unsure whether they are in the right place is answered
# by "What is this?" far better than by "More" or "Info". Screen readers
# announce it as written, so it must read as a whole sentence.
MORE_LABEL = {
    "hr": "Što je ovo?",
    "en": "What is this?",
    "it": "Che cos'è?",
    "de": "Was ist das?",
    "fr": "Qu'est-ce que c'est ?",
}
