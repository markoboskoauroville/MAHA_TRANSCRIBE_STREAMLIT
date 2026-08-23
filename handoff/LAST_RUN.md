# STEP: a voice that refuses, and a store that says why
STATUS: done, pushed as v151. No deploy needed.

TWO REAL FAULTS, BOTH FROM BABA'S PHONE

1. THE READER CRASHED THE WHOLE APP.
   edge_tts.exceptions.NoAudioReceived came back as a red wall of Python
   on his phone, on the tab he opened to hear something read.
   The BACKGROUND worker two functions above already swallowed its
   errors — "so one failed block cannot cancel the others" — and the
   FOREGROUND call, the block he is actually waiting for, had no guard
   at all. The one that could kill the run was the unguarded one.
   Edge is free and unauthenticated and refuses sometimes for reasons
   nobody here controls. It says so now and the app stays standing.

2. THE STORE WAS OFF AND SAID NOTHING.
   Baba recorded three times in Emina's session; nothing reached Drive
   and the log held only `[deliver]` lines. I was wrong twice about why
   — a timeout logs, a refusal logs — and he corrected me: the log WAS
   his session. Silence meant the code never tried.
   `drive_store()` needs four things and disables itself if any is
   missing, because "a half-configured store that half-works is worse
   than one that plainly does not". True, and it was also saying
   nothing. Somebody whose recordings are quietly not being kept
   deserves to know WHICH of the four is missing.
   It writes one line to the log now, once per session, naming them:
   DRIVE_SECRET, SHEETS_URL, SHEETS_TOKEN, or the sheet's own
   store_audio switch. Verified: "missing: DRIVE_SECRET, SHEETS_URL,
   SHEETS_TOKEN".

WHAT THIS MEANS FOR THE MISSING text.txt
- It was never a race and never a refusal. Storage is simply OFF for
  him now — and his one Drive folder is from 14:36, before he redeployed
  the main script. Everything since has gone nowhere.
- The next session should NOT start by reading the store path again. It
  should read his log tab, which will now name the missing piece.

NUMBERS
- box 16 — green; reader unchanged
- verified in AppTest: the log names all three missing secrets
- pyflakes caught `return` at module level in my first draft of the
  reader guard, which is exactly what it is for. st.stop() instead.

STILL OPEN, ASKED AND NOT YET DONE
- A LANGUAGE PILL IN THE OPEN NOTE. Baba: "there should be also a
  language pill because I need to change languages while I'm
  transcribing." Not started.
- The two-system split and the file explorer — docs/TWO_SYSTEMS.md.
