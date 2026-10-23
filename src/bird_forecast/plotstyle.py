"""Shared matplotlib style for report figures.

Colors are the dataviz skill's reference palette: categorical slots 1-3 on
the light surface, with lighter steps of the same hues for interval bars.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bird_forecast.paths import FIGURES

SPRING, FALL = "#2a78d6", "#eb6834"
MP, CHI = "#2a78d6", "#1baf7a"
SEASON_COLORS = {"spring": SPRING, "fall": FALL}
SEASON_TINTS = {"spring": "#9ec5f4", "fall": "#f5b195"}
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


def save(fig, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}")
