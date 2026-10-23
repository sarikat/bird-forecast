# Tasks

## Now — Milestone 1: data + model

- [ ] Find and download the Chicago collision dataset (Winger et al. 2019 / Weeks et al. 2020, Dryad); confirm years covered and fields
- [ ] Download matching NOAA hourly weather for Chicago (O'Hare/Midway, Integrated Surface Database)
- [ ] Compute moon phase / illumination for each night
- [ ] Build one table: one row per night, collisions + weather features
- [ ] Exploratory plots: collisions by day of year, by wind direction, by cloud cover
- [ ] Fit negative binomial model; check fit, overdispersion
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

- [ ] GitHub repo + GitHub Pages
- [ ] GitHub Actions daily cron to run forecast and deploy

## Later

- [ ] Animated wind map over the Great Lakes
- [ ] Forecast-vs-actual track record
- [ ] Email/text alerts on High/Extreme nights
- [ ] More cities via BirdCast radar data

## Done

- [x] Project scaffold (uv, git, README, task list)
