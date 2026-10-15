"""MET Norway (api.met.no) forecast client, used when Open-Meteo is unavailable.

Keyless and free, but one request per location. Differences from Open-Meteo, handled here:
  * wind is m/s  -> converted to mph;
  * no snowfall variable: hourly precipitation (mm water) is split into rain or snow by
    air temperature, and snow depth is estimated with a 10:1 snow-to-liquid ratio;
  * hourly steps for ~2.5 days, then 6-hourly: coarser steps are forward-filled.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

from apps.trips.errors import UpstreamError

from .client import LatLon, snap
from .models import HourlySeries

logger = logging.getLogger(__name__)

URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
USER_AGENT = "weather-aware-truck-routing/1.0 github.com/AbidAli-274/Spotter"
MS_TO_MPH = 2.236936
MM_PER_INCH = 25.4
SNOW_RATIO = 10.0  # cm of snow per cm of liquid water
SNOW_MAX_TEMP_C = 0.5
MAX_WORKERS = 4  # MET asks for <= 20 requests/second


class MetNorwayClient:
    source = "met-norway"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            timeout=settings.HTTP_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}
        )

    def hourly(self, points: list[LatLon], start: date, end: date) -> dict[LatLon, HourlySeries]:
        unique = sorted({snap(*p) for p in points})
        keys = {p: f"met:{p[0]}:{p[1]}" for p in unique}
        cached = cache.get_many(keys.values())
        result = {p: cached[k] for p, k in keys.items() if k in cached}
        missing = [p for p in unique if p not in result]
        if missing:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                fetched = list(pool.map(self._fetch, missing))
            for point, series in zip(missing, fetched, strict=True):
                result[point] = series
            cache.set_many(
                {keys[p]: s for p, s in zip(missing, fetched, strict=True)},
                settings.WEATHER_CACHE_TTL,
            )
        return result

    def _fetch(self, point: LatLon) -> HourlySeries:
        params = {"lat": f"{point[0]:.2f}", "lon": f"{point[1]:.2f}"}
        response = None
        for _attempt in range(2):
            try:
                response = self._client.get(URL, params=params)
            except httpx.TransportError as exc:
                logger.warning("MET Norway transport error: %s", exc)
                continue
            if response.status_code < 500:
                break
        if response is None or response.status_code >= 400:
            status = response.status_code if response is not None else "no response"
            logger.warning("MET Norway failed (%s)", status)
            raise UpstreamError(f"The backup weather provider failed (HTTP {status}).")
        return parse_timeseries(response.json()["properties"]["timeseries"])


def parse_timeseries(timeseries: list[dict[str, Any]]) -> HourlySeries:
    """Expand MET's mixed hourly / 6-hourly entries onto a single hourly grid."""
    times = [
        datetime.fromisoformat(t["time"].replace("Z", "+00:00")).astimezone(UTC) for t in timeseries
    ]
    start = times[0].replace(minute=0, second=0, microsecond=0)
    total = int((times[-1] - start).total_seconds() // 3600) + 7
    wind: list[float | None] = [None] * total
    rain: list[float | None] = [None] * total
    snow: list[float | None] = [None] * total

    for when, entry in zip(times, timeseries, strict=True):
        data = entry["data"]
        details = data["instant"]["details"]
        if "next_1_hours" in data:
            span, liquid_mm = 1, data["next_1_hours"]["details"].get("precipitation_amount", 0.0)
        elif "next_6_hours" in data:
            span = 6
            liquid_mm = data["next_6_hours"]["details"].get("precipitation_amount", 0.0) / 6
        else:
            span, liquid_mm = 1, 0.0
        is_snow = details.get("air_temperature", 10.0) <= SNOW_MAX_TEMP_C
        rain_in = 0.0 if is_snow else liquid_mm / MM_PER_INCH
        snow_in = liquid_mm * SNOW_RATIO / MM_PER_INCH if is_snow else 0.0
        base = int((when - start).total_seconds() // 3600)
        for i in range(base, min(base + span, total)):
            wind[i] = details.get("wind_speed", 0.0) * MS_TO_MPH
            rain[i], snow[i] = rain_in, snow_in

    return HourlySeries(
        start=start, wind_mph=tuple(wind), rain_in_hr=tuple(rain), snow_in_hr=tuple(snow)
    )
