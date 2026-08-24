"""HOW LONG THE NEXT TRANSCRIPTION WILL TAKE.

Baba, 24.8.2026: "statistically calculate, after a few sendings, how much
time it needs to transcribe, so from file to file the ETA is more
precise."

THE MODEL, and why it is this one. Transcription time is close to
proportional to audio length — a two-minute take costs roughly twice a
one-minute take on the same engine. So the thing worth remembering is not
a duration but a RATIO: wall seconds per audio second. Store the ratios,
take their MEDIAN, multiply by the length of the take about to be sent.

WHY THE MEDIAN AND NOT THE MEAN. One take that hit a rate limit and
retried for ninety seconds is not a fact about how fast the engine is,
but a mean would carry that limp into every later estimate. The median
ignores it. This is the whole reason the estimate improves rather than
drifting: outliers are the normal case here, not the exception.

WHY PER ENGINE. Groq and AssemblyAI are not the same speed and never
will be. Mixing their samples produces an estimate that is wrong for
both. Every sample carries its engine and the estimate asks for one.

WHAT THIS IS NOT. It is not a promise and it is never on the critical
path. No estimate, no problem — the caller shows the spinner without a
time. An estimator that can fail a transcription is a worse thing than
no estimator.
"""

# Below this many samples, an estimate says more about luck than about
# the engine. Three is the smallest number where a median means anything
# at all (it can ignore one outlier), and Baba asked for "after a few".
MIN_SAMPLES = 3

# Sanity rails on a single sample. A ratio outside these did not measure
# transcription — it measured a stall, a retry storm, or a clock that
# moved. Kept out of the history entirely rather than trusted to the
# median, because enough of them would BECOME the median.
MIN_RATIO = 0.005      # 200x faster than realtime; nothing is
MAX_RATIO = 20.0       # 20x slower than realtime; that is a failure


def usable(sample: dict) -> bool:
    """Is this sample a measurement of transcription, or of a stall?"""
    try:
        audio = float(sample.get("audio_s") or 0)
        wall = float(sample.get("wall_s") or 0)
    except (TypeError, ValueError):
        return False
    if audio <= 0 or wall <= 0:
        return False
    return MIN_RATIO <= (wall / audio) <= MAX_RATIO


def median(values):
    """The middle value. Returns None for an empty list rather than
    raising — every caller here would have to guard it otherwise."""
    xs = sorted(values)
    n = len(xs)
    if n == 0:
        return None
    mid = n // 2
    if n % 2:
        return xs[mid]
    return (xs[mid - 1] + xs[mid]) / 2.0


def ratio_for(samples, engine: str = ""):
    """Median wall-seconds-per-audio-second, or None when it cannot be
    known yet. `engine` filters; empty means every engine."""
    good = [float(s["wall_s"]) / float(s["audio_s"])
            for s in (samples or [])
            if usable(s) and (not engine or s.get("engine") == engine)]
    if len(good) < MIN_SAMPLES:
        return None
    return median(good)


def estimate(samples, audio_seconds: float, engine: str = ""):
    """Seconds the next transcription will probably take. None when
    there is not enough history, which the caller must handle."""
    try:
        audio = float(audio_seconds)
    except (TypeError, ValueError):
        return None
    if audio <= 0:
        return None
    r = ratio_for(samples, engine)
    if r is None:
        return None
    return r * audio


def spread(samples, engine: str = ""):
    """How much the samples disagree, as (fastest, slowest) ratio over
    the middle half. The caller may use it to decide whether to show a
    single number or a range; a wide spread means the estimate is a
    guess wearing a number's clothes."""
    good = sorted(float(s["wall_s"]) / float(s["audio_s"])
                  for s in (samples or [])
                  if usable(s) and (not engine or s.get("engine") == engine))
    if len(good) < MIN_SAMPLES:
        return None
    lo = good[len(good) // 4]
    hi = good[(3 * len(good)) // 4]
    return (lo, hi)


def human(seconds) -> str:
    """A duration a person reads at a glance. Never 'in 143 seconds'."""
    if seconds is None:
        return ""
    s = int(round(float(seconds)))
    if s < 5:
        return "a few seconds"
    if s < 60:
        # Rounded to five, because a one-second-precise estimate claims a
        # precision this method does not have.
        return "~%ds" % (max(5, int(round(s / 5.0) * 5)))
    m, rest = divmod(s, 60)
    if m < 10:
        return "~%dm %ds" % (m, int(round(rest / 10.0) * 10)) if rest >= 10 \
            else "~%dm" % m
    return "~%dm" % m
