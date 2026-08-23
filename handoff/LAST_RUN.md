# STEP: the login had no button, and froze
STATUS: done, pushed as v113

WHAT HAPPENED
- A visible "Log in" button, gold, under the password. Enter still
  works — but Enter is invisible, and an invisible control is one
  somebody has to be told about. This screen is the first thing Baba's
  mother meets.
- THE FREEZE, and it was not the login failing. Ticking Remember me
  queues a localStorage write, and that write is a COMPONENT: it needs a
  frontend round trip that does not come on that run. The page sat grey
  with the spinner turning until a manual refresh forced another run.
  The login had already SUCCEEDED; only the paint was missing. It now
  calls st.rerun() straight after a successful login rather than waiting
  on the storage cycle.
- The label is in LOGIN_LABELS in all five languages, like everything
  else on that screen.

NUMBERS
- login 11 (was 7) · calm login 32 — green
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- My first attempt at adding the label inserted it INSIDE the {who}
  placeholder of the continue string. Caught by the syntax error, file
  reverted, redone by inserting at each language block's opening brace.

STILL UNSURE — AND THIS ONE MATTERS
- THE REPAINT FIX HAS NO TEST, and I could not write one. Its mutation
  SURVIVED: removing st.rerun() left all 11 checks green, because
  AppTest has no browser and never hits the component round trip that
  caused the freeze. The button half is covered and its mutation fails.
  The freeze half is reasoned, not proven.
- So Baba's own login is the only real proof. If it still greys out with
  Remember me ticked, the cause is elsewhere and I was wrong.

FOR BABA
1. Log in on the live app with Remember me ticked. Tell me whether it
   still needs a refresh.
2. Then the test person: amber gear, Add a person, name `test`, leave
   the password EMPTY. Watch for the password shown once and the
   copyable message.
3. Then log in as `test` in a private window and meet the change screen.
