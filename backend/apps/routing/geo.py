"""Small, dependency-free geodesy helpers (spherical earth is plenty accurate here)."""

from __future__ import annotations

import bisect
import math
from collections.abc import Sequence

EARTH_RADIUS_MI = 3958.7613
METERS_PER_MILE = 1609.344

LonLat = tuple[float, float]


def haversine_mi(a: LonLat, b: LonLat) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def cumulative_miles(coords: Sequence[LonLat]) -> list[float]:
    """Distance from the start of the polyline to each vertex, in miles."""
    out = [0.0]
    for prev, cur in zip(coords, coords[1:], strict=False):
        out.append(out[-1] + haversine_mi(prev, cur))
    return out


def point_at_mile(coords: Sequence[LonLat], cum: Sequence[float], mile: float) -> LonLat:
    """Interpolate the coordinate `mile` miles along the polyline (clamped to its ends)."""
    if mile <= 0:
        return coords[0]
    if mile >= cum[-1]:
        return coords[-1]
    i = bisect.bisect_right(cum, mile)
    span = cum[i] - cum[i - 1]
    t = (mile - cum[i - 1]) / span if span else 0.0
    (lon1, lat1), (lon2, lat2) = coords[i - 1], coords[i]
    return (lon1 + (lon2 - lon1) * t, lat1 + (lat2 - lat1) * t)


def offset_perpendicular(a: LonLat, b: LonLat, mid: LonLat, miles: float) -> LonLat:
    """Point `miles` away from `mid`, perpendicular to the a→b direction.

    Positive miles offsets to the left of travel, negative to the right.
    Uses a local equirectangular projection, accurate for offsets of a few hundred miles.
    """
    lat0 = math.radians(mid[1])
    dx = (b[0] - a[0]) * math.cos(lat0)  # east component
    dy = b[1] - a[1]  # north component
    norm = math.hypot(dx, dy) or 1.0
    left_x, left_y = -dy / norm, dx / norm
    deg = miles / 69.0  # ~miles per degree of latitude
    return (mid[0] + left_x * deg / math.cos(lat0), mid[1] + left_y * deg)


def overlap_fraction(
    candidate: Sequence[LonLat],
    candidate_cum: Sequence[float],
    other: Sequence[LonLat],
    other_cum: Sequence[float],
    tolerance_mi: float = 2.0,
    step_mi: float = 5.0,
) -> float:
    """Share of `candidate`'s length that lies within `tolerance_mi` of `other`."""
    total = candidate_cum[-1]
    if total <= 0:
        return 1.0
    other_pts = [point_at_mile(other, other_cum, m) for m in _steps(other_cum[-1], step_mi / 2)]
    cell = tolerance_mi / 69.0
    grid: dict[tuple[int, int], list[LonLat]] = {}
    for p in other_pts:
        grid.setdefault((int(p[0] / cell), int(p[1] / cell)), []).append(p)

    near = count = 0
    for m in _steps(total, step_mi):
        p = point_at_mile(candidate, candidate_cum, m)
        cx, cy = int(p[0] / cell), int(p[1] / cell)
        count += 1
        if any(
            haversine_mi(p, q) <= tolerance_mi
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for q in grid.get((cx + dx, cy + dy), ())
        ):
            near += 1
    return near / count if count else 1.0


def _steps(total: float, step: float) -> list[float]:
    n = max(1, math.ceil(total / step))
    return [total * i / n for i in range(n + 1)]
