"""The modelling table: one row per migration-season night.

Rows cover every date in the spring (Mar-May) and fall (Aug-Nov) windows of
each year with collision records. A date with no collected birds counts as zero
only where we know McCormick Place was surveyed: 2000 onward, a light score was
recorded on every survey date, so `surveyed` is true exactly for those dates.
Before 2000 there is no effort record, so zeros there are assumptions.
"""

import pandas as pd

from bird_forecast import collisions, moon, weather

SEASON_MONTHS = {"spring": [3, 4, 5], "fall": [8, 9, 10, 11]}


def season_of(dates: pd.Series) -> pd.Series:
    month_to_season = {m: s for s, months in SEASON_MONTHS.items() for m in months}
    return dates.dt.month.map(month_to_season)


def build() -> pd.DataFrame:
    birds = collisions.load_collisions()
    counts = collisions.daily_counts(birds)
    light = collisions.load_light()

    first, last = birds["date"].dt.year.min(), birds["date"].dt.year.max()
    nights = pd.DataFrame({"date": pd.date_range(f"{first}-01-01", f"{last}-12-31")})
    nights["season"] = season_of(nights["date"])
    nights = nights.dropna(subset=["season"])

    nights = nights.merge(counts, on="date", how="left")
    nights[["mp", "chi"]] = nights[["mp", "chi"]].fillna(0).astype(int)
    nights = nights.merge(light, on="date", how="left")
    nights["surveyed"] = nights["light_score"].notna()

    nights["year"] = nights["date"].dt.year
    nights["day_of_year"] = nights["date"].dt.dayofyear
    # Moon at local midnight starting the night (05:00 UTC in CDT).
    midnight_utc = (nights["date"] + pd.Timedelta(hours=5)).dt.tz_localize("UTC")
    nights["moon_illum"] = moon.illumination(midnight_utc).to_numpy()

    wx = weather.nightly_features(weather.load_hourly(range(first - 1, last + 1)))
    nights = nights.merge(wx, on="date", how="left")

    # Tailwind for a migrant: south wind in spring, north wind in fall (m/s).
    nights["tailwind"] = nights["wind_v"].where(
        nights["season"] == "spring", -nights["wind_v"]
    )
    return nights.reset_index(drop=True)
