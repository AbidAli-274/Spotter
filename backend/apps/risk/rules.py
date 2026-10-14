"""Risk thresholds and load rules.

Boundary convention (documented in docs/RISK_RULES.md):
  * Lower bounds are inclusive: wind 25.0 mph is Moderate, rain 0.10 in/hr is Moderate.
  * Where the table shares an edge between two bands (e.g. rain 0.25), the more
    severe band wins, the conservative choice for a safety tool.
  * "No Travel" for rain/snow is strictly greater than 1.00 / 3.0, as written, so
    exactly 1.00 in/hr rain is Severe. Wind No Travel is >= 55 mph.
"""

from __future__ import annotations

from .models import Assessment, RiskLevel, WeatherSample

# Lower bounds for MODERATE, HIGH, SEVERE (inclusive). NO_TRAVEL handled separately.
WIND_BOUNDS = (25.0, 35.0, 45.0)
WIND_NO_TRAVEL_AT = 55.0  # >= 55 mph
RAIN_BOUNDS = (0.10, 0.25, 0.50)
RAIN_NO_TRAVEL_ABOVE = 1.00  # > 1.00 in/hr
SNOW_BOUNDS = (0.5, 1.0, 2.0)
SNOW_NO_TRAVEL_ABOVE = 3.0  # > 3.0 in/hr

# Load rules (pounds, strictly greater than)
HEAVY_LOAD_LB = 30_000
VERY_HEAVY_LOAD_LB = 40_000
HIGH_WIND_BAND_LOW = 35.0
SEVERE_WIND_BAND_LOW = 45.0

_LEVELS = (RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.SEVERE)


def _band(value: float, bounds: tuple[float, float, float]) -> RiskLevel:
    level = RiskLevel.LOW
    for bound, band_level in zip(bounds, _LEVELS, strict=True):
        if value >= bound:
            level = band_level
    return level


def classify_wind(mph: float) -> RiskLevel:
    if mph >= WIND_NO_TRAVEL_AT:
        return RiskLevel.NO_TRAVEL
    return _band(mph, WIND_BOUNDS)


def classify_rain(in_hr: float) -> RiskLevel:
    if in_hr > RAIN_NO_TRAVEL_ABOVE:
        return RiskLevel.NO_TRAVEL
    return _band(in_hr, RAIN_BOUNDS)


def classify_snow(in_hr: float) -> RiskLevel:
    if in_hr > SNOW_NO_TRAVEL_ABOVE:
        return RiskLevel.NO_TRAVEL
    return _band(in_hr, SNOW_BOUNDS)


def apply_load_rules(wind_mph: float, wind_level: RiskLevel, load_lb: float) -> RiskLevel:
    """Escalate the wind level for heavy loads. Never lowers a level."""
    if wind_mph >= WIND_NO_TRAVEL_AT:
        return RiskLevel.NO_TRAVEL
    if SEVERE_WIND_BAND_LOW <= wind_mph < WIND_NO_TRAVEL_AT and load_lb > HEAVY_LOAD_LB:
        return RiskLevel.NO_TRAVEL
    if HIGH_WIND_BAND_LOW <= wind_mph < SEVERE_WIND_BAND_LOW and load_lb > VERY_HEAVY_LOAD_LB:
        return max(wind_level, RiskLevel.SEVERE)
    return wind_level


def assess(sample: WeatherSample, load_lb: float) -> Assessment:
    """Classify one checkpoint: worst of wind/rain/snow, with load escalation on wind."""
    base_wind = classify_wind(sample.wind_mph)
    wind = apply_load_rules(sample.wind_mph, base_wind, load_lb)
    rain = classify_rain(sample.rain_in_hr)
    snow = classify_snow(sample.snow_in_hr)
    level = max(wind, rain, snow)

    drivers: list[str] = []
    if level > RiskLevel.LOW:
        for name, value, lvl, unit in (
            ("wind", sample.wind_mph, wind, "mph"),
            ("rain", sample.rain_in_hr, rain, "in/hr"),
            ("snow", sample.snow_in_hr, snow, "in/hr"),
        ):
            if lvl == level:
                drivers.append(
                    f"{name} {value:.2f} {unit}"
                    if unit == "in/hr"
                    else f"{name} {value:.0f} {unit}"
                )
    load_adjusted = wind > base_wind
    if load_adjusted:
        drivers.append(f"heavy load ({load_lb:,.0f} lb) escalates wind risk")

    return Assessment(
        level=level,
        wind_level=wind,
        rain_level=rain,
        snow_level=snow,
        load_adjusted=load_adjusted,
        drivers=tuple(drivers),
    )
