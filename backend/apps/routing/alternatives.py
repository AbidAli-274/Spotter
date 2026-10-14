"""Generate up to three distinct route options between two places.

ORS only supports native alternative routes for trips under ~100 km, so:
  * short trips ask ORS for native alternatives;
  * longer trips (and short ones where ORS returns too few) are built by routing through a
    via-point offset perpendicular to the trip direction on either side, keeping only
    candidates that are genuinely different corridors and not absurd detours.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from apps.trips.errors import ServiceError

from .geo import haversine_mi, offset_perpendicular, overlap_fraction
from .models import Place, Route
from .ors import OrsClient

logger = logging.getLogger(__name__)

TARGET_ROUTES = 3
NATIVE_MAX_STRAIGHT_MI = 40  # keep well inside ORS's 100 km native-alternatives cap
OFFSET_FRACTIONS = (0.10, 0.22)  # via-point distance as a share of the straight-line trip
MAX_OFFSET_MI = 250.0
MAX_DETOUR_RATIO = 1.6  # candidate distance vs fastest route
MAX_OVERLAP = 0.75  # share of a candidate allowed to follow an already-chosen route


def is_distinct(candidate: Route, chosen: list[Route]) -> bool:
    return all(
        overlap_fraction(candidate.coords, candidate.cum, r.coords, r.cum) < MAX_OVERLAP
        for r in chosen
    )


def generate_routes(
    ors: OrsClient,
    origin: Place,
    destination: Place,
    load_lb: float,
    target: int = TARGET_ROUTES,
    on_candidate_error: Callable[[Exception], None] | None = None,
) -> list[Route]:
    """Fastest-first list of 1..target distinct routes."""
    a, b = origin.lonlat, destination.lonlat
    straight = haversine_mi(a, b)

    routes: list[Route] = []
    if straight <= NATIVE_MAX_STRAIGHT_MI:
        try:
            native = ors.directions([a, b], load_lb=load_lb, alternatives=target - 1)
        except ServiceError as exc:
            logger.info("Native alternatives unavailable: %s", exc)
            native = []
        for route in native:
            if is_distinct(route, routes):
                routes.append(route)
    if not routes:
        routes = ors.directions([a, b], load_lb=load_lb)[:1]  # errors here are fatal

    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    for fraction in OFFSET_FRACTIONS:
        if len(routes) >= target:
            break
        offset = min(straight * fraction, MAX_OFFSET_MI)
        vias = [offset_perpendicular(a, b, mid, sign * offset) for sign in (1, -1)]
        with ThreadPoolExecutor(max_workers=len(vias)) as pool:
            futures = [pool.submit(ors.directions, [a, via, b], load_lb=load_lb) for via in vias]
        candidates: list[Route] = []
        for future in futures:
            try:
                candidates.extend(future.result())
            except ServiceError as exc:
                logger.info("Via-point candidate failed: %s", exc)
                if on_candidate_error:
                    on_candidate_error(exc)
        fastest = routes[0].distance_mi
        for candidate in sorted(candidates, key=lambda r: r.duration_s):
            if len(routes) >= target:
                break
            if candidate.distance_mi <= fastest * MAX_DETOUR_RATIO and is_distinct(
                candidate, routes
            ):
                routes.append(candidate)

    return sorted(routes, key=lambda r: r.duration_s)
