from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from ..storage import MacroStore


def load_values(store: MacroStore, series_id: str, end_date) -> pd.Series:
    frame = store.latest_series(series_id, end_date)
    if frame.empty:
        return pd.Series(dtype=float, name=series_id)
    series = pd.Series(
        frame["value"].astype(float).to_numpy(),
        index=pd.to_datetime(frame["period"]),
        name=series_id,
    )
    return series[~series.index.duplicated(keep="last")].sort_index()


def annualized_index_change(series: pd.Series, periods: int, periods_per_year: int = 12) -> float | None:
    clean = series.dropna()
    if len(clean) <= periods or clean.iloc[-periods - 1] <= 0:
        return None
    return float(((clean.iloc[-1] / clean.iloc[-periods - 1]) ** (periods_per_year / periods) - 1) * 100)


def percent_change(series: pd.Series, periods: int) -> float | None:
    clean = series.dropna()
    if len(clean) <= periods or clean.iloc[-periods - 1] == 0:
        return None
    return float((clean.iloc[-1] / clean.iloc[-periods - 1] - 1) * 100)


def point_change(series: pd.Series, periods: int) -> float | None:
    clean = series.dropna()
    if len(clean) <= periods:
        return None
    return float(clean.iloc[-1] - clean.iloc[-periods - 1])


def squash(value: float, scale: float) -> float:
    return float(np.tanh(value / scale))


def direction(signal: float, positive: str = "UP", negative: str = "DOWN") -> str:
    if signal > 0.15:
        return positive
    if signal < -0.15:
        return negative
    return "NEUTRAL"


def finite(value: float | None, digits: int = 3) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(float(value), digits)


def chart_series(
    series: pd.Series,
    series_id: str,
    label: str,
    max_points: int = 120,
) -> dict[str, Any]:
    clean = series.dropna().iloc[-max_points:]

    def date_label(index: Any) -> str:
        if isinstance(index, pd.Period):
            return index.to_timestamp(how="end").date().isoformat()
        if hasattr(index, "date"):
            return index.date().isoformat()
        return str(index)

    return {
        "series_id": series_id,
        "label": label,
        "points": [
            {"date": date_label(index), "value": round(float(value), 4)}
            for index, value in clean.items()
        ],
    }


def yoy_series(series: pd.Series, periods: int = 12) -> pd.Series:
    return series.pct_change(periods=periods, fill_method=None) * 100
