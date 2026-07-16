from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .analytics.modules import MODULE_DESCRIPTIONS, MODULE_RUNNERS
from .llm import DeepSeekClient
from .schemas import PanelConfig, ParsedQuery


ALLOWED_MODULES = tuple(MODULE_RUNNERS.keys())


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def heuristic_route(question: str, horizon_months: int | None = None) -> ParsedQuery:
    text = question.lower()
    modules: list[str] = []
    unsupported: list[str] = []
    intent = "GENERAL_MACRO"

    if any(word in text for word in ("通胀", "inflation", "cpi", "pce", "物价")):
        intent = "INFLATION"
        modules += ["US_INFLATION_MOMENTUM_V1", "US_COMMODITY_SUPPLY_DEMAND_V1", "US_LABOR_TIGHTNESS_V1"]
    if any(word in text for word in ("收益率", "利率", "treasury", "yield", "十年", "10年", "10-year", "fed", "美联储")):
        intent = "RATES"
        modules += ["US_TREASURY_YIELD_DECOMP_V1", "US_FINANCIAL_CONDITIONS_V1"]
        if "US_INFLATION_MOMENTUM_V1" not in modules:
            modules.append("US_INFLATION_MOMENTUM_V1")
    if any(word in text for word in ("衰退", "增长", "经济活动", "recession", "growth", "gdp", "需求")):
        intent = "ACTIVITY"
        modules += ["US_ACTIVITY_NOWCAST_MONITOR_V1", "US_LABOR_TIGHTNESS_V1", "US_FINANCIAL_CONDITIONS_V1"]
    if any(word in text for word in ("就业", "失业", "工资", "labor", "employment", "payroll", "wage")):
        intent = "LABOR"
        modules += ["US_LABOR_TIGHTNESS_V1", "US_ACTIVITY_NOWCAST_MONITOR_V1"]
    if any(word in text for word in ("油价", "能源", "原油", "wti", "oil", "energy")):
        intent = "ENERGY"
        modules += ["US_COMMODITY_SUPPLY_DEMAND_V1", "US_INFLATION_MOMENTUM_V1"]
    if any(word in text for word in ("财政", "赤字", "债务", "发行", "fiscal", "deficit", "debt", "issuance")):
        intent = "FISCAL"
        modules += ["US_TREASURY_SUPPLY_V1", "US_TREASURY_YIELD_DECOMP_V1", "US_FINANCIAL_CONDITIONS_V1"]
    if any(word in text for word in ("州", "面板", "固定效应", "房价", "state", "panel", "fixed effect", "house price")):
        intent = "HOUSING_PANEL"
        modules += ["US_STATE_HOUSING_LABOR_PANEL_V1"]
    if any(word in text for word in ("ai", "人工智能", "职位发布", "job posting")):
        unsupported.append("第一版尚未接入 Census BTOS AI adoption 与职位发布数据，只能覆盖劳动和活动结果。")
        modules += ["US_LABOR_TIGHTNESS_V1", "US_ACTIVITY_NOWCAST_MONITOR_V1"]
    if any(word in text for word in ("关税", "贸易", "进口", "出口", "tariff", "trade", "import", "export")):
        unsupported.append("第一版尚未实现关税事件与 Census 国际贸易工作流。")
    if not modules:
        modules = [
            "US_ACTIVITY_NOWCAST_MONITOR_V1",
            "US_LABOR_TIGHTNESS_V1",
            "US_INFLATION_MOMENTUM_V1",
            "US_TREASURY_YIELD_DECOMP_V1",
            "US_FINANCIAL_CONDITIONS_V1",
        ]

    modules = _unique(modules)[:7]
    coverage = "PARTIAL" if unsupported else "FULL"
    return ParsedQuery(
        horizon_months=horizon_months or 3,
        intent=intent,
        selected_modules=modules,
        panel_config=PanelConfig(),
        coverage=coverage,
        unsupported_aspects=unsupported,
        reasoning="Deterministic keyword fallback router",
    )


class QueryRouter:
    def __init__(self, llm: DeepSeekClient) -> None:
        self.llm = llm

    def route(self, question: str, horizon_months: int | None = None) -> tuple[ParsedQuery, dict[str, Any]]:
        fallback = heuristic_route(question, horizon_months)
        if not self.llm.available:
            return fallback, {"provider": "fallback", "status": "NO_KEY"}

        module_lines = "\n".join(
            f"- {module_id}: {description}"
            for module_id, description in MODULE_DESCRIPTIONS.items()
        )
        system = f"""
You are the constrained query router for MacroTrace, a US macro research engine.
You never write code, formulas, SQL, URLs, or new factor names. Select only module IDs from this allowlist:
{module_lines}

Return one JSON object with exactly these fields:
jurisdiction: always "US"
horizon_months: integer 1..60
intent: one of INFLATION, ACTIVITY, LABOR, RATES, FISCAL, ENERGY, HOUSING_PANEL, GENERAL_MACRO
selected_modules: array containing only allowlisted module IDs, maximum 7
panel_config: object with start_year (2000..2024), fixed_effects (ENTITY, TIME, TWO_WAY), covariance (HC1, CLUSTER_ENTITY)
coverage: FULL, PARTIAL, or UNSUPPORTED
unsupported_aspects: array of short Chinese strings
reasoning: one short Chinese sentence explaining the routing, not the economic answer

The state panel has a locked formula: state unemployment rate on state house-price YoY. You may select window/fixed effects/covariance only.
Mark trade, tariffs, AI adoption, firm data, detailed forecasts or causal claims PARTIAL unless the allowlist genuinely covers them.
""".strip()
        user = json.dumps(
            {"question": question, "user_horizon_months": horizon_months},
            ensure_ascii=False,
        )
        try:
            raw = self.llm.json_completion(system, user, max_tokens=900)
            raw["selected_modules"] = [
                module_id
                for module_id in _unique(raw.get("selected_modules", []))
                if module_id in ALLOWED_MODULES
            ][:7]
            if not raw["selected_modules"]:
                raw["selected_modules"] = fallback.selected_modules
                raw["coverage"] = "PARTIAL"
                raw.setdefault("unsupported_aspects", []).append("LLM 未选择合法模块，已使用固定路由。")
            if horizon_months is not None:
                raw["horizon_months"] = horizon_months
            parsed = ParsedQuery.model_validate(raw)
            return parsed, {"provider": "deepseek", "model": self.llm.model, "status": "SUCCESS"}
        except (ValidationError, ValueError, KeyError, TypeError, json.JSONDecodeError, Exception) as exc:  # noqa: BLE001
            return fallback, {"provider": "fallback", "status": "DEEPSEEK_FAILED", "error_type": type(exc).__name__}

