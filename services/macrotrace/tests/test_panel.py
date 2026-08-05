from __future__ import annotations

from datetime import UTC, date, datetime

import numpy as np
import pandas as pd

from backend.app.analytics.panel import run_state_panel
from backend.app.catalog import STATE_PANEL_STATES
from backend.app.schemas import PanelConfig
from backend.app.storage import MacroStore


def make_frame(series_id: str, label: str, frequency: str, values: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_id": "TEST",
            "series_id": series_id,
            "label": label,
            "period": values.index,
            "value": values.to_numpy(),
            "unit": "test",
            "frequency": frequency,
            "realtime_start": pd.NaT,
            "realtime_end": pd.NaT,
            "fetched_at": datetime(2025, 12, 31, tzinfo=UTC),
            "snapshot_id": "TEST_SNAPSHOT",
        }
    )


def test_real_panel_recipe_runs_locked_two_way_fixed_effects(tmp_path) -> None:
    store = MacroStore(tmp_path / "panel.duckdb")
    quarter_index = pd.date_range("2008-01-01", "2025-10-01", freq="QS")
    month_index = pd.date_range("2008-01-01", "2025-12-01", freq="MS")

    for state_number, (code, name) in enumerate(STATE_PANEL_STATES):
        t = np.arange(len(quarter_index))
        growth = 0.012 + 0.006 * np.sin(t / 5 + state_number / 3)
        hpi_values = 100 * np.exp(np.cumsum(growth))
        hpi = pd.Series(hpi_values, index=quarter_index)
        hpi_yoy = hpi.pct_change(4, fill_method=None) * 100
        quarterly_unemployment = 6 + state_number * 0.08 - 0.035 * hpi_yoy.fillna(4) + 0.3 * np.sin(t / 8)
        unemployment = pd.Series(index=month_index, dtype=float)
        for timestamp in month_index:
            quarter_position = min(
                len(quarter_index) - 1,
                max(0, np.searchsorted(quarter_index.values, timestamp.to_datetime64(), side="right") - 1),
            )
            unemployment.loc[timestamp] = quarterly_unemployment.iloc[quarter_position]

        store.save_observations(make_frame(f"{code}STHPI", f"HPI {name}", "Q", hpi))
        store.save_observations(make_frame(f"{code}UR", f"UR {name}", "M", unemployment))

    result = run_state_panel(
        store,
        date(2025, 12, 31),
        PanelConfig(start_year=2010, fixed_effects="TWO_WAY", covariance="CLUSTER_ENTITY"),
    )
    assert result["status"] == "SUCCESS"
    assert result["metrics"]["entities"] == 10
    assert result["metrics"]["observations"] > 500
    assert result["diagnostics"]["causal_claim_allowed"] is False
    assert result["metrics"]["coefficient_house_price_yoy"] < 0
