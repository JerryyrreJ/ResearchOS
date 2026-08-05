from __future__ import annotations

import pandas as pd

from backend.app.analytics.series_utils import annualized_index_change, chart_series, percent_change, point_change


def test_time_series_transforms_use_locked_periods() -> None:
    index = pd.date_range("2024-01-01", periods=13, freq="MS")
    series = pd.Series([100 + value for value in range(13)], index=index, dtype=float)

    assert round(percent_change(series, 12), 6) == 12.0
    assert annualized_index_change(series, 3) is not None
    assert point_change(series, 3) == 3.0


def test_transform_returns_none_when_history_is_short() -> None:
    series = pd.Series([100.0, 101.0], index=pd.date_range("2025-01-01", periods=2, freq="MS"))
    assert percent_change(series, 12) is None
    assert annualized_index_change(series, 3) is None


def test_chart_series_accepts_period_index() -> None:
    series = pd.Series([1.0, 2.0], index=pd.period_range("2025-01", periods=2, freq="M"))
    result = chart_series(series, "TEST", "Test")
    assert result["points"][0]["date"] == "2025-01-31"
