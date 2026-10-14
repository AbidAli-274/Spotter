"""End-to-end analysis with fake providers: ETA-based sampling, load rules, recommendation."""

from datetime import UTC, datetime, timedelta

import pytest

from apps.risk.models import RiskLevel
from apps.routing.models import Place, Route
from apps.trips.errors import ForecastRangeError
from apps.trips.schemas import PlaceInput, TripRequest
from apps.trips.services import TripAnalyzer, validate_departure
from apps.weather.client import snap
from apps.weather.models import HourlySeries

DEPARTURE = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
HOURS = 96


def line_route(lon: float, miles=200.0, hours=4.0) -> Route:
    deg = miles / 69.0
    return Route(
        coords=[(lon, 40.0), (lon, 40.0 + deg)],
        distance_mi=miles,
        duration_s=hours * 3600,
        time_knots=[(0, 0), (miles, hours * 3600)],
        summary=f"via lon {lon}",
    )


class FakeOrs:
    def __init__(self, routes):
        self.routes = routes

    def geocode(self, text):
        return Place(text, -100.0, 40.0 if text in ("A", "Dallas, TX") else 42.9)

    def directions(self, waypoints, *, load_lb=0, alternatives=0):
        # first call is the direct request; via-point calls pick the next prepared route
        if len(waypoints) == 2:
            return [self.routes[0]]
        return [self.routes[1] if waypoints[1][0] < waypoints[0][0] else self.routes[2]]


class FakeWeather:
    """`bad(lat_lon, hour_index) -> (wind, rain, snow)`; default calm."""

    def __init__(self, bad=None):
        self.bad = bad or (lambda point, hour: (5.0, 0.0, 0.0))

    def hourly(self, points, start, end):
        base = datetime(start.year, start.month, start.day, tzinfo=UTC)
        out = {}
        for p in {snap(*pt) for pt in points}:
            cols = [self.bad(p, base + timedelta(hours=h)) for h in range(HOURS)]
            out[p] = HourlySeries(
                start=base,
                wind_mph=tuple(c[0] for c in cols),
                rain_in_hr=tuple(c[1] for c in cols),
                snow_in_hr=tuple(c[2] for c in cols),
            )
        return out


def request(load=20_000, interval=25):
    return TripRequest(
        origin=PlaceInput("A"),
        destination=PlaceInput("B"),
        departure=DEPARTURE,
        load_lb=load,
        interval_mi=interval,
    )


def analyze(weather, routes=None, **kw):
    routes = routes or [line_route(-100.0), line_route(-101.0, 220, 4.5), line_route(-99.0, 240, 5)]
    return TripAnalyzer(FakeOrs(routes), weather).analyze(request(**kw))


def test_weather_is_sampled_at_each_checkpoints_eta_not_departure():
    # Storm hits only 3-4 hours after departure; only late checkpoints should see it.
    def storm(_point, when):
        hours_in = (when - DEPARTURE).total_seconds() / 3600
        return (5.0, 0.6, 0.0) if 2.5 <= hours_in <= 4.5 else (5.0, 0.0, 0.0)

    result = analyze(FakeWeather(storm))
    first = result["routes"][0]["checkpoints"]
    assert first[0]["risk"] == "low"  # departure: clear
    assert first[-1]["risk"] == "severe"  # arrival ~4h later: heavy rain (0.6 in/hr)
    assert first[-1]["eta"] == DEPARTURE + timedelta(hours=4)
    assert first[-1]["weather"]["rain_in_hr"] == pytest.approx(0.6)


def test_checkpoint_spacing_matches_requested_interval():
    for interval, expected in ((25, 9), (50, 5), (10, 21)):
        cps = analyze(FakeWeather(), interval=interval)["routes"][0]["checkpoints"]
        assert len(cps) == expected
        assert cps[-1]["mile"] == 200.0


def test_load_rules_applied_in_analysis():
    windy = FakeWeather(lambda *_: (50.0, 0.0, 0.0))
    light = analyze(windy, load=20_000)["routes"][0]["metrics"]
    heavy = analyze(windy, load=35_000)["routes"][0]["metrics"]
    assert light["worst_level"] == "severe"
    assert heavy["worst_level"] == "no_travel"
    assert heavy["miles_by_level"]["no_travel"] == pytest.approx(200.0)


def test_recommends_the_route_that_avoids_the_storm_even_if_slower():
    def storm_on_main(point, _when):
        lat, lon = point
        return (5.0, 0.7, 0.0) if abs(lon + 100.0) < 0.5 else (5.0, 0.0, 0.0)

    result = analyze(FakeWeather(storm_on_main))
    rec = result["recommendation"]
    by_id = {r["id"]: r for r in result["routes"]}
    assert by_id[rec["route_id"]]["recommended"]
    assert by_id[rec["route_id"]]["metrics"]["miles_by_level"]["severe"] == 0
    assert by_id["route-1"]["metrics"]["miles_by_level"]["severe"] > 0
    assert by_id["route-1"]["rank"] == 3
    assert "Severe" in rec["reason"]


def test_missing_weather_marks_checkpoints_unknown_not_low():
    class NoData(FakeWeather):
        def hourly(self, points, start, end):
            return {}

    result = analyze(NoData())
    route = result["routes"][0]
    assert all(c["risk"] is None and c["weather"] is None for c in route["checkpoints"])
    assert route["metrics"]["unknown_miles"] == pytest.approx(200.0)


def test_heatmap_has_48_hourly_levels_per_point_and_is_load_aware():
    windy_at_hour_5 = FakeWeather(
        lambda _p, when: (
            (42.0, 0.0, 0.0)
            if when == DEPARTURE.replace(minute=0) + timedelta(hours=5)
            else (5.0, 0.0, 0.0)
        )
    )
    light = analyze(windy_at_hour_5, load=10_000)["heatmap"]
    heavy = analyze(windy_at_hour_5, load=45_000)["heatmap"]
    assert light["hours"] == 48 and len(light["points"][0]["levels"]) == 48
    assert light["points"][0]["levels"][5] == RiskLevel.HIGH
    assert heavy["points"][0]["levels"][5] == RiskLevel.SEVERE
    assert light["points"][0]["levels"][4] == RiskLevel.LOW


def test_validate_departure_bounds():
    now = datetime.now(UTC)
    validate_departure(now)
    with pytest.raises(ForecastRangeError):
        validate_departure(now - timedelta(days=1))
    with pytest.raises(ForecastRangeError):
        validate_departure(now + timedelta(days=20))
