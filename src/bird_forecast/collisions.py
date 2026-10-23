"""Chicago collision records and McCormick Place light scores (Winger et al. 2019).

Each collision record is one bird, dated by the morning it was collected, so the
collision happened during the night that *ended* on that date. Locality is "MP"
(McCormick Place, surveyed consistently since 1978) or "CHI" (elsewhere in
downtown Chicago; volunteer effort grew roughly 30-fold after 2005, so CHI counts
are not comparable across years).
"""

import pandas as pd

from bird_forecast.paths import COLLISIONS_CSV, LIGHT_CSV


def load_collisions() -> pd.DataFrame:
    df = pd.read_csv(COLLISIONS_CSV, parse_dates=["Date"])
    df["species"] = df["Genus"] + " " + df["Species"]
    return df.rename(columns={"Date": "date", "Locality": "locality"})[
        ["date", "locality", "species"]
    ]


def load_light() -> pd.DataFrame:
    """Nightly McCormick Place light score, one row per date.

    A handful of dates appear twice in the source file; keep the mean.
    """
    df = pd.read_csv(LIGHT_CSV, parse_dates=["Date"])
    df = df.rename(columns={"Date": "date", "Light_Score": "light_score"})
    return df.groupby("date", as_index=False)["light_score"].mean()


def daily_counts(collisions: pd.DataFrame) -> pd.DataFrame:
    """Birds collected per date, one column per locality (MP, CHI)."""
    counts = (
        collisions.groupby(["date", "locality"]).size().unstack(fill_value=0)
    )
    return counts.rename(columns={"MP": "mp", "CHI": "chi"}).reset_index()
