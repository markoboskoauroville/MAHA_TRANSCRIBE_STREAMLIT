# -*- coding: utf-8 -*-
"""Help text shown under the gear icon, in both languages.

Written for people who are not programmers: what the app is for, what each
button does, in plain words.
"""

HELP = {
    "hr": """
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
""",

    "en": """
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
""",
}

# Shown on the password screen, before anyone is logged in.
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
}
