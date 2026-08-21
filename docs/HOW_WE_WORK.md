# How Baba and Claude work — the method

Written 20.8.2026, the day the workflow changed. Applies to **every**
project, not only this one.

---

## The short version

Baba runs **Claude Code** in Terminal on his Mac. The chat Claude does
not touch his machine. It thinks, decides, and hands Baba **prompts to
paste into Claude Code**, which does the actual work on the files.

    chat Claude   →  writes the prompt      (judgement, planning, review)
    Baba          →  pastes it, presses Enter
    Claude Code   →  reads and edits files, runs commands
    Baba          →  pastes the output back to chat Claude
    chat Claude   →  reads it, writes the next prompt

Baba calls this **spoon by spoon**. One step, then stop and wait. Not
five things at once.

---

## The rules, learned the hard way

**ONE SPOON AT A TIME.** Say "Baba, first do this", then stop. Wait for
"done" before the next one. He is often tired and his head is full; a
list of five steps is worse than useless.

**EVERY COMMAND BLOCK IS ONE CHAIN.** Joined with `;` or `&&` so the
whole thing is a single paste and a single Enter. Never loose lines he
must run one by one — he has carpal syndrome and every extra paste
costs him something real.

**REAL PATHS, NEVER PLACEHOLDERS.** `~/path/to/repo` cost twenty minutes.
His repo is at `~/Developer/MAHA_TRANSCRIBE_STREAMLIT`. Ask where a
thing lives rather than inventing a path.

**CHAINS CHECK BEFORE THEY ACT.** Look first, print what was found, then
do the thing. A wrong assumption should print a message, not half-perform
an operation.

**IN CLAUDE CODE: read the grey text before pressing Tab.** Tab accepts
the autocomplete suggestion as part of the message. If the suggestion is
not wanted, press Enter alone.

**TELL HIM WHEN HE IS IN THE WRONG CHAT.** He runs several projects at
once and loses track. If he starts describing another one, say so
immediately: *"Baba, you are in the wrong chat."* He asked for this
explicitly.

---

## Secrets

**Never print a secret into a session.** Claude Code was given this as a
standing rule and honoured it — generating values straight into
`~/Desktop/TTT-BACKUP/AUTH_SECRETS.txt`, reporting only lengths.

**A screenshot is more dangerous than text**, because it cannot be
masked as it is taken. Baba masks values in text well. He photographed
a Script Properties page with the Value column visible and did not think
of it as the same act. Say so once, plainly, and then respect his
decision.

**Ask for secrets as uploads, never as pasted text.** An upload lands on
disk. Pasted text is in the transcript forever and cannot be removed.
Say plainly what can and cannot be deleted; never claim to have shredded
something that is in the conversation.

---

## What Claude Code is good at, and what it is not

**Good:** reading a whole repo, editing many files coherently, running
tests, refusing to route around a permission gate, catching a mistake in
the instruction it was given. It corrected a `git stash drop` to a
`git stash pop` and saved Baba's four config lines.

**Cannot:** anything needing a browser sitting and waiting. `clasp login`
must run in a plain Terminal window, because the OAuth callback needs a
listener that survives the command. Apps Script `PropertiesService`
cannot be written from outside — those go in by hand.

---

## Reviewing its work

Read what it says it did and check the reasoning, not only the result.
It has twice added something nobody asked for and was right to:

- an unknown username costs the same half-second as a real one, so a
  fast "no" cannot be used to read the family list off the login screen
- the Drive folder name is frozen at account creation, so renaming a
  person never orphans their recordings

That is the level to hold it to. If it claims something works, ask how
it verified.
