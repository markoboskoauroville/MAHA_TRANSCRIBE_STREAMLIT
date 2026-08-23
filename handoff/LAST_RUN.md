# STEP: one clear, under the box
STATUS: done, pushed as v131. No deploy needed.

WHAT HAPPENED
- R's command row is gone. Baba: "archive and clear goes away — it
  should be only clear, as an action link under the text box."
- `archive` wrote into the OLD archive, which became notes in v98 and
  is displayed nowhere. The button had been writing into a drawer
  nobody opens for thirty-odd versions.
- `clear` is now one quiet link under the box, right-aligned, touching
  it at −1.8px — the same shape as T's "add to notes", so both modules
  put their one afterthought action in the same place.
- It only appears when there is something to clear.

NUMBERS
- reader: only the pre-existing check 8 red, nothing new
- browser-verified: archive absent, clear present, gap −1.8px
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- Removing the button orphaned its handler, and pyflakes caught that
  there were TWO `_keep_text` definitions in the same module. Removed
  the one I orphaned; the other belongs to the reader's own archive
  panel and was left alone rather than tidied blind.

STILL OPEN
- The note's red rec, never seen to work.
- test_reader 8, red since v101.
- The owner's tab bar wraps at 360px, seven tabs onto two lines, with
  `log` orphaned underneath — the same shape he objected to for `multi`.
- Per-provider test buttons; People and the test result as real tables.
- THE KEYS IN THE SHEET — its own session, starting from Key Tester and
  Password Keyring.
