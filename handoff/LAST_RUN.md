# STEP: the login is a form now, and it actually works
STATUS: done, pushed as v115

WHAT HAPPENED
- Baba photographed "Calling st.rerun() within a callback is a no-op."
  That warning IS v113's fix failing. A callback cannot repaint, so the
  rerun I added there never ran — the freeze was never fixed, only
  papered over with a warning.
- The login no longer happens inside a callback. The callback records
  what was typed; the main body performs the attempt. Finishing there
  falls straight through to the app, so there is no repaint to ask for.
- AND A SECOND BUG, found only by typing in a real browser: TYPING AND
  THEN CLICKING "Log in" did nothing. The click blurs the field, but
  Streamlit has not committed the value by the time the button's
  callback runs, so it read an empty box. Enter worked, because Enter
  commits. Every AppTest check passed either way — AppTest has no blur
  and no focus.
- The fix is a FORM. A form commits every widget inside it and THEN runs
  the submit callback; that ordering is the entire reason forms exist.
  The language pills stay outside it, because they must act the moment
  they are pressed.

NUMBERS
- Browser-verified BOTH ways: click -> logged in, no warning; Enter ->
  logged in, no warning. One action each, no refresh.
- login 11 · calm login 32 · notes UI 22 · box 16 · owner edge 5 — green
- mutation: removing the submit callback fails 5 checks
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- A form changes how tests drive the screen: set_value().run() no longer
  submits anything, because a form commits nothing until its button is
  pressed. Both login suites gained a submit() helper. That is the form
  working, not a regression.
- at.form_submit_button does not exist. A form's button is an ordinary
  button whose key is "FormSubmitter:<form>-<label>".

STILL UNSURE
- Nothing on this one. Unlike v113, both paths were driven in a real
  browser and seen to work.

FOR BABA
- Log in and tell me it is one press now, either way.
- Then: open a note, press the DECK's rec, and the words should join the
  note (v114). If the note's own red button still does nothing, the
  error will now be ON SCREEN — send me that text.
