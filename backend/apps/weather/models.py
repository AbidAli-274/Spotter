from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from apps.risk.models import WeatherSample

SECONDS_PER_HOUR = 3600


@dataclass(frozen=True, slots=True)
class HourlySeries:
    """Hourly UTC weather for one location, starting at `start` (top of an hour)."""

    start: datetime
    wind_mph: tuple[float | None, ...]
    rain_in_hr: tuple[float | None, ...]
    snow_in_hr: tuple[float | None, ...]

    def index_for(self, when: datetime) -> int:
        """Nearest hourly slot to `when` (may be outside the series)."""
        return round((when.astimezone(UTC) - self.start).total_seconds() / SECONDS_PER_HOUR)

    def sample(self, index: int) -> WeatherSample | None:
        if not 0 <= index < len(self.wind_mph):
            return None
        wind, rain, snow = self.wind_mph[index], self.rain_in_hr[index], self.snow_in_hr[index]
        if wind is None or rain is None or snow is None:
            return None
        return WeatherSample(wind_mph=wind, rain_in_hr=rain, snow_in_hr=snow)

    def at(self, when: datetime) -> WeatherSample | None:
        return self.sample(self.index_for(when))

    def hour_time(self, index: int) -> datetime:
        return self.start + timedelta(hours=index)
