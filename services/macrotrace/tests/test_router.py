from __future__ import annotations

from backend.app.llm import DeepSeekClient
from backend.app.router import QueryRouter


def router() -> QueryRouter:
    return QueryRouter(DeepSeekClient("", "deepseek-v4-flash", "https://api.deepseek.com"))


def test_inflation_yield_question_routes_to_fixed_modules() -> None:
    parsed, trace = router().route("未来美国通胀会不会加速，并推动10年期收益率上升？", 3)
    assert trace["provider"] == "fallback"
    assert "US_INFLATION_MOMENTUM_V1" in parsed.selected_modules
    assert "US_TREASURY_YIELD_DECOMP_V1" in parsed.selected_modules
    assert parsed.horizon_months == 3


def test_ai_question_is_partial_not_fabricated() -> None:
    parsed, _ = router().route("AI 是否已经导致美国失业率上升？", 6)
    assert parsed.coverage == "PARTIAL"
    assert parsed.unsupported_aspects
    assert all("AI" not in module_id or "STATE" in module_id for module_id in parsed.selected_modules)


def test_panel_question_cannot_change_formula() -> None:
    parsed, _ = router().route("用州级面板和双向固定效应研究房价与失业率", 12)
    assert "US_STATE_HOUSING_LABOR_PANEL_V1" in parsed.selected_modules
    assert parsed.panel_config.fixed_effects == "TWO_WAY"

