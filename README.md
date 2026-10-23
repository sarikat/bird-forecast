# Bird Forecast

A nightly forecast of bird-collision risk in Chicago during spring and fall migration.

Every afternoon it pulls tonight's weather forecast, runs it through a model trained
on decades of Chicago building-collision records, and publishes a risk level
(Low / Moderate / High / Extreme) to a static website.

## How it works

1. **Train once:** fit a count model (negative binomial) on historical nightly
   collisions from the Field Museum dataset, joined to NOAA weather and moon phase.
2. **Forecast daily:** fetch tonight's hourly forecast from the National Weather
   Service API, predict collisions, write `site/risk.json`.
3. **Publish:** a GitHub Actions cron job runs the forecast and deploys `site/`
   to GitHub Pages.

## Layout

- `src/bird_forecast/` — data loading, features, model, forecast
- `scripts/` — command-line entry points (download data, train, forecast)
- `data/` — downloaded and processed data (not committed)
- `models/` — saved fitted model
- `site/` — static web page
- `TASKS.md` — the task list

## Setup

```bash
uv sync
uv run scripts/download_weather.py   # NOAA hourly weather, 1978–2019
# Collision data: download by hand from https://doi.org/10.5061/dryad.8rr0498
# (Chicago_collision_data.csv, Light_levels_dryad.csv) into data/raw/winger2019/
uv run scripts/build_nightly.py      # one row per migration night
uv run scripts/explore.py            # exploratory figures
uv run scripts/train.py              # backtest + fit + save the model
uv run pytest
```

## Findings so far

- [First look at the data](reports/exploration.md)
- [The collision model](reports/model.md): building lights are the biggest factor (3–6×),
  then spring south winds and west winds in both seasons. On held-out years, nights rated
  High or Extreme were 20% of nights but 57% of birds.
