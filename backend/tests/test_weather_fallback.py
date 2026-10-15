from datetime import UTC, date, datetime

import httpx
import pytest
import respx

from apps.trips.errors import UpstreamError
from apps.weather.client import snap
from apps.weather.met_norway import URL, MetNorwayClient, parse_timeseries
from apps.weather.resilient import PRIMARY_DOWN_KEY, ResilientWeatherClient


def entry(time, wind_ms=10.0, temp=10.0, one_hour=None, six_hours=None):
    data = {"instant": {"details": {"wind_speed": wind_ms, "air_temperature": temp}}}
    if one_hour is not None:
        data["next_1_hours"] = {"details": {"precipitation_amount": one_hour}}
    if six_hours is not None:
        data["next_6_hours"] = {"details": {"precipitation_amount": six_hours}}
    return {"time": time, "data": data}


def test_wind_converted_from_ms_to_mph():
    series = parse_timeseries([entry("2099-01-01T00:00:00Z", wind_ms=10, one_hour=0.0)])
    assert series.wind_mph[0] == pytest.approx(22.37, abs=0.01)


def test_rain_vs_snow_split_by_temperature_with_10_to_1_ratio():
    rainy = parse_timeseries([entry("2099-01-01T00:00:00Z", temp=8, one_hour=2.54)])
    assert rainy.rain_in_hr[0] == pytest.approx(0.1)
    assert rainy.snow_in_hr[0] == 0

    snowy = parse_timeseries([entry("2099-01-01T00:00:00Z", temp=-3, one_hour=2.54)])
    assert snowy.rain_in_hr[0] == 0
    assert snowy.snow_in_hr[0] == pytest.approx(1.0)  # 0.1 in water -> 1 in snow


def test_six_hourly_entries_are_spread_over_six_hours():
    series = parse_timeseries(
        [
            entry("2099-01-01T00:00:00Z", one_hour=0.0),
            entry("2099-01-01T06:00:00Z", six_hours=15.24),
        ]
    )
    # 15.24 mm over 6h = 2.54 mm/h = 0.1 in/hr, for hours 6..11
    assert series.rain_in_hr[5] is None  # no entry covers hour 5: unknown, not zero
    assert all(series.rain_in_hr[h] == pytest.approx(0.1) for h in range(6, 12))
    assert series.at(datetime(2099, 1, 1, 9, tzinfo=UTC)).rain_in_hr == pytest.approx(0.1)


@respx.mock
def test_client_fetches_per_point_and_caches():
    route = respx.get(URL).respond(
        json={"properties": {"timeseries": [entry("2099-01-01T00:00:00Z", one_hour=0.0)]}}
    )
    client = MetNorwayClient()
    pts = [(40.0, -100.0), (41.0, -101.0)]
    out = client.hourly(pts, date(2099, 1, 1), date(2099, 1, 1))
    assert set(out) == {snap(*p) for p in pts}
    assert route.call_count == 2
    client.hourly(pts, date(2099, 1, 1), date(2099, 1, 1))
    assert route.call_count == 2
    assert "weather-aware-truck-routing" in route.calls[0].request.headers["user-agent"]


@respx.mock
def test_client_failure_raises_upstream_error():
    respx.get(URL).mock(return_value=httpx.Response(503))
    with pytest.raises(UpstreamError):
        MetNorwayClient().hourly([(40, -100)], date(2099, 1, 1), date(2099, 1, 1))


class Stub:
    def __init__(self, source, fail=False):
        self.source, self.fail, self.calls = source, fail, 0

    def hourly(self, points, start, end):
        self.calls += 1
        if self.fail:
            raise UpstreamError("HTTP 429")
        return {"ok": self.source}


ARGS = ([(40, -100)], date(2099, 1, 1), date(2099, 1, 1))


def test_uses_primary_when_healthy():
    primary, fallback = Stub("open-meteo"), Stub("met-norway")
    client = ResilientWeatherClient(primary, fallback)
    assert client.hourly(*ARGS) == {"ok": "open-meteo"}
    assert client.source == "open-meteo"
    assert fallback.calls == 0


def test_falls_back_and_then_skips_primary_during_cooldown():
    primary, fallback = Stub("open-meteo", fail=True), Stub("met-norway")
    client = ResilientWeatherClient(primary, fallback)
    assert client.hourly(*ARGS) == {"ok": "met-norway"}
    assert client.source == "met-norway"
    client.hourly(*ARGS)
    assert primary.calls == 1  # second request didn't retry the failing primary
    assert fallback.calls == 2


def test_cooldown_flag_is_cleared_between_tests(django_cache=None):
    from django.core.cache import cache

    assert cache.get(PRIMARY_DOWN_KEY) is None


def test_fallback_failure_propagates():
    client = ResilientWeatherClient(Stub("a", fail=True), Stub("b", fail=True))
    with pytest.raises(UpstreamError):
        client.hourly(*ARGS)
