# Tasks

## Now — Milestone 1: data + model

- [ ] Fit negative binomial model on the analysis set (MP, 2000–2016, surveyed nights); check fit, overdispersion
- [ ] Fall signal: try wind direction (sin/cos) and a cold-front feature, since the north–south tailwind misses it
- [ ] Test interactions: tailwind × season, low clouds × big-flight nights
- [ ] Decide what to do with 1978–1999 (no survey record): leave out, or use as a sensitivity check
- [ ] Backtest on held-out years; pick Low/Moderate/High/Extreme cutoffs
- [ ] Save fitted model to `models/`

## Next — Milestone 2: daily forecast

- [ ] Fetch tonight's hourly forecast from api.weather.gov
- [ ] Map forecast fields to the model's features (note forecast vs. observed weather mismatch)
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
