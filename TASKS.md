# Tasks

## Now — Milestone 2: daily forecast

- [ ] Fetch tonight's hourly forecast from the NWS gridpoint API (temperature, pressure, skyCover, ceilingHeight, wind, quantitativePrecipitation)
- [ ] Fetch last night's observed weather (O'Hare) for the previous-night features
- [ ] Map forecast fields to the same nightly features as `weather.nightly_features` → `features.add_derived`
- [ ] Forecast with lights on (17) and off (3); risk level uses the lights-on number
- [ ] Write `site/risk.json` for tonight + next 7 nights
- [ ] Handle the off-season (no migration) gracefully

## Next — Milestone 3: website

- [ ] Tonight's risk card (level, predicted range, one-line reason)
- [ ] 7-night outlook strip
- [ ] Season curve with tonight's marker
- [ ] "Why tonight" factor breakdown

## Next — Milestone 4: automation

- [ ] GitHub Pages
- [ ] GitHub Actions daily cron to run forecast and deploy

## Later

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
