#!/usr/bin/env bash
#
# PUSH THE SCRIPTS. Fill the secrets, send the file, print what to click.
#
# Baba: "I want that parameters fill in automatically from my local
# system... so I don't need to enter those things any more during
# update, only during change."
#
# That is what this is. The secrets live in ONE file on his Mac, outside
# git; this reads them, fills the script, sends it to Google with clasp,
# and puts everything back the way git expects. He types one command and
# then presses one button in the browser.
#
#   tools/push_gs.sh          both scripts
#   tools/push_gs.sh main     the sheet-bound one only
#   tools/push_gs.sh auth     the accounts one only
#
# THE BUTTON STAYS. `clasp push` updates the code; it does NOT publish
# it. A deployment is a named version, and making one needs the browser.
# So this ends by telling him exactly what to click, rather than
# pretending the job is done.

set -euo pipefail
cd "$(dirname "$0")/.."

WHICH="${1:-both}"

MAIN_ID="12NtdbhOSAJNX7UoV8AUrVnZwc5OS62RXeqvJzvu3AMpjRFjPDAET-dNx"
AUTH_ID="1iim9Qzakqq_j2cmFbu3KQFIBXwG_MVwqGs7yR7rETNvmq3AWNppPMHAY"

say() { printf '\n%s\n' "$*"; }

# ---- clasp must exist and be logged in --------------------------------
if ! command -v clasp >/dev/null 2>&1; then
  say "clasp is not installed. One time only:"
  echo "    npm install -g @google/clasp && clasp login"
  exit 1
fi
if ! clasp login --status >/dev/null 2>&1; then
  say "clasp is installed but not logged in. One time only:"
  echo "    clasp login"
  exit 1
fi

# ---- the main script --------------------------------------------------
#
# THE SECRETS GO IN, THE FILE GOES UP, THE SECRETS COME OUT AGAIN.
# apps_script/Code.gs is tracked, so it must end this script exactly as
# git has it — placeholders and all. The filled copy exists only for the
# seconds clasp needs to read it, and the trap puts the original back
# even if clasp fails or Baba presses ctrl-C.
push_main() {
  say "MAIN SCRIPT — the one bound to the sheet"

  python3 tools/fill_gs.py || {
    echo "Could not fill the secrets. Nothing sent."
    exit 1
  }

  cp apps_script/Code.gs /tmp/Code.gs.original
  # THE TRAP CLEANS EVERYTHING, not just the tracked file. A failed push
  # was leaving Code.filled.gs and .clasp.json behind — both gitignored,
  # so harmless, but a file with real secrets in it should not outlive
  # the seconds clasp needs to read it. Tested by making clasp fail.
  trap 'mv -f /tmp/Code.gs.original apps_script/Code.gs 2>/dev/null || true;
        rm -f apps_script/Code.filled.gs .clasp.json' EXIT

  cp apps_script/Code.filled.gs apps_script/Code.gs
  printf '{\n  "scriptId": "%s",\n  "rootDir": "apps_script"\n}\n' \
    "$MAIN_ID" > .clasp.json

  clasp push --force

  mv -f /tmp/Code.gs.original apps_script/Code.gs
  trap - EXIT
  rm -f apps_script/Code.filled.gs

  say "sent. Now press the button:"
  echo "  https://script.google.com/home/projects/$MAIN_ID/edit"
  echo "  Deploy -> Manage deployments -> pencil -> New version"
}

# ---- the accounts script ----------------------------------------------
#
# NO FILLING HERE. auth_script/Code.gs holds no secrets — its pepper and
# tokens live in Script Properties, which is why it can be pushed as it
# stands and why it was always the easy one.
push_auth() {
  say "ACCOUNTS SCRIPT — logins and passwords"

  printf '{\n  "scriptId": "%s",\n  "rootDir": "auth_script"\n}\n' \
    "$AUTH_ID" > .clasp.json

  clasp push --force

  say "sent. Now press the button:"
  echo "  https://script.google.com/home/projects/$AUTH_ID/edit"
  echo "  Deploy -> Manage deployments -> pencil -> New version"
}

case "$WHICH" in
  main) push_main ;;
  auth) push_auth ;;
  both) push_main; push_auth ;;
  *) echo "usage: tools/push_gs.sh [main|auth|both]"; exit 1 ;;
esac

# ---- leave nothing behind ---------------------------------------------
rm -f .clasp.json
say "Done. apps_script/Code.gs is back to its tracked state:"
grep -c "CHANGE_ME\|PUT_YOUR" apps_script/Code.gs | \
  sed 's/^/  placeholders restored: /'
