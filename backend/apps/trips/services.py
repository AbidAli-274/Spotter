"""Orchestrates a trip analysis: routes -> checkpoints -> weather -> risk -> recommendation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from apps.risk.metrics import compute_metrics
from apps.risk.models import CheckpointRisk, RiskLevel, RouteMetrics
from apps.risk.ranking import Recommendation, rank, recommend
from apps.risk.rules import assess
from apps.routing.alternatives import generate_routes
from apps.routing.geo import decimate
from apps.routing.models import Place, Route
from apps.routing.ors import OrsClient
from apps.routing.sampling import Checkpoint, make_checkpoints
from apps.weather.client import LatLon, OpenMeteoClient, forecast_horizon, snap
from apps.weather.models import HourlySeries

from .errors import ForecastRangeError
from .schemas import PlaceInput, TripRequest

HEATMAP_HOURS = 48
HEATMAP_MIN_SPACING_MI = 20.0
HEATMAP_MAX_POINTS_PER_ROUTE = 40
HEATMAP_CELL_DEG = 0.2  # merge overlapping routes into one grid cell (~14 mi)
PAST_TOLERANCE = timedelta(hours=2)
UNKNOWN = -1
ROUTE_LETTERS = "ABCDEFG"


@dataclass(slots=True)
class AnalyzedRoute:
    route: Route
    checkpoints: list[dict[str, Any]]
    metrics: RouteMetrics
    worst: RiskLevel | None


def validate_departure(departure: datetime, now: datetime | None = None) -> None:
    now = now or datetime.now(UTC)
    if departure < now - PAST_TOLERANCE:
        raise ForecastRangeError("Departure time is in the past.")
    if departure.date() > forecast_horizon(now.date()) - timedelta(days=1):
        raise ForecastRangeError(
            "Weather forecasts are only available about 15 days ahead. Choose an earlier departure."
        )


class TripAnalyzer:
    def __init__(self, ors: OrsClient | None = None, weather: OpenMeteoClient | None = None):
        self.ors = ors or OrsClient()
        self.weather = weather or OpenMeteoClient()

    def analyze(self, req: TripRequest) -> dict[str, Any]:
        validate_departure(req.departure)
        origin = self._resolve(req.origin)
        destination = self._resolve(req.destination)

        routes = generate_routes(self.ors, origin, destination, req.load_lb)
        checkpoint_sets = [make_checkpoints(r, req.interval_mi) for r in routes]
        heat_points = self._heatmap_points(routes)

        series = self._fetch_weather(req.departure, routes, checkpoint_sets, heat_points)
        analyzed = [
            self._analyze_route(r, cps, series, req)
            for r, cps in zip(routes, checkpoint_sets, strict=True)
        ]
        metrics = [a.metrics for a in analyzed]
        rec = recommend(metrics)
        order = rank(metrics)
        return {
            "origin": _place(origin),
            "destination": _place(destination),
            "departure": req.departure,
            "load_lb": req.load_lb,
            "interval_mi": req.interval_mi,
            "recommendation": _recommendation(rec),
            "routes": [
                self._route_payload(i, a, order.index(i) + 1, rec.index == i, req.departure)
                for i, a in enumerate(analyzed)
            ],
            "heatmap": self._heatmap(heat_points, series, req),
        }

    # -- steps -------------------------------------------------------------------
    def _resolve(self, spec: PlaceInput) -> Place:
        if spec.lat is not None and spec.lon is not None:
            return Place(spec.label, spec.lon, spec.lat)
        return self.ors.geocode(spec.label)

    @staticmethod
    def _heatmap_points(routes: list[Route]) -> list[LatLon]:
        cells: dict[tuple[int, int], LatLon] = {}
        for route in routes:
            spacing = max(HEATMAP_MIN_SPACING_MI, route.distance_mi / HEATMAP_MAX_POINTS_PER_ROUTE)
            for cp in make_checkpoints(route, spacing):
                lon, lat = cp.lonlat
                cell = (round(lat / HEATMAP_CELL_DEG), round(lon / HEATMAP_CELL_DEG))
                cells.setdefault(cell, snap(lat, lon))
        return sorted(cells.values())

    def _fetch_weather(
        self,
        departure: datetime,
        routes: list[Route],
        checkpoint_sets: list[list[Checkpoint]],
        heat_points: list[LatLon],
    ) -> dict[LatLon, HourlySeries]:
        start: date = departure.astimezone(UTC).date()
        latest = max(
            [departure + timedelta(seconds=r.duration_s) for r in routes]
            + [departure + timedelta(hours=HEATMAP_HOURS)]
        )
        points = {snap(cp.lonlat[1], cp.lonlat[0]) for cps in checkpoint_sets for cp in cps}
        points.update(heat_points)
        return self.weather.hourly(points, start, latest.astimezone(UTC).date())

    def _analyze_route(
        self,
        route: Route,
        checkpoints: list[Checkpoint],
        series: dict[LatLon, HourlySeries],
        req: TripRequest,
    ) -> AnalyzedRoute:
        rows: list[dict[str, Any]] = []
        risks: list[CheckpointRisk] = []
        for i, cp in enumerate(checkpoints):
            eta = req.departure + timedelta(seconds=cp.elapsed_s)
            hourly = series.get(snap(cp.lonlat[1], cp.lonlat[0]))
            sample = hourly.at(eta) if hourly else None
            assessment = assess(sample, req.load_lb) if sample else None
            level = assessment.level if assessment else None
            risks.append(CheckpointRisk(cp.mile, level))
            rows.append(
                {
                    "index": i,
                    "mile": round(cp.mile, 1),
                    "lat": round(cp.lonlat[1], 5),
                    "lon": round(cp.lonlat[0], 5),
                    "eta": eta,
                    "weather": (
                        {
                            "wind_mph": round(sample.wind_mph, 1),
                            "rain_in_hr": round(sample.rain_in_hr, 3),
                            "snow_in_hr": round(sample.snow_in_hr, 3),
                        }
                        if sample
                        else None
                    ),
                    "risk": _level(level),
                    "risk_value": int(level) if level is not None else UNKNOWN,
                    "drivers": list(assessment.drivers) if assessment else [],
                    "load_adjusted": bool(assessment and assessment.load_adjusted),
                }
            )
        metrics = compute_metrics(risks, route.distance_mi, route.duration_s)
        known = [r.level for r in risks if r.level is not None]
        return AnalyzedRoute(route, rows, metrics, max(known) if known else None)

    def _route_payload(
        self, i: int, a: AnalyzedRoute, rank_: int, recommended: bool, departure: datetime
    ) -> dict[str, Any]:
        m = a.metrics
        return {
            "id": f"route-{i + 1}",
            "name": f"Route {ROUTE_LETTERS[i]}",
            "summary": a.route.summary,
            "distance_mi": round(a.route.distance_mi, 1),
            "duration_s": round(a.route.duration_s),
            "arrival": departure + timedelta(seconds=a.route.duration_s),
            "rank": rank_,
            "recommended": recommended,
            "geometry": [[round(x, 5), round(y, 5)] for x, y in decimate(a.route.coords)],
            "metrics": {
                "miles_by_level": {_level(lv): round(m.miles(lv), 1) for lv in RiskLevel},
                "unknown_miles": round(m.unknown_miles, 1),
                "avg_risk": round(m.avg_risk, 2),
                "worst_level": _level(a.worst),
            },
            "checkpoints": a.checkpoints,
        }

    @staticmethod
    def _heatmap(
        points: list[LatLon], series: dict[LatLon, HourlySeries], req: TripRequest
    ) -> dict[str, Any]:
        start = req.departure.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        rows = []
        for point in points:
            hourly = series.get(point)
            levels = []
            for h in range(HEATMAP_HOURS):
                sample = hourly.at(start + timedelta(hours=h)) if hourly else None
                levels.append(int(assess(sample, req.load_lb).level) if sample else UNKNOWN)
            rows.append({"lat": point[0], "lon": point[1], "levels": levels})
        return {"start": start, "hours": HEATMAP_HOURS, "points": rows}


def _place(p: Place) -> dict[str, Any]:
    return {"label": p.label, "lat": p.lat, "lon": p.lon}


def _level(level: RiskLevel | None) -> str | None:
    return level.name.lower() if level is not None else None


def _recommendation(rec: Recommendation) -> dict[str, Any]:
    return {
        "route_index": rec.index,
        "route_id": f"route-{rec.index + 1}",
        "reason": rec.reason,
        "all_blocked": rec.all_blocked,
    }
