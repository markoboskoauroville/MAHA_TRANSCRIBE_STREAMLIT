# STEP: notes in Drive, beside the recordings
STATUS: done, pushed as v143. **THE MAIN SCRIPT NEEDS DEPLOYING.**

WHAT HAPPENED
- Baba: "to survive between sessions, notes should be saved in the same
  location where audio files are saved, and a simple text file as a
  backup in Google Drive."
- One `notes.txt` in the person's own Drive folder, beside their
  recordings. Plain text on purpose — a backup nobody can open without
  the app is not a backup.

WHY NOT put_text, WHICH ALREADY WRITES TEXT TO DRIVE
- It REFUSES a rec_id with no row in the index, deliberately: text for
  an unknown recording would be half of a pair that must never exist.
  A notebook is not half of a pair. It belongs to the PERSON, so it
  sits beside their recordings rather than inside one, and needed its
  own endpoint.

TWO STORES, AND WHICH IS WHICH
- THE BROWSER IS THE FAST COPY AND DRIVE IS THE TRUE ONE. The browser
  answers instantly and works with the sheet disconnected; Drive
  follows somebody to another device and survives a cleared browser.
  Neither alone is enough, and Drive alone would put a network round
  trip in front of every note.
- Restore reads Drive ONLY when the browser is empty — never as a
  merge. Two copies edited in two places cannot be merged without
  deciding which edit loses, and guessing there would lose somebody's
  words.
- The Drive write never blocks and never raises. A notebook that cannot
  reach Drive must still save to the browser, and the person must still
  be able to type.

NUMBERS
- notes drive (node, real Code.gs in a fake Drive) 14 — new
- notes persist 18 · notes 43 · drive text 20 — green
- mutations: no Drive write fails 2, duplicates-kept fails 2
- pyflakes clean

WHAT BROKE, AND WHAT I UNDID
- The fake Drive knew only createFile(blob); the real one also takes
  (name, content, mime), which is the shape notesPut_ uses. It would
  have thrown in the harness while working perfectly in Drive — the
  wrong kind of red, and the kind that teaches you to distrust the
  harness. It also had no setContent, so a second save silently did
  nothing and the notebook would have frozen at whatever it held first.
- My duplicate-cleanup check passed whether or not the loop existed,
  because one existing file goes down the setContent path and the loop
  never runs. It creates a real duplicate now, and the mutation fails.

FOR BABA — THE DEPLOY, AND IT IS THE AWKWARD ONE
- This is the MAIN script, which is `assume-unchanged` on his Mac and
  holds his three filled-in secrets. ADMIN.md §1.1 has the routine:
  un-hide, stash, pull, re-fill, re-hide. Until it is deployed, notes
  save to the browser exactly as they did in v140 and Drive is simply
  never reached — nothing breaks, the backup just is not there yet.
