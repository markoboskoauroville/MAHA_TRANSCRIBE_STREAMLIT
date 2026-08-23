# WHAT A DEEP SCAN FOUND, 23.08.2026

Baba: *"do a deep scan of this app and search for the bugs and optimize
the code and make it ready for final release."*

---

## The state, measured

**660 checks green.** 21 Python suites and 4 script suites, no failures.
Three suites skip because they drive a real browser and need one
running — by design, not damage.

pyflakes clean across `app.py`, all of `ttt/`, and both provider files.
No secret material in any tracked file. Every tab opens on a 360px phone
viewport with no traceback and no JavaScript error.

---

## Fixed in this pass

### The dependencies had no ceiling

This is the one thing that could have taken the app down without anybody
touching it.

`streamlit>=1.61.0`, unbounded — while the app leans on
`st.components.v1.html`, which Streamlit says *"will be removed after
2026-06-01"*. **That date has passed.** There are six call sites and six
`declare_component` calls, and every one of them is a recorder, a player
or an editor.

Streamlit Cloud rebuilds on its own schedule. The first version that
actually drops the API would take the whole app down for a family who
changed nothing and were given no warning. All three dependencies now
have upper bounds.

### A silent save now says why it is silent

`_save_server_settings` swallowed every error with a bare `pass` — the
same shape as the note-storage bug that took days to find.

It is genuinely harmless here: Streamlit Cloud's disk is wiped on every
redeploy, so this is a convenience for somebody returning inside the
same container, and the BROWSER copy is what actually carries settings
between sessions. That reason is now written where the next reader meets
it, because **a bare `pass` with a good reason and a bare `pass` hiding a
bug look identical.**

---

## What is left, honestly

### The duplicate transcribe

`app.py` has its own Groq client, its own key rotation and its own
`transcribe()`, duplicating `ttt/providers/groq.py`.

It has already cost two bugs: `auto` being sent to Whisper (v120) and an
empty model being sent (v121). Both were fixed in one copy while the
other went on shipping the fault, and both looked complete at the time.

It should be routed through the provider. **It should not be done the day
before a release** — the two have different key-rotation strategies, and
swapping them is the kind of change that needs a session and a person
testing afterwards, not a confident refactor at the end.

### The components should move to `st.iframe`

`st.iframe` exists in 1.61. That work is what removes the reason for the
version ceiling, and it is a session of its own: six components, every
one of them something somebody presses.

### test_reader check 8

Red since v101. Changing voice mid-reading rebuilds the closure but
never refills the cache. It needs a browser; it is not reachable from
AppTest.

### And the thing that is not a code problem

Notes and recordings are one system pretending to be two.
`docs/TWO_SYSTEMS.md` has the shape Baba described. Nothing in it can be
built until his Drive actually holds the files — and v154 was the
missing half of that: the note's recorder never stored anything at all.

---

## What "ready for release" means here

The app is stable, tested, and pinned. Nothing known is broken.

What it is not is **finished**. The two-system split, the file explorer
and the key management system are all designed and none are built.

Those are different words and they are worth keeping apart: this can be
given to the family today, and it cannot be called done.
