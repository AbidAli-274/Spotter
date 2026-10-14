"""OpenRouteService client: geocoding autocomplete and HGV directions."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

from apps.trips.errors import GeocodingError, RoutingError, UpstreamError

from .geo import METERS_PER_MILE
from .models import Place, Route

logger = logging.getLogger(__name__)

PROFILE = "driving-hgv"
LB_TO_TONNES = 0.000453592
RETRY_STATUSES = {502, 503, 504}


def _cache_key(prefix: str, payload: Any) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]
    return f"{prefix}:{digest}"


class OrsClient:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            base_url=settings.ORS_BASE_URL, timeout=settings.HTTP_TIMEOUT_SECONDS
        )

    # -- HTTP ------------------------------------------------------------------
    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not settings.ORS_API_KEY:
            raise UpstreamError("ORS_API_KEY is not configured on the server.")
        headers = {"Authorization": settings.ORS_API_KEY}
        last_error: Exception | None = None
        for _attempt in range(2):  # one retry on transient failures
            try:
                response = self._client.request(method, path, headers=headers, **kwargs)
            except httpx.TransportError as exc:
                last_error = exc
                continue
            if response.status_code in RETRY_STATUSES:
                last_error = RuntimeError(f"ORS returned {response.status_code}")
                continue
            return response
        logger.warning("ORS request failed: %s", last_error)
        raise UpstreamError("The routing provider is unavailable. Please retry shortly.")

    # -- Geocoding ---------------------------------------------------------------
    def autocomplete(self, text: str, size: int = 5) -> list[Place]:
        text = " ".join(text.split())
        key = _cache_key("ors-ac", [text.lower(), size])
        if (hit := cache.get(key)) is not None:
            return [Place(*p) for p in hit]
        response = self._request(
            "GET",
            "/geocode/autocomplete",
            params={"text": text, "size": size, "boundary.country": "US"},
        )
        places = self._places(response)
        cache.set(key, [(p.label, p.lon, p.lat) for p in places], settings.GEOCODE_CACHE_TTL)
        return places

    def geocode(self, text: str) -> Place:
        text = " ".join(text.split())
        key = _cache_key("ors-geo", text.lower())
        if (hit := cache.get(key)) is not None:
            return Place(*hit)
        response = self._request(
            "GET",
            "/geocode/search",
            params={"text": text, "size": 1, "boundary.country": "US"},
        )
        places = self._places(response)
        if not places:
            raise GeocodingError(f"Could not find a U.S. location for '{text}'.")
        place = places[0]
        cache.set(key, (place.label, place.lon, place.lat), settings.GEOCODE_CACHE_TTL)
        return place

    @staticmethod
    def _places(response: httpx.Response) -> list[Place]:
        if response.status_code == 429:
            raise UpstreamError("Geocoding rate limit reached. Please retry shortly.")
        if response.status_code >= 400:
            raise UpstreamError("The geocoding provider returned an error.")
        features = response.json().get("features", [])
        return [
            Place(
                label=f["properties"].get("label", "Unknown"),
                lon=f["geometry"]["coordinates"][0],
                lat=f["geometry"]["coordinates"][1],
            )
            for f in features
        ]

    # -- Directions ----------------------------------------------------------------
    def directions(
        self,
        waypoints: list[tuple[float, float]],
        *,
        load_lb: float = 0,
        alternatives: int = 0,
    ) -> list[Route]:
        """Routes through `waypoints` ([lon, lat]...). `alternatives` > 0 asks ORS for extra
        routes; ORS only supports that for trips under ~100 km."""
        body: dict[str, Any] = {
            "coordinates": [list(w) for w in waypoints],
            "instructions": True,
            "radiuses": [-1] * len(waypoints),  # snap to the nearest road at any distance
            "options": {
                "vehicle_type": "hgv",
                "profile_params": {"restrictions": {"weight": round(load_lb * LB_TO_TONNES, 2)}},
            },
        }
        if alternatives:
            body["alternative_routes"] = {
                "target_count": alternatives + 1,
                "share_factor": 0.6,
                "weight_factor": 1.6,
            }
        key = _cache_key("ors-dir", body)
        if (hit := cache.get(key)) is not None:
            return [self._route_from_cache(r) for r in hit]

        response = self._request("POST", f"/v2/directions/{PROFILE}/geojson", json=body)
        if response.status_code == 429:
            raise UpstreamError("Routing rate limit reached. Please retry in a minute.")
        if response.status_code >= 400:
            message = self._error_message(response)
            raise RoutingError(f"No drivable route found: {message}")
        routes = [self._parse_route(f) for f in response.json().get("features", [])]
        if not routes:
            raise RoutingError("No drivable route found between those locations.")
        cache.set(key, [self._route_to_cache(r) for r in routes], settings.ROUTE_CACHE_TTL)
        return routes

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            return response.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            return f"provider returned HTTP {response.status_code}"

    @staticmethod
    def _parse_route(feature: dict[str, Any]) -> Route:
        props = feature["properties"]
        summary = props["summary"]
        knots: list[tuple[float, float]] = [(0.0, 0.0)]
        road_meters: dict[str, float] = {}
        meters = seconds = 0.0
        for segment in props.get("segments", []):
            for step in segment.get("steps", []):
                meters += step["distance"]
                seconds += step["duration"]
                knots.append((meters / METERS_PER_MILE, seconds))
                name = step.get("name") or "-"
                if name != "-":
                    road_meters[name] = road_meters.get(name, 0.0) + step["distance"]
        distance_mi = summary["distance"] / METERS_PER_MILE
        if len(knots) < 2:  # no instructions returned; fall back to constant speed
            knots = [(0.0, 0.0), (distance_mi, summary["duration"])]
        top_roads = sorted(road_meters, key=road_meters.__getitem__, reverse=True)[:2]
        return Route(
            coords=[tuple(c[:2]) for c in feature["geometry"]["coordinates"]],
            distance_mi=distance_mi,
            duration_s=summary["duration"],
            time_knots=knots,
            summary=("via " + ", ".join(top_roads)) if top_roads else "",
        )

    @staticmethod
    def _route_to_cache(route: Route) -> dict[str, Any]:
        return {
            "coords": route.coords,
            "distance_mi": route.distance_mi,
            "duration_s": route.duration_s,
            "knots": route.time_knots,
            "summary": route.summary,
        }

    @staticmethod
    def _route_from_cache(data: dict[str, Any]) -> Route:
        return Route(
            coords=[tuple(c) for c in data["coords"]],
            distance_mi=data["distance_mi"],
            duration_s=data["duration_s"],
            time_knots=[tuple(k) for k in data["knots"]],
            summary=data["summary"],
        )
