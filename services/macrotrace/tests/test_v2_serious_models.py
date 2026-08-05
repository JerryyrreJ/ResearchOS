from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.app.analytics.serious_models import _monthly, run_dynamic_factor, run_growth_at_risk, run_local_projection, run_var
from backend.app.registry import RegistryStore
from backend.app.storage import MacroStore


ROOT = Path(__file__).resolve().parents[1]


def frame(series_id: str, index: pd.DatetimeIndex, values: np.ndarray, frequency: str = "M") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_id": "SYNTHETIC_DGP",
            "series_id": series_id,
            "label": series_id,
            "period": index,
            "value": values,
            "unit": "test",
            "frequency": frequency,
            "realtime_start": pd.NaT,
            "realtime_end": pd.NaT,
            "fetched_at": datetime(2025, 12, 31, tzinfo=UTC),
            "snapshot_id": "KNOWN_DGP",
        }
    )


def build_store(tmp_path) -> tuple[MacroStore, RegistryStore]:
    rng = np.random.default_rng(42)
    store = MacroStore(tmp_path / "known_dgp.duckdb")
    registry = RegistryStore(ROOT / "registry" / "v2")
    monthly = pd.date_range("1995-01-01", periods=360, freq="MS")
    common = rng.normal(0.25, 0.6, len(monthly))
    indpro = 100 * np.exp(np.cumsum(common + rng.normal(0, .15, len(monthly))) / 100)
    retail = 200 * np.exp(np.cumsum(.7 * common + rng.normal(0, .25, len(monthly))) / 100)
    payroll = 100000 * np.exp(np.cumsum(.45 * common + rng.normal(0, .12, len(monthly))) / 100)
    unemployment = np.maximum(2.5, 6 - np.cumsum(common) / 35 + rng.normal(0, .08, len(monthly)))
    cpi = 100 * np.exp(np.cumsum(.2 + .08 * common + rng.normal(0, .08, len(monthly))) / 100)
    yields = 4 + np.cumsum(rng.normal(0, .08, len(monthly)))
    wti = 45 * np.exp(np.cumsum(rng.normal(.1, 4.5, len(monthly))) / 100)
    for series_id, values in {
        "INDPRO": indpro,
        "RSAFS": retail,
        "CES0000000001": payroll,
        "LNS14000000": unemployment,
        "CUSR0000SA0": cpi,
        "DGS10": yields,
        "RWTC": wti,
    }.items():
        store.save_observations(frame(series_id, monthly, values))
    quarterly = pd.date_range("1995-01-01", periods=120, freq="QS")
    nfci_q = rng.normal(0, .6, len(quarterly))
    growth = 2.5 - .8 * nfci_q + rng.normal(0, 1.2, len(quarterly))
    gdp = 10000 * np.cumprod((1 + growth / 100) ** .25)
    store.save_observations(frame("GDPC1", quarterly, gdp, "Q"))
    nfci_monthly_index = pd.date_range(quarterly[0], periods=120 * 3, freq="MS")
    nfci_monthly = np.repeat(nfci_q, 3) + rng.normal(0, .05, len(nfci_monthly_index))
    store.save_observations(frame("NFCI", nfci_monthly_index, nfci_monthly))
    return store, registry


def test_dynamic_factor_and_var_recover_executable_known_dgp(tmp_path) -> None:
    store, registry = build_store(tmp_path)
    factors = ["F.ACTIVITY.INDPRO", "F.ACTIVITY.RETAIL", "F.LABOR.PAYROLL", "F.LABOR.UNEMPLOYMENT", "F.CPI.HEADLINE"]
    dfm = run_dynamic_factor(store, registry, date(2025, 12, 31), "N.DFM", factors, {"estimation_window_years": 15, "factor_count": 1, "forecast_horizon": 3})
    assert dfm["status"] == "SUCCESS"
    assert dfm["table"]["statistics"]["Observations"][0] >= 100
    assert any(item["diagnostic_id"] == "DFM.OOS" for item in dfm["diagnostics"])
    assert dfm["robustness"]["pca_test_leakage_allowed"] is False
    var = run_var(store, registry, date(2025, 12, 31), "N.VAR", ["F.CPI.HEADLINE", "F.LABOR.UNEMPLOYMENT", "F.ACTIVITY.INDPRO", "F.RATES.UST10"], {"lags": 2, "forecast_horizon": 3, "identification": "REGISTERED_CHOLESKY", "estimation_window_years": 15})
    assert var["status"] in {"SUCCESS", "WARNING"}
    assert any(item["diagnostic_id"] == "VAR.STABILITY" for item in var["diagnostics"])
    assert {chart["kind"] for chart in var["charts"]} >= {"forecast_fan", "irf", "fevd"}


def test_dynamic_factor_rejects_fewer_than_three_registered_indicators(tmp_path) -> None:
    store, registry = build_store(tmp_path)
    with pytest.raises(RuntimeError, match="at least three"):
        run_dynamic_factor(store, registry, date(2025, 12, 31), "N.DFM.TOO_SHALLOW", ["F.ACTIVITY.INDPRO", "F.ACTIVITY.RETAIL"], {"estimation_window_years": 15, "factor_count": 1, "forecast_horizon": 3})


def test_quarterly_information_is_carried_between_release_months() -> None:
    quarterly = pd.Series(
        [100.0, 102.0, 103.0],
        index=pd.date_range("2025-01-01", periods=3, freq="QS"),
    )
    monthly = _monthly(quarterly)
    assert monthly.loc["2025-02-01"] == 100.0
    assert monthly.loc["2025-03-01"] == 100.0
    assert monthly.diff().notna().sum() >= 6


def test_local_projection_and_growth_at_risk_have_method_specific_contracts(tmp_path) -> None:
    store, registry = build_store(tmp_path)
    lp = run_local_projection(store, registry, date(2025, 12, 31), "N.LP", ["F.ENERGY.WTI", "F.CPI.HEADLINE", "F.LABOR.UNEMPLOYMENT"], {"response_horizon": 12, "lags": 3, "covariance": "HAC", "shock_scale": 1.0})
    assert lp["status"] == "SUCCESS"
    assert lp["charts"][0]["kind"] == "event_study"
    assert "causal" in " ".join(lp["table"]["notes"]).lower()
    scenario_response = lp["aggregation_input"]["scenario_response"]
    assert scenario_response["shock_factor_id"] == "F.ENERGY.WTI"
    assert scenario_response["observed_shock_standard_deviation_pct"] > 0
    assert len(scenario_response["response_path"]) == 13
    gar = run_growth_at_risk(store, registry, date(2025, 12, 31), "N.GAR", ["F.ACTIVITY.REAL_GDP", "F.MONETARY.NFCI"], {"quantiles": [0.05, 0.25, 0.5, 0.75, 0.95], "forecast_horizon_quarters": 4, "estimation_window": "EXPANDING"})
    assert gar["status"] == "SUCCESS"
    assert len(gar["table"]["columns"]) == 5
    assert gar["aggregation_input"]["downside_quantile"] < gar["aggregation_input"]["point_forecast"]
    assert gar["sample"]["forecast_origin"] > gar["sample"]["end"]
    assert any(item["diagnostic_id"] == "GAR.TAIL_CALIBRATION" for item in gar["diagnostics"])
    assert gar["robustness"]["label_availability_lag_quarters"] == 4
