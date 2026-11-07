"""Fetch NWS weather, forecast the next 7 nights, write site/risk.json.

Each run also keeps a dated copy in site/history/ so forecasts can later be
checked against what happened.

Usage: uv run scripts/forecast.py
"""

import json

import pandas as pd

from bird_forecast import forecast, model, nws
from bird_forecast.paths import ROOT

SITE = ROOT / "site"


def season_year(now: pd.Timestamp) -> int:
    """The year whose seasons the page shows: next year's once fall is over."""
    local = now.tz_convert(nws.TZ)
    return local.year + 1 if local.month == 12 else local.year


def main() -> None:
    now = pd.Timestamp.now(tz="UTC")
    hourly, nws_updated = nws.hourly_weather(now)
    nights = forecast.forecast_nights(hourly, now)
    _, meta = model.load()

    report = {
        "generated_at": now.isoformat(timespec="seconds"),
        "nws_forecast_updated": nws_updated.isoformat(),
        "location": "McCormick Place, Chicago",
        "weather_source": f"NWS forecast grid {nws.GRIDPOINT} and observations at {nws.STATION}",
        "model": {
            "train_years": meta.train_years,
            "level_cutoffs": meta.level_cutoffs,
            "lights_on_score": forecast.LIGHTS_ON,
            "lights_off_score": forecast.LIGHTS_OFF,
        },
        "nights": nights,
        "next_season_start": forecast.next_season_start(now),
        "season_curves": {
            season: forecast.season_curve(season_year(now), season) for season in ("spring", "fall")
        },
    }
    text = json.dumps(report, indent=2) + "\n"
    (SITE / "history").mkdir(parents=True, exist_ok=True)
    (SITE / "risk.json").write_text(text)
    local_date = now.tz_convert(nws.TZ).date()
    (SITE / "history" / f"{local_date}.json").write_text(text)

    for n in nights:
        if n["in_season"]:
            print(f"Night of {n['night_of']}: {n['level']:<8} lights on {n['lights_on']['expected']:>5} "
                  f"(80% {n['lights_on']['range80']}), off {n['lights_off']['expected']:>5}  "
                  f"{n['vs_typical']}x typical  {n['weather']['wind']}  "
                  + ", ".join(f"{d['factor']} {d['effect']}x" for d in n["drivers"]))
        else:
            print(f"Night of {n['night_of']}: off-season")


if __name__ == "__main__":
    main()
