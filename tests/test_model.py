import numpy as np
import pandas as pd
import pytest

from bird_forecast import model
from bird_forecast.paths import NIGHTLY_CSV

needs_data = pytest.mark.skipif(not NIGHTLY_CSV.exists(), reason="run scripts/build_nightly.py first")


def test_level_of_uses_cutoffs_as_lower_bounds():
    levels = model.level_of(np.array([0.5, 2.0, 5.0, 9.9, 10.0, 50.0]), [2.0, 5.0, 10.0])
    assert levels.tolist() == ["Low", "Moderate", "High", "High", "Extreme", "Extreme"]


def test_prepare_clamps_year_to_training_range():
    nights = pd.DataFrame({"date": pd.to_datetime(["1990-05-01", "2008-05-01", "2026-05-01"]),
                           "season": "spring"})
    assert model.prepare(nights)["year_c"].tolist() == [-8, 0, 8]


def test_season_day_closes_the_summer_gap():
    nights = pd.DataFrame({
        "date": pd.to_datetime(["2010-03-01", "2010-05-31", "2010-08-01", "2010-11-30"]),
        "season": ["spring", "spring", "fall", "fall"],
    })
    days = model.prepare(nights)["season_day"].tolist()
    assert days == [0, 91, 100, 221]
    assert all(model.SEASON_DAY_BOUNDS[0] < d < model.SEASON_DAY_BOUNDS[1] for d in days)


def test_predictive_quantiles_widen_with_mean():
    q = model.predictive_quantiles(np.array([1.0, 10.0]), alpha=1.0, q=[0.1, 0.9])
    assert (q[1] >= q[0]).all() and q[1, 1] > q[0, 1]


@needs_data
def test_fitted_model_matches_statsmodels(tmp_path, monkeypatch):
    data = model.analysis_set(pd.read_csv(NIGHTLY_CSV, parse_dates=["date"]))
    res = model.fit(data)
    monkeypatch.setattr(model, "MODEL_PKL", tmp_path / "m.pkl")
    monkeypatch.setattr(model, "MODEL_META", tmp_path / "m.json")
    meta = model.ModelMeta(model.FORMULA, model.TRAIN_YEARS, len(data), 1.0, [1, 2, 3], (3, 17), {})
    model.save(res, meta)
    fitted, _ = model.load(tmp_path / "m.pkl")
    sample = data.sample(50, random_state=0)
    np.testing.assert_allclose(fitted.predict(sample), res.predict(sample), rtol=1e-10)
