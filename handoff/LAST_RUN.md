# STEP: a recommendation, not a wall
STATUS: done, pushed as v136. No deploy needed.

WHAT HAPPENED
- The forced password change is a NOTICE now: one line, `change it`
  which opens the grey gear where the fields already are, and `later`.
  The whole app works behind it.
- Baba: "just recommend to change the password, but it should work
  immediately without stopping user from using the app... we are not
  torturing the user or forcing it to do anything."

WHAT IT COSTS, SAID PLAINLY
- The password Baba handed somebody stays valid until they choose to
  change it. He said it aloud, sent it in a message, and it is in his
  own screenshot — so it is a password several places know.
- THE TEST THAT ARGUED THE OTHER WAY IS KEPT, not deleted. It said: "a
  banner can be dismissed; a screen cannot, and the password that went
  through WhatsApp is still the one that opens the door until this is
  done." That was not wrong. It is still the right call: standing
  between his mother and the one thing she opened the app to do, over a
  password she did not choose, is the larger harm.
- The flag is NOT cleared by dismissing. `later` means later, not
  never — the nudge returns next session, and only an actual change
  settles it.

A REAL GAP FOUND WHILE MOVING IT
- The Settings panel — which is now the only place a password is
  changed — did NOT clear the flag on success. Somebody would have
  changed their password and been asked again on their next login. It
  clears both session keys now, matching what the script does in the
  sheet on the same call.

NUMBERS
- must change 15 · accounts 51 — green
- browser-verified: notice above a working app, both buttons present,
  no overflow
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- Held on one line, the sentence was CUT at the panel edge and both
  buttons were squeezed out of existence. §27 forbids the first and the
  second is worse. The sentence has its own line and wraps; a sentence
  is the one thing on a screen that may take two lines without apology.
- Four checks asserted the wall. Rewritten to the new intent, with the
  old argument kept in the file rather than removed.
