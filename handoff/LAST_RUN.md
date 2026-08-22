# STEP: make the owner's screen look like a control panel
STATUS: done, pushed as v110

WHAT HAPPENED
- Square buttons (3px), rows sitting on each other, one thin rule as the
  only separator, and labels BESIDE their boxes instead of above them.
- The owner's gear is now FIRST in the tab row, before the one everybody
  has: T R TR ⚙amber ⚙grey L H. For a family member nothing moves —
  they never see the amber one.
- Trimmed the band above the tabs: the panel's top padding was 14px on
  top of Streamlit's own, which put empty space between the browser bar
  and the first thing anybody looks at. Bottom padding kept.
- The whole owner module is dense, not only the People half — it was
  only People at first, which left round pills above square ones on one
  screen, worse than either.

NUMBERS
- admin users 39 · owner edge 5 — green
- button radius 3px measured in the browser
- panel height 475px, from 605px on a taller viewport
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- TWO REAL BUGS from v109, both visible in Baba's screenshot and neither
  caught by any test: `adm_who` and `adm_engine` were rendering as raw
  string KEYS, because the script that was supposed to add those strings
  had a guard that skipped it and reported nothing. t() falls back to
  the key, so the screen showed its own internals. Added.
- I first scoped the dense stylesheet with a sibling selector hanging
  off statusbox_admin. Fragile and one refactor from styling nothing.
  Removed the scope entirely: the sheet is emitted only while the
  owner's tab renders, and Streamlit rebuilds the page each run, so it
  cannot leak by construction.
- Check 13 anchored its ordering test to the "Add a person" heading,
  which this change replaced with a plain rule. Re-anchored to the list
  itself — a check tied to a label breaks when the wording changes.

STILL UNSURE
- I still cannot SEE the People table: no AUTH_URL here, so it draws the
  not-connected sentence. Everything above it is verified in the
  browser; the table's density is tested but not seen.

FOR BABA
- Unchanged: ADMIN_USER = "admin", deploy the AUTH script, add
  AUTH_ADMIN_TOKEN, then create Emina and Marinko.
