"""Weather client that falls back to a secondary provider when the primary is unavailable."""

from __future__ import annotations

import logging
from datetime import date

from django.core.cache import cache

from apps.trips.errors import UpstreamError

from .client import LatLon, OpenMeteoClient
from .met_norway import MetNorwayClient
from .models import HourlySeries

logger = logging.getLogger(__name__)

PRIMARY_DOWN_KEY = "weather:primary-down"
PRIMARY_COOLDOWN_S = 10 * 60  # after a failure, go straight to the fallback for a while


class ResilientWeatherClient:
    """Open-Meteo first (richer, batched), MET Norway if it is rate-limited or down.

    `source` names the provider that served the last call so the API can report it.
    """

    def __init__(self, primary=None, fallback=None) -> None:
        self.primary = primary or OpenMeteoClient()
        self.fallback = fallback or MetNorwayClient()
        self.source = self.primary.source

    def hourly(self, points: list[LatLon], start: date, end: date) -> dict[LatLon, HourlySeries]:
        if not cache.get(PRIMARY_DOWN_KEY):
            try:
                result = self.primary.hourly(points, start, end)
                self.source = self.primary.source
                return result
            except UpstreamError as exc:
                logger.warning("Primary weather provider failed, using fallback: %s", exc)
                cache.set(PRIMARY_DOWN_KEY, True, PRIMARY_COOLDOWN_S)
        result = self.fallback.hourly(points, start, end)
        self.source = self.fallback.source
        return result
