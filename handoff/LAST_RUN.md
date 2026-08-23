# STEP: tiers, a required password, and a test result you can read
STATUS: done, pushed as v123

WHAT HAPPENED
- FREE and STUDIO, not "normal". Baba: "it is a free tier or studio
  tier — not normal and studio." Each engine carries a `tier` word now.
  The stored id stays `normal`, because renaming it means another script
  change, another deploy and another migration to say one word
  differently on screen.
- The status line shows the TIER, not the parts: `transcribe · free ·
  admin` instead of `Edge / Groq`. "Edge / Groq" answers a question
  nobody asks at the foot of a page; "free" answers the one they do.
  The parts are still named in the owner's panel, where he is choosing
  between them and needs to know what he buys.
- The note field is gone from Add a person — just username and
  password. The COLUMN stays in the sheet; it was the form that had a
  field nobody fills.
- THE PASSWORD IS NO LONGER OPTIONAL. Empty used to mean "generate one",
  which reads as optional on a form and is not what he wants: he hands
  people a password he chose and can say out loud. Empty is refused now,
  with the reason on screen — and so is an empty name.
- "check engine" is "test".

THE OVERLAP IN HIS SCREENSHOT
- "all parts answered" printed ACROSS the line beneath it. A caption and
  a text sitting under this panel's tight spacing, with the gap closed
  and no line-height given back. The whole verdict is one code block
  now — a block cannot overlap itself, and it lines up in a column like
  the people table above it.

WHAT BROKE, AND WHAT I UNDID
- test_accounts had been SILENTLY BROKEN SINCE v115, when the login
  became a form: three helpers still used set_value().run(), which
  submits nothing to a form. Nothing noticed for eight versions because
  the suite was not run. It has one submit() helper now, like the other
  two login suites.
- Four checks asserted the removed note field, the old "normal" label,
  or a generated password. All moved to what is now true.

NUMBERS
- admin users 49 · accounts 51 · engines 28 · engine UI 18 · engine
  sheet 28 · users 32 · login 11 · notes UI 22 · owner edge 5
- components 18, executed in node
- pyflakes clean

STILL UNSURE — AND IT IS A WHOLE SESSION, NOT A FIX
- The key management Baba described is a project of its own: upload-only
  entry through a file picker, every key tested on arrival with a
  reason when it fails, per-key usage so he can invoice studio users,
  and delete. He named two of his own apps to copy from — Key Tester
  and Password Keyring — and I have not read either. That should start
  with reading them, not with writing code here.

FOR BABA
- Open a note and press its red rec. The editor came back in v122 and
  that button has still never been seen to work.
