# STEP: compact the admin panel
STATUS: done, pushed as v109

WHAT HAPPENED
- The People panel is one table, one selection, one set of actions.
  Before: six buttons per person — 24 targets for four people, most of a
  phone screen. Now a table showing every person with their engine,
  whether they have a password yet, and their note; a radio to pick one;
  a radio for their engine; then reset / rename / delete.
- The engine is a radio because it is one choice out of three, which is
  what three pills were pretending not to be.
- docs/HOW_WE_WORK.md gained "Who each screen is for": the family's
  screens are governed by rule 6 completely, the amber gear is not, and
  the exception applies behind is_admin() and NOWHERE else.

NUMBERS
- admin users 39 · owner edge 5 · calm login 32 · engine UI 18 — green
- four mutations applied and all four caught: showing only the selected
  person, the strip not naming who it is about, the admin password not
  being sent, the "no pw" marker dropped from the table
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- Nothing in the app. Three checks named per-person button keys that no
  longer exist, and one named a person the fixture never had ("emina" —
  it seeds admin, baba, mama). Rewritten around a pick() helper, which
  is better: selecting the person is a separate act in the test now, the
  same way it is on the screen.
- One long shell chain timed out midway and left the version bump and
  this file unwritten. Redone in smaller pieces. Nothing was lost —
  git status showed exactly what had and had not been done.

STILL UNSURE
- I could not SEE the new panel. This sandbox has no AUTH_URL, so it
  drew the not-connected sentence instead — correct behaviour, useless
  for judging a layout. The tests cover the shape; Baba's eye is the
  check that matters. Tell me if it is still too tall.

FOR BABA
- Unchanged: ADMIN_USER = "admin" in the cloud secrets, deploy the AUTH
  script, add AUTH_ADMIN_TOKEN, and create accounts for Emina and
  Marinko.
