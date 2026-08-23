# STEP: you choose the password, and copy is visible
STATUS: done, pushed as v129. **DEPLOY THE ACCOUNTS SCRIPT.**

WHAT HAPPENED
- RESET NOW TAKES A CHOSEN PASSWORD. Baba: "I don't want this password
  to be automatically generated — I am assigning password as I like."
  userCreate_ has taken one since v112 and reset never did, so half the
  app let him choose and half did not. Empty still generates, which is
  the right answer when he has nothing in mind; it is simply no longer
  the only answer.
- THE COPY BUTTON IS ALWAYS VISIBLE. Streamlit fades it in on hover,
  which on a phone means it appears only after a press that might have
  done something else. A control nobody can see has to be explained —
  and the line explaining it is now gone, because it does not need to be.
- Two lines removed: "one tap on the corner copies it" explained that
  button, and "Write this down NOW" told him to do the thing he had
  just done. Both were true when the app generated passwords and nobody
  knew them. They stopped being true and stayed on screen.
- The dismiss stays. It is the only thing that takes a password off the
  screen, and a password that lingers through a session is a password in
  the next screenshot.

NUMBERS
- admin users 50 · auth script 66 — green
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- MY EDIT TO ttt/accounts.py SILENTLY DID NOT APPLY, twice. The script
  reported success and the file was unchanged — the same class of fault
  §74 earned a rule about, and my assert did not catch it because it
  passed against a stale read. Done with a direct edit instead, and the
  signature printed to prove it.
- A duplicate string key: `adm_newpw` already existed as the "write this
  down" warning, so my new one collided. Renamed to `adm_setpw`.
- Check 14 asserted the removed warning; it now asserts the dismiss,
  which is what has to survive.

FOR BABA
1. DEPLOY THE ACCOUNTS SCRIPT (New version). Until then reset ignores
   the password you type and generates one — and the message will show
   the generated one, which is the one that works.
2. Then: press reset password on somebody, type a password you choose,
   confirm, and check the message shows YOURS.
