import pytest

from apps.routing.geo import (
    cumulative_miles,
    haversine_mi,
    offset_perpendicular,
    overlap_fraction,
    point_at_mile,
)
from apps.routing.models import Route
from apps.routing.sampling import make_checkpoints

CHICAGO = (-87.65, 41.85)
DENVER = (-104.99, 39.74)


def test_haversine_known_distance():
    assert haversine_mi(CHICAGO, DENVER) == pytest.approx(920, abs=10)


def test_point_at_mile_interpolates_and_clamps():
    coords = [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]
    cum = cumulative_miles(coords)
    assert point_at_mile(coords, cum, -5) == coords[0]
    assert point_at_mile(coords, cum, 9999) == coords[-1]
    lon, lat = point_at_mile(coords, cum, cum[1])
    assert (lon, lat) == pytest.approx((0.0, 1.0))
    assert point_at_mile(coords, cum, cum[1] / 2)[1] == pytest.approx(0.5)


def test_offset_is_perpendicular_and_signed():
    a, b = (-100.0, 40.0), (-90.0, 40.0)  # due east
    mid = (-95.0, 40.0)
    left = offset_perpendicular(a, b, mid, 50)
    right = offset_perpendicular(a, b, mid, -50)
    assert left[0] == pytest.approx(mid[0])
    assert left[1] > mid[1] > right[1]
    assert haversine_mi(mid, left) == pytest.approx(50, rel=0.05)


def straight_route(miles: float, hours: float) -> Route:
    deg = miles / 69.0
    return Route(
        coords=[(-100.0, 40.0), (-100.0, 40.0 + deg)],
        distance_mi=miles,
        duration_s=hours * 3600,
        time_knots=[(0.0, 0.0), (miles, hours * 3600)],
    )


def test_overlap_fraction_identical_and_disjoint():
    r1 = straight_route(100, 2)
    far = Route(
        coords=[(-90.0, 40.0), (-90.0, 41.5)],
        distance_mi=100,
        duration_s=7200,
        time_knots=[(0, 0), (100, 7200)],
    )
    assert overlap_fraction(r1.coords, r1.cum, r1.coords, r1.cum) == 1.0
    assert overlap_fraction(far.coords, far.cum, r1.coords, r1.cum) == 0.0


def test_checkpoints_include_start_and_end_with_monotonic_eta():
    route = straight_route(110, 2)
    cps = make_checkpoints(route, 25)
    assert [c.mile for c in cps] == [0, 25, 50, 75, 100, 110]
    assert cps[0].elapsed_s == 0
    assert cps[-1].elapsed_s == pytest.approx(7200)
    assert all(b.elapsed_s > a.elapsed_s for a, b in zip(cps, cps[1:], strict=False))


def test_final_checkpoint_not_duplicated_when_close_to_end():
    cps = make_checkpoints(straight_route(101, 2), 25)
    assert [c.mile for c in cps] == [0, 25, 50, 75, 101]


def test_seconds_follow_slow_and_fast_segments():
    route = Route(
        coords=[(-100.0, 40.0), (-100.0, 41.5)],
        distance_mi=100,
        duration_s=5400,
        time_knots=[(0, 0), (10, 1800), (100, 5400)],  # slow city leg then highway
    )
    assert route.seconds_at(5) == pytest.approx(900)
    assert route.seconds_at(55) == pytest.approx(3600)
