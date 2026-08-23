# STEP: notes survive
STATUS: done, pushed as v140. No deploy needed.

WHAT HAPPENED
- Baba: "notes are not surviving between sessions — I create a note, I
  log in as Emina again, and the note is gone." They lived in
  session_state alone, which dies with the tab. Everything a person
  typed was kept exactly as long as they kept the page open.
- They are written to the browser now, under a key that names the
  person, and read back on the next visit. Verified end to end in a
  real browser: note made, page reloaded, logged in again, note there.

WHAT THIS IS NOT, so nobody finds out the hard way
- The notes stay on THAT DEVICE. They will not follow Emina to her
  phone, and clearing the browser loses them. Drive is the durable
  answer — it is designed (§60: every note already carries the rec_id
  of its audio) but needs the MAIN script changed and deployed, and
  Baba's notes were disappearing today.

THREE FAULTS, AND ONLY A BROWSER FOUND TWO OF THEM
1. My first version compared the notebook against what was in memory at
   the top of the module — which would have missed every change made by
   a CALLBACK, because callbacks run BEFORE the script body. It compares
   against the last SAVED copy now.
2. The write was queued at the END of a run, and the bridge sends what
   was queued BEFORE it. So the write waited for a run that might never
   come: measured, localStorage held `[]` while a note sat on screen.
   It asks for one more run now, and cannot loop because the
   fingerprint is set first.
3. Restore gave up on the first render after a reload, when LS_DATA is
   empty because the component has not reported yet — marking the
   notebook restored and never reading it back. It waits now.
- FAULTS 2 AND 3 SURVIVED EVERY BEHAVIOURAL CHECK. Both live on the far
  side of a component, and a component returns its default under
  AppTest. They have source checks, labelled as such: false comfort
  from eleven green checks that cannot see the bug is worse than an
  honest note saying which kind of check this is.

NUMBERS
- notes persist 14 (new) · notes 43 · notes UI 22 · box 16 — green
- all four mutations caught
- browser-verified: SURVIVED THE RELOAD
- pyflakes clean
