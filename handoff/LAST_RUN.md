# STEP: the sync path, on TTT mini's rules
STATUS: done, pushed as v167. No deploy needed.
**The key/credit panel Baba asked for is NOT built yet — see below.**

WHAT HAPPENED
- Baba: "TTT mini as a role model for how to deal with sync and async
  with AssemblyAI. Until 2 minutes you can go sync, for English only,
  Croatian is not. These buttons — auto, eng, hr — control it."
- I CLONED THE REPO AND READ IT rather than guessing, and its reasoning
  is better than what I would have arrived at. The rules come across
  intact, and so do the reasons.

THE FACT UNDERNEATH, which I did not know and would not have assumed
- AssemblyAI's sync endpoint does not accept `hr` AT ALL. Its language
  list is en, es, de, fr, it, pt, tr, nl, sv, no, da, fi, hi, vi, ar,
  he, ja, ur, zh.
- So Croatian sent up that path comes back as FLUENT CROATIAN THAT IS
  THE WRONG WORDS. Not garbled, not empty, not obviously broken —
  plausible sentences nobody would question without knowing what was
  said. A wrong answer that looks right is worse than an error, because
  there is nothing to notice.

THE RULES, PORTED
- AN ALLOW-LIST, NOT A DENY-LIST: only `en`, because only English's
  sync output has actually been READ by somebody. A language nobody has
  checked is excluded by default rather than included by accident.
- AUTO COLLAPSES TO ASYNC. A language the app has not been told is
  English is one that might be Croatian, and the safe answer to "might
  be" is the slow path.
- 118 seconds, not 120. The service rejects at 120 and our figure is
  CALCULATED while theirs is measured, so two seconds are left as room
  for the two to disagree.
- 0.5s floor (the endpoint rejects under 80ms), 40 MB ceiling, and NOT
  KNOWING THE LENGTH COUNTS AS TOO LONG.
- EVERY CONDITION IS A REASON TO SAY NO. TTT mini's words and they are
  right: "Fast is a preference; arriving is not." Nobody is told which
  path was taken, because the only visible difference is how long the
  words take.

WHAT COST ME TEN MINUTES, AND IT WAS NOT THE CODE
- Two checks failed after a mutation was reverted, and the file on disk
  was demonstrably correct. It was a STALE __pycache__ — Python was
  running the mutated bytecode. I nearly "fixed" correct code.
  Mutation testing must clear the cache between runs.

STILL TO BUILD, and Baba asked for all of it
- The paste/test/delete panel for his own AssemblyAI key, the free/paid
  toggle, hours-left from the $50 starting credit, cost per hour, and
  the link to pay. The settings keys are already reserved
  (aai_key, aai_on, aai_rate, aai_credit, aai_spent_s) and the storage
  question is answered: the SETTINGS SHEET, because
  _save_server_settings writes to a disk Streamlit Cloud wipes on every
  redeploy.
- ON THE PRICE: sources disagree — $0.15/hr base async, $0.21, $0.37
  with add-ons. It must be EDITABLE and must link to AssemblyAI's own
  page rather than hardcoding a number that will be wrong.

NUMBERS
- aai sync 11 (new) · engines 28 · box 16 — green
- mutation: allowing Croatian on sync fails 2
- pyflakes clean
