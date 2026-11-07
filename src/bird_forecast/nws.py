"""Live weather from the National Weather Service API (api.weather.gov).

Two sources, both converted to the same hourly frame as `weather.load_hourly`
so the nightly features are computed by exactly the same code as in training:

- Observations: routine hourly METAR reports from O'Hare (KORD). NWS keeps
  about 7 days, which covers the previous-night features.
- Forecast: the raw gridpoint forecast for the 2.5 km cell over O'Hare, about
  7 days ahead. Each field is a list of values with ISO 8601 "start/duration"
  validity windows, expanded here to one row per hour.

Known differences from the training data, which used observations only:
sky cover is a forecast percentage rather than METAR layer categories, and
rain comes from forecast precipitation amounts rather than gauge readings.
"""

import json
import urllib.request

import numpy as np
import pandas as pd

from bird_forecast.weather import HOURLY_COLUMNS, TZ, wind_components

API = "https://api.weather.gov"
# NWS asks automated clients to identify themselves in the User-Agent.
USER_AGENT = "bird-forecast (github.com/sarikat/bird-forecast)"
STATION = "KORD"
GRIDPOINT = "LOT/66,77"  # the forecast cell containing O'Hare
ROUTINE_MINUTE = 51  # O'Hare's hourly METAR goes out at :51; the rest are 5-minute obs
MEASURABLE_PRECIP_MM = 0.25  # forecast amounts below 0.01 in count as dry
OBS_CHUNK = pd.Timedelta(days=2)  # the API returns at most ~500 observations

# Total sky cover implied by each METAR cloud layer, in eighths, matching how
# ISD encodes METAR reports in the training data.
LAYER_OKTAS = {"SKC": 0, "CLR": 0, "NSC": 0, "FEW": 2, "SCT": 4, "BKN": 7, "OVC": 8, "VV": 8}


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _value(prop: dict | None) -> float:
    if not prop or prop.get("value") is None:
        return np.nan
    return float(prop["value"])


def observation_rows(features: list[dict]) -> pd.DataFrame:
    """Hourly frame from /stations/{id}/observations features (routine reports only)."""
    rows = []
    for feature in features:
        p = feature["properties"]
        time = pd.Timestamp(p["timestamp"]).tz_convert(TZ)
        if time.minute != ROUTINE_MINUTE:
            continue
        speed = _value(p.get("windSpeed")) / 3.6  # km/h -> m/s
        from_deg = _value(p.get("windDirection"))
        if speed == 0:
            u = v = 0.0
        else:  # NaN direction (variable wind) leaves the components missing, as in ISD
            u, v = wind_components(speed, from_deg)
        layers = p.get("cloudLayers") or []
        oktas = max((LAYER_OKTAS.get(layer["amount"], np.nan) for layer in layers), default=np.nan)
        # precipitationLastHour is omitted or null when it isn't raining.
        precip = _value(p.get("precipitationLastHour"))
        rows.append({
            "time": time, "wind_u": u, "wind_v": v, "wind_speed": speed,
            "temp_c": _value(p.get("temperature")),
            "dewpoint_c": _value(p.get("dewpoint")),
            "pressure_hpa": _value(p.get("seaLevelPressure")) / 100,
            "precip_mm": 0.0 if np.isnan(precip) else precip,
            "sky_cover": oktas / 8,
        })
    frame = pd.DataFrame(rows, columns=["time", *HOURLY_COLUMNS])
    return frame.drop_duplicates("time").set_index("time").sort_index()


def fetch_observations(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    features = []
    chunk_start = start
    while chunk_start < end:
        chunk_end = min(chunk_start + OBS_CHUNK, end)
        url = (f"{API}/stations/{STATION}/observations"
               f"?start={chunk_start.tz_convert('UTC'):%Y-%m-%dT%H:%M:%SZ}"
               f"&end={chunk_end.tz_convert('UTC'):%Y-%m-%dT%H:%M:%SZ}")
        features += _get(url)["features"]
        chunk_start = chunk_end
    return observation_rows(features)


def _expand(values: list[dict]) -> pd.Series:
    """One value per hour from gridpoint values valid over "start/duration" windows."""
    out = {}
    for item in values:
        start, duration = item["validTime"].split("/")
        hours = int(pd.Timedelta(duration) / pd.Timedelta(hours=1))
        for h in pd.date_range(pd.Timestamp(start), periods=hours, freq="h"):
            out[h] = item["value"]
    return pd.Series(out, dtype=float).sort_index()


def gridpoint_rows(props: dict) -> pd.DataFrame:
    """Hourly frame from a /gridpoints/{wfo}/{x},{y} response's properties."""
    speed = _expand(props["windSpeed"]["values"]) / 3.6  # km/h -> m/s
    from_deg = _expand(props["windDirection"]["values"])
    u, v = wind_components(speed, from_deg)

    # Precipitation comes as amounts over (usually 6-hour) blocks: drop
    # sub-measurable blocks, then spread each amount evenly over its hours.
    precip = {}
    for item in props["quantitativePrecipitation"]["values"]:
        start, duration = item["validTime"].split("/")
        hours = int(pd.Timedelta(duration) / pd.Timedelta(hours=1))
        amount = item["value"] or 0.0
        per_hour = amount / hours if amount >= MEASURABLE_PRECIP_MM else 0.0
        for h in pd.date_range(pd.Timestamp(start), periods=hours, freq="h"):
            precip[h] = per_hour

    frame = pd.DataFrame({
        "wind_u": u, "wind_v": v, "wind_speed": speed,
        "temp_c": _expand(props["temperature"]["values"]),
        "dewpoint_c": _expand(props["dewpoint"]["values"]),
        "precip_mm": pd.Series(precip, dtype=float),
        "sky_cover": _expand(props["skyCover"]["values"]) / 100,
    })
    frame = frame.reindex(columns=HOURLY_COLUMNS)
    # An empty field (no values) leaves a plain Index; coerce back to times.
    frame.index = pd.DatetimeIndex(frame.index).tz_convert(TZ)
    frame.index.name = "time"
    return frame.sort_index()


def fetch_forecast() -> tuple[pd.DataFrame, pd.Timestamp]:
    """Hourly forecast frame and the time NWS last updated it."""
    props = _get(f"{API}/gridpoints/{GRIDPOINT}")["properties"]
    return gridpoint_rows(props), pd.Timestamp(props["updateTime"])


def hourly_weather(now: pd.Timestamp, history: pd.Timedelta = pd.Timedelta(days=7)) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Observed weather up to now, then forecast weather after it."""
    observed = fetch_observations(now - history, now)
    forecast, updated = fetch_forecast()
    last_obs = observed.index.max() if len(observed) else now - history
    combined = pd.concat([observed, forecast[forecast.index > last_obs]])
    return combined, updated
