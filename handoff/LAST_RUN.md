# STEP: the seconds you do not send are free
STATUS: done, pushed as v169. No deploy needed.
**The module is built and tested. IT IS NOT WIRED INTO THE RECORDERS
YET — that is the next step and it deserves its own careful pass.**

WHAT BABA GAVE ME
- A cost document that ranks its own advice, and puts silence trimming
  first of everything: "the single biggest saver and it costs nothing in
  quality, because you are deleting seconds that carried no words."

I AUDITED THE APP AGAINST IT FIRST, rather than building blindly
- Trim silence: NOT DONE. The number one lever, untouched.
- Audit model ids: done yesterday, v168, two models only.
- Cache by audio hash: not done.
- Retry once not three: WAIT_SCHEDULE is (5, 30, 125) — three waits.
  Worth revisiting.
- Log billed seconds: already done, per engine.

MEASURED, NOT CLAIMED
- On a clip shaped like real dictation — 8 seconds of words inside 19
  seconds of recording — the trim saved 48%. That is the top of the
  document's own 30-50% range, and it is money, because async is billed
  per second of audio.

TWO THRESHOLDS, AND THIS IS THE PART THAT MATTERS
- TRIMMING asks "is this gap worth cutting" at -42dB. Being wrong leaves
  a few seconds of silence in.
- THE SILENCE CHECK asks "is this worth uploading at all" at -60dB.
  Being wrong costs somebody their words.
- MY FIRST VERSION USED ONE THRESHOLD FOR BOTH and a completely silent
  file reported "not silent" — because trim_silence deliberately returns
  the ORIGINAL when the trim comes back empty, a guard meant for the
  quiet-microphone case, which swallowed the very case the check exists
  to find. Found by measuring a synthetic silent take, not by reasoning.
- Verified across real levels: -31dB, -47dB and -55dB are all kept;
  only -61dB, which is below hearing, is refused.

AND IT NEVER LOSES A RECORDING
- ffmpeg failure, an empty result, a missing file, or a saving under a
  tenth: the untouched original comes back. A saving is worth having and
  it is never worth a lost dictation.

NUMBERS
- trim 11 (new) · aai sync 17 · source 19 — green
- mutation: collapsing the two thresholds fails 3, including throwing
  away a very quiet voice
- pyflakes clean
