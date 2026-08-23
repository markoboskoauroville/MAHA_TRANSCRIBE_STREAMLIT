# STEP: the notice has room
STATUS: done, pushed as v144. No deploy needed.

WHAT HAPPENED
- Baba: "it is again too close to the buttons, it looks unprofessional
  and amateurish."
- TWO FAULTS, and only one was the spacing.
  1. The gap below the notice was ~5px. This app's default gap is
     tight, which is right BETWEEN things that belong together and
     wrong between things that do not. The notice and the tab row are
     strangers; the space between them has to say so. 26px now,
     measured. The card's own padding grew with it — text touching its
     own edge looks like a mistake even when the outside spacing is
     right.
  2. THE SENTENCE WRAPPED MID-SENTENCE: "Worth / changing." That made
     the widest thing on the screen the one saying the least, and it is
     most of why it read as amateurish. It is one line now: "This
     password was chosen for you."

CONFIRMED WORKING, from Baba's screenshot
- His note "This is the new note." survived a reload and a fresh login.
  v140 and v143 are doing what they claim.

NUMBERS
- must change 15 — green
- browser-measured: sentence 17px tall (one line), gap 26px
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- One check asserted the old wording. Rewritten to assert the MEANING
  rather than the exact words, so a better sentence does not fail it —
  the previous version would have.

STILL OPEN
- The reset-password test, oldest outstanding.
- test_reader 8, red since v101.
- The owner's tab bar wraps at 360px.
- THE KEYS IN THE SHEET — its own session.
