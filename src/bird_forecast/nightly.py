"""The modelling table: one row per migration-season night.

Rows cover every date in the spring (Mar-May) and fall (Aug-Nov) windows of
each year with collision records. A date with no collected birds counts as zero
only where we know McCormick Place was surveyed: 2000 onward, a light score was
recorded on every survey date, so `surveyed` is true exactly for those dates.
Before 2000 there is no effort record, so zeros there are assumptions.
"""

import pandas as pd

from bird_forecast import collisions, features, moon, weather


def build() -> pd.DataFrame:
    birds = collisions.load_collisions()
    counts = collisions.daily_counts(birds)
    light = collisions.load_light()

    first, last = birds["date"].dt.year.min(), birds["date"].dt.year.max()
    wx = weather.nightly_features(weather.load_hourly(range(first - 1, last + 1)))
    wx = features.add_derived(wx)
    nights = wx[wx["date"].dt.year.between(first, last)].dropna(subset=["season"])

    nights = nights.merge(counts, on="date", how="left")
    nights[["mp", "chi"]] = nights[["mp", "chi"]].fillna(0).astype(int)
    nights = nights.merge(light, on="date", how="left")
    nights["surveyed"] = nights["light_score"].notna()

    nights["year"] = nights["date"].dt.year
    nights["day_of_year"] = nights["date"].dt.dayofyear
    nights["moon_illum"] = moon_at_night(nights["date"])
    return nights.reset_index(drop=True)


def moon_at_night(dates: pd.Series) -> pd.Series:
    """Moon illumination at local midnight starting the night (05:00 UTC in CDT)."""
    midnight_utc = (dates + pd.Timedelta(hours=5)).dt.tz_localize("UTC")
    return moon.illumination(midnight_utc).to_numpy()
