"""Moon illumination from the mean synodic month.

Accurate to within about a day of phase, which is plenty for a nightly feature
and avoids an astronomy dependency.
"""

import numpy as np
import pandas as pd

SYNODIC_MONTH = 29.530588853  # days
NEW_MOON_EPOCH = pd.Timestamp("2000-01-06 18:14", tz="UTC")


def illumination(when: pd.Series) -> pd.Series:
    """Fraction of the moon's disc lit (0 = new, 1 = full) at each UTC time."""
    days = (when - NEW_MOON_EPOCH) / pd.Timedelta(days=1)
    phase = (days / SYNODIC_MONTH) % 1.0
    return pd.Series((1 - np.cos(2 * np.pi * phase)) / 2, index=when.index)
