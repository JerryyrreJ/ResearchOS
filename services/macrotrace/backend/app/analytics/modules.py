from __future__ import annotations

from datetime import date
from typing import Any, Callable

import numpy as np
import pandas as pd

from ..schemas import PanelConfig
from ..storage import MacroStore
from .panel import run_state_panel
from .series_utils import (
    annualized_index_change,
    chart_series,
    direction,
    finite,
    load_values,
    percent_change,
    point_change,
    squash,
    yoy_series,
)


def _confidence(required: list[pd.Series]) -> str:
    available = sum(not item.empty and item.notna().sum() >= 24 for item in required)
    if available == len(required):
        return "HIGH"
    if available >= max(1, len(required) - 1):
        return "MEDIUM"
    return "LOW"


def inflation_momentum(store: MacroStore, as_of: date, _: PanelConfig) -> dict[str, Any]:
    cpi = load_values(store, "CUSR0000SA0", as_of)
    core_cpi = load_values(store, "CUSR0000SA0L1E", as_of)
    pce = load_values(store, "PCEPI", as_of)
    core_pce = load_values(store, "PCEPILFE", as_of)
    series = [cpi, core_cpi, pce, core_pce]
    if any(item.empty for item in series):
        raise RuntimeError("Inflation series missing")

    metrics = {
        "cpi_3m_saar": annualized_index_change(cpi, 3),
        "cpi_yoy": percent_change(cpi, 12),
        "core_cpi_3m_saar": annualized_index_change(core_cpi, 3),
        "core_cpi_yoy": percent_change(core_cpi, 12),
        "pce_3m_saar": annualized_index_change(pce, 3),
        "pce_yoy": percent_change(pce, 12),
        "core_pce_3m_saar": annualized_index_change(core_pce, 3),
        "core_pce_yoy": percent_change(core_pce, 12),
    }
    acceleration = np.nanmean(
        [
            metrics["cpi_3m_saar"] - metrics["cpi_yoy"],
            metrics["core_cpi_3m_saar"] - metrics["core_cpi_yoy"],
            metrics["pce_3m_saar"] - metrics["pce_yoy"],
            metrics["core_pce_3m_saar"] - metrics["core_pce_yoy"],
        ]
    )
    signal = squash(float(acceleration), 1.5)
    return {
        "module_id": "US_INFLATION_MOMENTUM_V1",
        "lane_ids": ["US.INFLATION"],
        "status": "SUCCESS",
        "evidence_type": "DESCRIPTIVE",
        "title": "通胀动量与广度",
        "signal": finite(signal),
        "direction": direction(signal, "ACCELERATING", "DECELERATING"),
        "confidence": _confidence(series),
        "summary": "比较 CPI、核心 CPI、PCE 与核心 PCE 的三个月年化动量和同比速度。",
        "metrics": {key: finite(value, 2) for key, value in metrics.items()},
        "evidence": [
            {"claim": "CPI 3m SAAR", "value": finite(metrics["cpi_3m_saar"], 2), "unit": "percent", "source": "BLS", "as_of": cpi.index[-1].date().isoformat()},
            {"claim": "Core CPI 3m SAAR", "value": finite(metrics["core_cpi_3m_saar"], 2), "unit": "percent", "source": "BLS", "as_of": core_cpi.index[-1].date().isoformat()},
            {"claim": "Core PCE YoY", "value": finite(metrics["core_pce_yoy"], 2), "unit": "percent", "source": "BEA via FRED", "as_of": core_pce.index[-1].date().isoformat()},
        ],
        "charts": [
            {
                "chart_id": "inflation_yoy",
                "title": "美国通胀同比",
                "kind": "line",
                "series": [
                    chart_series(yoy_series(cpi), "CPI_YOY", "CPI同比", 72),
                    chart_series(yoy_series(core_cpi), "CORE_CPI_YOY", "核心CPI同比", 72),
                    chart_series(yoy_series(core_pce), "CORE_PCE_YOY", "核心PCE同比", 72),
                ],
            }
        ],
        "diagnostics": {"transform": "fixed 3m annualized and 12m percent changes", "causal_claim_allowed": False},
    }


def labor_tightness(store: MacroStore, as_of: date, _: PanelConfig) -> dict[str, Any]:
    payroll = load_values(store, "CES0000000001", as_of)
    unemployment = load_values(store, "LNS14000000", as_of)
    earnings = load_values(store, "CES0500000003", as_of)
    if any(item.empty for item in (payroll, unemployment, earnings)):
        raise RuntimeError("Labor series missing")
    payroll_changes = payroll.diff().dropna()
    payroll_3m = float(payroll_changes.tail(3).mean())
    unemployment_3m = point_change(unemployment, 3) or 0.0
    earnings_yoy = percent_change(earnings, 12) or 0.0
    tightness_score = payroll_3m / 180 - unemployment_3m / 0.4 + (earnings_yoy - 3.5) / 2
    signal = squash(tightness_score, 2.0)
    return {
        "module_id": "US_LABOR_TIGHTNESS_V1",
        "lane_ids": ["US.LABOR"],
        "status": "SUCCESS",
        "evidence_type": "DESCRIPTIVE",
        "title": "劳动力市场与工资压力",
        "signal": finite(signal),
        "direction": direction(signal, "TIGHT", "SOFT"),
        "confidence": _confidence([payroll, unemployment, earnings]),
        "summary": "使用非农、失业率和平均时薪的固定组合判断劳动市场紧张度。",
        "metrics": {
            "payroll_3m_average_change_thousands": finite(payroll_3m, 1),
            "unemployment_rate": finite(float(unemployment.iloc[-1]), 2),
            "unemployment_3m_change_pp": finite(unemployment_3m, 2),
            "average_hourly_earnings_yoy": finite(earnings_yoy, 2),
        },
        "evidence": [
            {"claim": "3m average payroll change", "value": finite(payroll_3m, 1), "unit": "thousands", "source": "BLS", "as_of": payroll.index[-1].date().isoformat()},
            {"claim": "Unemployment rate", "value": finite(float(unemployment.iloc[-1]), 2), "unit": "percent", "source": "BLS", "as_of": unemployment.index[-1].date().isoformat()},
            {"claim": "Average hourly earnings YoY", "value": finite(earnings_yoy, 2), "unit": "percent", "source": "BLS", "as_of": earnings.index[-1].date().isoformat()},
        ],
        "charts": [
            {"chart_id": "labor", "title": "失业率与非农就业", "kind": "dual_line", "series": [chart_series(unemployment, "UNRATE", "失业率", 96), chart_series(payroll / 1000, "PAYEMS_M", "非农就业（百万）", 96)]}
        ],
        "diagnostics": {"formula_locked": True, "causal_claim_allowed": False},
    }


def activity_momentum(store: MacroStore, as_of: date, _: PanelConfig) -> dict[str, Any]:
    industrial = load_values(store, "INDPRO", as_of)
    retail = load_values(store, "RSAFS", as_of)
    payroll = load_values(store, "CES0000000001", as_of)
    if any(item.empty for item in (industrial, retail, payroll)):
        raise RuntimeError("Activity series missing")
    industrial_3m = annualized_index_change(industrial, 3) or 0.0
    retail_3m = annualized_index_change(retail, 3) or 0.0
    payroll_3m_pct = annualized_index_change(payroll, 3) or 0.0
    signal = squash(np.mean([industrial_3m, retail_3m, payroll_3m_pct]), 5.0)
    return {
        "module_id": "US_ACTIVITY_NOWCAST_MONITOR_V1",
        "lane_ids": ["US.ACTIVITY"],
        "status": "SUCCESS",
        "evidence_type": "DESCRIPTIVE",
        "title": "实体活动动量",
        "signal": finite(signal),
        "direction": direction(signal, "EXPANDING", "CONTRACTING"),
        "confidence": _confidence([industrial, retail, payroll]),
        "summary": "工业生产、名义零售和非农就业构成透明的活动动量监测器。",
        "metrics": {"industrial_production_3m_saar": finite(industrial_3m, 2), "retail_sales_3m_saar": finite(retail_3m, 2), "payroll_level_3m_saar": finite(payroll_3m_pct, 2)},
        "evidence": [
            {"claim": "Industrial production 3m SAAR", "value": finite(industrial_3m, 2), "unit": "percent", "source": "Federal Reserve via FRED", "as_of": industrial.index[-1].date().isoformat()},
            {"claim": "Retail sales 3m SAAR", "value": finite(retail_3m, 2), "unit": "percent", "source": "Census via FRED", "as_of": retail.index[-1].date().isoformat()},
        ],
        "charts": [{"chart_id": "activity", "title": "工业生产与零售销售（标准化展示）", "kind": "line", "series": [chart_series(industrial / industrial.iloc[-60] * 100 if len(industrial) > 60 else industrial, "INDPRO", "工业生产", 72), chart_series(retail / retail.iloc[-60] * 100 if len(retail) > 60 else retail, "RSAFS", "零售销售", 72)]}],
        "diagnostics": {"retail_is_nominal": True, "causal_claim_allowed": False},
    }


def energy_pressure(store: MacroStore, as_of: date, _: PanelConfig) -> dict[str, Any]:
    wti = load_values(store, "RWTC", as_of)
    if wti.empty:
        raise RuntimeError("EIA WTI series missing")
    change_4w = percent_change(wti, 4) or 0.0
    change_13w = percent_change(wti, 13) or 0.0
    signal = squash(np.mean([change_4w, change_13w]), 15.0)
    return {
        "module_id": "US_COMMODITY_SUPPLY_DEMAND_V1",
        "lane_ids": ["US.COMMODITY_ENERGY"],
        "status": "SUCCESS",
        "evidence_type": "DESCRIPTIVE",
        "title": "能源价格压力",
        "signal": finite(signal),
        "direction": direction(signal, "INFLATIONARY", "DISINFLATIONARY"),
        "confidence": "HIGH" if len(wti) > 100 else "MEDIUM",
        "summary": "使用 EIA 官方 WTI 周度现货价格观察短期能源成本冲击。",
        "metrics": {"wti_latest": finite(float(wti.iloc[-1]), 2), "wti_4w_change_pct": finite(change_4w, 2), "wti_13w_change_pct": finite(change_13w, 2)},
        "evidence": [{"claim": "WTI weekly spot price", "value": finite(float(wti.iloc[-1]), 2), "unit": "USD per barrel", "source": "EIA API v2", "as_of": wti.index[-1].date().isoformat()}],
        "charts": [{"chart_id": "wti", "title": "WTI 周度现货价格", "kind": "line", "series": [chart_series(wti, "RWTC", "WTI", 156)]}],
        "diagnostics": {"frequency": "weekly", "causal_claim_allowed": False},
    }


def treasury_yield(store: MacroStore, as_of: date, _: PanelConfig) -> dict[str, Any]:
    nominal = load_values(store, "DGS10", as_of)
    real = load_values(store, "DFII10", as_of)
    breakeven = load_values(store, "T10YIE", as_of)
    two_year = load_values(store, "DGS2", as_of)
    if any(item.empty for item in (nominal, real, breakeven, two_year)):
        raise RuntimeError("Treasury yield series missing")
    aligned = pd.concat([nominal.rename("nominal"), real.rename("real"), breakeven.rename("breakeven"), two_year.rename("two_year")], axis=1).sort_index().ffill().dropna()
    latest = aligned.iloc[-1]
    change_20d = aligned.iloc[-1] - aligned.iloc[-21] if len(aligned) > 21 else aligned.iloc[-1] - aligned.iloc[0]
    residual = float(latest.nominal - latest.real - latest.breakeven)
    signal = squash(float(change_20d.nominal), 0.35)
    return {
        "module_id": "US_TREASURY_YIELD_DECOMP_V1",
        "lane_ids": ["US.MONETARY", "US.FISCAL_TREASURY"],
        "status": "SUCCESS",
        "evidence_type": "IDENTITY_PROXY",
        "title": "10 年期收益率分解",
        "signal": finite(signal),
        "direction": direction(signal, "YIELD_UP", "YIELD_DOWN"),
        "confidence": "HIGH",
        "summary": "把名义 10 年期收益率与实际收益率、盈亏平衡通胀和残差代理对齐，观察最近 20 个交易日变化。",
        "metrics": {"ust10y": finite(latest.nominal, 2), "ust2y": finite(latest.two_year, 2), "real10y": finite(latest.real, 2), "breakeven10y": finite(latest.breakeven, 2), "identity_residual": finite(residual, 3), "ust10y_20d_change_pp": finite(change_20d.nominal, 2), "real10y_20d_change_pp": finite(change_20d.real, 2), "breakeven10y_20d_change_pp": finite(change_20d.breakeven, 2)},
        "evidence": [
            {"claim": "10-year Treasury yield", "value": finite(latest.nominal, 2), "unit": "percent", "source": "Federal Reserve H.15 via FRED", "as_of": aligned.index[-1].date().isoformat()},
            {"claim": "10-year real yield", "value": finite(latest.real, 2), "unit": "percent", "source": "Federal Reserve via FRED", "as_of": aligned.index[-1].date().isoformat()},
            {"claim": "10-year breakeven", "value": finite(latest.breakeven, 2), "unit": "percent", "source": "Federal Reserve via FRED", "as_of": aligned.index[-1].date().isoformat()},
        ],
        "charts": [{"chart_id": "treasury", "title": "10 年期名义、实际收益率与通胀补偿", "kind": "line", "series": [chart_series(aligned.nominal, "DGS10", "10Y名义", 180), chart_series(aligned.real, "DFII10", "10Y实际", 180), chart_series(aligned.breakeven, "T10YIE", "10Y盈亏平衡通胀", 180)]}],
        "diagnostics": {"decomposition_is_proxy": True, "aligned_with_forward_fill": True, "causal_claim_allowed": False},
    }


def financial_conditions(store: MacroStore, as_of: date, _: PanelConfig) -> dict[str, Any]:
    nfci = load_values(store, "NFCI", as_of)
    if nfci.empty:
        raise RuntimeError("NFCI series missing")
    change_13w = point_change(nfci, 13) or 0.0
    latest = float(nfci.iloc[-1])
    signal = squash(-latest - change_13w, 0.5)
    return {
        "module_id": "US_FINANCIAL_CONDITIONS_V1",
        "lane_ids": ["US.MONETARY", "US.FIN_STABILITY"],
        "status": "SUCCESS",
        "evidence_type": "DESCRIPTIVE",
        "title": "金融条件",
        "signal": finite(signal),
        "direction": direction(signal, "EASING", "TIGHTENING"),
        "confidence": "HIGH",
        "summary": "NFCI 高于零通常表示较历史平均更紧，低于零表示较松。",
        "metrics": {"nfci_latest": finite(latest, 3), "nfci_13w_change": finite(change_13w, 3)},
        "evidence": [{"claim": "NFCI", "value": finite(latest, 3), "unit": "index", "source": "Chicago Fed via FRED", "as_of": nfci.index[-1].date().isoformat()}],
        "charts": [{"chart_id": "nfci", "title": "Chicago Fed NFCI", "kind": "area", "series": [chart_series(nfci, "NFCI", "NFCI", 208)]}],
        "diagnostics": {"interpretation": "positive=tighter, negative=looser", "causal_claim_allowed": False},
    }


def fiscal_debt(store: MacroStore, as_of: date, _: PanelConfig) -> dict[str, Any]:
    debt = load_values(store, "DEBT_TO_PENNY_TOTAL", as_of)
    if debt.empty:
        raise RuntimeError("Treasury debt series missing")
    monthly = debt.groupby(debt.index.to_period("M")).last()
    yoy = percent_change(monthly, 12) or 0.0
    change_3m = percent_change(monthly, 3) or 0.0
    signal = squash(np.mean([yoy - 5, change_3m * 4 - 5]), 5.0)
    return {
        "module_id": "US_TREASURY_SUPPLY_V1",
        "lane_ids": ["US.FISCAL_TREASURY"],
        "status": "SUCCESS",
        "evidence_type": "DESCRIPTIVE",
        "title": "联邦债务与供给压力代理",
        "signal": finite(signal),
        "direction": direction(signal, "PRESSURE_UP", "PRESSURE_DOWN"),
        "confidence": "MEDIUM",
        "summary": "Debt to the Penny 反映债务存量变化，不等同于净发行期限结构或期限溢价。",
        "metrics": {"total_debt_trillion": finite(float(debt.iloc[-1]) / 1e12, 2), "debt_yoy_pct": finite(yoy, 2), "debt_3m_pct": finite(change_3m, 2)},
        "evidence": [{"claim": "Total public debt outstanding", "value": finite(float(debt.iloc[-1]) / 1e12, 2), "unit": "trillion USD", "source": "Treasury Fiscal Data", "as_of": debt.index[-1].date().isoformat()}],
        "charts": [{"chart_id": "debt", "title": "美国联邦债务存量", "kind": "line", "series": [chart_series(monthly / 1e12, "DEBT", "总债务（万亿美元）", 120)]}],
        "diagnostics": {"supply_proxy_only": True, "causal_claim_allowed": False},
    }


ModuleRunner = Callable[[MacroStore, date, PanelConfig], dict[str, Any]]


MODULE_RUNNERS: dict[str, ModuleRunner] = {
    "US_INFLATION_MOMENTUM_V1": inflation_momentum,
    "US_LABOR_TIGHTNESS_V1": labor_tightness,
    "US_ACTIVITY_NOWCAST_MONITOR_V1": activity_momentum,
    "US_COMMODITY_SUPPLY_DEMAND_V1": energy_pressure,
    "US_TREASURY_YIELD_DECOMP_V1": treasury_yield,
    "US_FINANCIAL_CONDITIONS_V1": financial_conditions,
    "US_TREASURY_SUPPLY_V1": fiscal_debt,
    "US_STATE_HOUSING_LABOR_PANEL_V1": lambda store, as_of, config: run_state_panel(store, as_of, config),
}


MODULE_DESCRIPTIONS = {
    "US_INFLATION_MOMENTUM_V1": "CPI/PCE 1-3 month momentum and year-over-year inflation",
    "US_LABOR_TIGHTNESS_V1": "Payroll, unemployment and wage pressure",
    "US_ACTIVITY_NOWCAST_MONITOR_V1": "Industrial production, retail sales and employment activity",
    "US_COMMODITY_SUPPLY_DEMAND_V1": "EIA WTI energy-price pressure",
    "US_TREASURY_YIELD_DECOMP_V1": "10-year nominal/real/breakeven yield decomposition",
    "US_FINANCIAL_CONDITIONS_V1": "Chicago Fed NFCI financial conditions",
    "US_TREASURY_SUPPLY_V1": "Treasury debt stock and supply-pressure proxy",
    "US_STATE_HOUSING_LABOR_PANEL_V1": "Real state panel: unemployment and FHFA house prices with fixed effects",
}
