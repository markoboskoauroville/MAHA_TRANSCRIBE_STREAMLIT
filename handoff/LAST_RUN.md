# STEP: the overlap, solved at the root — and the cursor
STATUS: done, pushed as v138. No deploy needed.

THE OVERLAP, AND WHY IT KEPT COMING BACK
- Baba asked four times about text overlapping at the top, and I fixed
  it four times. Four different elements — the tabs, the
  interface-language label, the engine test result, the password notice
  — and ONE cause I never looked for.
- v122 set the header's height to zero, to close an empty band. That
  does not remove it: Streamlit's header is POSITION: FIXED, so zeroing
  its height leaves the toolbar where it is and lets the whole page
  scroll UNDERNEATH it. Whatever is at the top gets printed through.
- The header stays now, transparent and click-through, and the page has
  padding-top: 64px — MEASURED, because its box is 60px in a browser
  and my first guess of 2.4rem still let content under it.
- Verified: header bottom 60, first element top 65. CLEAR.
- THE LESSON, and it is in HOW_WE_WORK.md now: four rounds went into
  moving the thing being overlapped instead of asking what was
  overlapping it. When a layout fault returns after a fix, the fix was
  a patch. Measure the geometry.

AND A TRAP INSIDE THE FIX
- ttt/theme.py is one f-string, so a brace in a COMMENT is read as
  code. Writing the offending CSS inside braces in that very note
  crashed the app with NameError: name 'height' is not defined. Also
  written down.

THE CURSOR
- A take now lands WHERE THE CURSOR WAS. Baba: "it ignores my cursor
  and just puts a line at the end." That made a note a log rather than
  a document — you could add to the bottom and nowhere else.
- Python cannot know where a cursor is; only the frame can. It reads
  selectionStart when rec is PRESSED, before the press takes focus off
  the textarea — some browsers then report 0, which would put every
  take at the very top.
- A stale caret is CLAMPED to the length: slicing past the end silently
  drops the tail. No caret means the end, which is the honest answer
  for a take from the deck, since the deck has no cursor.

NUMBERS
- notes 43 (was 39) · components 18 executed — green
- mutation: ignoring the caret fails 2
- pyflakes clean

FOR BABA
- The note's rec, with a cursor placed mid-text — it should land there.
- And the reset-password test, still owed.
