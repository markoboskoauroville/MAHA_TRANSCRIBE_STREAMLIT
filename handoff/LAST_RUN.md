# STEP: copy and clear under every box
STATUS: done, pushed as v132. No deploy needed.

WHAT HAPPENED
- ONE RULE, EVERY MODULE. Baba: "under all tabs we have text box, copy
  clear under. As an action link, not an action button. Copy is more
  important than clear, that is the rule."
- `box_links()` is the one helper: T, R, and BOTH halves of TR use it.
  Before this each had its own arrangement — a bordered command row
  here, a single link there, copy in one and not the other. Three
  shapes for one idea is three things to keep in step, and they had
  already drifted.
- It renders nothing when the box is empty. Nothing to copy, nothing to
  clear, and a dead link is a question with no good answer.
- T's command row now holds only what is particular to T: `new`, plus
  the studio tools. `add to notes` rides on the links line rather than
  starting another.

THE COPY BUTTON HAD TO BE TAUGHT TO LOOK LIKE A LINK
- It is a COMPONENT — nothing else can reach the clipboard — so it
  cannot be a Streamlit button styled like the ones beside it.
  cp_html() gained a `link=True` mode. Its colour is written as a hex
  rather than var(--dim), because the component renders inside an
  IFRAME and cannot see the page's CSS variables — a var() there
  resolves to nothing.

NUMBERS
- box 16 · tier 13 · notes UI 22 · source 19 — green
- browser-verified in T: copy · clear · add to notes, one line, right
  aligned, glued to the box
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- `tx_clear` moved into the helper and took a new key, which three test
  files still named. Updated. One of them then failed for a good
  reason: it checked an EMPTY box, where the links deliberately do not
  render. It seeds the box now.

STILL OPEN
- The note's red rec, never seen to work.
- test_reader 8, red since v101.
- The owner's tab bar wraps at 360px with `log` orphaned underneath.
- THE KEYS IN THE SHEET — its own session.
