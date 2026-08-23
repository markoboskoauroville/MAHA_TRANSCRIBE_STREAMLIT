# STEP: the owner is trusted, and the actions are links
STATUS: done, pushed as v127. **DEPLOY THE ACCOUNTS SCRIPT.**

WHAT HAPPENED
- rename user · reset password · delete user — one line, as links, in
  that order. Baba: "these should be links at the top, not buttons...
  first rename, then reset password, and delete user is the last thing."
  The order is an argument about danger as much as habit: rename changes
  a word, reset changes a password, delete ends an account. Least harm
  first, so a hand moving down the row moves toward the thing it should
  hesitate over.
- Full words. "reset" and "delete" alone left "reset what" and "delete
  what" to be inferred beside somebody's name.
- THE ADMIN PASSWORD IS NO LONGER ASKED FOR, in the app or the script.
- And the placeholder stopped saying "password (optional)" — it has been
  required since v123 and told people the opposite for four versions,
  which is worse than saying nothing.

WHY IT FELT BROKEN, WHICH IS NOT WHY HE THINKS
- "He asked me for a password and I did not have a place to enter it."
  The box WAS there — rendering BELOW the confirm buttons. So pressing
  yes sent an empty password, the script refused, and the refusal read
  as a demand with nowhere to answer it. A layout fault wearing the
  clothes of a security one.

WHAT REMOVING IT COSTS — SAID ONCE, AND WRITTEN IN THE SCRIPT
- THE ADMIN TOKEN ALONE NOW DELETES PEOPLE. The second factor existed
  because a token can leak into a screenshot, and Baba's has, once. For
  five family members on a sheet he owns that is a fair trade. What is
  LEFT is the token separation: the login token still cannot reach any
  admin action, and that is now the only thing between a leaked login
  token and the family's accounts. Two checks assert exactly that.
- adminProved_ is left in the script, working and uncalled, with a note
  saying why — for the day the trade stops being fair.

NUMBERS
- admin users 49 · auth script 66 — green
- order and one-line fit measured in a browser
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- Five script checks and seven app checks asserted the protection I had
  just removed. Rewritten to assert the NEW truth rather than deleted,
  so the day it changes back the change is visible.
- The test stub still enforced the password after the real script had
  stopped. A stub stricter than the thing it stands for fails tests
  about a rule that no longer exists.

FOR BABA — TWO THINGS, IN ORDER
1. DEPLOY THE ACCOUNTS SCRIPT (New version). Until then the deployed
   one still demands the password the app no longer sends, so delete,
   rename and reset will all refuse.
2. Then: the note's red rec, still never seen to work.

NOT DONE FROM THIS ROUND
- Per-provider test buttons (test Edge, test Groq, and one each for the
  studio three) instead of one whole-engine test.
- The People list and the test result as real tables.
- THE KEYS IN THE SHEET. Baba now wants Speechify, AssemblyAI and Claude
  keys stored in the Google Sheet, read-only there, managed entirely
  from the app — list, test, delete — copying his Key Tester app. NOTE
  THAT THIS REVERSES his earlier "I will never enter the keys table, we
  need to delete those." It is the right call and it is a session of its
  own; it starts by reading Key Tester and Password Keyring.
