# DELIVERY RECORD — TTT-LLL v183 — 24.8.2026

Hume keys come in PAIRS, live in the SHEET, and fall back across 21
accounts so nobody waits.

    VERSION    new: v183   previous: v182
    TOUCHED    app.py, ttt/keyring.py, ttt/vr.py, ttt/sheet.py,
               apps_script/Code.gs, tests/test_vr.py

## ⚠️ THE APPS SCRIPT NEEDS A DEPLOY

`keys_put` and `keys_get` are new branches, alongside `eta_put`/`eta_get`
from v177 which were never deployed either. Until then keys live only in
the session and vanish on redeploy.

    Deploy -> Manage deployments -> ✏️ -> Version: NEW VERSION

## WHAT THE KEY TESTER TAUGHT

Rather than invent a convention, the KEY_TESTER repo was read. Its
KeyParser documents Hume exactly: the dashboard exports an account name,
then "API key", then the key, then "Secret key", then the secret. Both
tokens are plain alphanumeric with NO PREFIX. Its Providers.kt tests a
pair with Basic base64(api:secret) against /oauth2-cc/token.

Both were adopted verbatim, so the two repos agree.

## MEASURED WITH ALL 21 ACCOUNTS

    pair auth (oauth2-cc)   21 of 21 returned an access token
    api key alone (TTS)     21 of 21 returned 200
    import                  21 accounts -> 21 keys, labels intact,
                            re-import adds 0
    REAL FALLBACK           a ring of 5 fabricated keys followed by 3
                            real ones: walked all 5, marked each dead,
                            produced audio from the 6th. 3 survivors
                            still usable, none wrongly burned

## THE THING THAT MAKES THIS ENTERPRISE-GRADE

Hume limits per minute PER ACCOUNT. v182 paced globally at 12s, which
meant 21 working accounts were exactly as slow as one. The pace is now
PER KEY, and the ring hands out whichever account has rested.

Measured, 20 rehearsals three seconds apart:

    1 account    171 seconds of waiting
    3 accounts    18 seconds
    21 accounts    0 seconds

With 21 accounts the coffee message should never appear at all. It is
still there, still true, and still the thing that shows if the ring ever
runs dry.

## THE PAIR IMPORTER, AND THE BUG IT PREVENTS

`import_keys` would have taken 21 accounts as 42 keys — neither token
carries a prefix, so its generic pass grabs both. The ring would then
have rotated through 21 secrets that authenticate nothing, failing every
second call with no visible pattern. `import_pairs` reads the LABELS
instead, exactly as Key Tester does.

Mutated to prove it: made the importer also store secrets as keys, and
check 49 went red with (4, 4) where 2 was correct.

## GATES

    G1 PROVENANCE   pass    clean tree, v183 > v182, main
    G2 SECRETS      pass    THREE scans, not one: prefixed shapes in the
                            staged diff -> 0; BABA'S ACTUAL 21 keys and
                            21 secrets searched for literally in the
                            diff -> 0; every tracked file searched for a
                            real key prefix -> none. Error bodies are
                            still scrubbed of 32+ char runs before
                            display
    G3 ANALYSIS     pass    72 python files, pyflakes 0 findings;
                            Code.gs parses clean as JS
    G4 DEAD CODE    pass    import_pairs, pick_rested, usable_count,
                            hume_keys_from_sheet, hume_keys_to_sheet,
                            put_keys, get_keys — all referenced
    G5 DEAD LOOPS   pass    pick_rested is a single bounded pass over
                            the ring; sheet calls carry _post's 8s
                            timeout; hume_call 120s
    G6 STRESS       partial 166 checks green (61 in VR, 21 new).
                            MUTATED: importer storing secrets as keys
                            (red), pick_rested seeing only the first key
                            (3 red), dead keys not skipped (2 red).
                            TWO EARLIER MUTATIONS WERE INEFFECTIVE and
                            are recorded as such below rather than
                            counted as passes
    G7 BUDGETS      base+   166 checks (was 145)
    G8 UPGRADE      pass    keys gain "secret" and "last_used"; both are
                            read with .get() and default safely, so a
                            ring stored by v182 loads unchanged. A v182
                            app reading a v183 ring ignores both extra
                            fields
    G9 RECORD       this document

## NOT TESTED

    THE SHEET ROUND TRIP    keys_put/keys_get are written and parse, but
                            NOTHING HAS BEEN STORED OR FETCHED — the
                            script is not deployed. This is the largest
                            untested surface in this delivery
    NO PHONE, NO LISTENING  still true from v182: nobody has heard VR
    429 NEVER PROVOKED      with 21 accounts it is now even harder to
                            reach, so the cool-down path stays unproven
    WAV NOT OPUS            still shipping ~96KB per second of speech
    THE ADMIN PANEL         the pair import path is asserted by reading;
                            nobody has pushed the button
    STILL OPEN              copy/clear rule, ETA sheet deploy,
                            AssemblyAI round trip, HR->ENG and
                            single->multi mid-recording, Speechify
                            test-key button, TR deck audio

## WHAT WAS WRONG WITH THE GATE — §15, eighth report

**TWO OF MY MUTATIONS THIS SESSION CHANGED NOTHING.** One narrowed a
condition that another branch immediately satisfied; one moved an index
in a parser that keys off labels, not offsets. Both produced a green
suite, which reads exactly like "the check is weak" and is in fact "the
mutation was". The module says to make each check fail on purpose; it
should also say to CONFIRM THE MUTATION ACTUALLY CHANGED BEHAVIOUR —
an ineffective mutation is worse than none, because it certifies a check
that was never exercised.

**G2 should require searching for the ACTUAL secret, not only its
shape.** Every previous report scanned for patterns. Today there were 42
real credentials in play, and the only honest check was to search the
diff for each of them literally. Shape scanning would have missed a key
pasted into a comment as an example.

**Still true from v176-v182:** G8 has no web-app row, G2's history scan
degrades silently on a shallow clone, G6 cannot record mutations,
nothing catches visual drift, and nothing checks that a failure path
does the right thing.
