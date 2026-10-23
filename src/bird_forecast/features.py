"""Derived nightly features, shared by model training and the live forecast.

Input is a frame of raw nightly weather (one row per consecutive date, as from
`weather.nightly_features`); lagged features need the nights before each row,
so pass the full run of nights, not just migration-season ones.
"""

import numpy as np
import pandas as pd

SEASON_MONTHS = {"spring": [3, 4, 5], "fall": [8, 9, 10, 11]}
GOOD_TAILWIND = 2.0  # m/s; a night birds would want to fly
NIGHTS_SINCE_CAP = 7


def season_of(dates: pd.Series) -> pd.Series:
    month_to_season = {m: s for s, months in SEASON_MONTHS.items() for m in months}
    return dates.dt.month.map(month_to_season)


def add_derived(wx: pd.DataFrame) -> pd.DataFrame:
    wx = wx.sort_values("date").reset_index(drop=True)
    if not wx["date"].diff().dropna().eq(pd.Timedelta(days=1)).all():
        raise ValueError("nights must be consecutive dates")
    wx = wx.assign(season=season_of(wx["date"]))

    # Tailwind for a migrant: south wind in spring, north wind in fall (m/s).
    # Outside the seasons the sign doesn't matter; use the spring convention.
    sign = np.where(wx["season"] == "fall", -1.0, 1.0)
    wx["tailwind"] = sign * wx["wind_v"]
    # Last night's conditions, judged by tonight's season (birds grounded by
    # a headwind or rain last night may all go tonight).
    wx["tailwind_prev"] = sign * wx["wind_v"].shift(1)
    wx["rain_prev"] = (wx["rain_hours"].shift(1) > 0).astype(float).where(wx["rain_hours"].shift(1).notna())
    wx["temp_change_prev"] = wx["temp_change_24h"].shift(1)
    wx["any_rain"] = (wx["rain_hours"] > 0).astype(float)

    # Nights since the last good flying night, capped: a backlog of birds
    # waiting for favourable winds.
    good = (wx["tailwind"] > GOOD_TAILWIND).to_numpy()
    since = np.empty(len(wx))
    count = NIGHTS_SINCE_CAP
    for i, is_good in enumerate(good):
        since[i] = min(count, NIGHTS_SINCE_CAP)
        count = 0 if is_good else count + 1
    wx["nights_since_good"] = since
    return wx
