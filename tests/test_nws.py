import numpy as np
import pandas as pd
import pytest

from bird_forecast import forecast, nws


def obs(timestamp, speed_kmh=18.0, direction=180, layers=("BKN",), precip=None, temp=10.0):
    props = {
        "timestamp": timestamp,
        "temperature": {"value": temp},
        "dewpoint": {"value": 5.0},
        "windSpeed": {"value": speed_kmh},
        "windDirection": {"value": direction},
        "seaLevelPressure": {"value": 101500},
        "cloudLayers": [{"amount": a, "base": {"value": 1000}} for a in layers],
    }
    if precip is not None:
        props["precipitationLastHour"] = {"value": precip}
    return {"properties": props}


def test_observations_keep_routine_reports_only():
    rows = nws.observation_rows([obs("2026-11-07T01:51:00+00:00"), obs("2026-11-07T01:55:00+00:00")])
    assert len(rows) == 1
    assert rows.index[0].tz is not None


def test_observation_units_and_wind_direction():
    row = nws.observation_rows([obs("2026-11-07T01:51:00+00:00", speed_kmh=36, direction=180)]).iloc[0]
    assert row["wind_speed"] == pytest.approx(10.0)  # 36 km/h = 10 m/s
    assert row["wind_v"] == pytest.approx(10.0)  # a south wind blows north
    assert row["wind_u"] == pytest.approx(0.0, abs=1e-9)
    assert row["pressure_hpa"] == pytest.approx(1015.0)


def test_observation_sky_cover_is_the_thickest_layer():
    row = nws.observation_rows([obs("2026-11-07T01:51:00+00:00", layers=("FEW", "OVC"))]).iloc[0]
    assert row["sky_cover"] == 1.0


def test_observation_calm_and_missing_precip():
    row = nws.observation_rows([obs("2026-11-07T01:51:00+00:00", speed_kmh=0, direction=None)]).iloc[0]
    assert (row["wind_u"], row["wind_v"], row["precip_mm"]) == (0.0, 0.0, 0.0)


def test_gridpoint_expands_windows_to_hours():
    props = {
        "windSpeed": {"values": [{"validTime": "2026-11-08T00:00:00+00:00/PT3H", "value": 36.0}]},
        "windDirection": {"values": [{"validTime": "2026-11-08T00:00:00+00:00/PT3H", "value": 270}]},
        "temperature": {"values": [{"validTime": "2026-11-08T00:00:00+00:00/PT1H", "value": 5.0},
                                   {"validTime": "2026-11-08T01:00:00+00:00/PT2H", "value": 4.0}]},
        "dewpoint": {"values": []},
        "skyCover": {"values": [{"validTime": "2026-11-08T00:00:00+00:00/PT3H", "value": 50}]},
        "quantitativePrecipitation": {"values": [{"validTime": "2026-11-08T00:00:00+00:00/PT3H", "value": 0.1}]},
    }
    hourly = nws.gridpoint_rows(props)
    assert len(hourly) == 3
    assert hourly["temp_c"].tolist() == [5.0, 4.0, 4.0]
    assert hourly["wind_u"].iloc[0] == pytest.approx(10.0)  # a west wind blows east
    assert hourly["sky_cover"].iloc[0] == 0.5
    assert (hourly["precip_mm"] == 0).all()  # 0.1 mm is below measurable
    assert np.isnan(hourly["pressure_hpa"]).all()


@pytest.mark.parametrize("local_time, expected", [
    ("2026-11-07 15:00", "2026-11-08"),  # afternoon: tonight ends tomorrow
    ("2026-11-07 23:00", "2026-11-08"),  # night in progress
    ("2026-11-08 02:00", "2026-11-08"),  # still the same night
    ("2026-11-08 08:00", "2026-11-09"),  # after dawn: next night
])
def test_first_night(local_time, expected):
    now = pd.Timestamp(local_time, tz="America/Chicago")
    assert forecast.first_night(now) == pd.Timestamp(expected)
