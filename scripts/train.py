"""Backtest and fit the collision model, then save it to models/.

Backtest: leave-one-year-out. For each year 2000-2016, fit on the other years,
then predict the held-out year's nights. Risk-level cutoffs are also set from
the training years only, so the level table is a fair test of how the levels
would have performed on an unseen season.

Usage: uv run scripts/train.py
"""

import warnings

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from patsy import dmatrix
from scipy import stats

from bird_forecast import model
from bird_forecast.paths import NIGHTLY_CSV
from bird_forecast.plotstyle import INK, INK_2, SEASON_COLORS, SEASON_TINTS, SURFACE, save

warnings.filterwarnings("ignore", category=RuntimeWarning)  # NB fits probe extreme alphas
EXAMPLE_YEAR = 2016  # the most recent season, so it isn't cherry-picked
PARAM_DRAWS = 2000
rng = np.random.default_rng(0)


def backtest(data: pd.DataFrame, formula: str) -> pd.DataFrame:
    out = []
    for year in sorted(data["year"].unique()):
        train, test = data[data["year"] != year], data[data["year"] == year]
        res = model.fit(train, formula)
        cutoffs = np.percentile(res.predict(train), model.LEVEL_PERCENTILES)
        mu = res.predict(test).to_numpy()
        out.append(test.assign(mu=mu, alpha=res.params["alpha"], level=model.level_of(mu, cutoffs)))
    return pd.concat(out)


def scores(bt: pd.DataFrame) -> dict:
    y, mu = bt["mp"].to_numpy(), bt["mu"].to_numpy()
    worst = y >= np.quantile(y, 0.9)
    flagged = mu >= np.quantile(mu, 0.9)
    return {
        "log_score": float(model.nb_logpmf(y, mu, bt["alpha"].to_numpy()).mean()),
        "spearman": float(stats.spearmanr(mu, y).statistic),
        "worst_10pct_nights_flagged": float((worst & flagged).sum() / worst.sum()),
        "birds_on_flagged_nights": float(y[flagged].sum() / y.sum()),
    }


def level_table(bt: pd.DataFrame) -> pd.DataFrame:
    worst = bt["mp"] >= bt["mp"].quantile(0.9)
    g = bt.assign(worst=worst).groupby("level")
    table = pd.DataFrame({
        "nights": g.size(),
        "share_of_nights": g.size() / len(bt),
        "avg_birds": g["mp"].mean(),
        "share_of_birds": g["mp"].sum() / bt["mp"].sum(),
        "share_of_worst_nights": g["worst"].sum() / worst.sum(),
    })
    return table.reindex(model.LEVELS)


def plot_levels(table: pd.DataFrame) -> None:
    colors = ["#cde2fb", "#86b6ef", "#3987e5", "#184f95"]  # ordinal blue ramp
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    x = np.arange(len(table))
    axes[0].bar(x, table["avg_birds"], color=colors, width=0.7)
    for i, v in enumerate(table["avg_birds"]):
        axes[0].text(i, v, f"{v:.1f}", ha="center", va="bottom", color=INK_2, fontsize=8)
    axes[0].set_title("Average birds on nights at each level")
    axes[0].set_ylabel("birds per night")
    for row, column in [(1, "share_of_nights"), (0, "share_of_birds")]:
        left = 0.0
        for i, level in enumerate(model.LEVELS):
            width = table.loc[level, column]
            axes[1].barh(row, width, left=left, color=colors[i], edgecolor=SURFACE, linewidth=2, height=0.6)
            if width > 0.08:
                axes[1].text(left + width / 2, row, f"{level}\n{width:.0%}", ha="center", va="center",
                             color=SURFACE if i >= 2 else INK, fontsize=8)
            left += width
    axes[1].set_yticks([0, 1], ["share of birds", "share of nights"])
    axes[1].set_xlim(0, 1)
    axes[1].xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    top = table.loc[["High", "Extreme"]].sum()
    axes[1].set_title(f"High + Extreme: {top['share_of_nights']:.0%} of nights, "
                      f"{top['share_of_birds']:.0%} of birds")
    axes[1].grid(axis="y", visible=False)
    axes[0].grid(axis="x", visible=False)
    axes[0].set_xticks(x, model.LEVELS)
    fig.suptitle("Backtest: risk levels on held-out years, 2000–2016", x=0.01, ha="left",
                 fontweight="bold", color=INK)
    fig.tight_layout()
    save(fig, "06_backtest_levels.png")


def plot_example_year(bt: pd.DataFrame) -> None:
    yr = bt[bt["year"] == EXAMPLE_YEAR]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True, gridspec_kw={"width_ratios": [3, 4]})
    for ax, season in zip(axes, ["spring", "fall"]):
        s = yr[yr["season"] == season].sort_values("date")
        band = model.predictive_quantiles(s["mu"], s["alpha"].iloc[0], [0.1, 0.9])
        # One mark per surveyed night; unsurveyed nights are simply blank.
        ax.vlines(s["date"], band[:, 0], band[:, 1], color=SEASON_TINTS[season], linewidth=3,
                  label="80% forecast range")
        ax.plot(s["date"], s["mu"], "_", color=SEASON_COLORS[season], markersize=8,
                markeredgewidth=2, label="forecast")
        ax.plot(s["date"], s["mp"], "o", color=INK, markersize=3, label="birds collected")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %-d"))
        ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=[1, 15]))
        ax.set_title(f"{season.capitalize()} {EXAMPLE_YEAR}")
        ax.legend(loc="upper left")
    axes[0].set_ylabel("birds per night, McCormick Place")
    fig.suptitle(f"Forecast vs. reality for {EXAMPLE_YEAR}, a year the model never saw",
                 x=0.01, ha="left", fontweight="bold", color=INK)
    fig.tight_layout()
    save(fig, "07_example_year.png")


SCENARIOS = [
    ("Lights: fully on vs. mostly off", {"light_score": 17}, {"light_score": 3}),
    ("South wind 5 m/s vs. calm", {"wind_u": 0, "wind_v": 5, "wind_speed": 5}, {"wind_u": 0, "wind_v": 0, "wind_speed": 0}),
    ("North wind 5 m/s vs. calm", {"wind_u": 0, "wind_v": -5, "wind_speed": 5}, {"wind_u": 0, "wind_v": 0, "wind_speed": 0}),
    ("West wind 5 m/s vs. calm", {"wind_u": 5, "wind_v": 0, "wind_speed": 5}, {"wind_u": 0, "wind_v": 0, "wind_speed": 0}),
    # Last evening held fixed, so tonight's temperature moves with the change.
    ("6 °C warmer than last evening", {"temp_change_24h": 6, "temp_evening_c": +6}, {"temp_change_24h": 0}),
    ("6 °C cooler than last evening", {"temp_change_24h": -6, "temp_evening_c": -6}, {"temp_change_24h": 0}),
    ("Rain overnight vs. dry", {"any_rain": 1}, {"any_rain": 0}),
    ("Overcast vs. clear", {"sky_cover": 1}, {"sky_cover": 0}),
    ("Full moon vs. new moon", {"moon_illum": 1}, {"moon_illum": 0}),
]


def scenario_effects(res, data: pd.DataFrame) -> pd.DataFrame:
    """Rate ratio for each scenario on a typical night, with 95% intervals from
    draws of the coefficients. The NB model is log-linear, so the ratio is the
    same for any baseline night apart from the parts that differ."""
    beta = res.params.drop("alpha")
    cov = res.cov_params().loc[beta.index, beta.index]
    draws = rng.multivariate_normal(beta, cov, size=PARAM_DRAWS)
    rows = []
    for season in ["spring", "fall"]:
        typical = data[data["season"] == season].median(numeric_only=True).to_frame().T
        typical["season"] = season
        for label, a, b in SCENARIOS:
            # temp_evening_c is given as a shift from the typical night.
            if "temp_evening_c" in a:
                a = {**a, "temp_evening_c": typical["temp_evening_c"] + a["temp_evening_c"]}
            xa = dmatrix(model.FORMULA, typical.assign(**a), return_type="dataframe")
            xb = dmatrix(model.FORMULA, typical.assign(**b), return_type="dataframe")
            diff = (xa - xb)[beta.index].to_numpy()[0]
            ratio = np.exp(draws @ diff)
            rows.append({"scenario": label, "season": season, "ratio": float(np.exp(beta @ diff)),
                         "lo": float(np.percentile(ratio, 2.5)), "hi": float(np.percentile(ratio, 97.5))})
    return pd.DataFrame(rows)


def plot_effects(effects: pd.DataFrame) -> None:
    labels = [s[0] for s in SCENARIOS]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    y = np.arange(len(labels))[::-1]
    for i, season in enumerate(["spring", "fall"]):
        e = effects[effects["season"] == season].set_index("scenario").loc[labels]
        yy = y + (0.5 - i) * 0.3
        ax.hlines(yy, e["lo"], e["hi"], color=SEASON_TINTS[season], linewidth=2.5)
        ax.plot(e["ratio"], yy, "o", color=SEASON_COLORS[season], markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=1, label=season.capitalize())
    ax.axvline(1, color=INK, linewidth=0.8, linestyle=":")
    ax.set_xscale("log")
    ticks = [0.25, 0.5, 1, 2, 4, 8]
    ax.set_xticks(ticks, ["¼×", "½×", "1×", "2×", "4×", "8×"])
    ax.minorticks_off()
    ax.set_yticks(y, labels)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("collisions vs. comparison night (95% interval)")
    ax.legend(loc="lower right")
    ax.set_title("Fitted model: how much each condition changes collisions, all else equal")
    fig.tight_layout()
    save(fig, "08_model_effects.png")


def main() -> None:
    nights = pd.read_csv(NIGHTLY_CSV, parse_dates=["date"])
    data = model.analysis_set(nights)
    print(f"Training set: {len(data):,} nights, {data['mp'].sum():,} birds")

    print("Backtesting (leave one year out)...")
    bt_cal = backtest(data, model.CALENDAR)
    bt = backtest(data, model.FORMULA)
    comparison = pd.DataFrame({"calendar only": scores(bt_cal), "full model": scores(bt)})
    print(comparison.round(3).to_string())
    levels = level_table(bt)
    print(levels.round(3).to_string())

    plot_levels(levels)
    plot_example_year(bt)

    res = model.fit(data)
    effects = scenario_effects(res, data)
    print(effects.round(2).to_string(index=False))
    plot_effects(effects)

    meta = model.ModelMeta(
        formula=model.FORMULA,
        train_years=model.TRAIN_YEARS,
        n_nights=len(data),
        alpha=float(res.params["alpha"]),
        level_cutoffs=np.percentile(res.predict(data), model.LEVEL_PERCENTILES).round(3).tolist(),
        light_score_range=(float(data["light_score"].min()), float(data["light_score"].max())),
        backtest={
            "scores": comparison.round(4).to_dict(),
            "levels": levels.round(4).to_dict(orient="index"),
        },
    )
    model.save(res, meta)
    print(f"Saved model: alpha={meta.alpha:.2f}, level cutoffs={meta.level_cutoffs}")


if __name__ == "__main__":
    main()
