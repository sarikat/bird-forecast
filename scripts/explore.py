"""First exploratory plots of the nightly table -> reports/figures/.

Most panels show a *relative collision rate*: birds on nights in a bin divided
by the birds we'd expect on those nights from the date alone (a seasonal curve
scaled to each year's total). That way "fall is busy" doesn't masquerade as
"north winds are deadly". Analysis set: McCormick Place, 2000-2016, surveyed
nights only, since that's where zero-collision nights are known to be real.

Usage: uv run scripts/explore.py
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bird_forecast.paths import FIGURES, NIGHTLY_CSV

# Reference palette (dataviz skill): categorical slots 1-3, light surface.
SPRING, FALL = "#2a78d6", "#eb6834"
MP, CHI = "#2a78d6", "#1baf7a"
SEASON_COLORS = {"spring": SPRING, "fall": FALL}
SEASON_TINTS = {"spring": "#9ec5f4", "fall": "#f5b195"}  # interval bars
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.labelsize": 9, "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": INK_2, "ytick.color": INK_2, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.frameon": False, "legend.fontsize": 8, "font.size": 9, "lines.linewidth": 2,
})

BASELINE_WINDOW_DAYS = 15
BOOTSTRAP_REPS = 1000
rng = np.random.default_rng(0)


def save(fig, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}")


def add_baseline(n: pd.DataFrame) -> pd.DataFrame:
    """Expected birds per night from the date alone: a smoothed day-of-year
    curve, scaled so each year's expected total matches its actual total."""
    by_day = n.groupby("day_of_year")["mp"].mean()
    by_day = by_day.reindex(range(1, 367))
    curve = by_day.rolling(BASELINE_WINDOW_DAYS, center=True, min_periods=3).mean()
    n = n.assign(curve=n["day_of_year"].map(curve))
    year_scale = n.groupby("year")["mp"].sum() / n.groupby("year")["curve"].sum()
    return n.assign(expected=n["curve"] * n["year"].map(year_scale))


def relative_rate(group: pd.DataFrame) -> tuple[float, float, float]:
    """Observed / expected birds with a 95% bootstrap interval over nights."""
    obs, exp = group["mp"].to_numpy(), group["expected"].to_numpy()
    idx = rng.integers(0, len(group), size=(BOOTSTRAP_REPS, len(group)))
    boots = obs[idx].sum(axis=1) / exp[idx].sum(axis=1)
    return obs.sum() / exp.sum(), *np.percentile(boots, [2.5, 97.5])


def plot_annual_totals(all_nights: pd.DataFrame) -> None:
    totals = all_nights.groupby("year")[["mp", "chi"]].sum()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(totals.index, totals["mp"], color=MP, label="McCormick Place")
    ax.plot(totals.index, totals["chi"], color=CHI, label="Rest of downtown")
    ax.annotate("McCormick Place", (totals.index[-1], totals["mp"].iloc[-1]),
                xytext=(6, 0), textcoords="offset points", color=INK_2, va="center", fontsize=8)
    ax.annotate("Rest of downtown", (totals.index[-1], totals["chi"].iloc[-1]),
                xytext=(6, 0), textcoords="offset points", color=INK_2, va="center", fontsize=8)
    ax.axvline(2005, color=INK_2, linewidth=0.8, linestyle=":")
    ax.text(2004.6, totals.values.max() * 0.97, "volunteer monitoring\nexpands downtown",
            color=INK_2, fontsize=8, va="top", ha="right")
    ax.set_title("Birds collected per year")
    ax.set_ylabel("birds")
    ax.legend(loc="upper left")
    ax.set_xlim(totals.index.min(), totals.index.max() + 6)
    save(fig, "01_annual_totals.png")


def plot_season_curve(n: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True,
                             gridspec_kw={"width_ratios": [3, 4]})
    for ax, season in zip(axes, ["spring", "fall"]):
        s = n[n["season"] == season]
        daily = s.groupby("date")["mp"].first()
        doy = s.groupby("day_of_year")["mp"]
        q = doy.quantile([0.25, 0.75]).unstack()
        mean = doy.mean().rolling(7, center=True, min_periods=1).mean()
        dates = pd.to_datetime("2001-01-01") + pd.to_timedelta(mean.index - 1, unit="D")
        ax.fill_between(dates, q[0.25].rolling(7, center=True, min_periods=1).mean(),
                        q[0.75].rolling(7, center=True, min_periods=1).mean(),
                        color=SEASON_COLORS[season], alpha=0.18, linewidth=0, label="middle 50% of nights")
        ax.plot(dates, mean, color=SEASON_COLORS[season], label="average night")
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %-d"))
        ax.xaxis.set_major_locator(matplotlib.dates.DayLocator(bymonthday=[1, 15]))
        ax.set_title(f"{season.capitalize()}  ({len(daily):,} nights)")
        ax.legend(loc="upper left")
    axes[0].set_ylabel("birds per night, McCormick Place")
    fig.suptitle("When collisions happen: average and typical nights, 2000–2016",
                 x=0.01, ha="left", fontweight="bold", color=INK)
    fig.tight_layout()
    save(fig, "02_season_curve.png")


def plot_count_distribution(n: pd.DataFrame) -> None:
    counts = np.sort(n["mp"].to_numpy())[::-1]
    share_birds = np.cumsum(counts) / counts.sum()
    share_nights = np.arange(1, len(counts) + 1) / len(counts)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    bins = [0, 1, 2, 3, 5, 10, 20, 50, 100, 300]
    labels = ["0", "1", "2", "3–4", "5–9", "10–19", "20–49", "50–99", "100+"]
    hist = pd.cut(n["mp"], bins, right=False, labels=labels).value_counts().reindex(labels)
    axes[0].bar(labels, hist.values, color=MP, width=0.8)
    axes[0].set_title("Most nights are quiet")
    axes[0].set_xlabel("birds collected that night")
    axes[0].set_ylabel("nights")
    axes[0].grid(axis="x", visible=False)
    axes[1].plot(share_nights * 100, share_birds * 100, color=MP)
    for pct in (5, 10):
        y = share_birds[int(len(counts) * pct / 100) - 1] * 100
        axes[1].plot([pct], [y], "o", color=MP, markersize=6, markeredgecolor=SURFACE, markeredgewidth=1)
        axes[1].annotate(f"worst {pct}% of nights → {y:.0f}% of birds", (pct, y),
                         xytext=(8, -12), textcoords="offset points", color=INK_2, fontsize=8)
    axes[1].set_title("A few bad nights kill most birds")
    axes[1].set_xlabel("% of nights, worst first")
    axes[1].set_ylabel("% of all birds")
    axes[1].set_ylim(0, 102)
    mean, var = n["mp"].mean(), n["mp"].var()
    fig.text(0.01, -0.04, f"Mean {mean:.1f} birds/night, variance {var:.0f}: far more spread than a "
             "Poisson count allows, which is why the model will be negative binomial.",
             color=INK_2, fontsize=8)
    fig.tight_layout()
    save(fig, "03_count_distribution.png")


def plot_wind_rose(n: pd.DataFrame) -> None:
    sectors = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    n = n.dropna(subset=["wind_from_deg"]).assign(
        sector=lambda d: pd.Categorical(
            np.array(sectors)[((d["wind_from_deg"] + 22.5) // 45 % 8).astype(int)], sectors))
    fig, axes = plt.subplots(1, 2, figsize=(8, 4.2), subplot_kw={"projection": "polar"})
    theta = np.deg2rad(np.arange(0, 360, 45))
    rmax = 0
    for ax, season in zip(axes, ["spring", "fall"]):
        s = n[n["season"] == season]
        rates = s.groupby("sector", observed=False).apply(lambda g: relative_rate(g)[0] if len(g) >= 20 else np.nan)
        rmax = max(rmax, np.nanmax(rates.values))
        ax.bar(theta, rates.values, width=np.deg2rad(38), color=SEASON_COLORS[season],
               edgecolor=SURFACE, linewidth=2)
        ax.plot(np.linspace(0, 2 * np.pi, 200), np.ones(200), color=INK, linewidth=0.8, linestyle=":")
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_xticks(theta, sectors)
        ax.set_title(f"{season.capitalize()}", pad=14)
        ax.grid(color=GRID)
        ax.spines["polar"].set_color(GRID)
    for ax in axes:
        ax.set_ylim(0, rmax * 1.05)
        ax.set_yticks([1, 2, 3][: int(rmax) + 1])
        ax.set_yticklabels([f"{v}×" for v in [1, 2, 3][: int(rmax) + 1]], color=INK_2, fontsize=7)
    fig.suptitle("Collision rate by direction the wind blows from\n(dotted ring = typical night for that date)",
                 x=0.01, ha="left", fontweight="bold", color=INK, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    save(fig, "04_wind_rose.png")


FACTORS = [
    ("light_score", "Building lights (window bays lit)", [3, 6, 11, 15, 18], ["3–5", "6–10", "11–14", "15–17"]),
    ("tailwind", "Tailwind for migrants (m/s)", [-99, -3, -1, 1, 3, 99], ["< −3", "−3 to −1", "−1 to 1", "1 to 3", "> 3"]),
    ("sky_cover", "Cloud cover", [-0.01, 0.25, 0.5, 0.75, 1.01], ["0–25%", "25–50%", "50–75%", "75–100%"]),
    ("rain_hours", "Hours of rain overnight", [-1, 0, 2, 99], ["0", "1–2", "3+"]),
    ("temp_change_24h", "Temp. change since last evening (°C)", [-99, -5, -2, 2, 5, 99], ["< −5", "−5 to −2", "−2 to 2", "2 to 5", "> 5"]),
    ("moon_illum", "Moon illuminated", [-0.01, 0.25, 0.5, 0.75, 1.01], ["0–25%", "25–50%", "50–75%", "75–100%"]),
]


def plot_factors(n: pd.DataFrame) -> pd.DataFrame:
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.4), sharey=True)
    rows = []
    for ax, (col, title, bins, labels) in zip(axes.flat, FACTORS):
        for i, season in enumerate(["spring", "fall"]):
            s = n[n["season"] == season].dropna(subset=[col])
            s = s.assign(bin=pd.cut(s[col], bins, labels=labels))
            x = np.arange(len(labels)) + (i - 0.5) * 0.22
            for j, (label, g) in enumerate(s.groupby("bin", observed=False)):
                if len(g) < 15:
                    continue
                rate, lo, hi = relative_rate(g)
                rows.append({"factor": col, "season": season, "bin": label, "nights": len(g),
                             "rate": rate, "lo": lo, "hi": hi})
                ax.vlines(x[j], lo, hi, color=SEASON_TINTS[season], linewidth=2.5)
                ax.plot(x[j], rate, "o", color=SEASON_COLORS[season], markersize=7,
                        markeredgecolor=SURFACE, markeredgewidth=1,
                        label=season.capitalize() if j == 0 else None)
        ax.axhline(1, color=INK, linewidth=0.8, linestyle=":")
        ax.set_xticks(range(len(labels)), labels)
        ax.set_title(title, fontsize=10)
        ax.grid(axis="x", visible=False)
        ax.set_yscale("log")
        ax.set_yticks([0.25, 0.5, 1, 2, 4], ["¼×", "½×", "1×", "2×", "4×"])
        ax.minorticks_off()
    for ax in axes[:, 0]:
        ax.set_ylabel("collisions vs. typical night")
    axes[0, 0].legend(loc="upper left")
    fig.suptitle("What makes a bad night? Each dot: birds collected ÷ birds expected for those dates "
                 "(95% interval)", x=0.01, ha="left", fontweight="bold", color=INK, fontsize=11)
    fig.tight_layout()
    save(fig, "05_factors.png")
    return pd.DataFrame(rows)


def main() -> None:
    all_nights = pd.read_csv(NIGHTLY_CSV, parse_dates=["date"])
    n = all_nights[all_nights["surveyed"] & all_nights["year"].between(2000, 2016)]
    n = add_baseline(n)
    print(f"Analysis set: {len(n):,} surveyed nights, {n['mp'].sum():,} birds (McCormick Place, 2000–2016)")

    plot_annual_totals(all_nights)
    plot_season_curve(n)
    plot_count_distribution(n)
    plot_wind_rose(n)
    rates = plot_factors(n)
    print(rates.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
