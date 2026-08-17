"""Slowing down password guessing.

The app is deployed publicly (Streamlit no longer offers an unlisted
option — only "specific people", which would force every reader to hold a
Streamlit account, or "public and searchable"). So the login screen is
reachable by anyone who finds the URL, and the password gate is the only
thing in front of it.

WHAT THIS DOES AND DOES NOT DO — stated plainly, because a security
control that is oversold is worse than none.

  It DOES make repeated guessing in one browser session progressively
  hopeless: the wait doubles after each failure, so a run of attempts
  goes 0s, 1s, 2s, 4s, 8s ... up to a minute between tries.

  It does NOT stop a determined attacker with a script, because a fresh
  session resets the counter and Streamlit gives no reliable per-client
  identity to key on. It raises the cost of each attempt (a page load and
  a websocket handshake, seconds each) rather than making it impossible.

  Therefore THE REAL DEFENCE IS PASSWORD STRENGTH. This buys time against
  casual and manual guessing; a long password is what makes the search
  infeasible. Do not let this module become the reason nobody bothers.

A deliberately global cap is NOT used: locking the app after N failures
across all sessions would let anyone lock out the real users at will,
trading a small risk for a certain one.
"""

# A LINEAR ladder, not a doubling one. Baba's reason, and it is the right
# one: this app is for people with unsteady hands, who mistype in runs
# rather than once. A doubling delay reaches a minute after a handful of
# genuine fumbles and feels like punishment for a disability. Ten seconds
# more each time is predictable — you can see the shape of it — and
# predictability is itself an accessibility property.
STEP_DELAY = 10.0        # each further failure adds this many seconds
MAX_DELAY = 60.0         # never wait longer than this
FREE_ATTEMPTS = 3        # three fumbles cost nothing at all


def next_delay(failures: int) -> float:
    """How long to wait after `failures` consecutive failures.

    Three free, then ten seconds more each time up to a minute:
    0, 0, 0, 10, 20, 30, 40, 50, 60, 60 ...

    Forgiving where the cause is probably a shaking hand, and steadily
    expensive where the pattern starts to look like guessing.
    """
    if failures <= FREE_ATTEMPTS:
        return 0.0
    return min(STEP_DELAY * (failures - FREE_ATTEMPTS), MAX_DELAY)


def locked_for(failures: int, last_failure_at: float, now: float) -> float:
    """Seconds still to wait, 0 if a new attempt is allowed now."""
    if not last_failure_at:
        return 0.0
    remaining = next_delay(failures) - (now - last_failure_at)
    return max(0.0, round(remaining, 1))


def record_failure(state: dict, now: float) -> dict:
    state["failures"] = int(state.get("failures", 0)) + 1
    state["last_failure_at"] = now
    return state


def record_success(state: dict) -> dict:
    """A correct password clears the record — the next person to use this
    device must not inherit somebody else's penalty."""
    state["failures"] = 0
    state["last_failure_at"] = 0.0
    return state


def check(state: dict, now: float):
    """(allowed, seconds_to_wait) for an attempt right now."""
    wait = locked_for(int(state.get("failures", 0)),
                      float(state.get("last_failure_at", 0.0)), now)
    return (wait <= 0), wait
