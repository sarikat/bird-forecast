"""Turn hourly weather (observed + forecast) into nightly collision forecasts.

Each night is forecast twice, with McCormick Place fully lit and mostly dark;
the risk level is the lights-on one ("how bad tonight is if the lights stay
on"). Each forecast is explained by comparing it with a typical night for the
same date: swap one group of weather inputs back to its typical value and see
how much the forecast moves.
"""

import numpy as np
import pandas as pd

from bird_forecast import features, model, weather
from bird_forecast.nightly import moon_at_night

LIGHTS_ON, LIGHTS_OFF = 17, 3  # the range of McCormick Place light scores
MIN_NIGHT_HOURS = 10  # of the 12 hours from 19:00 to 07:00
DRIVER_THRESHOLD = 1.25  # report a factor if it moves the forecast by at least this ratio

DRIVER_GROUPS = {
    "wind": ["wind_u", "wind_v", "wind_speed"],
    "temperature": ["temp_evening_c", "temp_change_24h"],
    "clouds and rain": ["sky_cover", "any_rain"],
    "moon": ["moon_illum"],
    "recent nights": ["tailwind_prev", "rain_prev", "temp_change_prev", "nights_since_good"],
}
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def first_night(now: pd.Timestamp) -> pd.Timestamp:
    """Morning date of the next night to forecast: tonight, or the night in
    progress if it's between 19:00 and 07:00."""
    local = now.tz_convert(weather.TZ)
    return (local - pd.Timedelta(hours=weather.NIGHT_END_HOUR)).tz_localize(None).normalize() + pd.Timedelta(days=1)


def nightly_inputs(hourly: pd.DataFrame) -> pd.DataFrame:
    """Model inputs for every night the hourly weather covers."""
    nights = features.add_derived(weather.nightly_features(hourly))
    nights["moon_illum"] = moon_at_night(nights["date"])
    nights["complete"] = (nights["n_obs"] >= MIN_NIGHT_HOURS) & nights["temp_evening_c"].notna()
    return nights


def wind_label(u: float, v: float, speed: float) -> str:
    if speed < 1 or np.hypot(u, v) < 0.5:
        return "light and variable"
    from_deg = np.rad2deg(np.arctan2(-u, -v)) % 360
    return f"{COMPASS[int((from_deg + 22.5) // 45) % 8]} at {speed:.0f} m/s"


def drivers(fitted: model.FittedModel, night: pd.DataFrame, typical: dict[str, float]) -> list[dict]:
    mu = float(fitted.predict(night).iloc[0])
    out = []
    for group, columns in DRIVER_GROUPS.items():
        swapped = night.assign(**{c: typical[c] for c in columns})
        ratio = mu / float(fitted.predict(swapped).iloc[0])
        if ratio >= DRIVER_THRESHOLD or ratio <= 1 / DRIVER_THRESHOLD:
            out.append({"factor": group, "effect": round(ratio, 2)})
    return sorted(out, key=lambda d: -abs(np.log(d["effect"])))


def forecast_nights(hourly: pd.DataFrame, now: pd.Timestamp, n_nights: int = 7) -> list[dict]:
    fitted, meta = model.load()
    nights = nightly_inputs(hourly)
    start = first_night(now)
    nights = nights[(nights["date"] >= start) & nights["complete"]].head(n_nights)

    results = []
    for _, row in nights.iterrows():
        night = row.to_frame().T.infer_objects()
        evening = row["date"] - pd.Timedelta(days=1)
        entry = {
            "night_of": f"{evening:%Y-%m-%d}",
            "morning": f"{row['date']:%Y-%m-%d}",
            "season": row["season"] if isinstance(row["season"], str) else None,
            "weather": {
                "wind": wind_label(row["wind_u"], row["wind_v"], row["wind_speed"]),
                "wind_speed_ms": round(row["wind_speed"], 1),
                "temp_evening_c": round(row["temp_evening_c"], 1),
                "temp_change_c": None if pd.isna(row["temp_change_24h"]) else round(row["temp_change_24h"], 1),
                "sky_cover_pct": None if pd.isna(row["sky_cover"]) else round(100 * row["sky_cover"]),
                # NWS forecasts precipitation amounts only ~3 days out; beyond
                # that the model treats the night as dry, and we say "unknown".
                "rain": None if pd.isna(row["precip_mm"]) else bool(row["any_rain"]),
                "moon_pct": round(100 * row["moon_illum"]),
            },
        }
        if entry["season"] is None:
            entry["in_season"] = False
            results.append(entry)
            continue

        on = night.assign(light_score=LIGHTS_ON)
        off = night.assign(light_score=LIGHTS_OFF)
        mu_on = float(fitted.predict(on).iloc[0])
        mu_off = float(fitted.predict(off).iloc[0])
        typical = meta.typical[entry["season"]]
        mu_typical = float(fitted.predict(on.assign(**typical)).iloc[0])
        lo, hi = model.predictive_quantiles(np.array([mu_on]), meta.alpha, [0.1, 0.9])[0]
        entry.update({
            "in_season": True,
            "level": str(model.level_of(np.array([mu_on]), meta.level_cutoffs)[0]),
            "lights_on": {"expected": round(mu_on, 1), "range80": [int(lo), int(hi)]},
            "lights_off": {
                "expected": round(mu_off, 1),
                "level": str(model.level_of(np.array([mu_off]), meta.level_cutoffs)[0]),
            },
            "typical_for_date": round(mu_typical, 1),
            "vs_typical": round(mu_on / mu_typical, 2),
            "drivers": drivers(fitted, on, typical),
        })
        results.append(entry)
    return results
