"""Open-Meteo forecast client (free, keyless, batched multi-location)."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta

import httpx
from django.conf import settings
from django.core.cache import cache

from apps.trips.errors import UpstreamError

from .models import HourlySeries

logger = logging.getLogger(__name__)

LatLon = tuple[float, float]
CHUNK_SIZE = 50  # locations per request keeps the URL comfortably short
COORD_DECIMALS = 2  # ~1 km; the forecast grid is coarser than that
MAX_FORECAST_DAYS = 15  # Open-Meteo serves up to 16 days including today
HOURLY_VARS = "wind_speed_10m,rain,showers,snowfall"


def forecast_horizon(today: date | None = None) -> date:
    return (today or datetime.now(UTC).date()) + timedelta(days=MAX_FORECAST_DAYS)


def snap(lat: float, lon: float) -> LatLon:
    return (round(lat, COORD_DECIMALS), round(lon, COORD_DECIMALS))


class OpenMeteoClient:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS)

    def hourly(
        self, points: Iterable[LatLon], start: date, end: date
    ) -> dict[LatLon, HourlySeries]:
        """Hourly series per (snapped) point covering `start`..`end` inclusive (UTC dates).

        `end` is clamped to the forecast horizon; hours beyond it are simply absent.
        """
        end = min(end, forecast_horizon())
        unique = sorted({snap(*p) for p in points})
        keys = {p: f"om:{p[0]}:{p[1]}:{start}:{end}" for p in unique}
        cached = cache.get_many(keys.values())
        result: dict[LatLon, HourlySeries] = {}
        missing: list[LatLon] = []
        for point, key in keys.items():
            if key in cached:
                result[point] = cached[key]
            else:
                missing.append(point)

        chunks = [missing[i : i + CHUNK_SIZE] for i in range(0, len(missing), CHUNK_SIZE)]
        if chunks:
            with ThreadPoolExecutor(max_workers=min(4, len(chunks))) as pool:
                for fetched in pool.map(lambda c: self._fetch(c, start, end), chunks):
                    result.update(fetched)
            cache.set_many(
                {keys[p]: result[p] for p in missing if p in result}, settings.WEATHER_CACHE_TTL
            )
        return result

    def _fetch(self, points: list[LatLon], start: date, end: date) -> dict[LatLon, HourlySeries]:
        params = {
            "latitude": ",".join(str(p[0]) for p in points),
            "longitude": ",".join(str(p[1]) for p in points),
            "hourly": HOURLY_VARS,
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "UTC",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        response = None
        for _attempt in range(2):
            try:
                response = self._client.get(settings.OPEN_METEO_URL, params=params)
            except httpx.TransportError as exc:
                logger.warning("Open-Meteo transport error: %s", exc)
                continue
            if response.status_code < 500:
                break
        if response is None or response.status_code >= 400:
            status = response.status_code if response is not None else "no response"
            reason = _reason(response)
            logger.warning("Open-Meteo failed (%s): %s", status, reason)
            raise UpstreamError(
                f"The weather provider is unavailable (HTTP {status}: {reason}). "
                "Please retry shortly."
            )

        payload = response.json()
        items = payload if isinstance(payload, list) else [payload]
        return {pt: self._parse(item) for pt, item in zip(points, items, strict=True)}

    @staticmethod
    def _parse(item: dict) -> HourlySeries:
        hourly = item["hourly"]
        start = datetime.fromisoformat(hourly["time"][0]).replace(tzinfo=UTC)

        def column(name: str) -> list[float | None]:
            return hourly[name]

        rain = [_sum(r, s) for r, s in zip(column("rain"), column("showers"), strict=True)]
        return HourlySeries(
            start=start,
            wind_mph=tuple(column("wind_speed_10m")),
            rain_in_hr=tuple(rain),
            snow_in_hr=tuple(column("snowfall")),
        )


def _sum(a: float | None, b: float | None) -> float | None:
    if a is None and b is None:
        return None
    return (a or 0.0) + (b or 0.0)


def _reason(response: httpx.Response | None) -> str:
    """Short provider-supplied reason (Open-Meteo returns {"reason": "..."} on errors)."""
    if response is None:
        return "no response"
    try:
        return str(response.json().get("reason", response.text))[:160]
    except ValueError:
        return response.text[:160]
