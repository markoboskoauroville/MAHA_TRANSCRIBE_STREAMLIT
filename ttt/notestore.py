"""NOTES ON THE MACHINE, PER PERSON. Marko, 7.9.2026: "per-user note saving,
so any transcription is saved for later, and they can be revoked or deleted.
A notes managing system like Google Keep. Only text, no audio, not much
space."

WHERE. Until today notes lived in the browser (localStorage) and, for the
studio, in Drive. On the Oracle machine there is a disk that is Marko's own,
so the notebook of each person is kept there as well: one SQLite file
(TTT_NOTES_DB, e.g. /home/ubuntu/.maha/notes.db), one row per person, the
whole notebook as JSON (two hundred notes of text are kilobytes, and a whole
notebook is what the app reads and writes anyway).

WHO. The person is `st.session_state["_user"]` (the door's user behind
pages.dev, the accounts name otherwise). No user, no row: the browser copy
goes on working exactly as before.

NEVER A DEPENDENCY. Every function here returns quietly on any failure; a
notebook that cannot be read from the machine is simply read from the
browser, as it was yesterday.
"""

import json
import os
import sqlite3
import time

PATH = os.environ.get("TTT_NOTES_DB", "")


def enabled() -> bool:
    return bool(PATH)


def _db():
    d = os.path.dirname(PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    c = sqlite3.connect(PATH, timeout=5)
    c.execute("CREATE TABLE IF NOT EXISTS notebooks (user TEXT PRIMARY KEY, json TEXT NOT NULL, "
              "count INTEGER, updated REAL)")
    return c


def load(user: str):
    """The person's notebook as a list, or None when there is none (or no machine store)."""
    if not enabled() or not user:
        return None
    try:
        c = _db()
        row = c.execute("SELECT json FROM notebooks WHERE user=?", (user,)).fetchone()
        c.close()
        if not row:
            return None
        got = json.loads(row[0])
        return got if isinstance(got, list) else None
    except Exception:                                    # noqa: BLE001
        return None


def save(user: str, notes) -> bool:
    """Write the whole notebook. Text only: any note carrying audio bytes
    would be a mistake upstream, and it is not stored here."""
    if not enabled() or not user or not isinstance(notes, list):
        return False
    try:
        body = json.dumps(notes, ensure_ascii=False)
        c = _db()
        c.execute("INSERT INTO notebooks (user, json, count, updated) VALUES (?,?,?,?) "
                  "ON CONFLICT(user) DO UPDATE SET json=excluded.json, count=excluded.count, updated=excluded.updated",
                  (user, body, len(notes), time.time()))
        c.commit()
        c.close()
        return True
    except Exception:                                    # noqa: BLE001
        return False


def counts():
    """user -> number of notes, for an admin who may see counts and never texts."""
    if not enabled():
        return {}
    try:
        c = _db()
        out = {u: n for u, n in c.execute("SELECT user, count FROM notebooks")}
        c.close()
        return out
    except Exception:                                    # noqa: BLE001
        return {}
