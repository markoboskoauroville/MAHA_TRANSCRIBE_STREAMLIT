# STEP: one way in
STATUS: done, pushed as v116

WHAT HAPPENED
- "Continue as {name}" is gone. Baba: "Login is enough." Two gold
  buttons a centimetre apart doing almost the same thing is a choice
  nobody asked to make, and the name is already filled in above.
- The capability it carried is not lost: submitting with an EMPTY
  password completes a remembered login. Safe ONLY because the screen is
  a form now — it submits when the button is pressed or Enter is struck,
  never while somebody is halfway through filling it.

THE HOLE THE TESTS CAUGHT, IN THE SAME CHANGE
- My first version let ANY empty submit complete the remembered login.
  Typing "emina" over the filled-in "baba" and submitting signed BABA
  in — somebody let into an account under a name they did not type. The
  v114 bug in a new coat, five minutes after I wrote the comment that
  explains v114.
- Fixed: the name box must still hold their name, or be empty. The
  mutation that drops that condition fails 5 checks.

A CHECK THAT ASSERTED THE OPPOSITE
- test_calm_login 12 said submitting empty does NOTHING, with a comment
  arguing a form was too dangerous to try: "the login screen is the one
  place where a mistake locks out everybody". The caution was right; the
  conclusion was wrong. Rewritten with its history kept, because the
  lesson is that "too risky to try" was standing in for "not yet
  measured".

NUMBERS
- calm login 32 · login 11 — green
- one mutation, 5 checks red
- pyflakes clean; one button seen in a browser

WHAT BROKE, AND WHAT I UNDID
- Two checks asserted the removed button. Moved to the behaviour that
  replaced it, which is what should have been checked all along.

STILL UNSURE
- Nothing here.

FOR BABA
- Log in and confirm one press, one button.
- Then v114's note tests: the DECK's rec inside an open note, and the
  note's own red button. If the red one still does nothing, its error is
  on screen now — send me that text.
