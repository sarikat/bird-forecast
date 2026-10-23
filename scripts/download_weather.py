"""Download historical hourly weather for Chicago O'Hare from NOAA.

Source: NCEI Integrated Surface Database ("global-hourly"), via the
NCEI Access Data Service. One CSV per year in data/raw/noaa_isd/.
Years already downloaded are skipped.

Usage: uv run scripts/download_weather.py [first_year] [last_year]
"""

import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

STATION = "72530094846"  # Chicago O'Hare (USAF 725300, WBAN 94846)
# Wind, cloud ceiling, visibility, temperature, dew point, sea-level
# pressure, precipitation, sky cover
DATA_TYPES = "WND,CIG,VIS,TMP,DEW,SLP,AA1,GF1"
API = "https://www.ncei.noaa.gov/access/services/data/v1"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "noaa_isd"


def download_year(year: int) -> Path:
    out = OUT_DIR / f"ORD_{year}.csv"
    if out.exists():
        return out
    params = urllib.parse.urlencode({
        "dataset": "global-hourly",
        "stations": STATION,
        "startDate": f"{year}-01-01",
        "endDate": f"{year}-12-31T23:59:59",
        "dataTypes": DATA_TYPES,
        "format": "csv",
    })
    with urllib.request.urlopen(f"{API}?{params}", timeout=120) as resp:
        body = resp.read()
    if not body.startswith(b'"STATION"'):
        raise RuntimeError(f"{year}: unexpected response: {body[:200]!r}")
    tmp = out.with_suffix(".part")
    tmp.write_bytes(body)
    tmp.rename(out)
    return out


def main() -> None:
    first = int(sys.argv[1]) if len(sys.argv) > 1 else 1978
    last = int(sys.argv[2]) if len(sys.argv) > 2 else 2019
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for year in range(first, last + 1):
        path = download_year(year)
        rows = path.read_bytes().count(b"\n") - 1
        print(f"{year}: {rows} hourly records")
        time.sleep(0.5)  # be polite to the API


if __name__ == "__main__":
    main()
