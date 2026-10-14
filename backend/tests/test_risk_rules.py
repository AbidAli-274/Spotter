import pytest

from apps.risk.models import RiskLevel as R
from apps.risk.models import WeatherSample
from apps.risk.rules import assess, classify_rain, classify_snow, classify_wind

L, M, H, S, N = R.LOW, R.MODERATE, R.HIGH, R.SEVERE, R.NO_TRAVEL


@pytest.mark.parametrize(
    ("mph", "expected"),
    [
        (0, L),
        (24.9, L),
        (25, M),
        (34.9, M),
        (35, H),
        (44.9, H),
        (45, S),
        (54.9, S),
        (55, N),
        (80, N),
    ],
)
def test_wind_thresholds(mph, expected):
    assert classify_wind(mph) == expected


@pytest.mark.parametrize(
    ("in_hr", "expected"),
    [
        (0, L),
        (0.099, L),
        (0.10, M),
        (0.249, M),
        (0.25, H),
        (0.499, H),
        (0.50, S),
        (1.00, S),
        (1.01, N),
    ],
)
def test_rain_thresholds(in_hr, expected):
    assert classify_rain(in_hr) == expected


@pytest.mark.parametrize(
    ("in_hr", "expected"),
    [(0, L), (0.49, L), (0.5, M), (0.99, M), (1.0, H), (1.99, H), (2.0, S), (3.0, S), (3.01, N)],
)
def test_snow_thresholds(in_hr, expected):
    assert classify_snow(in_hr) == expected


def sample(wind=0.0, rain=0.0, snow=0.0):
    return WeatherSample(wind_mph=wind, rain_in_hr=rain, snow_in_hr=snow)


@pytest.mark.parametrize("load", [0, 10_000, 80_000])
def test_wind_55_is_no_travel_for_any_load(load):
    assert assess(sample(wind=55), load).level == N


@pytest.mark.parametrize(("load", "expected"), [(30_000, S), (30_001, N), (80_000, N)])
def test_wind_45_to_54_heavy_load_is_no_travel(load, expected):
    result = assess(sample(wind=50), load)
    assert result.level == expected
    assert result.load_adjusted == (expected == N)


@pytest.mark.parametrize(("load", "expected"), [(40_000, H), (40_001, S), (80_000, S)])
def test_wind_35_to_44_very_heavy_load_is_severe(load, expected):
    result = assess(sample(wind=40), load)
    assert result.level == expected
    assert result.load_adjusted == (expected == S)


def test_load_rule_never_lowers_a_worse_level():
    # Heavy rain already Severe; wind band escalation must not reduce it.
    assert assess(sample(wind=40, rain=0.7), 50_000).level == S
    assert assess(sample(wind=20, rain=2.0), 0).level == N


def test_light_load_unaffected_by_load_rules():
    assert assess(sample(wind=44), 20_000).level == H
    assert assess(sample(wind=54), 20_000).level == S


def test_overall_level_is_worst_condition_and_lists_drivers():
    result = assess(sample(wind=26, rain=0.3, snow=0.1), 10_000)
    assert result.level == H
    assert result.rain_level == H and result.wind_level == M
    assert any("rain" in d for d in result.drivers)
    assert not any("wind" in d for d in result.drivers)


def test_calm_weather_is_low_with_no_drivers():
    result = assess(sample(), 80_000)
    assert result.level == L
    assert result.drivers == ()
