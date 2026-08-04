from __future__ import annotations

import json
from typing import Any

import numpy as np

from .llm import DeepSeekClient
from .schemas import ParsedQuery


WEIGHTS_BY_INTENT: dict[str, dict[str, float]] = {
    "INFLATION": {
        "US_INFLATION_MOMENTUM_V1": 0.55,
        "US_COMMODITY_SUPPLY_DEMAND_V1": 0.20,
        "US_LABOR_TIGHTNESS_V1": 0.25,
    },
    "RATES": {
        "US_TREASURY_YIELD_DECOMP_V1": 0.40,
        "US_INFLATION_MOMENTUM_V1": 0.20,
        "US_COMMODITY_SUPPLY_DEMAND_V1": 0.10,
        "US_LABOR_TIGHTNESS_V1": 0.10,
        "US_FINANCIAL_CONDITIONS_V1": 0.10,
        "US_TREASURY_SUPPLY_V1": 0.10,
    },
    "ACTIVITY": {
        "US_ACTIVITY_NOWCAST_MONITOR_V1": 0.50,
        "US_LABOR_TIGHTNESS_V1": 0.30,
        "US_FINANCIAL_CONDITIONS_V1": 0.20,
    },
    "LABOR": {
        "US_LABOR_TIGHTNESS_V1": 0.70,
        "US_ACTIVITY_NOWCAST_MONITOR_V1": 0.30,
    },
    "ENERGY": {
        "US_COMMODITY_SUPPLY_DEMAND_V1": 0.75,
        "US_INFLATION_MOMENTUM_V1": 0.25,
    },
    "FISCAL": {
        "US_TREASURY_SUPPLY_V1": 0.45,
        "US_TREASURY_YIELD_DECOMP_V1": 0.35,
        "US_FINANCIAL_CONDITIONS_V1": 0.20,
    },
}


def _score(parsed: ParsedQuery, modules: list[dict[str, Any]]) -> float:
    successful = [module for module in modules if module.get("status") == "SUCCESS"]
    if not successful:
        return 0.0
    weights = WEIGHTS_BY_INTENT.get(parsed.intent, {})
    weighted = [
        (float(module.get("signal") or 0), weights.get(module["module_id"], 1.0))
        for module in successful
        if module["module_id"] != "US_STATE_HOUSING_LABOR_PANEL_V1"
    ]
    if not weighted:
        return 0.0
    numerator = sum(signal * weight for signal, weight in weighted)
    denominator = sum(weight for _, weight in weighted)
    return float(np.clip(numerator / denominator, -1, 1))


def _direction(intent: str, score: float) -> str:
    if intent == "HOUSING_PANEL":
        return "ASSOCIATION_ONLY"
    if score > 0.15:
        return "UPWARD" if intent in ("INFLATION", "RATES", "FISCAL", "ENERGY") else "STRONGER"
    if score < -0.15:
        return "DOWNWARD" if intent in ("INFLATION", "RATES", "FISCAL", "ENERGY") else "WEAKER"
    return "MIXED"


def _headline(intent: str, direction: str) -> str:
    labels = {
        "INFLATION": "美国通胀压力",
        "RATES": "美国利率与 10 年期收益率压力",
        "ACTIVITY": "美国实体活动",
        "LABOR": "美国劳动力市场",
        "ENERGY": "美国能源价格压力",
        "FISCAL": "美国财政与债务供给压力",
        "HOUSING_PANEL": "州房价与失业率面板关系",
        "GENERAL_MACRO": "美国宏观状态",
    }
    direction_zh = {
        "UPWARD": "偏上行",
        "DOWNWARD": "偏下行",
        "STRONGER": "偏强",
        "WEAKER": "偏弱",
        "MIXED": "信号混合",
        "ASSOCIATION_ONLY": "只报告条件相关",
    }
    return f"{labels.get(intent, '美国宏观状态')}：{direction_zh[direction]}"


def _falsifiers(intent: str) -> list[str]:
    mapping = {
        "INFLATION": ["后续 CPI 与核心 PCE 的三个月年化同时低于各自同比。", "WTI 与工资动量同时显著反转。"],
        "RATES": ["10 年期实际收益率和盈亏平衡通胀同时反转。", "金融条件显著收紧并压低活动数据。"],
        "ACTIVITY": ["工业生产、非农与零售三组信号连续两次同向反转。"],
        "LABOR": ["非农三个月均值明显转负且失业率持续上升。"],
        "ENERGY": ["WTI 的 4 周和 13 周变化同时转向相反方向。"],
        "FISCAL": ["债务增速与长端收益率压力同时回落。"],
        "HOUSING_PANEL": ["改变样本窗或固定效应后，核心系数符号与显著性不稳定。"],
    }
    return mapping.get(intent, ["核心泳道在下一轮官方数据发布后出现一致反转。"])


def deterministic_synthesis(parsed: ParsedQuery, modules: list[dict[str, Any]]) -> dict[str, Any]:
    score = _score(parsed, modules)
    direction = _direction(parsed.intent, score)
    successful = [module for module in modules if module.get("status") == "SUCCESS"]
    failed = [module for module in modules if module.get("status") != "SUCCESS"]
    high_confidence = sum(module.get("confidence") == "HIGH" for module in successful)
    if parsed.coverage == "FULL" and not failed and high_confidence >= max(1, len(successful) // 2):
        confidence = "HIGH"
    elif successful:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    drivers = sorted(
        [
            {
                "module_id": module["module_id"],
                "title": module["title"],
                "direction": module["direction"],
                "signal": module.get("signal", 0),
                "summary": module["summary"],
            }
            for module in successful
        ],
        key=lambda item: abs(float(item.get("signal") or 0)),
        reverse=True,
    )
    return {
        "headline": _headline(parsed.intent, direction),
        "direction": direction,
        "score": round(score, 3),
        "confidence": confidence,
        "coverage": parsed.coverage,
        "drivers": drivers,
        "conflicts": [
            driver for driver in drivers if (float(driver.get("signal") or 0) * score < 0)
        ],
        "falsifiers": _falsifiers(parsed.intent),
        "unsupported_aspects": parsed.unsupported_aspects,
    }


def llm_interpretation(
    llm: DeepSeekClient,
    question: str,
    parsed: ParsedQuery,
    modules: list[dict[str, Any]],
    deterministic: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not llm.available:
        return None, {"provider": "none", "status": "NO_KEY"}
    compact_modules = [
        {
            "module_id": module.get("module_id"),
            "title": module.get("title"),
            "direction": module.get("direction"),
            "confidence": module.get("confidence"),
            "metrics": module.get("metrics"),
            "summary": module.get("summary"),
            "status": module.get("status"),
        }
        for module in modules
    ]
    system = """
You write the Chinese explanation layer for MacroTrace. The numerical analysis has already been executed by deterministic Python modules on real data.
Return JSON with exactly: answer, mechanism, tensions, limitations.
- answer: 2-4 concise Chinese sentences directly answering the question.
- mechanism: array of at most 4 Chinese strings.
- tensions: array of at most 3 Chinese strings describing conflicting evidence.
- limitations: array of at most 3 Chinese strings.
Never invent or recompute a number. Only mention a number if it appears verbatim in supplied module metrics. Never convert descriptive/associational evidence into causality. Do not claim unsupported coverage.
""".strip()
    user = json.dumps(
        {
            "question": question,
            "parsed_query": parsed.model_dump(),
            "deterministic_synthesis": deterministic,
            "module_results": compact_modules,
        },
        ensure_ascii=False,
        default=str,
    )
    try:
        result = llm.json_completion(system, user, max_tokens=1000)
        clean = {
            "answer": str(result.get("answer", ""))[:1800],
            "mechanism": [str(item)[:400] for item in result.get("mechanism", [])[:4]],
            "tensions": [str(item)[:400] for item in result.get("tensions", [])[:3]],
            "limitations": [str(item)[:400] for item in result.get("limitations", [])[:3]],
        }
        return clean, {"provider": "deepseek", "model": llm.model, "status": "SUCCESS"}
    except Exception as exc:  # noqa: BLE001
        return None, {"provider": "deepseek", "status": "FAILED", "error_type": type(exc).__name__}

