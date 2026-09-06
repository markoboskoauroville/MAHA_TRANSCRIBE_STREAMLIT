# SECRETS AUDIT — what this version actually reads

Generated from the source at v245, 6.9.2026. Every LIVE row was
confirmed by finding the line that reads it; every DEAD row by
finding no reader at all.

**The brief that uses this is [`handoff/CLAUDE_CODE_SECRETS.md`](../handoff/CLAUDE_CODE_SECRETS.md).**

| name | what for | state | note |
|---|---|---|---|
| `ADMIN_USER / ADMIN_USERn` | access | **LIVE** | names the owner; also matched by the tier scanner |
| `STUDIO_USERn` | access | **LIVE** | grants the studio tier |
| `FREE_USERn` | access | **LIVE** | grants the free tier |
| `APP_PASSWORDS` | access | **LIVE** | the shared-password door, a list |
| `APP_PASSWORD` | access | **LIVE (legacy)** | older single-password form, still read |
| `GOOGLE_API_KEYS` | keys | **LIVE** | the Gemini ring. Ten TTS requests per account per day |
| `GROQ_API_KEYS` | keys | **LIVE** | the app's own Groq ring |
| `GROQ_API_KEY` | keys | **LIVE (legacy)** | older single form |
| `ASSEMBLYAI_API_KEYS` | keys | **LIVE** | studio speech in |
| `SPEECHIFY_API_KEYS` | keys | **LIVE** | studio speech out |
| `ANTHROPIC_API_KEY` | keys | **LIVE** | studio text work |
| `HUME_ACCOUNTS` | keys | **LIVE** | array of tables: name, key, secret |
| `HUME_API_KEYS` | keys | **LIVE (legacy)** | older form, keys without secrets |
| `TABS_OFF` | options | **LIVE** | tabs hidden from everybody |
| `REMEMBER_SECRET` | options | **LIVE** | signs the remember-me cookie |
| `AUTH_URL` | options | **LIVE** | read by auth_url(), 2 call sites |
| `AUTH_LOGIN_TOKEN` | options | **LIVE** | read by auth_token(), 1 call site |
| `AUTH_ADMIN_TOKEN` | options | **LIVE** | read by auth_admin_token(), 1 call site |
| `DRIVE_SECRET` | options | **ALIAS ONLY** | accepted only as a fallback name for REMEMBER_SECRET |
| `SHEETS_URL` | dead | **DEAD** | the Apps Script deployment. No reader anywhere since v237 |
| `SHEETS_TOKEN` | dead | **DEAD** | paired with SHEETS_URL. No reader anywhere since v237 |

## How this was checked

```
grep -oE 'st.secrets.get\("([A-Z_0-9]+)"' app.py ttt/*.py | sort -u
```

`SHEETS_URL` and `SHEETS_TOKEN` return nothing from that, and nothing
from a whole-repository grep either. They are still present in
`.streamlit/secrets.toml.example`, which is stale — that file is not
the list to work from.

`secrets_template()` in `app.py` is generated from `SECRET_NAMES` and
is therefore correct for the KEY rows; it does not cover the access or
option rows, which is why this table exists.
