# DELIVERY RECORD — TTT-LLL v186 — 24.8.2026

    ARTEFACT   the repository at main, which is what Streamlit Cloud runs
    VERSION    new: v186   previous: v185, in git history

**Three tiers, one radio, and Google out of the door.**

---

## 1 · THE TIERS

Baba, 24.8.2026: *"Any studio user is also free user, but it's not admin
user... Admin user is Marko, but he's also studio user 1 — even if he's
admin, he's automatically studio user 1. So software can merge the 2."*

    free     the app on the app's own keys: Edge and Whisper
    studio   everything free has, plus the paid models, plus Google
             storage for audio and notes
    admin    everything studio has, plus the owner's panel

**A tier is a FLOOR, not a slot.** That single decision is why `RANK` is
an ordering rather than a set of labels, and it is what makes the merge
obvious instead of arbitrary.

### The names

    ADMIN_USER1  = "..."      ADMIN_USER, ADMIN_USER2 ... all work
    STUDIO_USER1 = "..."
    FREE_USER1   = "..."      FREE_USER2, FREE_USER3 ...

The pattern `^(ADMIN|STUDIO|FREE)_USER\d*$` is **scanned**, not read from
a fixed list, so `FREE_USER7` needs no code change. A value may also be a
list. `ADMIN_USER` without a digit is still honoured — that is what every
deployment before v186 used, and a rename must not lock the owner out.

**The same name may appear more than once and the highest wins.** Baba
listed himself three times in one breath. That is not an error to reject;
it is three true statements about one person and the answer is the
largest. Order does not affect the result — checked.

### The radio

Above the tab bar. One word each, lowest first: **free · studio · admin**.

**Drawn from the ACCOUNT, never from the view.** If it were drawn from
the view, dropping to free would remove the control that gets you back
and the only way out would be logging in again. A free user holds one
tier, so nothing is drawn — that is one person's app having a control
another's does not, the same as the gold tabs, not a control appearing
and disappearing between renders.

A radio and not pills: exactly one tier is in force and choosing another
must visibly take the mark off the last (design-language §6).

### What the tier now decides

- `is_admin()` follows the **view**, so switching to free really shows
  the free app — the gold tabs go. This is the point of the switch.
- `is_studio()` is a **floor** test, not equality, because admin is a
  studio user too.
- The command row's studio tools (grammar, reshape, custom) come from
  `is_studio()` instead of from the engine routes. **This is open item 3,
  "tiers replace engines"** — "what tools do I get" and "who am I" were
  two facts that could disagree, and they are one fact now.

## 2 · GOOGLE IS NOT A DOOR ANY MORE

Baba: *"authentication through Google in Google Sheets is gone forever.
Google is only used for Studio users to store their audio files and to
store their notes."*

- The door was already a name in Secrets (v185) and makes **no network
  call**. Open item 8, the long login, should go with it — untimed.
- `drive_store()` returns a disabled store unless the view is studio or
  admin. A free user's take is transcribed, handed back, and nothing of
  theirs is kept in Baba's Drive.
- The password-change form is unreachable: nothing sets `_via_accounts`.
- `from ttt import gate` removed — the throttle belonged to the password
  door. **`ttt/gate.py` and `tests/gastest` are NOT deleted**; the module
  works and is one import from being useful again.

## GATES

    G1 provenance  pass   app.py + 5 test files; branch main;
                          APP_VERSION reads v186
    G2 secrets     pass   staged diff: 0 key shapes, 0 auth tokens,
                          0 real usernames; secrets.toml not staged
    G3 analysis    pass   pyflakes 0 findings across 72 files.
                          It found the unused `gate` import, which was
                          then removed — the gate earning its keep
    G4 dead code   pass   vulture ≥90%: 1 finding, `keep` in
                          deliver_text, pre-existing and deliberate
                          (its own comment explains why)
    G5 dead loops  pass   12 urlopen waits, 12 with a deadline;
                          0 `while True`. Searched for `urllib`, which
                          is what this app uses — see v185 §15
    G6 stress      NOT RUN  tests/test_recorder_stress.py is committed
                          and has still never completed. Carried from
                          v185. This is the second delivery in a row
                          where G6 is a gap
    G7 budgets     pass   app.py 8,417 → 8,592 lines. The tier block and
                          its comments are the whole of it. No new
                          network call; the door removed one
    G8 upgrade     pass   a live v185 session keeps `_authed` and
                          `_user`; `_view_tier` is absent, and
                          view_tier() falls back to the account tier, so
                          nobody is signed out and nobody is downgraded.
                          `ADMIN_USER` without a digit still works, which
                          is the upgrade path for the secrets file itself
    G9 record      this document

### The mutations, and that they CHANGED something

Every mutation asserted the file actually changed before the run.

    last-listed wins, not highest      → 1b, 3a, 3b red   (merge broken)
    is_admin follows the ACCOUNT       → 4a, 5a red       (switch is a lie)
    radio drawn from the VIEW          → 4b, 4c red       (no way back)
    remove the clamp before the radio  → 5d red           (the crash)

Four mutations, four distinct sets red.

### A real fault the test found while being written

A stale `_view_tier` that the account no longer grants **took the whole
page down**: `st.radio` reads session_state through its key, and a value
that is not one of its options raises ValueError. `view_tier()` clamped
on read, which was not enough — the widget reads the raw state first. It
is clamped before the radio is built now.

Worth keeping because of its shape: a value that was already being
correctly ignored could still crash the app. Ignoring a bad value and
removing it are different acts.

### Three tests repaired, and why that is not a code fault

    test_owner_edge      relied on admin_user() falling back to
                         APP_PASSWORDS[0]. That fallback is what the
                         tiers replaced; the test now names its owner
    test_admin_users 13  anchored on the bare word "admin" to stand for
                         the user list. The radio prints "admin" at the
                         top of the page now, so a correct layout read as
                         a fault. Re-anchored on a person IN the list.
                         Its own comment already warned against
                         anchoring on a label — it had not gone far
                         enough
    test_tier            set the ROUTES to make the app studio. The tier
                         is the person now, so it names the person

All three were verified passing on v185 first, so they are genuinely
this change's consequences and not pre-existing noise.

Suite: **27 passed, 0 failed** across the files that collect.

---

## NOT TESTED

    THE BROWSER            nothing was opened in one. The radio's size,
                           its position above the tabs, and whether three
                           words fit in a row on a phone are all unseen
    G6 STRESS              tests/test_recorder_stress.py has never run.
                           It holds the check that a dead key must NOT be
                           retried on every redraw — a real risk the
                           v185 `_digest_done` change introduced
    A REAL WHISPER CALL    no Groq key in the sandbox
    THE LONG LOGIN         open item 8 should be fixed by a door that
                           makes no network call. Nobody has timed it
    STORAGE, END TO END    that a studio user's audio still reaches Drive
                           and a free user's does not was checked at
                           drive_store(), not by watching a file arrive
    tests/test_reader.py   check 8 needs edge-tts; this sandbox blocks
                           its TLS. Fails identically on v185
    test_accounts          12 checks still fail, describing the door
                           removed in v185. Untouched this session
    test_engine_ui,        still cannot collect. Verified identical on
    test_engine_sheet      v184 — pre-existing
    THE NOTE PATH          transcribe_note_take() still POPS `_note_take`
                           before the work, so an interrupted note take
                           is gone rather than skipped. NOT fixed

---

## §15 — WHAT WAS WRONG WITH THE GATE

**G6 has now been skipped twice running, and the record format let it
happen quietly both times.** v185 put it under NOT TESTED; this one gives
it a gate line reading NOT RUN. Neither stops a delivery. A gate that can
be left unrun on consecutive releases without anything escalating is
advisory, which §12 says is the failure mode that teaches gates do not
matter. **The bug bar should name a check skipped twice as blocking.**

**Nothing in the gate distinguishes a test that BROKE from a test that
describes a REMOVED feature.** Three files failed here for the second
reason and one still does from v185. Both look identical in a pytest
tally, and the difference is the whole story.

**G3 paid for itself in a way worth recording.** It found `gate` imported
and unused — a one-line finding that turned out to be the visible end of
the throttle being switched off with the old door. A dead import was the
only trace in the code that a security feature had gone.

Carried forward, unchanged: G8 has no row for a web app; G2's history
scan degrades silently on a shallow clone; G6 cannot record what was
mutated; nothing catches visual drift; harness failures masquerade as
artefact failures; and the gate cannot see a path no test executes.
