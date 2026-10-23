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
```
