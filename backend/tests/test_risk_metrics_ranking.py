import pytest

from apps.risk.metrics import compute_metrics, segment_lengths
from apps.risk.models import CheckpointRisk, RiskLevel, RouteMetrics
from apps.risk.ranking import rank, recommend

L, M, H, S, N = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
)


def test_segment_lengths_sum_to_total():
    lengths = segment_lengths([0, 25, 50, 100], 100)
    assert lengths == [12.5, 25.0, 37.5, 25.0]
    assert sum(lengths) == pytest.approx(100)


def test_metrics_weight_levels_by_miles():
    cps = [CheckpointRisk(0, L), CheckpointRisk(50, S), CheckpointRisk(100, S)]
    m = compute_metrics(cps, 100, 3600)
    assert m.miles(L) == pytest.approx(25)
    assert m.miles(S) == pytest.approx(75)
    assert m.avg_risk == pytest.approx(0.75 * 3)


def test_unknown_checkpoints_are_excluded_from_average():
    cps = [CheckpointRisk(0, M), CheckpointRisk(50, None), CheckpointRisk(100, M)]
    m = compute_metrics(cps, 100, 3600)
    assert m.unknown_miles == pytest.approx(50)
    assert m.avg_risk == pytest.approx(1.0)


def metrics(severe=0.0, high=0.0, avg=0.0, duration=3600.0, no_travel=0.0):
    return RouteMetrics(
        total_miles=100,
        duration_s=duration,
        miles_by_level={S: severe, H: high, N: no_travel},
        avg_risk=avg,
    )


def test_fewest_severe_miles_wins_over_everything():
    routes = [
        metrics(severe=10, high=0, avg=0.1, duration=100),
        metrics(severe=0, high=90, avg=2, duration=9999),
    ]
    assert recommend(routes).index == 1


def test_high_miles_break_severe_ties():
    routes = [metrics(high=30), metrics(high=10), metrics(high=20)]
    assert rank(routes) == [1, 2, 0]


def test_avg_risk_then_duration_break_remaining_ties():
    assert rank([metrics(avg=1.0), metrics(avg=0.5)]) == [1, 0]
    assert rank([metrics(avg=1.0, duration=500), metrics(avg=1.0, duration=400)]) == [1, 0]


def test_no_travel_route_loses_even_if_otherwise_better():
    routes = [metrics(no_travel=5, duration=100), metrics(severe=40, high=40, duration=9999)]
    rec = recommend(routes)
    assert rec.index == 1
    assert not rec.all_blocked


def test_all_blocked_flagged_and_least_blocked_chosen():
    rec = recommend([metrics(no_travel=30), metrics(no_travel=10)])
    assert rec.index == 1
    assert rec.all_blocked


def test_reason_mentions_deciding_factor():
    rec = recommend([metrics(severe=14), metrics(severe=0), metrics(severe=22)])
    assert "Severe" in rec.reason and "0 mi" in rec.reason


def test_single_route():
    assert recommend([metrics()]).index == 0


def test_empty_raises():
    with pytest.raises(ValueError):
        recommend([])


def test_reason_lists_only_alternatives_that_differ():
    rec = recommend([metrics(high=0), metrics(high=0), metrics(high=25)])
    assert rec.reason == "Fewest High miles: 0 mi vs 25 mi on the alternatives."
