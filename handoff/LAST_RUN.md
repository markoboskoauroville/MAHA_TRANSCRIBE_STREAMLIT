# STEP: the AssemblyAI key panel, at last
STATUS: done, pushed as v171. No deploy needed.

WHAT HAPPENED, AND IT IS ON ME
- Baba: "I still don't see a keyring for AssemblyAI in the settings.
  There is no testing, there is no paste box, there is nothing. Where
  are you?"
- HE IS RIGHT. He asked for the panel in v167. I built the sync rules,
  then the rates, then two other features, saying each time that the
  panel was "still to come". Three versions of groundwork for something
  invisible without the thing itself. The arithmetic was the easy half
  and I kept choosing it.

WHAT IS THERE NOW, in Settings
- A paste box, and nothing else until a key exists — offering a toggle
  for a provider nobody can reach is offering a switch that does nothing.
- The key MASKED once saved. A key on screen is a key in the next
  screenshot, and this whole project has been screenshots.
- A toggle: the free engine, or AssemblyAI.
- "about 226 hours left · $47.48 of credit · 12.0 hours used, $2.52",
  the two rates, and a link to AssemblyAI's pricing page.
- test key, delete key (two presses), and a way to CORRECT THE CREDIT —
  a number that can only go down is wrong the first time somebody tops
  up, and the app cannot know that they did.

SAID TO BE AN ESTIMATE, IN WORDS
- This counts only what THIS APP transcribed. Somebody using their key
  elsewhere sees a figure that is too generous and there is no way for
  the app to know. One word stops the number being a promise.

AND THE DOUBLED LABEL FROM HIS SCREENSHOT
- "AFTER TRANSCRIBING" printed twice: my heading above, and the radio's
  own label rendering despite label_visibility="collapsed", which hides
  a label from SIGHT and renders it anyway. THE SAME FAULT AS v156's
  recordings heading, in the same file, two hundred lines apart. Fixed.

NUMBERS
- aai sync 28 (was 17) · trim 17 · box 16 — green
- mutations: printing the key instead of masking fails 1, removing the
  estimate warning fails 1
- arithmetic checked by hand: 50 − 12×0.21 = 47.48, ÷0.21 = 226.1
- pyflakes clean

STILL NOT WIRED
- The toggle SAVES but nothing reads `aai_on` yet to route work to
  AssemblyAI. That is the next step, and it is where the sync/async
  rules from v167 finally get used.
