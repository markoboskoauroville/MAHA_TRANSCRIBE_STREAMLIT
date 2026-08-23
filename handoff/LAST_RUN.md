# STEP: AUTO returned nothing
STATUS: fixed and pushed as v120

WHAT BABA REPORTED
- AUTO: no transcription at all.
- HR: correct, filters to Croatian.
- ENG: behaves like AUTO, recognises every language.

THE AUTO BUG, AND WHY v118 DID NOT FIX IT
- "auto" was being SENT to Whisper. That is a 400, the key rotation then
  tried every key, every one failed, and the result was an empty string
  — so the screen showed nothing and named no fault.
- v118 fixed exactly this in ttt/providers/groq.py. It changed nothing,
  because THE PATH A RECORDING TAKES NEVER GOES NEAR THAT FILE. app.py
  has its own copy of the Groq call at line ~1569, talking to the SDK
  directly, and transcribe_any_size routes through that one.
- One implementation in the module, used from everywhere, is the rule.
  The cost of having two was a fix that read as complete and did
  nothing for a whole version.
- Nothing tested the SHAPE of the request, which is why a wrong shape
  shipped twice. tests/test_language.py now does: 13 checks, and the
  mutation that sends "auto" again fails 2 of them.

ENG — NOT A BUG, AND I SHOULD SAY SO PLAINLY
- Whisper's `language` is a HINT, not a filter. It biases the decoder;
  it does not refuse other languages. Croatian audio with language=en
  still decodes as Croatian, because the model recognises it and the
  hint is weak against strong evidence.
- HR "works" for the same reason in reverse: Croatian audio plus a
  Croatian hint agree, so the result is clean.
- There is no setting that makes Whisper transcribe ONLY English and
  refuse the rest. It cannot be fixed in the app because it is not the
  app's behaviour. Options if it matters: check the returned language
  and reject the take, or use AssemblyAI, whose language_detection is a
  real detector rather than a hint.

NUMBERS
- language 13 (new) · box 16 · source 19 — green
- one mutation applied, 2 checks red
- pyflakes clean

FOR BABA
- Try AUTO again after this deploys. It should transcribe now.
- ENG will still pick up Croatian. That is Whisper, not the app — tell
  me if you want the app to REJECT a take whose language is not the one
  you asked for, which is the only honest way to get what you described.
