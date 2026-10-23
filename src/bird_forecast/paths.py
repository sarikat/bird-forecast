from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "reports" / "figures"

COLLISIONS_CSV = RAW / "winger2019" / "Chicago_collision_data.csv"
LIGHT_CSV = RAW / "winger2019" / "Light_levels_dryad.csv"
WEATHER_DIR = RAW / "noaa_isd"
NIGHTLY_CSV = PROCESSED / "nightly.csv"
