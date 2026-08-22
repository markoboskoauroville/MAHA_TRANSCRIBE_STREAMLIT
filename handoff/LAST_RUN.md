# STEP: plan the four accounts changes
STATUS: done — plan only, no code

WHAT HAPPENED
- Wrote `docs/ACCOUNTS_CHANGES.md`: two engines, a password you choose,
  must-change-on-first-login, and one copyable message — each with what
  it touches, plus the deploy answer and the breakage table.
- Traced the engine value end to end before deciding anything, because
  the answer to "what must I deploy" depended on it: panel →
  `ACCOUNTS.user_engine` (auth script) → users tab → `login_` →
  `_assigned_engine` → `adopt_sheet_engine()` → the routes.

THE DECISIONS I TOOK, AND WHY
- Store **`normal`**, and accept **`free` forever on read** via an alias
  in `EN.get()`. Nothing here updates atomically, so every value already
  written has to keep meaning something.
- `userEngine_` keeps accepting an empty string and stores `normal`.
  The deployed panel sends `""` for its "global" button; if you deploy
  the script before I push the app, that press must not become an error.
- The forced change screen is a FAMILY screen, so hard rule 6 governs it
  completely — none of the owner-density from `HOW_WE_WORK.md` applies.
- The copy message is built from the SCRIPT'S REPLY, never from what you
  typed. That one rule is what makes an undeployed script visible
  instead of silently wrong.

NUMBERS
- nothing run — planning only. No test, no app code changed.

WHAT BROKE, AND WHAT I UNDID
- Nothing. Read-only work.

STILL UNSURE
- **Blank engine cells need a decision from you, not from me.** Blank
  meant "follow the global row". If that row says `free`, blank becomes
  `normal` and nobody moves; if it says `studio`, those people are on
  studio today and writing `normal` would quietly demote them. The
  migration previews the global value and the affected names before it
  writes anything.
- Whether the app should know its own public URL for the message. It
  cannot work it out reliably; I would use an optional `APP_URL` secret
  and simply leave the link out when it is unset.

FOR BABA
- Deploy needed: **the accounts script only** (New version). The main
  script does NOT need one — checked in the code, reasons in §5 — and
  the Streamlit app redeploys itself when I push.
- One decision before building: blank engine cells, above.
- Older queue, unchanged: `ADMIN_USER = "admin"`, deploy the AUTH
  script, add `AUTH_ADMIN_TOKEN`, then create Emina and Marinko. Step 1
  of `SELF_UPGRADE.md` — the live Claude API check — is also still
  unrun, so the `temperature` fix stays asserted rather than proven.
