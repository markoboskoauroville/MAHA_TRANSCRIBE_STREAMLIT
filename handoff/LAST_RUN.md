# STEP: people in a dropdown, and three faults only data revealed
STATUS: done, pushed as v111

WHAT HAPPENED
- The person picker is a dropdown; the engine stays a radio. The
  difference is how many there are: engines are three and will stay
  three, so a radio shows all of them and choosing costs one press.
  People grow, and a radio for a family of eight is eight rows standing
  open forever when the table above already says who exists.
- I finally SAW the panel. Stood up a throwaway accounts script on
  localhost so it had four people in it, then looked. Three faults were
  visible at once that no test had caught and no amount of reading
  would have found.

THE THREE, ALL FROM SEEING IT
- The engine radio WRAPPED onto two lines with a gap, because the labels
  were "Speechify / AssemblyAI / Claude". Short labels beside a person's
  name — free · studio · global — since he already knows what they mean
  by the time he is assigning one. The long names stay where he CHOOSES
  the engine and needs to know what he is buying.
- The name and note boxes started at different x. Same column ratio,
  different positions: st.text renders preformatted text that does not
  wrap, so "note (optional)" stretched its own column and pushed its box
  right. The labels are placeholders inside the boxes now — nothing
  beside them to fall out of line with, and a row shorter each.
- Both measured, not judged: boxes now at x=16 with identical widths.

NUMBERS
- admin users 39 — green, and the dropdown mutation caught (exit 1,
  "'baba' is not in list")
- panel 733px with four people in it
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- Nothing in the app. The fake accounts script was deleted after use.

STILL UNSURE
- The people table is aligned with spaces in a monospace block. It will
  hold as long as names stay under fourteen characters; a longer one
  will push its row's columns out. Fine for a family, wrong for fifty.

FOR BABA
- Unchanged: ADMIN_USER = "admin", deploy the AUTH script, add
  AUTH_ADMIN_TOKEN, then create Emina and Marinko.
