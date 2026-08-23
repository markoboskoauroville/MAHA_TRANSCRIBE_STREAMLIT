# STEP: a file manager that behaves like one
STATUS: done, pushed as v158. No deploy needed.

FOUR THINGS, ALL BABA'S
1. LINKS, NOT PILLS. "When we are doing file management, it's like a
   system tool." A pill is a choice being offered; a link is a thing you
   do to what you have selected. This panel is the one place in the app
   that is about FILES rather than about words, and it should look like
   it.
2. PLAY AND TRANSCRIBE GREY OUT WITH MORE THAN ONE TICKED. Only delete
   works on many. The asymmetry is not arbitrary: playing two files at
   once is not a thing, and transcribing several would make one box of
   text with no way to tell whose words were whose. Deleting many is the
   one act that is genuinely the same act repeated.
   THEY GREY, THEY DO NOT VANISH — links that disappear make the panel
   jump as you tick, and nobody can learn where a control lives if it is
   not there when they look.
3. SELECT ALL, and the same link clears it. One control for a thing and
   its opposite: "select all" beside "select none" is two words for one
   decision.
4. THE PLAYER SITS UNDER ITS OWN FILE. It used to appear at the foot of
   the panel — fine with three recordings, wrong with thirty, because a
   player a long way from the row that summoned it belongs to nothing in
   particular.

THE CACHE THAT MAKES IT USABLE
- The audio is held for the session. This renders on EVERY tick of any
  checkbox, and fetching from Drive each time would make the list
  unusable — a player open at the top would refetch every time somebody
  ticked something at the bottom.

NUMBERS
- box 16 · tier 15 · notes UI 27 — green
- driven against a fake Drive: select all -> 4 picked, play greyed,
  delete live; one picked -> play live, player opens in ITS OWN ROW,
  audio cached under that rec_id
- pyflakes clean

WHAT COST ME TIME, AND IT WAS THE HARNESS
- My fake Drive kept dying: it lived in /tmp, which is cleaned between
  tool calls here. Two rounds of "the panel is empty" were the server
  being gone, not the app. Fakes live in /home/claude/fakes now.
