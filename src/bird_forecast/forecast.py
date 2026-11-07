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


def driver_detail(group: str, row: pd.Series) -> str:
    """What tonight's inputs for a driver group actually are, in plain words."""
    if group == "wind":
        return wind_label(row["wind_u"], row["wind_v"], row["wind_speed"])
    if group == "temperature":
        change = row["temp_change_24h"]
        trend = "" if pd.isna(change) else f", {change:+.0f} °C vs. last evening"
        return f"{row['temp_evening_c']:.0f} °C in the evening{trend}"
    if group == "clouds and rain":
        sky = "" if pd.isna(row["sky_cover"]) else f"{100 * row['sky_cover']:.0f}% cloud"
        rain = "rain unknown" if pd.isna(row["precip_mm"]) else ("rain" if row["any_rain"] else "dry")
        return ", ".join(s for s in (sky, rain) if s)
    if group == "moon":
        return f"{100 * row['moon_illum']:.0f}% lit"
    since = int(row["nights_since_good"])
    if since == 0:
        return "last night was a good flying night"
    if since >= features.NIGHTS_SINCE_CAP:
        return f"no good flying night in {since}+ nights"
    return f"{since} night{'s' if since > 1 else ''} since a good flying night"


def drivers(fitted: model.FittedModel, night: pd.DataFrame, typical: pd.DataFrame) -> list[dict]:
    """Every driver group's effect on tonight vs. a typical night for the date
    (`typical`: the same night with typical weather), biggest first."""
    mu = float(fitted.predict(night).iloc[0])
    row = night.iloc[0]
    out = []
    for group, columns in DRIVER_GROUPS.items():
        swapped = night.assign(**{c: typical[c].to_numpy() for c in columns})
        ratio = mu / float(fitted.predict(swapped).iloc[0])
        out.append({
            "factor": group,
            "effect": round(ratio, 2),
            "detail": driver_detail(group, row),
            "notable": bool(ratio >= DRIVER_THRESHOLD or ratio <= 1 / DRIVER_THRESHOLD),
        })
    return sorted(out, key=lambda d: -abs(np.log(d["effect"])))


def headline(entry: dict) -> str:
    notable = [d for d in entry["drivers"] if d["notable"]][:2]
    if not notable:
        return "Close to a typical night for this date."
    parts = []
    for d in notable:
        change = "raises risk" if d["effect"] > 1 else "lowers risk to"
        parts.append(f"{d['factor'].capitalize()} ({d['detail']}) {change} {d['effect']:.1f}×")
    return "; ".join(parts) + "."


def next_season_start(now: pd.Timestamp) -> str | None:
    """First night of the next season the model covers, or None if tonight is in one."""
    _, meta = model.load()
    start = first_night(now)
    dates = pd.date_range(start, periods=366)
    nights = pd.DataFrame({"date": dates, "season": features.season_of(pd.Series(dates))})
    ok = nights["season"].notna()
    ok[ok] = model.covered(meta, nights[ok])
    first = dates[ok.to_numpy().argmax()]
    return None if first == start else f"{first:%Y-%m-%d}"


def season_curve(year: int, season: str) -> list[dict]:
    """Expected birds on a typical-weather night with lights on, for every
    night of one season: the backdrop the forecast nights are drawn against."""
    fitted, meta = model.load()
    months = features.SEASON_MONTHS[season]
    dates = pd.date_range(f"{year}-{months[0]:02d}-01", pd.Timestamp(f"{year}-{months[-1]:02d}-01") + pd.offsets.MonthEnd(1))
    nights = pd.DataFrame({"date": dates, "season": season, "light_score": LIGHTS_ON})
    nights = nights[model.covered(meta, nights)]
    dates = nights["date"]
    mu = fitted.predict(model.typical_for(meta, nights)).to_numpy()
    return [{"morning": f"{d:%Y-%m-%d}", "typical": round(float(m), 2)} for d, m in zip(dates, mu)]


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
        if entry["season"] is None or not model.covered(meta, night).iloc[0]:
            entry["in_season"] = False
            results.append(entry)
            continue

        on = night.assign(light_score=LIGHTS_ON)
        off = night.assign(light_score=LIGHTS_OFF)
        mu_on = float(fitted.predict(on).iloc[0])
        mu_off = float(fitted.predict(off).iloc[0])
        typical = model.typical_for(meta, on)
        mu_typical = float(fitted.predict(typical).iloc[0])
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
        entry["headline"] = headline(entry)
        results.append(entry)
    return results
