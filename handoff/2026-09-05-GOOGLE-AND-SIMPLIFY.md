# HANDOVER — 5.9.2026, at v237

Where the Google engine and the simplification work stand. Everything
below was measured or run, not remembered.

`HANDOVER.md` is the standing document; this is one session's addendum.

---

## STATE

`main` = **v237**, pushed and verified by SHA, working tree clean.
Sweep green: every suite, every line a number, every number zero
failures. Run it before believing anything:

    python3 tools/sweep.py

It clears caches, runs the linter, runs 57 suites, and BLOCKS on a suite
that produces no number — a crash and a pass look equally unlike a
failure. Lint baseline 159; any rise blocks. Never raise the baseline to
make a green: that is how a backlog becomes a floor.

---

## DONE THIS SESSION

- **v234** the Google pill was never drawn — `zip((ecol1, ecol2),
  EN.ENGINES)`, two columns and three engines, and zip stops at the
  shorter side silently. Plus the secrets template panel, generated from
  `SECRET_NAMES`, the same tuple the loader reads.
- **v235** Google's thirty voices, one adjective each and nothing else.
  Per-tab switches for the owner.
- **v236** one sentence, one file, one highlight. The word highlight is
  gone; the sentence sounding is lit, exact by construction. Buffer 3.
- **v237** spreadsheet, Apps Script and `ttt/accounts.py` removed.

---

## BABA'S FOUR STEPS — 1 DONE, 2/3/4 NOT STARTED

### 2 — TWO ENGINES

His correction, verbatim: *"We have Edge/Groq or Google because the
Google option second can do everything through API keys. We can do TTS,
STT, and we can do translations as well."*

    normal   stt groq    tts edge    llm groq
    google   stt google  tts google  llm google

`ttt/engines.py` currently has google as `tts: edge`. **Change to
`tts: google`.** The reason I originally kept Edge there — losing word
timings — died with v236. There are none to lose.

Studio goes as an ENGINE. Speechify, AssemblyAI and Hume STAY as
providers: *"Hume can stay, AssemblyAI can stay, Speechify can stay."*

**SOLVE THIS FIRST — a real collision.** v236 makes the reader generate
one file per sentence. Google's free tier is TEN TTS REQUESTS PER
ACCOUNT PER DAY. One paragraph spends an account. `ttt/speech.py` has
both planners for exactly this reason: `plan_sentences` for Edge,
`plan_even` (blocks) for engines metered by the call. **The reader must
pick the planner by engine.** A block highlight is still exact — the
block IS the file — merely coarser. That does not break his rule.

### 3 — REMOVE PER-USER KEY ENTRY

No uploader, no paste box in Settings. Keys from Secrets only.
Around `app.py:11087`, keys `{prov.id}_key_file`, `{prov.id}_key_paste`.

### 4 — THE KEY TESTER PANEL (the big one)

*"Just make one entry for administrator, a key tester... look in
repository, it's called Key Tester Android app. Everything that that
Android app does, this key tester supposed to do here... there should be
option fill secrets, and then it will take all these keys and make new
secret. There should be also a form to put all the keys needed, and then
the secret file will be generated in front of my eyes."*

Port the parser from `markoboskoauroville/KEY_TESTER`,
`app/src/main/java/org/mantra/keytester/KeyParser.kt`. Its rules:

    GOOGLE      AQ.[...]{20,}  or  AIza[...]{20,}
    ANTHROPIC   sk-ant-[...]{20,}
    GROQ        gsk_[...]{20,}
    SPEECHIFY   sk_[...]{16,}  when length >= 44
    ELEVENLABS  sk_[...]{16,}  when shorter
    HUME        a PAIR per account, read from the LABELS in the export:
                <account name> / "API key" / <key> / "Secret key" / <secret>
                Both halves are plain alphanumeric so SHAPE CANNOT TAG
                THEM — only the labels can. Auth needs both halves.

`secrets_template()` and `secrets_loaded()` already exist in `app.py`
and emit paste-ready TOML from `SECRET_NAMES`. BUILD ON THEM. Missing:
parse an uploaded file, test each key live, show working/dead, and emit
the finished block with the REAL keys in it.

---

## MEASURED FACTS — do not re-derive, these cost live calls

**Baba's Google keys start `AQ.`, 53 chars — not `AIza`.** My first
extractor assumed AIza, sliced three characters off all 21, and every
key looked invalid.

    LLM  gemini-3.6-flash              200
    TTS  gemini-2.5-flash-preview-tts  200, audio/L16;codec=pcm;rate=24000
                                       NO RIFF HEADER — raw PCM, and no
                                       browser plays it as-is
    bad key                            401 UNAUTHENTICATED,
                                       ACCESS_TOKEN_TYPE_UNSUPPORTED
    GET /v1beta/voices                 404 — no voices endpoint exists;
                                       the adjectives are docs-only
    gemini-2.0-flash                   404, retired, use 3.6

**The documented 3-per-minute TTS limit did not hold** — five calls in a
row all 200 on 5.9.2026. Recorded, not acted on.

**One account is spent**: key 1 (`av.live.vmix`) used 6 of its 10 daily
TTS calls on my probes. If it answers `zero_credits`, that is why.

**Hume has NO children's voices and refuses to make one.** 160 voices,
AGE axis only Middle-Aged / Young / Old. Voice-design for a child returns
400 `child_content_filter`, code E0809 — a policy filter. DO NOT look for
a phrasing that evades it; that risks all 21 accounts.

**Hume cannot clone from a sample** — saving a voice needs a
`generation_id`, which only comes from audio Hume itself generated.

**`verdict()` in `ttt/providers/google.py` agrees with all eight measured
answers.** Five verdicts: working / busy / no credit / refused / unknown.
A 429 carrying a money word is NO CREDIT, not busy — retrying that spins
against a wall all day.

---

## TRAPS WALKED INTO THIS SESSION

**Deleting `ttt/sheet.py` took the whole app down at import**, because
`ttt/accounts.py` imported `ttt.sheet._post` at module level. No error
page, nothing. The sweep caught it as eight suites crashing at once.
**Before deleting a module, grep for every IMPORTER, not just callers.**

**A check matching its own comment** — seventh time. The comment saying
something was REMOVED contains the string, so the check can only be made
green by deleting the reason. Strip comments before matching.

**`index()` crashes where `find()` reports** — six times this session.

**A test can be perfectly correct about the WRONG RULE.** `test_undo`
asserted the exact behaviour Baba complained about, green for 34
versions.

Written up in `MANTRA_MANIFEST/modules/checking-the-checks.md`, with
`tools/lint_checks.py` for the four mechanical faces.

---

## NOT TESTED

**A browser.** Everything visual in v234–v237 is source inspection. Four
faults this session reached Baba rather than the tests, each a claim
about a browser made from reading source.

- whether the sentence hand-off is AUDIBLE (buffer of 3 is a guess about
  phone latency)
- the tab switches on a phone
- the secrets template copying on mobile
- Streamlit's file uploader on Android Firefox
- **Google TTS end to end through the app** — the API call is proven,
  nothing has played a Gemini voice through the reader

---

## THE RULE THAT MATTERS MOST

When something does not work end to end, **read every file on the path
once before theorising about any of them.** Three rounds went on
component-timing theories for a localStorage bug whose cause was one word
in a 42-line file I had never opened.
