from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

from ..catalog import STATE_PANEL_STATES
from ..schemas import PanelConfig
from ..storage import MacroStore
from .series_utils import finite, load_values


def build_state_panel(
    store: MacroStore,
    as_of_date: date,
    start_year: int,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for state_code, state_name in STATE_PANEL_STATES:
        unemployment = load_values(store, f"{state_code}UR", as_of_date)
        house_prices = load_values(store, f"{state_code}STHPI", as_of_date)
        if unemployment.empty or house_prices.empty:
            continue

        unemployment_q = unemployment.groupby(unemployment.index.to_period("Q")).mean()
        hpi_q = house_prices.groupby(house_prices.index.to_period("Q")).last()
        panel = pd.concat(
            [unemployment_q.rename("unemployment_rate"), hpi_q.rename("house_price_index")],
            axis=1,
        ).dropna()
        panel["house_price_yoy"] = panel["house_price_index"].pct_change(4, fill_method=None) * 100
        panel = panel.dropna()
        panel["entity"] = state_code
        panel["entity_name"] = state_name
        panel["quarter"] = panel.index.astype(str)
        panel = panel[panel.index.year >= start_year]
        frames.append(panel.reset_index(drop=True))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def run_state_panel(
    store: MacroStore,
    as_of_date: date,
    config: PanelConfig,
) -> dict[str, Any]:
    panel = build_state_panel(store, as_of_date, config.start_year)
    if panel.empty or len(panel) < 80:
        raise RuntimeError("Insufficient state panel observations")

    base = pd.DataFrame({"house_price_yoy": panel["house_price_yoy"].astype(float)})
    if config.fixed_effects in ("ENTITY", "TWO_WAY"):
        entity_dummies = pd.get_dummies(panel["entity"], prefix="state", drop_first=True, dtype=float)
        base = pd.concat([base, entity_dummies], axis=1)
    if config.fixed_effects in ("TIME", "TWO_WAY"):
        time_dummies = pd.get_dummies(panel["quarter"], prefix="quarter", drop_first=True, dtype=float)
        base = pd.concat([base, time_dummies], axis=1)

    exog = sm.add_constant(base.astype(float), has_constant="add")
    outcome = panel["unemployment_rate"].astype(float)
    model = sm.OLS(outcome, exog).fit()
    if config.covariance == "CLUSTER_ENTITY":
        model = model.get_robustcov_results(cov_type="cluster", groups=panel["entity"])
        names = list(exog.columns)
        parameter_map = dict(zip(names, model.params, strict=True))
        standard_error_map = dict(zip(names, model.bse, strict=True))
        pvalue_map = dict(zip(names, model.pvalues, strict=True))
    else:
        parameter_map = model.params.to_dict()
        standard_error_map = model.bse.to_dict()
        pvalue_map = model.pvalues.to_dict()

    coefficient = float(parameter_map["house_price_yoy"])
    standard_error = float(standard_error_map["house_price_yoy"])
    pvalue = float(pvalue_map["house_price_yoy"])

    latest_rows = (
        panel.sort_values("quarter")
        .groupby(["entity", "entity_name"], as_index=False)
        .tail(1)
        .sort_values("entity")
    )
    average_by_quarter = panel.groupby("quarter", as_index=False).agg(
        unemployment_rate=("unemployment_rate", "mean"),
        house_price_yoy=("house_price_yoy", "mean"),
    )

    return {
        "module_id": "US_STATE_HOUSING_LABOR_PANEL_V1",
        "lane_ids": ["US.HOUSING_CONSUMPTION", "US.LABOR"],
        "status": "SUCCESS",
        "evidence_type": "ASSOCIATIONAL",
        "title": "州房价与失业率：真实双向固定效应面板",
        "signal": 0.0,
        "direction": "ASSOCIATION_ONLY",
        "confidence": "MEDIUM" if len(STATE_PANEL_STATES) >= 10 else "LOW",
        "summary": (
            "该模型使用十个美国州的真实失业率与 FHFA 房价指数；"
            "系数只表示条件相关，不解释为房价对失业率的因果效应。"
        ),
        "metrics": {
            "coefficient_house_price_yoy": finite(coefficient, 4),
            "standard_error": finite(standard_error, 4),
            "p_value": finite(pvalue, 4),
            "r_squared": finite(float(model.rsquared), 4),
            "observations": int(model.nobs),
            "entities": int(panel["entity"].nunique()),
            "quarters": int(panel["quarter"].nunique()),
            "start_year": config.start_year,
            "fixed_effects": config.fixed_effects,
            "covariance": config.covariance,
        },
        "evidence": [
            {
                "claim": "House-price growth coefficient in the locked panel specification",
                "value": finite(coefficient, 4),
                "unit": "unemployment percentage points per 1pp HPI YoY",
                "source": "FRED distribution of BLS LAUS and FHFA all-transactions HPI",
                "as_of": as_of_date.isoformat(),
            }
        ],
        "latest_entities": [
            {
                "entity": row.entity,
                "name": row.entity_name,
                "quarter": row.quarter,
                "unemployment_rate": finite(row.unemployment_rate, 2),
                "house_price_yoy": finite(row.house_price_yoy, 2),
            }
            for row in latest_rows.itertuples()
        ],
        "charts": [
            {
                "chart_id": "state_panel_average",
                "title": "十州平均：失业率与房价同比",
                "kind": "dual_line",
                "series": [
                    {
                        "series_id": "PANEL_UR",
                        "label": "平均失业率",
                        "points": [
                            {"date": str(row.quarter), "value": finite(row.unemployment_rate, 3)}
                            for row in average_by_quarter.tail(64).itertuples()
                        ],
                    },
                    {
                        "series_id": "PANEL_HPI_YOY",
                        "label": "平均房价同比",
                        "points": [
                            {"date": str(row.quarter), "value": finite(row.house_price_yoy, 3)}
                            for row in average_by_quarter.tail(64).itertuples()
                        ],
                    },
                ],
            }
        ],
        "diagnostics": {
            "formula_locked": "unemployment_rate ~ house_price_yoy + selected fixed effects",
            "missing_policy": "complete cases after quarterly alignment",
            "causal_claim_allowed": False,
        },
    }

