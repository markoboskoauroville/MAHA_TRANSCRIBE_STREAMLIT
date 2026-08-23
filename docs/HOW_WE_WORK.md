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

## Who each screen is for

Two audiences, and they want opposite things.

**The family — T, R, TR, the grey gear, the login.** Baba's mother, his
father, his brother. They do not read easily. Hard rule 6 governs
completely: 44px targets, generous type, nothing clipped, nothing that
breaks at 250%. *"Anything that breaks at a large text size is a bug of
the same seriousness as losing someone's recording."*

**The owner — the amber gear, and only the amber gear.** One person who
knows what every word means, on his own phone, doing something
deliberate. Baba: *"It is not for users who are old. It is for a young
administrator who is very smart."*

There, density wins. A table read at a glance beats six buttons per
person; a radio beats three pills. Six actions for four people was 24
targets and most of a screen, to say what one line says better.

**The exception is scoped and must not leak.** It applies behind
`is_admin()` and nowhere else. If a family member can reach a screen,
rule 6 governs it entirely — no exceptions, no judgement calls.

---

## Deploy prompts: TWO boxes, always

Baba asked for this in his own words: *"for this kind of prompts, give
Marko two code boxes, one after the other."*

**Box one is the command.** Everything he needs to type, in one line,
with the real path — including the `git pull`, because a file he has not
pulled is a file that is not current, and that has already cost a wasted
deploy:

```bash
cd ~/Developer/MAHA_TRANSCRIBE_STREAMLIT && git pull && open auth_script/Code.gs
```

**Box two is the URL, alone.** Nothing else in it, so one tap selects
the whole thing:

```
https://script.google.com/home/projects/<id>/edit
```

Then the words: select all, paste over, save, `Manage deployments` → ✏️
→ **New version**.

**Why two and not one.** A URL buried in a sentence has to be selected
by hand on a phone, and a command with a placeholder path in it has to
be edited before it will run. Both were happening. Two boxes, each
complete, each copied with one tap.

The two script ids, so neither has to be hunted for:

| project | what it is | id |
|---|---|---|
| main | bound to the sheet: usage, Drive, settings | `12NtdbhOSAJNX7UoV8AUrVnZwc5OS62RXeqvJzvu3AMpjRFjPDAET-dNx` |
| auth | accounts: logins, passwords, people | `1iim9Qzakqq_j2cmFbu3KQFIBXwG_MVwqGs7yR7rETNvmq3AWNppPMHAY` |

**And say WHICH ONE.** They look identical in the editor, and pasting
the accounts script over the main one would take the family's app down
and lose his three filled-in secrets in the same move.

---

## Why things kept overlapping at the top — SOLVED, do not undo it

Baba, four separate times: *"the text is overlapping."* The tabs, the
interface-language label, the engine test result, the password notice.
Four different elements, four symptom fixes, one cause.

**The cause.** v122 set the height of Streamlit's header to zero, to
close an empty band above the tabs. That does not remove the header:
Streamlit's header is `position: fixed`, so zeroing its height leaves
the toolbar exactly where it is and lets the whole page scroll
UNDERNEATH it. Whatever happens to be at the top gets printed through.

**The fix.** The header stays, transparent and click-through, and the
page is given `padding-top: 64px` — MEASURED, because its box is 60px
in a real browser and 2.4rem was not enough. Anything that wants to sit
higher must shrink that padding, never the header.

**The lesson, which is the point of writing this down.** Four rounds
went into moving the thing being overlapped instead of asking what was
overlapping it. When a layout fault comes back after a fix, the fix was
a patch: stop adjusting the victim and measure the geometry.

`ttt/theme.py` is an f-string, so **a brace in a COMMENT is read as
code**. Writing "height: 0" inside braces in that very note crashed the
app with `NameError: name 'height' is not defined`. Say such things in
words there.

---

## Insert where the cursor is, not at the end

Baba: *"it does not insert when I put my cursor — it ignores my cursor
and just puts a line at the end."*

**Python cannot know where a cursor is.** Only the component can, and
only if it sends it. `note_frontend` reads `selectionStart` at the
moment rec is pressed — before the press has taken focus off the
textarea, which on some browsers reports 0 and would put every take at
the very top.

A caret arriving from a previous render can be past the end of text
that has since been shortened, so it is **clamped**; slicing past the
end silently drops the tail. And no caret means the end, which is the
honest answer for a take from the deck, since the deck has no cursor.

---

## The one rule that is never bent

Never `New deployment`.
Always `Deploy` → `Manage deployments` → ✏️ → Version: `New version`.

Baba asked for this stated once, plainly, and obeyed every time —
*"not sometimes I skip, not and then I do it."*

**Why it matters more than it looks.** `New deployment` creates a second
web app at a different URL. The first one keeps running, and
`SHEETS_URL` in Streamlit still points at it. So the old code goes on
answering, the new code sits there unreached, and nothing appears to
change — which sends you hunting a bug in code that was correct all
along.

It applies to every Apps Script project in every one of Baba's repos,
not only this one. The single exception is the very first deployment of
a brand-new script, when there is nothing yet to update.

**How to check.** Open `Manage deployments` and count the entries. One
means it was done right. Two means a second web app exists and Streamlit
is still talking to the old one.

**A note on how to write warnings for Baba.** He asked for this rule to
stand out and it was first written with a red ⛔ and a drawn box. He read
the symbol as *"something is broken"* and it frightened him. Use
`code style` for the thing being named, plain sentences for the reason,
and no alarm symbols. A warning that reads like a fault report makes him
look for damage that is not there.

---

## Report through the repo, not through Baba

He was copying terminal output into chat by hand, every step, all day,
with carpal syndrome. Stop making him do that.

**After every step: write `handoff/LAST_RUN.md`, commit, push.** One
file, overwritten each time. He types "done" in chat; the other Claude
pulls and reads it. See `handoff/README.md` for the shape and the rules
— the important one being that the file is COMMITTED, so no secret ever
goes in it, only the name of one.

Pull before starting a step and before pushing, because chat Claude
pushes to the same branch.

---

## Do not stop to ask. Run the whole step.

Baba, 22.8.2026: *"Because I am a beginner and I do not understand these
comments, I am saying yes to all that comes. Run every step, do not
stop, otherwise this takes too much time."*

He is right about the cost. A permission prompt he cannot evaluate is
not a safety check — it is a delay he answers `yes` to by reflex, and
answering `yes` by reflex is worse than not being asked, because it
teaches him that prompts do not mean anything.

**So: run the step through.** Do not stop between edits, tests and
commits inside one agreed piece of work. Report at the END, with what
was done and what it cost.

### What makes that safe, and what does not

It is safe because **everything is committed and pushed**. Any file this
damages comes back with `git checkout -- <file>`. That is real
protection, and it is the only reason the rule above is acceptable.

It does **not** cover two files, and they are in the Deny list for
exactly that reason:

- `apps_script/Code.gs` — holds his filled-in secrets, and is
  `assume-unchanged`, so **git cannot restore it.** Never edit it.
- `.streamlit/secrets.toml` — never edit, never read aloud.

Anything OUTSIDE the repo — installing packages, changing his shell,
touching his Desktop, rotating a key — still stops and asks. Those
change his machine, not the work, and git will not undo them.

### Still stop for these

- a **decision that changes what gets built** — ask, with the options
  laid out and a recommendation
- anything that **deletes data that is not in git**: a Drive folder, a
  sheet row, a deployment
- anything **outside the repo**
- when you are about to do something he told you not to

### And keep telling him what it cost

Running without stopping means he is not watching each step, so the
report at the end carries more weight, not less. Say what broke, what
you had to undo, and what you are unsure of. **A mistake volunteered is
the whole basis of him being able to say `yes` at all.**

---

## Starting a session — the exact command

```bash
cd ~/Developer/MAHA_TRANSCRIBE_STREAMLIT && claude
```

It must be run from **inside** the repo. `claude` on its own in the home
folder opens the wrong project and reads nothing useful.

First prompt of any session, always the same shape:

```
Pull the latest from GitHub and tell me what arrived. Then read
HANDOVER.md §72 and tell me in five sentences where we are and what is
next. Change nothing else.
```

`§72` is whichever section is currently "WHERE THIS SESSION ENDS — START
HERE". When a session ends, that number moves and the old one is marked
superseded, because a stale starting point is worse than none.

---

## HOW TO FEED BABA — the teaspoon method

This is not a style preference. It is what makes the difference between
a session that moves and one that stalls, and it was arrived at by
getting it wrong first.

**ONE SPOON. Then stop.**
Give exactly one action. Say what to do, and nothing about the step
after it. Then wait for "done". A list of five steps is worse than
useless — he reads the first, loses the thread, and has to ask again.
He will say *"give me the next spoon"* when he is ready.

**ONE CHAIN, ONE PASTE, ONE ENTER.**
Every command block is joined with `;` or `&&` so the whole thing runs
from a single paste. Never loose lines he must run one at a time. He has
carpal syndrome; every extra copy-paste costs him something real. This
was his own request, in his own words: *"we work with chains."*

**CHAINS LOOK BEFORE THEY ACT.**
Print what was found, then act on it. A wrong assumption should produce
a message, not a half-finished operation. `ls` before `cp`. `git status`
before `git pull`.

**REAL PATHS, NEVER PLACEHOLDERS.**
`~/path/to/repo` cost twenty minutes and a confusing error. If the path
is unknown, ask — do not invent one and hope.

**SAY WHICH WINDOW.**
Terminal, Claude Code, or the browser. They are three different places
and the same command does not work in all of them. `clasp login` in
particular MUST be in a plain Terminal window, because it needs a
listener that survives the command.

**IN CLAUDE CODE: grey text is a guess, not your words.**
Claude Code autocompletes ahead of the cursor. Tab accepts that guess as
part of the message. **Read it before pressing Tab.** If it is not
wanted, press Enter alone. For a pasted prompt there is no suggestion, so
it is just Enter.

**CHECK THE LINE BEFORE HE SENDS IT.**
He often types a next step ahead of time — `do step 9`, `AUTH_ADMIN_USER
is set`. Sometimes it is not true yet. Say *"don't press Enter yet"* and
why. Twice this saved a wasted ten minutes.

**BEFORE HE PASTES A LOG, REMIND HIM TO GLANCE AT IT.**
Passwords and tokens travel by reflex. It happened three times in one
session. Once, plainly, then respect his decision — it is his app.

**HE IS ON A PHONE HALF THE TIME.**
Then he cannot run anything. Do the work in the repo, push it, and give
him the pull for when he is back at the Mac.

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

## Learning the code, tip by tip

Baba: *"give me some new insights so I learn the code effortlessly, tip
by tip."* These are the ideas that actually explain this codebase.

**Ask it WHY, not just what.** After any change: *"why did you do it
that way, and what would break if you did the obvious thing instead?"*
The answer is where the learning is. Most of this project's hard-won
rules came from an obvious thing that broke.

**The best question in the repo is "what did you verify?"**
If it says something works, ask how it knows. "It passes" and "I ran it
and watched it fail when I broke it" are different claims.

**Read one commit message a day.** They are written to be read later and
each one carries a whole small lesson. `git log --oneline | head -20`,
pick one, `git show <hash>`.

**Three ideas that unlock most of this app:**

*A widget key belongs to Streamlit, not to you.* Three sessions were
lost to text landing in the archive and not the box, because the
transcript was stored under the text area's own key and the browser kept
overwriting it (§63). The fix — keep your value somewhere Streamlit does
not manage, and let the widget be only a view of it — is the single most
useful thing in this codebase.

*A component is an iframe, and an iframe is a different world.* It
cannot see the page around it, and the page cannot see inside. That is
why the deck, the reader and the note editor are components: they need
their own DOM. It is also why AppTest cannot test them and only a real
browser can (§68, §70).

*A convenience must never be a dependency.* The sheet, Drive, the
archive — every one of them can be unreachable and the app must still
work. The login screen is the sharpest case: a failure there locks out
everybody, including him, so `APP_PASSWORDS` exists as a door that
always opens.

**When something passes on the first try, suspect the test.** Roughly
half of all failures in this project were in the test, not the code, and
§71 documents a test that could not fail and had been green for weeks
because of it.

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
