# NEXT — add Google as a third engine

**From Baba, 5.9.2026, via the session that built
[`GOOGLE_TTS_STT`](https://github.com/markoboskoauroville/GOOGLE_TTS_STT).**

> "In the admin panel, admin can switch free engine from Edge/Groq to Google
> only. Switch as PAIRS, so I can switch a complete set — either it will be
> Edge, Groq, or Google, everything. I need that pill inside my admin setting
> panel, and then all the users get the benefit of Google voices. And adapt the
> user interface to new providers."

Everything measured about the provider is in the manifest:
**`modules/gemini-speech.md`**, with `modules/keyring.md` for the ring and
`apis/gemini.md` for key formats. Read that first. This file is only what to do
in THIS repository.

---

## 1. What is being asked for

`ttt/engines.py` already has exactly the right shape and says so in its own
docstring: an engine is **a preset over the three routing tasks**, not a new
mechanism, and nothing downstream learns a vendor's name.

Today:

```
FREE      stt groq        tts edge        llm groq
STUDIO    stt assemblyai  tts speechify   llm anthropic
```

Add a third, complete across all three tasks:

```
GOOGLE    stt google      tts google      llm google
```

**As a pair, all three at once.** That is the whole request: one press moves the
free tier from Edge/Groq to Google, and every user on the free tier gets Google
voices without touching anything. The patch bay still exists for anyone who
wants a mixed set — this only adds a preset.

---

## 2. Secrets format

Match the shape `GROQ_API_KEYS` already uses, because a person setting this up
should be able to read one name and guess the other.

```toml
# --- Google Gemini -----------------------------------------------------
#
# Several keys so a rate-limited one can rest while another works. Google's
# free tier is TEN TTS REQUESTS PER ACCOUNT PER DAY, so this list is not an
# optimisation, it is the mechanism: eighteen accounts is eighteen budgets.
#
# Keys from AI Studio start with AQ. — that is the only format Google issues
# now. Old AIza keys are not made any more.
#
# QUOTAS ARE PER PROJECT, NOT PER KEY. Two keys made inside the same Google
# Cloud project share one budget, so twenty keys from one project is one
# budget wearing twenty hats. One key per account.
GOOGLE_API_KEYS = [
    "AQ.key_one",
    "AQ.key_two",
]
```

On Streamlit Community Cloud this goes in **Settings → Secrets**, never in the
repository. It can also live in a `k_google` tab of the spreadsheet, the same way
`k_groq` does — follow whichever `GROQ_API_KEYS` does, and follow it exactly.

**Names must match `apps_script/Code.gs` letter for letter**, per the note at
the top of `secrets.toml.example`. If it is `GOOGLE_API_KEYS` here it is
`GOOGLE_API_KEYS` there.

---

## 3. The provider

New file `ttt/providers/google.py`, alongside `groq.py` and `edge.py`, against
`providers/base.py` like the rest. It carries all three capabilities.

**Endpoint** `https://generativelanguage.googleapis.com/v1beta`, key in the
`x-goog-api-key` header.

**TTS** — `gemini-2.5-flash-preview-tts`, falling back to
`gemini-3.1-flash-tts-preview`.

```
POST /models/{model}:generateContent
{"contents":[{"parts":[{"text": PROMPT}]}],
 "generationConfig":{"responseModalities":["AUDIO"],
   "speechConfig":{"voiceConfig":{"prebuiltVoiceConfig":{"voiceName": VOICE}}}}}
```

Returns **raw 24 kHz mono 16-bit PCM, base64, with no header**. Write the WAV
header yourself. Nothing warns you.

**STT** — `gemini-3.1-flash-lite`, then `gemini-3.6-flash`, then
`gemini-3.5-flash`. Audio as `inlineData`. It does **not** accept webm, which is
what a browser recorder makes, so audio has to be converted first.

**LLM** — the same Flash chain, plain `generateContent`.

**`test_key`** must call a real endpoint, per the `engines.py` docstring, and it
must be a **generateContent**, not a `GET /models`: a listing returns 200 for an
account with zero credit, so it tests validity and nothing else.

---

## 4. The ring, and the five verdicts

`ttt/keyring.py` is the reference implementation and does not need changing —
but the Google mapping has one trap that has already cost a live key:

**The retry hint is checked FIRST and wins.** Google answers a spent account and
an impatient one with the same status and the same word. Match on *quota* alone
and you tell somebody to delete a live key because they pressed Test twice in a
second.

```
retryDelay | Retry-After | RetryInfo | QuotaFailure | "per minute" | "try again in"
    -> COOL, never dead
credit | balance | depleted | insufficient | billing | payment | prepayment
    -> no credit, its own word
401 | 403                 -> dead
5xx | 404 | no network    -> unknown, never dead
```

A **prepaid account with an empty balance answers 429**, exactly like a rate
limit, and waiting will never help. Check for it before the rate-limit branch.

**A 429 states the limit it just refused you**, and the `quotaId` says whether it
was the minute or the day. Parse the JSON, not the message string: a regex that
expects a space after the colon works against Google's pretty-printed output and
silently reads every daily wall as a minute limit.

**Sort candidates by budget remaining, largest first**, not round robin. Round
robin spreads the spend evenly and then every account hits its wall inside the
same few minutes.

---

## 5. The user interface

`§0 rule 2`: if a tab knows a vendor's name, that is a bug. So most of this is
data, not code.

- **Voices.** Thirty prebuilt, and Google publishes **one adjective each** —
  no gender, no age, no accent. Do not synthesise those facets from how a name
  sounds. The VR tab's filters should show what exists and no more; a blank is a
  fact and a guess is not.
- **Emotions.** There is no per-utterance `description` field like Hume's. There
  is ONE prose direction for the whole call and a speaker name per line, so
  inline direction has to be **compiled** into a preamble plus a parenthetical
  per line. Measured: it works, and it is not subtle.
- **Two speakers maximum** per call, via `multiSpeakerVoiceConfig`.
- **No word timings.** Edge streams word boundary events and Gemini returns audio
  and nothing else, so anything riding on `ttt/wordtimes.py` — the reader
  highlight — **cannot follow a Google voice**. This is the one place where the
  swap is not transparent and the UI has to say so rather than highlight the
  wrong word. Decide it deliberately: sentence-level timing from audio length, a
  forced aligner, or the highlight off for Google.
- **Eight minutes per call.** Longer text has to be split; see
  `modules/chunking-and-sending.md`, which is the same rule from the other
  direction — cut at silence, not at the clock.

---

## 6. Where it will hurt

**Ten TTS requests per account per day.** Not per hour. With every free user on
one shared ring, a handful of people auditioning voices spends the whole day
before lunch.

Three things follow, and they are not optional at this scale:

1. **Cache every preview.** A preview is a fixed voice, a fixed direction and a
   fixed sentence, so the second press is a question already answered. Key it on
   the sha of the prompt actually sent, so editing a direction invalidates it
   automatically. It never expires.
2. **Meter per user, not just per key.** One person can spend the whole ring.
3. **Say which account answered and whether it was cached.** A request that
   looks free is one nobody counts until the wall.

---

## 7. The check

`engines.py` is right that a green light meaning "a key is present" is worse
than no light. For Google the check must ask for **real work**, because a
listing succeeds on an account with no credit. One tiny `generateContent` per
account, and report the five verdicts rather than ok/not-ok — *busy* and *no
credit* are both healthy accounts and must not read as failures.

---

## 8. Suggested order

1. `GOOGLE_API_KEYS` in secrets and in `secrets.toml.example`, with the
   per-project warning in the comment.
2. `ttt/providers/google.py` with all three capabilities and a real `test_key`.
3. The 429 mapping into the ring's four verdicts, retry hint first. **Write the
   test before the mapping** — that trap has already cost a live key once.
4. `Engine("google", "Google", {...})` in `ENGINES`, all three routes.
5. The pill in the admin panel, and the engine check reporting five verdicts.
6. The VR tab: thirty voices, one adjective each, nothing invented.
7. The reader: decide what the highlight does without word timings, and say so
   on screen.
