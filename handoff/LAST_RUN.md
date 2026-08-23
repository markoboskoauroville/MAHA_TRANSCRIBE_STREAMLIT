# STEP: a new recording shows up
STATUS: done, pushed as v165. No deploy needed.

WHAT HAPPENED
- Baba: "I'm just recording audio and it doesn't automatically come on
  the recording after every record stop."
- `_recs` is fetched ONCE per session, because the panel redraws on
  every tick of a checkbox and a network round trip each time would make
  the list unusable. That was right — and it was only half a rule.
- THE CACHE WAS DROPPED AFTER A DELETE AND NEVER AFTER A STORE. So the
  newest recording, the one he had just made and would most want to see,
  was the one thing the list could not show. It appeared next session,
  which reads as the app losing it and finding it again.
- Dropped on store now, in BOTH recorders. A note's take is a recording
  like any other; "the list is stale" has to be true of both, or the
  deck refreshes and the note does not — which is exactly the split that
  hid the note storage gap for fifty versions.

WHAT I NEARLY GOT WRONG CHECKING IT
- My verification searched the 600 characters after `finish_keeping` for
  the cache drop and reported FALSE. The edit was there — at the
  nineteenth line, pushed past my window by the comment explaining it.
  I widened the window rather than "fixing" code that was already
  correct. A check that is too narrow reports the same thing as a bug.

NUMBERS
- box 16 · notes UI 27 — green
- confirmed both paths drop the cache after a successful store, and that
  dropping it causes a real refetch
- pyflakes clean
