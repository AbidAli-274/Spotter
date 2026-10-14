"""Route recommendation.

Preference order (strictly lexicographic, per the brief):
  1. fewest Severe miles
  2. fewest High miles
  3. lowest average risk
  4. shortest travel time
No Travel miles are compared first: a route that cannot legally/safely be
driven must lose to any route that can.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .models import RiskLevel, RouteMetrics

# Values are compared at the precision shown to the user, so a route is never
# preferred over another for a difference the UI would display as equal.
MILES_PRECISION = 1
RISK_PRECISION = 2


@dataclass(frozen=True, slots=True)
class Recommendation:
    index: int
    reason: str
    all_blocked: bool  # every route contains No Travel conditions


def _rank_key(m: RouteMetrics) -> tuple[float, float, float, float, float]:
    return (
        round(m.miles(RiskLevel.NO_TRAVEL), MILES_PRECISION),
        round(m.miles(RiskLevel.SEVERE), MILES_PRECISION),
        round(m.miles(RiskLevel.HIGH), MILES_PRECISION),
        round(m.avg_risk, RISK_PRECISION),
        m.duration_s,
    )


def rank(metrics: Sequence[RouteMetrics]) -> list[int]:
    """Indices ordered best to worst."""
    return sorted(range(len(metrics)), key=lambda i: _rank_key(metrics[i]))


def recommend(metrics: Sequence[RouteMetrics]) -> Recommendation:
    if not metrics:
        raise ValueError("At least one route is required.")
    order = rank(metrics)
    best = order[0]
    all_blocked = all(m.miles(RiskLevel.NO_TRAVEL) > 0 for m in metrics)
    return Recommendation(best, _explain(best, metrics, order), all_blocked)


def _explain(best: int, metrics: Sequence[RouteMetrics], order: list[int]) -> str:
    best_m = metrics[best]
    others = [metrics[i] for i in order[1:]]
    if not others:
        return "Only one route was available."

    if best_m.miles(RiskLevel.NO_TRAVEL) > 0:
        return (
            f"Every route has No Travel conditions; this one has the least "
            f"({best_m.miles(RiskLevel.NO_TRAVEL):.0f} mi). Delay departure or reconsider the trip."
        )

    for level, label in (
        (RiskLevel.NO_TRAVEL, "No Travel"),
        (RiskLevel.SEVERE, "Severe"),
        (RiskLevel.HIGH, "High"),
    ):
        mine = best_m.miles(level)
        theirs = [m.miles(level) for m in others]
        if any(round(mine, MILES_PRECISION) != round(t, MILES_PRECISION) for t in theirs):
            if level == RiskLevel.NO_TRAVEL:
                return "Only route(s) without No Travel conditions."
            comparison = " and ".join(f"{t:.0f}" for t in theirs)
            return f"Fewest {label} miles: {mine:.0f} mi vs {comparison} mi on the alternatives."

    if any(
        round(best_m.avg_risk, RISK_PRECISION) != round(m.avg_risk, RISK_PRECISION) for m in others
    ):
        comparison = " and ".join(f"{m.avg_risk:.2f}" for m in others)
        return (
            f"Lowest average risk ({best_m.avg_risk:.2f} vs {comparison}) "
            "with equal Severe/High exposure."
        )

    return "Routes carry equal weather risk; this one is the fastest."
