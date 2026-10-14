from datetime import UTC, date, datetime

import httpx
import pytest
import respx

from apps.trips.errors import UpstreamError
from apps.weather.client import OpenMeteoClient, snap

URL = "https://meteo.test/v1/forecast"


def location(wind, rain, showers, snow):
    n = len(wind)
    return {
        "hourly": {
            "time": [f"2099-01-01T{h:02d}:00" for h in range(n)],
            "wind_speed_10m": wind,
            "rain": rain,
            "showers": showers,
            "snowfall": snow,
        }
    }


@pytest.fixture(autouse=True)
def _near_horizon(monkeypatch):
    monkeypatch.setattr("apps.weather.client.forecast_horizon", lambda today=None: date(2100, 1, 1))


@respx.mock
def test_batches_points_parses_and_sums_rain_and_showers():
    route = respx.get(URL).respond(
        json=[
            location([10, 40], [0.1, 0.0], [0.05, 0.0], [0.0, 0.5]),
            location([5, None], [0, None], [0, None], [0, None]),
        ]
    )
    pts = [(40.0, -100.0), (41.0, -101.0)]
    series = OpenMeteoClient().hourly(pts, date(2099, 1, 1), date(2099, 1, 1))
    assert route.call_count == 1
    assert "latitude=40.0%2C41.0" in str(route.calls[0].request.url)
    first = series[snap(*pts[0])]
    sample = first.at(datetime(2099, 1, 1, 1, 20, tzinfo=UTC))
    assert (sample.wind_mph, sample.snow_in_hr) == (40, 0.5)
    assert first.sample(0).rain_in_hr == pytest.approx(0.15)
    # null data and out-of-range times become unknown, not zero
    second = series[snap(*pts[1])]
    assert second.sample(1) is None
    assert second.sample(99) is None


@respx.mock
def test_single_location_response_is_an_object_not_a_list():
    respx.get(URL).respond(json=location([1], [0], [0], [0]))
    series = OpenMeteoClient().hourly([(40, -100)], date(2099, 1, 1), date(2099, 1, 1))
    assert len(series) == 1


@respx.mock
def test_results_are_cached():
    route = respx.get(URL).respond(json=location([1], [0], [0], [0]))
    client = OpenMeteoClient()
    args = ([(40, -100)], date(2099, 1, 1), date(2099, 1, 1))
    client.hourly(*args)
    client.hourly(*args)
    assert route.call_count == 1


@respx.mock
def test_provider_failure_raises_upstream_error():
    respx.get(URL).mock(return_value=httpx.Response(500))
    with pytest.raises(UpstreamError):
        OpenMeteoClient().hourly([(40, -100)], date(2099, 1, 1), date(2099, 1, 1))
