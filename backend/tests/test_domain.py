from datetime import date, datetime, timedelta, timezone

from app.domain import (
    baseline,
    compare_periods,
    consumption_stats,
    depletion_estimate,
    detect_anomaly,
    estimate_carbon_kg,
    estimate_cost_impact,
    maintenance_status,
    priority_score,
    sustained_rise,
    warranty_status,
)


def test_stats_and_baseline():
    assert consumption_stats([])["count"] == 0
    assert consumption_stats([1, 2, 3])["mean"] == 2
    assert baseline([1, 2, 3, 4], 2)["mean"] == 3.5


def test_anomaly_requires_history_and_flags_spike():
    assert detect_anomaly([1, 2], 4)["insufficient_data"] is True
    result = detect_anomaly([1, 1, 1, 1, 4], 4)
    assert result["flagged"] is True
    assert result["direction"] == "above"


def test_comparison_rise_and_estimates():
    assert compare_periods([2, 2], [3, 3])["percent_change"] == 50
    assert sustained_rise([1, 1, 1, 1.3, 1.4, 1.5])
    assert estimate_carbon_kg(10, 0.71)["label"] == "estimate"
    assert estimate_cost_impact(2, None)["status"] == "unavailable"
    assert estimate_cost_impact(2, 3)["value"] == 6
    assert 0 <= priority_score(1, 1, 1, 1, 1) <= 100


def test_inventory_ignores_restocking():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    entries = [
        {"logged_at": start, "quantity": 10},
        {"logged_at": start + timedelta(days=2), "quantity": 8},
        {"logged_at": start + timedelta(days=4), "quantity": 12},
        {"logged_at": start + timedelta(days=6), "quantity": 10},
    ]
    result = depletion_estimate(entries)
    assert result["average_daily_use"] == 1
    assert result["confidence"] == "low"


def test_status_helpers():
    today = date(2026, 1, 1)
    assert warranty_status(today + timedelta(days=5), today, 30)["status"] == "expiring_soon"
    assert warranty_status(today - timedelta(days=1), today, 30)["status"] == "expired"
    assert maintenance_status(today - timedelta(days=400), 365, today)["status"] == "overdue"
