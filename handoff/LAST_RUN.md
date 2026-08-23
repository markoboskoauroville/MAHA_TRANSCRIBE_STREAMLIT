# STEP: the tier decides what you get, and one edge not two
STATUS: done, pushed as v124

WHAT HAPPENED
- ONE EDGE. v122 gave the deck's container a border, and the deck draws
  its own frame inside its iframe — a line around a line. Baba: "when I
  said colour I meant the edge which is already there, not to add an
  additional one." The fill stays; the border is gone. Same for the note.
- GRAMMAR AND RESHAPE ARE STUDIO ONLY. Baba: "we remove this from the
  free user, they do not pay." It is not only price: both send the text
  to a language model, which on the free tier means his own Groq keys
  paying for somebody else's rewriting. Transcription is the service;
  rewriting is the extra.
- CUSTOM, studio only. Press it and a box opens: say what you want done,
  and it is done to the text already in the box. It goes through the
  SAME transform path as grammar and reshape — one implementation,
  three doors — with no preset named, because an explicit instruction
  wins and naming one only makes the app fetch wording it discards.
- The owner is not exempt. He is on whatever tier he chose, so he sees
  exactly what that tier gives.

NUMBERS
- tier 12 (new) · box 16 — green
- mutated BOTH ways: everyone gets them (3 red), nobody does (3 red)
- deckbox border measured at 0px in a browser
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- My first test set _assigned_engine and proved nothing: EN.current
  derives the engine from the ROUTES every render, deliberately, so a
  hand-patched crosspoint reads "mixed" instead of claiming an engine
  that is not running. The test sets the routes now.

STILL TO DO FROM THIS ROUND — NOT STARTED, AND EACH NEEDS A DECISION
1. The deck's "sent 198 KB · 2.5s" line moving to the TOP of the
   recorder, small, against the edge. That is inside the component.
2. AUTO/HR/ENG and single/multi onto ONE line. They were split into two
   in v118 because five pills do not fit below 412px without clipping,
   and §27 says no word may be cut. Fitting them means smaller type —
   worth doing, but it is a deliberate trade and I would rather he say
   so than have me shrink his controls unasked.
3. The command row as text links rather than a bordered table.
4. Usage: one row per person instead of a tab each, and the k_* key
   tabs deleted. That needs a MAIN SCRIPT change and his deploy, and I
   asked him a question about it that is still unanswered — totals
   only, or totals plus one shared events tab keeping the detail.

FOR BABA
- The note's red rec still has never been seen to work. It is the
  oldest open thing.
