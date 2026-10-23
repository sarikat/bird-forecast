"""Historical hourly weather at O'Hare (NOAA ISD) -> one row of features per night.

ISD packs each measurement into a comma-separated field with quality codes and
sentinel values for "missing"; see the ISD format document
(https://www.ncei.noaa.gov/data/global-hourly/doc/isd-format-document.pdf).
Only the routine hourly reports are used: SAO before mid-1996, METAR (FM-15)
after. They are the only report types with consistent 1-hour precipitation
and sky cover across the whole record.
"""

import numpy as np
import pandas as pd

from bird_forecast.paths import WEATHER_DIR

TZ = "America/Chicago"
ROUTINE_REPORTS = {"SAO", "FM-15"}
BAD_QC = {"2", "3", "6", "7"}  # suspect or erroneous

# A night runs from 19:00 local on the evening before to 07:00 on the date the
# birds were collected; shifting local time forward 5 hours puts the whole
# window on that collection date.
NIGHT_START_HOUR = 19
NIGHT_END_HOUR = 7
NIGHT_SHIFT = pd.Timedelta(hours=24 - NIGHT_START_HOUR)


def _part(field: pd.Series, i: int) -> pd.Series:
    return field.str.split(",", expand=True)[i]


def _value(field: pd.Series, i: int, qc_i: int, missing: str, scale: float = 1.0) -> pd.Series:
    """Numeric part i of an ISD field, NaN where missing or flagged bad by qc part qc_i."""
    value = _part(field, i)
    bad = value.isna() | (value.str.lstrip("+") == missing) | _part(field, qc_i).isin(BAD_QC)
    return pd.to_numeric(value, errors="coerce").where(~bad) / scale


def load_hourly(years: range | None = None) -> pd.DataFrame:
    """Parsed routine hourly observations with a local-time index."""
    files = sorted(WEATHER_DIR.glob("ORD_*.csv"))
    if years is not None:
        files = [f for f in files if int(f.stem.split("_")[1]) in years]
    raw = pd.concat((pd.read_csv(f, dtype=str) for f in files), ignore_index=True)
    raw = raw[raw["REPORT_TYPE"].str.strip().isin(ROUTINE_REPORTS)].copy()

    out = pd.DataFrame(index=raw.index)
    out["time"] = pd.to_datetime(raw["DATE"], utc=True).dt.tz_convert(TZ)

    # Wind: direction the wind blows FROM (degrees), speed in m/s. Calm = 0.
    wind_dir = _value(raw["WND"], 0, 1, "999")
    wind_speed = _value(raw["WND"], 3, 4, "9999", scale=10)
    calm = _part(raw["WND"], 2) == "C"
    wind_speed = wind_speed.mask(calm, 0.0)
    theta = np.deg2rad(wind_dir)
    # Components of where the air is going: v > 0 is a south wind (blowing north).
    out["wind_u"] = (-wind_speed * np.sin(theta)).mask(calm, 0.0)
    out["wind_v"] = (-wind_speed * np.cos(theta)).mask(calm, 0.0)
    out["wind_speed"] = wind_speed

    out["ceiling_m"] = _value(raw["CIG"], 0, 1, "99999")  # 22000 = unlimited
    out["visibility_km"] = _value(raw["VIS"], 0, 1, "999999", scale=1000)
    out["temp_c"] = _value(raw["TMP"], 0, 1, "9999", scale=10)
    out["dewpoint_c"] = _value(raw["DEW"], 0, 1, "9999", scale=10)
    out["pressure_hpa"] = _value(raw["SLP"], 0, 1, "99999", scale=10)

    # Precipitation: only 1-hour accumulations, so nothing is double counted.
    precip = _value(raw["AA1"].fillna("99,9999,9,9"), 1, 3, "9999", scale=10)
    one_hour = _part(raw["AA1"].fillna("99,9999,9,9"), 0) == "01"
    out["precip_mm"] = precip.where(one_hour)

    # Total sky cover in oktas (0-8); 9/10 mean sky obscured, i.e. fully covered.
    oktas = _value(raw["GF1"].fillna("99,99,9"), 0, 2, "99")
    out["sky_cover"] = oktas.clip(upper=8) / 8

    return out.set_index("time").sort_index()


def nightly_features(hourly: pd.DataFrame) -> pd.DataFrame:
    """One row per night, keyed by the date the night ended (collection date)."""
    hour = hourly.index.hour
    night = hourly[(hour >= NIGHT_START_HOUR) | (hour < NIGHT_END_HOUR)].copy()
    night["date"] = (night.index + NIGHT_SHIFT).tz_localize(None).normalize()
    g = night.groupby("date")

    feats = pd.DataFrame({
        "n_obs": g.size(),
        "wind_u": g["wind_u"].mean(),
        "wind_v": g["wind_v"].mean(),
        "wind_speed": g["wind_speed"].mean(),
        "sky_cover": g["sky_cover"].mean(),
        "low_ceiling_frac": g["ceiling_m"].agg(lambda s: (s.dropna() < 1000).mean()),
        "visibility_min_km": g["visibility_km"].min(),
        "precip_mm": g["precip_mm"].sum(min_count=1),
        "rain_hours": g["precip_mm"].agg(lambda s: (s > 0).sum()),
    })
    # Wind direction (from), for plotting; NaN when the mean wind is near calm.
    mean_speed = np.hypot(feats["wind_u"], feats["wind_v"])
    feats["wind_from_deg"] = (
        np.rad2deg(np.arctan2(-feats["wind_u"], -feats["wind_v"])) % 360
    ).where(mean_speed > 0.5)

    # Evening conditions (19-22h local) and their change from the previous
    # evening: fronts show up as sharp temperature and pressure changes.
    evening = night[night.index.hour.isin(range(NIGHT_START_HOUR, 23))]
    eg = evening.groupby("date")
    feats["temp_evening_c"] = eg["temp_c"].mean()
    feats["pressure_evening_hpa"] = eg["pressure_hpa"].mean()
    feats = feats.asfreq("D")
    feats["temp_change_24h"] = feats["temp_evening_c"].diff()
    feats["pressure_change_24h"] = feats["pressure_evening_hpa"].diff()
    feats = feats.dropna(subset=["n_obs"])
    feats.index.name = "date"
    return feats.reset_index()
