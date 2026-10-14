"""Checkpoint placement along a route."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .geo import LonLat
from .models import Route

ALLOWED_INTERVALS_MI = (10, 25, 50)


@dataclass(frozen=True, slots=True)
class Checkpoint:
    mile: float
    lonlat: LonLat
    elapsed_s: float


def make_checkpoints(route: Route, interval_mi: float) -> list[Checkpoint]:
    """Checkpoints every `interval_mi` miles, always including start and end."""
    total = route.distance_mi
    miles = [i * interval_mi for i in range(math.floor(total / interval_mi) + 1)]
    # Skip a final sample that would sit almost on top of the destination.
    if total - miles[-1] > interval_mi * 0.1:
        miles.append(total)
    else:
        miles[-1] = total
    return [Checkpoint(m, route.point_at(m), route.seconds_at(m)) for m in miles]
