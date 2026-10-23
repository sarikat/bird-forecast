import pandas as pd
import pytest

from bird_forecast import features


def nights(start: str, wind_v: list[float], rain_hours: list[float] | None = None) -> pd.DataFrame:
    n = len(wind_v)
    return pd.DataFrame({
        "date": pd.date_range(start, periods=n),
        "wind_v": wind_v,
        "rain_hours": rain_hours or [0.0] * n,
        "temp_change_24h": [0.0] * n,
    })


def test_tailwind_sign_flips_by_season():
    spring = features.add_derived(nights("2010-05-01", [3.0, 3.0]))
    fall = features.add_derived(nights("2010-10-01", [3.0, 3.0]))
    assert spring["tailwind"].tolist() == [3.0, 3.0]  # south wind helps in spring
    assert fall["tailwind"].tolist() == [-3.0, -3.0]  # and hinders in fall


def test_previous_night_uses_tonights_season():
    # Aug 1 is fall, Jul 31 isn't a season night, but last night's south wind
    # is still a headwind for a fall migrant leaving on Aug 1.
    wx = features.add_derived(nights("2010-07-31", [4.0, 0.0]))
    assert wx.loc[1, "tailwind_prev"] == -4.0


def test_nights_since_good_counts_and_caps():
    good, bad = 3.0, 0.0
    wx = features.add_derived(nights("2010-04-01", [good, bad, bad, good, bad] + [bad] * 8))
    assert wx["nights_since_good"].tolist()[:6] == [7, 0, 1, 2, 0, 1]
    assert wx["nights_since_good"].max() == features.NIGHTS_SINCE_CAP


def test_rain_prev_is_missing_on_first_night():
    wx = features.add_derived(nights("2010-04-01", [0.0, 0.0], rain_hours=[2.0, 0.0]))
    assert pd.isna(wx.loc[0, "rain_prev"]) and wx.loc[1, "rain_prev"] == 1.0


def test_rejects_gaps_in_dates():
    wx = nights("2010-04-01", [0.0, 0.0, 0.0]).drop(index=1)
    with pytest.raises(ValueError):
        features.add_derived(wx)
