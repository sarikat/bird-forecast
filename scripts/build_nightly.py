"""Build data/processed/nightly.csv: one row per migration-season night.

Usage: uv run scripts/build_nightly.py
"""

from bird_forecast import nightly
from bird_forecast.paths import NIGHTLY_CSV


def main() -> None:
    table = nightly.build()
    NIGHTLY_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(NIGHTLY_CSV, index=False)
    print(f"{len(table)} nights -> {NIGHTLY_CSV}")


if __name__ == "__main__":
    main()
