"""Negative binomial model of nightly collisions at McCormick Place.

The expected count is a product of a seasonal calendar curve, the building's
lights, and the night's weather, each allowed to act differently in spring and
fall. Counts are far more variable than Poisson (variance ~17x the mean), so
the NB2 dispersion `alpha` is estimated alongside the coefficients.

Every predictor must be available at forecast time from the NWS forecast for
tonight plus observed weather for last night; see features.py.
"""

import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from patsy import dmatrix
from scipy import stats

from bird_forecast.paths import ROOT

MODEL_PKL = ROOT / "models" / "collision_model.pkl"
MODEL_META = ROOT / "models" / "collision_model.json"

TRAIN_YEARS = (2000, 2016)

# The formula is fully self-describing (fixed knots, fixed categories), so the
# saved model is just this string plus coefficients, and patsy rebuilds the
# exact same design matrix for any new night.
SEASON = 'C(season, levels=["fall", "spring"])'
# Seasonal curve: a spline over "season day", which counts from Mar 1 through
# spring, then resumes at Aug 1 after a one-week gap. Using day of year
# instead would leave a 2.5-month empty stretch that spline pieces span
# with almost no data, giving huge, unstable coefficients.
SPRING_START_DOY, FALL_START_DOY, FALL_OFFSET = 60, 213, 100
SEASON_DAY_KNOTS = (15, 35, 55, 75, 125, 145, 160, 175, 190, 210)
SEASON_DAY_BOUNDS = (-1, 224)

CALENDAR = (
    f"{SEASON} + bs(season_day, knots={SEASON_DAY_KNOTS}, lower_bound={SEASON_DAY_BOUNDS[0]},"
    f" upper_bound={SEASON_DAY_BOUNDS[1]}) + year_c"
)
LIGHTS = f"{SEASON}:light_score"
WEATHER = (
    f"{SEASON}:(wind_u + wind_v + wind_speed + temp_evening_c + temp_change_24h"
    " + pressure_change_24h + sky_cover + low_ceiling_frac + any_rain + moon_illum)"
)
PREVIOUS_NIGHT = f"{SEASON}:(tailwind_prev + rain_prev + temp_change_prev + nights_since_good)"

FORMULA = " + ".join([CALENDAR, LIGHTS, WEATHER, PREVIOUS_NIGHT])
PREDICTORS = [
    "season", "season_day", "year_c", "light_score",
    "wind_u", "wind_v", "wind_speed", "temp_evening_c", "temp_change_24h",
    "pressure_change_24h", "sky_cover", "low_ceiling_frac", "any_rain", "moon_illum",
    "tailwind_prev", "rain_prev", "temp_change_prev", "nights_since_good",
]

LEVELS = ["Low", "Moderate", "High", "Extreme"]
# Levels split nights at these percentiles of predicted collisions, so on a
# typical season about half the nights are Low and 1 in 20 is Extreme.
LEVEL_PERCENTILES = [50, 80, 95]


def prepare(nights: pd.DataFrame) -> pd.DataFrame:
    """Add model-only columns. The year trend is clamped to the training years,
    so forecasts for later years use the last fitted year's level."""
    year = nights["date"].dt.year.clip(*TRAIN_YEARS)
    doy = nights["date"].dt.dayofyear
    season_day = doy.where(
        nights["season"] == "spring", doy - FALL_START_DOY + FALL_OFFSET + SPRING_START_DOY
    ) - SPRING_START_DOY
    return nights.assign(year_c=year - 2008, season_day=season_day)


def analysis_set(nights: pd.DataFrame) -> pd.DataFrame:
    """Surveyed McCormick Place nights in the training years with complete predictors."""
    n = nights[nights["surveyed"] & nights["year"].between(*TRAIN_YEARS)]
    n = prepare(n)
    return n.dropna(subset=PREDICTORS).reset_index(drop=True)


def fit(data: pd.DataFrame, formula: str = FORMULA):
    """Fit NB2 starting from a Poisson GLM's coefficients. statsmodels' default
    start can wander off to alpha=0; from the Poisson fit, BFGS is reliable."""
    poisson = smf.glm(f"mp ~ {formula}", data, family=sm.families.Poisson()).fit()
    start = np.append(poisson.params.to_numpy(), 1.0)
    res = smf.negativebinomial(f"mp ~ {formula}", data).fit(
        start_params=start, method="bfgs", maxiter=1000, disp=0
    )
    if not (res.mle_retvals["converged"] and np.isfinite(res.params).all()):
        raise RuntimeError("negative binomial fit did not converge")
    return res


def predictive_quantiles(mu: np.ndarray, alpha: float, q: list[float]) -> np.ndarray:
    """Quantiles of the NB2 predictive distribution for each predicted mean."""
    r = 1 / alpha
    mu = np.asarray(mu, dtype=float)[:, None]
    return stats.nbinom.ppf(q, r, r / (r + mu))


def nb_logpmf(y: np.ndarray, mu: np.ndarray, alpha: float) -> np.ndarray:
    r = 1 / alpha
    return stats.nbinom.logpmf(y, r, r / (r + mu))


def level_of(mu: np.ndarray, cutoffs: list[float]) -> np.ndarray:
    return np.array(LEVELS)[np.searchsorted(cutoffs, mu, side="right")]


@dataclass
class ModelMeta:
    formula: str
    train_years: tuple[int, int]
    n_nights: int
    alpha: float
    level_cutoffs: list[float]
    light_score_range: tuple[float, float]
    backtest: dict


class FittedModel:
    """Just what prediction needs: the formula and its coefficients.
    Independent of statsmodels, so a saved model survives library upgrades."""

    def __init__(self, formula: str, params: pd.Series):
        self.formula = formula
        self.params = params

    def predict(self, nights: pd.DataFrame) -> pd.Series:
        x = dmatrix(self.formula, prepare(nights), NA_action="raise", return_type="dataframe")
        beta = self.params.drop("alpha")
        return np.exp(x[beta.index] @ beta)


def save(results, meta: ModelMeta) -> None:
    MODEL_PKL.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PKL.open("wb") as f:
        pickle.dump(FittedModel(meta.formula, results.params), f)
    MODEL_META.write_text(json.dumps(asdict(meta), indent=2) + "\n")


def load(path: Path = MODEL_PKL) -> tuple[FittedModel, ModelMeta]:
    with path.open("rb") as f:
        fitted = pickle.load(f)
    meta = ModelMeta(**json.loads(MODEL_META.read_text()))
    return fitted, meta
