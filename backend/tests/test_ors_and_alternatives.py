import httpx
import pytest
import respx

from apps.routing.alternatives import generate_routes
from apps.routing.models import Place, Route
from apps.routing.ors import OrsClient
from apps.trips.errors import GeocodingError, RoutingError, UpstreamError

BASE = "https://ors.test"


def feature(coords, meters, seconds, names=("I-80", "-")):
    half = len(coords) // 2
    return {
        "geometry": {"coordinates": [list(c) for c in coords]},
        "properties": {
            "summary": {"distance": meters, "duration": seconds},
            "segments": [
                {
                    "steps": [
                        {
                            "distance": meters * 0.8,
                            "duration": seconds * 0.5,
                            "name": names[0],
                            "way_points": [0, half],
                        },
                        {
                            "distance": meters * 0.2,
                            "duration": seconds * 0.5,
                            "name": names[1],
                            "way_points": [half, len(coords) - 1],
                        },
                    ]
                }
            ],
        },
    }


COORDS = [(-100.0, 40.0), (-100.0, 41.0), (-100.0, 42.0), (-100.0, 43.0)]


@respx.mock
def test_geocode_returns_place_and_caches():
    route = respx.get(f"{BASE}/geocode/search").respond(
        json={
            "features": [
                {
                    "geometry": {"coordinates": [-87.6, 41.8]},
                    "properties": {"label": "Chicago, IL, USA"},
                }
            ]
        }
    )
    client = OrsClient()
    assert client.geocode("  Chicago  IL ").label == "Chicago, IL, USA"
    client.geocode("chicago IL")
    assert route.call_count == 1


@respx.mock
def test_geocode_not_found():
    respx.get(f"{BASE}/geocode/search").respond(json={"features": []})
    with pytest.raises(GeocodingError):
        OrsClient().geocode("zzzz")


@respx.mock
def test_directions_parses_steps_into_time_knots_and_summary():
    respx.post(f"{BASE}/v2/directions/driving-hgv/geojson").respond(
        json={"features": [feature(COORDS, 160934.4, 7200)]}
    )
    route = OrsClient().directions([(-100, 40), (-100, 43)], load_lb=40000)[0]
    assert route.distance_mi == pytest.approx(100)
    assert route.summary == "via I-80"
    assert route.time_knots[-1] == pytest.approx((100.0, 7200.0))
    assert route.seconds_at(80) == pytest.approx(3600)


@respx.mock
def test_directions_retries_once_on_503_then_succeeds():
    respx.post(f"{BASE}/v2/directions/driving-hgv/geojson").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"features": [feature(COORDS, 1000, 60)]}),
        ]
    )
    assert len(OrsClient().directions([(-100, 40), (-100, 43)])) == 1


@respx.mock
def test_directions_gives_upstream_error_after_repeated_failure():
    respx.post(f"{BASE}/v2/directions/driving-hgv/geojson").respond(503)
    with pytest.raises(UpstreamError):
        OrsClient().directions([(-100, 40), (-100, 43)])


@respx.mock
def test_directions_client_error_becomes_routing_error():
    respx.post(f"{BASE}/v2/directions/driving-hgv/geojson").respond(
        404, json={"error": {"message": "Could not find routable point"}}
    )
    with pytest.raises(RoutingError, match="routable"):
        OrsClient().directions([(-100, 40), (-100, 43)])


@respx.mock
def test_directions_cached_by_request():
    route = respx.post(f"{BASE}/v2/directions/driving-hgv/geojson").respond(
        json={"features": [feature(COORDS, 1000, 60)]}
    )
    client = OrsClient()
    client.directions([(-100, 40), (-100, 43)], load_lb=1000)
    client.directions([(-100, 40), (-100, 43)], load_lb=1000)
    assert route.call_count == 1


class FakeOrs:
    """Returns a different corridor depending on whether a via-point is east or west."""

    def __init__(self, fail_vias=False):
        self.calls = []
        self.fail_vias = fail_vias

    def directions(self, waypoints, *, load_lb=0, alternatives=0):
        self.calls.append((len(waypoints), alternatives))
        if len(waypoints) == 2:
            return [make_route(0.0, 1000, 10)]
        if self.fail_vias:
            raise RoutingError("nope")
        lon_shift = 1.5 if waypoints[1][0] > waypoints[0][0] else -1.5
        return [make_route(lon_shift, 1200, 12)]


def make_route(lon_shift, miles, hours):
    coords = [(-100.0 + lon_shift, 30.0 + i) for i in range(0, 15)]
    return Route(
        coords=coords,
        distance_mi=miles,
        duration_s=hours * 3600,
        time_knots=[(0, 0), (miles, hours * 3600)],
    )


A = Place("A", -100.0, 30.0)
B = Place("B", -100.0, 44.0)


def test_long_trip_builds_three_distinct_routes_fastest_first():
    fake = FakeOrs()
    routes = generate_routes(fake, A, B, load_lb=0)
    assert len(routes) == 3
    assert [r.duration_s for r in routes] == sorted(r.duration_s for r in routes)
    assert (2, 2) not in fake.calls  # no native alternatives for a long trip


def test_failed_via_candidates_degrade_to_single_route():
    routes = generate_routes(FakeOrs(fail_vias=True), A, B, load_lb=0)
    assert len(routes) == 1
