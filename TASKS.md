# Tasks

## Now — Milestone 3: website

- [ ] Tonight's risk card (level, predicted range, one-line reason)
- [ ] 7-night outlook strip
- [ ] Season curve with tonight's marker
- [ ] "Why tonight" factor breakdown

## Next — Milestone 4: automation

- [ ] GitHub Pages
- [ ] GitHub Actions daily cron to run forecast and deploy

## Later

- [ ] Track record: score each `site/history/` forecast against what happened (needs a source of live collision counts, e.g. Chicago Bird Collision Monitors)
- [ ] Use NWS probabilityOfPrecipitation for nights beyond the ~3-day rain-amount horizon
- [ ] Upstream weather (e.g. St. Louis / Indianapolis in spring, Minneapolis / Green Bay in fall) as extra features
- [ ] Sensitivity check using 1978–1999 (no survey-effort record)
- [ ] Recalibrate the top end: the riskiest 10% of nights are over-predicted (16.1 forecast vs. 12.6 observed)
- [ ] Animated wind map over the Great Lakes
- [ ] Forecast-vs-actual track record
- [ ] Email/text alerts on High/Extreme nights
- [ ] More cities via BirdCast radar data

## Done

- [x] Project scaffold (uv, git, README, task list)
- [x] Public GitHub repo: https://github.com/sarikat/bird-forecast
- [x] Download O'Hare hourly weather 1978–2019 (`scripts/download_weather.py`)
- [x] Download collision + light-score data (Dryad, manual) into `data/raw/winger2019/`
- [x] Inspect collision data: 1978–2016, MP vs. CHI; CHI effort jumps after 2005, so model MP only
- [x] Light scores: date alignment checked; light-score dates = survey nights (2000+)
- [x] Parse NOAA weather into nightly features; compute moon illumination
- [x] Build nightly table (`scripts/build_nightly.py` → `data/processed/nightly.csv`)
- [x] Exploratory plots + findings (`scripts/explore.py`, `reports/exploration.md`)
- [x] Negative binomial model with season-specific lights, weather and previous-night effects (`src/bird_forecast/model.py`)
- [x] Leave-one-year-out backtest; risk levels at 50th/80th/95th percentiles (`scripts/train.py`, `reports/model.md`)
- [x] Saved model (`models/collision_model.pkl` + `.json`) — formula + coefficients only
- [x] Dropped pressure change + low ceiling (not in the NWS Chicago grid; no backtest loss)
- [x] Live weather from NWS: O'Hare hourly observations + gridpoint forecast (`src/bird_forecast/nws.py`)
- [x] Nightly forecast, lights on vs. off, with drivers vs. a typical night (`src/bird_forecast/forecast.py`)
- [x] `scripts/forecast.py` → `site/risk.json` (+ dated copy in `site/history/`); off-season nights flagged
