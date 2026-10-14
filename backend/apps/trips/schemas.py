"""Plain data carried between the trips service layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PlaceInput:
    label: str
    lat: float | None = None
    lon: float | None = None


@dataclass(frozen=True, slots=True)
class TripRequest:
    origin: PlaceInput
    destination: PlaceInput
    departure: datetime  # timezone-aware
    load_lb: float
    interval_mi: int
