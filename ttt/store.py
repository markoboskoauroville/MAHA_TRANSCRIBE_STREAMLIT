"""Three-layer per-user storage. Knows nothing about what it stores.

    1. st.session_state   this run
    2. browser localStorage   the one that really survives
    3. a server-side file   same-instance convenience only

Streamlit Community Cloud is stateless and shared: it does NOT guarantee
disk across restarts, so layer 3 is a nicety and layer 2 is the real store.
Anything that must survive belongs in localStorage.

Any number of independent namespaces can be kept side by side (settings,
provider keys, saved texts...) — each is its own blob under its own
localStorage key, so one growing large never threatens another.

The localStorage bridge is deliberately declared by the CALLER and handed
in, not created here: it must be re-declared on every script run from the
entrypoint. See HANDOVER incident 1 — a bridge living in a module went
stale in a warm process and took the whole app down with a TypeError.
"""

import json
import os
import tempfile


class Store:
    """One namespace of per-user data.

    `ls_read` is a dict of everything already read out of localStorage this
    run. `ls_write(key, value)` queues a localStorage write. Both come from
    the entrypoint, so this module never touches Streamlit at all and can
    be used (or tested) without it.
    """

    def __init__(self, namespace: str, user: str, ls_read: dict = None,
                 ls_write=None, defaults: dict = None, local_only: bool = False):
        self.namespace = namespace
        self.user = user
        self.ls_read = ls_read or {}
        self._ls_write = ls_write
        self.defaults = dict(defaults or {})
        # local_only: never touch the server-side file, browser storage
        # only. For anything holding a person's own CONTENT rather than
        # their preferences. The server file is shared-container state on
        # Streamlit Cloud, keyed by username — so somebody who guessed a
        # password could read the previous holder's saved text out of it.
        # Preferences are not worth that risk either, but saved documents
        # certainly are not.
        self.local_only = local_only

    # ---- addressing -------------------------------------------------
    @property
    def ls_key(self) -> str:
        return f"maha_{self.namespace}_{self.user}"

    def _file(self) -> str:
        d = os.path.join(tempfile.gettempdir(), f"maha_{self.namespace}")
        os.makedirs(d, exist_ok=True)
        safe = "".join(c for c in self.user if c.isalnum()) or "user"
        return os.path.join(d, safe + ".json")

    # ---- read / write -----------------------------------------------
    def load(self) -> dict:
        """localStorage first, then the server file, then defaults. Never
        raises: unreadable storage falls through to the next layer."""
        raw = self.ls_read.get(self.ls_key)
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return {**self.defaults, **data}
            except Exception:
                pass
        if not self.local_only:
            try:
                with open(self._file(), encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return {**self.defaults, **data}
            except Exception:
                pass
        return dict(self.defaults)

    def save(self, values: dict) -> None:
        """Write to both durable layers. Never raises — persistence is a
        convenience and must never be able to take the app down."""
        if not self.local_only:
            try:
                with open(self._file(), "w", encoding="utf-8") as f:
                    json.dump(values, f, ensure_ascii=False)
                try:
                    os.chmod(self._file(), 0o600)
                except Exception:
                    pass
            except Exception:
                pass
        if self._ls_write:
            try:
                self._ls_write(self.ls_key, json.dumps(values, ensure_ascii=False))
            except Exception:
                pass

    def forget(self) -> None:
        try:
            os.remove(self._file())
        except Exception:
            pass
        if self._ls_write:
            try:
                self._ls_write(self.ls_key, None)
            except Exception:
                pass
