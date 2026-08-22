# STEP: clean up the login screen
STATUS: done, pushed as v107

WHAT HAPPENED
- Everything on that screen now comes from LOGIN_LABELS. The Continue
  button came from STRINGS through t(), which follows ui_lang, while the
  field labels follow the login screen's own pills — two sources on one
  screen, which is why Baba saw "Korisnik / Lozinka" above "Continue as
  admin". Mixed reads as broken, not as bilingual.
- The login screen now defaults to ENGLISH. The five pills still work
  and the choice sticks for the session.
- Removed: the "Remembered on this device — press Enter, or the button"
  caption, and the "Not me — sign in as someone else" button. A login
  screen that has to explain itself has already failed. "Not me" is not
  lost — type a different name over the filled-in one.
- The "What is this?" fold-out has no frame now.
- FOUND WHILE LOOKING: three paragraphs about installing an icon on a
  phone were rendering OPEN, below the fold-out, on the screen a person
  meets before typing anything — outside the expander that exists to
  fold them away. The comment above the code had claimed for months that
  they were inside it. Moved in. The screen went from ~22 lines to 7.

NUMBERS
- calm login 32 · login 7 · notes 39 · box 16 — all green
- pyflakes clean across app.py and ttt/
- login screen: 7 lines of text, no page errors, no sideways scroll

WHAT BROKE, AND WHAT I UNDID
- My first CSS targeted [data-testid="stExpander"] and changed nothing
  visible: the border is drawn on the inner <details>. Measured it in
  the browser rather than guessing again, then targeted both.
- Three checks in test_calm_login clicked the button I had just removed.
  Rewritten to test the CAPABILITY — somebody else types their own name
  and their own password gets THEM in, not the remembered person —
  which is the thing that actually matters.

STILL UNSURE
- Whether English-by-default is right for Baba's mother, who does not
  read English. She presses HR once and it sticks for that session, but
  it does not persist across a new browser. If that turns out to matter,
  the fix is to remember the login language in localStorage.

FOR BABA
- The old queue is unchanged and all three are still yours: deploy the
  AUTH script, add AUTH_ADMIN_TOKEN to the Streamlit Cloud secrets, and
  create accounts for Emina and Marinko — the users tab has only `admin`
  in it, so they are still getting in through APP_PASSWORDS.
