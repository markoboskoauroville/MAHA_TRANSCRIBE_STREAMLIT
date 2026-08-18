# Word-level timings for read-aloud highlighting

**A measured method, not a proposal.** Every number here was produced by
running the code against ground truth, and the experiments that failed are
written down beside the one that worked, because the failures are what stop
the next person repeating a year of tuning.

Written 18.8.2026 for TTT-LLL. Portable to any project that has to move a
highlight in time with synthesised or recorded speech.

---

## 1. The problem

You have text on screen and audio of it being spoken. You want to colour
the word currently being said. For that you need, per word, a start time.

Some engines give them to you. **Speechify returns exact word marks.**
**Edge TTS returns nothing at all.** When there are no marks, the usual
fallback is to divide the audio's duration among the words in proportion to
their length in characters.

That fallback is what drifts, and this document is about why, and what to
do instead.

---

## 2. The finding that changes everything

The intuitive fix is: *find the silences between the words.* Detect gaps in
the amplitude envelope, and those gaps are the word boundaries.

**This cannot work, and here is the measurement that shows it.**

Take audio from an engine that reports true word marks, and look at the
interval between the end of each word and the start of the next:

```
words measured                        256
inter-word intervals                  238
exactly zero seconds                  236  (99.2%)
longer than 100 ms                      2  ( 0.8%)
```

**99.2% of inter-word intervals are exactly zero.** Speech does not stop
between words. Saying "the elements" involves no silence; the tongue simply
moves from one shape to the next. The two intervals over 100 ms were clause
pauses, not word boundaries.

So an algorithm hunting for inter-word silence is hunting for something that
is not there. It will find stop-consonant closures — the brief silence
inside the /t/ of "water" — and mistake them for word boundaries. In one
7.3-second sentence, naive pause detection found **ten** "pauses" where the
sentence had four real ones.

If you have been trying to fix highlight drift with silence detection and
getting nowhere, this is why.

---

## 3. What is actually wrong with proportional timing

Not word length. **Pauses.**

Real speech contains pauses at commas, clause breaks, full stops, and before
an emphasised word. A proportional split does not know they exist, so it
hands each word a slice of the pause as well. Every word after the first
comma is then late, and the error accumulates for the rest of the line.

Measured, on a sentence heavy with punctuation ("Wait — what? No, absolutely
not; that is not what I said, and you know it."), the proportional method was
**664 ms out on average** — the highlight two-thirds of a second behind the
voice, and getting worse toward the end.

Weighting by syllables instead of characters does **not** fix this. Measured:
231 ms mean error by characters, 232 ms by syllables. Identical. The word
weighting was never the problem.

---

## 4. What works: word timestamps from a speech recogniser

Send the audio to a speech-to-text model that reports **word-level
timestamps**, and map the words it heard onto the words you are displaying.

This inverts the usual instinct. You are not transcribing — you already know
the text. You are using the recogniser purely as a **time measuring
instrument**, and throwing its transcript away except as a key for
alignment.

### Results, against exact ground-truth marks

Held-out set: 144 words, unseen sentences, a voice not used during
development.

| method | mean | median | p90 | within 50 ms | within 100 ms |
|---|---|---|---|---|---|
| char-proportional (the usual fallback) | 138 ms | 119 ms | 261 ms | 26% | 45% |
| DSP envelope alignment (see §6) | 195 ms | 113 ms | 427 ms | 25% | 46% |
| **Whisper word timestamps** | **79 ms** | **48 ms** | **153 ms** | **51%** | **78%** |

On the development set the same method scored 89 ms mean / 48 ms median, so
it does not depend on tuning: nothing about it was fitted.

**Perceptual context.** Under about 50 ms a highlight reads as simultaneous
with the voice. By 100 ms an attentive reader notices. Past 200 ms it is
plainly wrong and the reader stops trusting it. The median lands at 48 ms —
inside the "simultaneous" band — and 78% of words are inside the "not
noticeable" band.

### Cost

A `whisper-large-v3-turbo` call on 4 seconds of audio took **0.42 s**. It is
one extra network call per rendered block, and it can run while the audio is
already playing, because the first word's timing is the only one needed
immediately.

---

## 5. How to implement it

### 5.1 Ask for word granularity

The parameter is easy to miss and silently absent from the default response.
Against an OpenAI-compatible endpoint:

```
POST /v1/audio/transcriptions
  model                       whisper-large-v3-turbo
  response_format             verbose_json      <- REQUIRED
  timestamp_granularities[]   word              <- REQUIRED
  language                    en | hr | ...     <- give it if you know it
  file                        16 kHz mono audio
```

`response_format=json` will not carry timings. It must be `verbose_json`,
and the granularity parameter really does take the literal square brackets
in the field name.

### 5.2 Map heard words onto displayed words

**This is the part that gets skipped, and it is where the failures are.**
The recogniser returns the words it *heard*, which are not the words you
*hold*. Measured differences on real output:

* it writes `1947` where the text says `1947`, but `12%` where the text
  says `12 percent`
* it writes `1,` `2,` `3,` where the text says `One two three`
* it merges and splits differently: `3,500 people` arrived as one token
* it mishears, and it sometimes drops a word entirely

So align the two sequences with **Needleman–Wunsch** over normalised tokens
(lowercase, strip punctuation, spell small integers as words). Score an
exact match highest, a prefix match lower — `people` against `3,500 people`
is real evidence — and everything else negative.

Any displayed word left unmatched gets its time **interpolated between its
matched neighbours**. Do not leave it without a time: a highlight that stops
moving is worse than one that is slightly early.

### 5.3 Never let it be a dependency

The timing call must be allowed to fail. If the network is down, the key is
exhausted, or the response has no `words` array, fall back to proportional
timing and carry on. Losing the highlight's precision is a small harm;
losing the audio is a large one.

---

## 6. What did not work, and the numbers

Recorded so nobody rebuilds them.

**Silence detection between words.** The premise is false — see §2. 99.2% of
inter-word intervals are zero.

**Syllable-weighted proportional timing.** 232 ms vs 231 ms for characters.
No improvement whatsoever.

**Full DSP alignment** — energy envelope, spectral flux, pause segmentation,
and dynamic programming to assign words to phrases and place boundaries
within them. This was built completely and tuned. It reached 200 ms on the
development set (a 13% improvement) but **195 ms on held-out data, which is
worse than the 138 ms of the naive method it was meant to beat.** The
duration prior was fitted to the development corpus and did not generalise.
It is not worth shipping.

**DSP refinement on top of Whisper anchors** — snapping each boundary to the
nearest low-energy, high-flux frame within a window. Tried at nine
window/weight settings. Best result 88 ms against 89 ms unrefined: no
improvement, and wider windows made it worse. This follows directly from
§2 — if there is no acoustic gap at a word boundary, there is no acoustic
evidence to snap to.

**Things that genuinely did help**, if you must build a no-network fallback:

* *Punctuation predicts pauses.* On the hardest sentence, four of five true
  phrase breaks sat on `,` `;` `?` `.`. Adding this cue cut that sentence's
  error from 608 ms to 322 ms.
* *Digits are spoken far longer than they look.* `1947` has no vowel, so a
  vowel-counting syllable estimate calls it one syllable; it is spoken
  "nineteen forty-seven" and takes 1.3 seconds. About 1.3 syllables per
  digit matches how numbers are read aloud.
* *Fit the duration prior, do not guess it.* Least squares on ground truth
  gave 0.168 s base + 0.155 s per syllable. The guess (0.055 + 0.180)
  underestimated a one-syllable word by 25%.

---

## 7. Rendering: the highlight that shakes

Separate problem, same feature, and worth stating because it wastes as much
time as the timing does.

**Change the word's COLOUR and nothing else.** Not a background, not bold,
not a border, not a font-weight change. Anything that alters the text's
metrics reflows the line, and every word after the highlighted one shifts by
a fraction of a pixel. That is the shaking.

**The test that catches it:** capture the bounding box of a *fixed* word —
one that is not being highlighted — before and during the highlight. If `x`
or `y` moves by a single pixel, the approach is wrong. Measure it; do not
look at it and decide it seems fine.

If a stronger emphasis than colour is needed, pre-reserve the space: apply
the bold weight to every word permanently in a transparent colour, or use
`text-shadow`, which does not participate in layout.

---

## 8. Recommended architecture

```
Does the TTS engine return word marks?
├─ YES (e.g. Speechify)  -> use them. They are exact; nothing beats them.
└─ NO  (e.g. Edge)       -> send the rendered audio to a word-timestamp
                            recogniser, map heard words onto displayed
                            words, interpolate any that did not match.
                            └─ call failed? -> proportional timing, and
                                               carry on without it.
```

Three layers, degrading in that order. The top layer costs nothing, the
middle layer costs one call and lands the median inside 50 ms, and the
bottom layer is never good but is always available.
