"""Turn per-checkpoint levels into mileage-weighted route metrics."""

from __future__ import annotations

from collections.abc import Sequence

from .models import CheckpointRisk, RiskLevel, RouteMetrics


def segment_lengths(miles: Sequence[float], total_miles: float) -> list[float]:
    """Road length each checkpoint 'owns': half the gap to each neighbour.

    The first checkpoint covers [0, midpoint] and the last [midpoint, total],
    so lengths always sum to `total_miles`.
    """
    if not miles:
        return []
    bounds = [0.0]
    bounds += [(a + b) / 2 for a, b in zip(miles, miles[1:], strict=False)]
    bounds.append(total_miles)
    return [max(0.0, hi - lo) for lo, hi in zip(bounds, bounds[1:], strict=False)]


def compute_metrics(
    checkpoints: Sequence[CheckpointRisk], total_miles: float, duration_s: float
) -> RouteMetrics:
    lengths = segment_lengths([c.mile for c in checkpoints], total_miles)
    metrics = RouteMetrics(total_miles=total_miles, duration_s=duration_s)
    weighted = 0.0
    known = 0.0
    for checkpoint, length in zip(checkpoints, lengths, strict=True):
        if checkpoint.level is None:
            metrics.unknown_miles += length
            continue
        metrics.miles_by_level[checkpoint.level] = (
            metrics.miles_by_level.get(checkpoint.level, 0.0) + length
        )
        weighted += int(checkpoint.level) * length
        known += length
    metrics.avg_risk = weighted / known if known else 0.0
    return metrics


def has_no_travel(metrics: RouteMetrics) -> bool:
    return metrics.miles(RiskLevel.NO_TRAVEL) > 0
