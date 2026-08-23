# STEP: the list says when it was read
STATUS: done, pushed as v166. No deploy needed.

WHAT BABA DESCRIBED
- "After user clicks stop, you send one copy to Whisper, one copy to
  Google Drive, link it to your recordings, and then the number is +1."
- That is exactly what the code does, and I CHECKED THE ORDER rather
  than assuming: the store runs at line 5863 and the panel at 6222, so
  the cache dropped by v165 is refetched in the SAME pass. The count
  should already be right.

SO WHY ADD ANYTHING
- Because I have guessed wrong twice today about his Drive, and a cached
  remote list should never be something somebody has to TRUST.
- The fold now says WHEN the list was read — "list read at 20:02:11" —
  and carries a `refresh` link beside it.
- That is the honest answer to "why is my recording not here": one press
  settles it, instead of a conversation about whose fault it is. And if
  the count is ever stale, the timestamp shows it rather than leaving
  somebody to wonder.

WHAT PYFLAKES CAUGHT, IMMEDIATELY
- I copied the button line out of `_rec_actions`, which is drawn twice
  and keys itself with `where`. This panel is drawn ONCE and there is no
  `where` here. Undefined name, caught the moment I ran it — which is
  exactly what it is for, and cheaper than finding it on his phone.

NUMBERS
- box 16 · notes UI 27 — green
- verified: read at 20:02:11, refresh pressed, re-read at 20:02:12
- pyflakes clean
