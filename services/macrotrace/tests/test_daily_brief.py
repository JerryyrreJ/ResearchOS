from __future__ import annotations

from backend.app.daily_brief import DailyBriefSelectionAgent, DailyBriefService


class NoLlm:
    available = False


def _item(item_id: str, domain: str, score: float) -> dict:
    return {
        "item_id": item_id,
        "source_id": "TEST",
        "source_name": "测试来源",
        "source_home": "https://example.com",
        "title": f"标题 {item_id}",
        "source_summary": "来源原文摘要",
        "url": f"https://example.com/{item_id}",
        "published_at": "2026-08-05T00:00:00+00:00",
        "domain": domain,
        "recency_score": score,
    }


def test_selection_agent_limits_one_domain_from_crowding_out_the_brief() -> None:
    items = [_item(f"macro-{index}", "宏观经济", 1 - index / 100) for index in range(8)]
    items += [_item("bond", "债券与利率", 0.5), _item("equity", "股票市场", 0.4)]
    selected = DailyBriefSelectionAgent().select(items)

    assert sum(item["domain"] == "宏观经济" for item in selected) == 4
    assert {item["domain"] for item in selected} >= {"宏观经济", "债券与利率", "股票市场"}


def test_daily_brief_fallback_preserves_source_and_creates_empirical_question(tmp_path) -> None:
    service = DailyBriefService(tmp_path, NoLlm())
    rows = [_item("one", "行业与产业", 0.8)]
    service.search_agent.search = lambda _lookback: (rows, [{"source_id": "TEST", "name": "测试来源", "status": "成功", "items": "1"}])

    result = service.generate()

    assert result["items"][0]["url"] == rows[0]["url"]
    assert result["items"][0]["generation_mode"] == "中文安全回退"
    assert "美国行业" in result["items"][0]["empirical_question"]
    assert service.latest() == result
