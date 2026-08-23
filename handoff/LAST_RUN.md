# STEP: remove silences, as a setting
STATUS: done, pushed as v170. No deploy needed.
**Now wired into BOTH recorders. v169 built the module; this connects it.**

WHAT HAPPENED
- Baba: "add option in the settings, remove silences, so user can choose
  and experiment with the feature and build it in."
- A toggle in Settings, OFF by default, obeyed by the deck AND the
  note's own recorder.

WHY A SETTING AND NOT A DEFAULT, which is the right instinct
- The saving is real — 48% measured on a clip shaped like dictation —
  but the cost of being wrong is a clipped first syllable, which costs a
  re-record, which costs more than the silence did.
- Somebody who can turn it off and compare will find that out in a
  minute. Somebody who cannot will just think the app eats words.
- Off by default so that nobody's dictation changes shape because a new
  version arrived.

IT SAYS WHAT IT DID
- "silence removed: 9s less audio sent (48% smaller)", under the box,
  once. This is the ONLY setting in the app whose effect is invisible in
  the result — the words come back identical and only the bill changes —
  so a person experimenting with it has nothing to look at unless it
  says so.

BOTH RECORDERS, and the count is checked
- A test asserts `maybe_trim(to_flac16k(raw))` appears exactly TWICE.
  The setting being true of the deck and not the note is the same split
  that hid the note storage gap for fifty versions.

WHAT I FIXED IN MY OWN TEST
- Check 11 split the source on "if not" and indexed [1], so deleting the
  guard raised IndexError instead of reporting a red check. A test that
  CRASHES tells you something is wrong without telling you what, which
  is most of its value gone. It fails cleanly now — mutation caught, 2
  red.

NUMBERS
- trim 17 (was 11) · box 16 · notes UI 27 · source 19 — green
- mutations: the note losing the trim fails 1; the setting being ignored
  fails 2
- pyflakes clean
