from datetime import datetime

from blueprints.reports import build_monthly_comparison_metrics


def test_build_monthly_comparison_metrics_uses_latest_month_and_average_fat():
    month_rows = [
        {"month": "2026-01", "liters": 100.0, "amount": 5000, "avg_fat": 5.6},
        {"month": "2026-02", "liters": 140.0, "amount": 7000, "avg_fat": 6.2},
        {"month": "2026-03", "liters": 120.0, "amount": 6000, "avg_fat": 5.8},
    ]

    metrics = build_monthly_comparison_metrics(month_rows, "2026-03")

    assert metrics["current_month"] == "2026-03"
    assert metrics["highest_month"] == "2026-02"
    assert metrics["highest_amount"] == 7000
    assert metrics["current_month_liters"] == 120.0
    assert metrics["current_month_amount"] == 6000
    assert metrics["current_month_avg_fat"] == 5.8
    assert metrics["month_difference_liters"] == 20.0
    assert metrics["month_difference_amount"] == 1000
    assert metrics["month_difference_avg_fat"] == 0.2
