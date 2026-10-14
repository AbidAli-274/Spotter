from __future__ import annotations

import bisect
from dataclasses import dataclass, field

from .geo import LonLat, cumulative_miles, point_at_mile


@dataclass(frozen=True, slots=True)
class Place:
    label: str
    lon: float
    lat: float

    @property
    def lonlat(self) -> LonLat:
        return (self.lon, self.lat)


@dataclass(slots=True)
class Route:
    """A drivable route with a distance→time curve for ETA lookups."""

    coords: list[LonLat]
    distance_mi: float
    duration_s: float
    # (miles_from_start, seconds_from_start) at maneuver boundaries, ascending.
    time_knots: list[tuple[float, float]]
    summary: str = ""
    cum: list[float] = field(init=False)

    def __post_init__(self) -> None:
        self.cum = cumulative_miles(self.coords)

    def point_at(self, mile: float) -> LonLat:
        # Provider distance and polyline length differ slightly; scale to stay consistent.
        scale = self.cum[-1] / self.distance_mi if self.distance_mi else 1.0
        return point_at_mile(self.coords, self.cum, mile * scale)

    def seconds_at(self, mile: float) -> float:
        """Elapsed driving time at `mile`, interpolated between maneuver knots."""
        knots = self.time_knots
        if mile <= knots[0][0]:
            return knots[0][1]
        if mile >= knots[-1][0]:
            return knots[-1][1]
        i = bisect.bisect_right([k[0] for k in knots], mile)
        (m0, s0), (m1, s1) = knots[i - 1], knots[i]
        t = (mile - m0) / (m1 - m0) if m1 > m0 else 0.0
        return s0 + (s1 - s0) * t
