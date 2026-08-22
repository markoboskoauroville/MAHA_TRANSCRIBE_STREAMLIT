# handoff/ — how Claude Code and chat Claude talk without Baba in the middle

Baba, 22.8.2026: *"tell him every terminal output of every step is pushed
to the repository in some temp folder, and I will just type here done,
and you will pick up what the result is."*

He was copying terminal output into chat by hand, every step, all day.
He has carpal syndrome. This removes that entirely.

## The loop

    Claude Code   finishes a step
                  writes handoff/LAST_RUN.md
                  commits and pushes
    Baba          types "done" in chat
    chat Claude   pulls, reads LAST_RUN.md, writes the next prompt
    Baba          pastes it into Claude Code

One word from him instead of a screenful.

## The rules

**One file, overwritten.** `handoff/LAST_RUN.md`, replaced each time —
not appended, not a new file per step. Chat Claude reads the newest and
only the newest; a folder of numbered logs is a folder to search.

**Push it, or it does not exist.** Chat Claude reads GitHub, not the
Mac. An unpushed file is invisible.

**NO SECRETS, EVER.** This file is committed. Before writing it, check
for tokens, passwords, pepper values, `AUTH_*` values, `SHEETS_TOKEN`,
`DRIVE_SECRET`, API keys. Write the NAME and never the value. If a
command's output would contain one, do not paste that output — say what
it showed in words.

**Say what it cost.** Not only what passed: what broke, what had to be
undone, what is still unsure. Baba is not watching the steps any more,
so this file is the only place the truth lives.

**Keep it short.** Twenty lines is plenty. It is a report, not a
transcript — the transcript is what he was trying to stop sending.

## The shape

```markdown
# STEP: what was asked
STATUS: done | partly | blocked

WHAT HAPPENED
- three or four lines, plainly

NUMBERS
- pytest tests/  ->  16 passed, 2 skipped
- pyflakes       ->  clean

WHAT BROKE, AND WHAT I UNDID
- or: nothing

STILL UNSURE
- or: nothing

FOR BABA
- anything only he can do: a deploy, a secret, a decision
```

## Pulling on both sides

Chat Claude pushes too. So Claude Code **pulls before it starts a step**
and before it pushes, or the two will collide on `HANDOVER.md` and
`app.py`. If a pull ever conflicts, stop and say so — do not resolve a
conflict in `app.py` unsupervised.
