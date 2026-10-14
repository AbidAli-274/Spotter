"""Domain types for weather risk. Framework-free on purpose."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


@dataclass(frozen=True, slots=True)
class WeatherSample:
    """Weather at one checkpoint/time, in the units used by the risk table."""

    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True, slots=True)
class Assessment:
    """Risk classification for a single checkpoint."""

    level: RiskLevel
    wind_level: RiskLevel
    rain_level: RiskLevel
    snow_level: RiskLevel
    load_adjusted: bool = False  # True when a load rule raised the wind level
    drivers: tuple[str, ...] = ()  # human-readable reasons for `level`


@dataclass(frozen=True, slots=True)
class CheckpointRisk:
    """A checkpoint on a route; `level` is None when weather was unavailable."""

    mile: float
    level: RiskLevel | None


@dataclass(slots=True)
class RouteMetrics:
    """Mileage-weighted risk summary for one route."""

    total_miles: float
    duration_s: float
    miles_by_level: dict[RiskLevel, float] = field(default_factory=dict)
    unknown_miles: float = 0.0
    avg_risk: float = 0.0

    def miles(self, level: RiskLevel) -> float:
        return self.miles_by_level.get(level, 0.0)
