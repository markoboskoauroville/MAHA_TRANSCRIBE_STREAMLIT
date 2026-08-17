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

# Baba's ladder, specified exactly. Three quick tries so an unsteady hand
# is not punished for fumbling, then it becomes serious very fast.
#
#   attempt 1   immediate
#   attempt 2   after 3 seconds
#   attempt 3   after 6 seconds
#   attempt 4   after 1 minute
#   then        2, 4, 8, 16 minutes, capping at 16
#
# The shape matters: the cheap part is generous enough for a real person
# having trouble typing, and the expensive part climbs fast enough that
# guessing is pointless. Sixteen minutes is the ceiling because an
# unbounded wait would be indistinguishable from the app being broken,
# and someone locked out forever cannot tell the difference.
LADDER = [
    0,      # no failures yet
    3,      # after 1 failure
    6,      # after 2
    60,     # after 3  — one minute
    120,    # after 4  — two
    240,    # after 5  — four
    480,    # after 6  — eight
    960,    # after 7  — sixteen, and the cap
]
MAX_DELAY = float(LADDER[-1])


def next_delay(failures: int) -> float:
    """Seconds to wait before the next attempt, after `failures` in a row."""
    if failures <= 0:
        return 0.0
    if failures < len(LADDER):
        return float(LADDER[failures])
    return MAX_DELAY


def humanise(seconds: float, minutes_word: str = "min", seconds_word: str = "s") -> str:
    """A wait a person can act on. "960 s" is a number nobody can hold;
    "16 min" is a decision about whether to make tea."""
    seconds = max(0, int(round(seconds)))
    if seconds < 60:
        return f"{seconds} {seconds_word}"
    mins = seconds // 60
    rest = seconds % 60
    if rest and mins < 3:
        return f"{mins} {minutes_word} {rest} {seconds_word}"
    return f"{mins} {minutes_word}"


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
