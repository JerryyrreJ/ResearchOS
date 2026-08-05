from __future__ import annotations

from datetime import UTC, datetime

from backend.app.catalog import ALL_SERIES, dataset_label_zh, factor_label_zh, series_label_zh
from backend.app.daily_brief import REPORT_PRODUCTS, SOURCES, DailyBriefSelectionAgent, DailyBriefService, OfficialSourceSearchAgent


class NoLlm:
    available = False


class CapturingLlm:
    available = True

    def __init__(self) -> None:
        self.system = ""
        self.payload: dict = {}

    def json_completion(self, system: str, user: str, max_tokens: int) -> dict:
        import json

        self.system = system
        self.payload = json.loads(user)
        slot = self.payload["view_slots"][0]
        return {
            "headline": "美股市场投资观点",
            "summary": "基于官方证据形成有退出条件的方向性判断。",
            "items": [
                {
                    "item_id": slot["item_id"],
                    "headline": "条件性偏多美国大型股票指数ETF",
                    "summary": "若政策和盈利证据继续同向改善，则未来一至四周风险偏好有望改善。",
                    "significance": "通过美国大型股票指数ETF表达，证据转弱时退出。",
                    "stance": "条件性偏多",
                    "asset_expression": "美国大型股票指数ETF",
                    "time_horizon": "未来一至四周",
                    "core_thesis": "政策和盈利证据若继续同向改善，风险偏好可能改善。",
                    "catalysts": ["后续官方证据继续同向改善"],
                    "falsifiers": ["后续官方证据转弱"],
                    "exit_conditions": ["证据转弱时退出"],
                    "confidence": "低",
                    "confidence_basis": "当前只有单一官方来源。",
                    "support_level": "筛选级观点",
                    "evidence_refs": slot["evidence_refs"],
                    "source_refs": slot["source_refs"],
                    "empirical_question": "这一条件性偏多观点能否通过盈利预期、估值与风险偏好机制影响未来一至四周美股表现，何种证据会推翻它？",
                }
            ],
        }


def test_daily_brief_catalog_has_ten_real_feed_sources() -> None:
    by_id = {source.source_id: source for source in SOURCES}

    assert len(by_id) >= 10
    assert by_id["STLFED"].url == "https://www.stlouisfed.org/rss/page%20resources/publications/blog-entries"
    assert by_id["ATL_GDPNOW"].url == "https://www.atlantafed.org/rss/GDPNow"
    assert by_id["ATL_MACROBLOG"].url == "https://www.atlantafed.org/rss/macroblog"
    assert by_id["CFTC"].url == "https://www.cftc.gov/RSS/RSSGP/rssgp.xml"
    assert by_id["CENSUS"].url == "https://www.census.gov/economic-indicators/indicator.xml"
    assert all(source.url.startswith("https://") and source.home_url.startswith("https://") for source in SOURCES)


def test_source_fetch_failure_is_visible_and_safe(monkeypatch) -> None:
    class BrokenClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            raise OSError("offline")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("backend.app.daily_brief.httpx.Client", BrokenClient)
    rows, status = OfficialSourceSearchAgent()._fetch_source(SOURCES[0], datetime.now(UTC))

    assert rows == []
    assert status == {"source_id": "FED", "name": "美联储", "status": "暂不可用", "items": "0"}


def test_expanded_catalog_labels_are_chinese_including_arizona_series() -> None:
    assert series_label_zh("AZUR") == "亚利桑那州失业率"
    assert series_label_zh("AZSTHPI") == "亚利桑那州全口径房价指数"
    assert all(any("\u3400" <= char <= "\u9fff" for char in spec.label) for spec in ALL_SERIES)
    assert dataset_label_zh("DS.FRED.STATE_PANEL") == "美国州级经济面板数据"
    assert factor_label_zh("F.STATE.UNEMPLOYMENT") == "美国州级失业率"


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

    view = result["items"][0]
    assert view["url"] == rows[0]["url"]
    assert view["generation_mode"] == "跨来源条件性观点回退"
    assert view["stance"] == "防守性低配"
    assert view["asset_expression"]
    assert view["time_horizon"]
    assert view["catalysts"] and view["falsifiers"] and view["exit_conditions"]
    assert view["confidence"] == "低"
    assert view["evidence_refs"] == ["one"]
    assert view["source_refs"] == ["TEST"]
    assert "反证条件" in view["empirical_question"]
    assert result["report_mode"] == "investment_views"
    assert service.latest() == result


def test_report_products_have_distinct_execution_profiles() -> None:
    assert set(REPORT_PRODUCTS) == {"daily", "weekly", "monthly", "equity", "futures"}
    for product in REPORT_PRODUCTS.values():
        assert int(product["lookback_hours"]) > 0
        assert int(product["item_limit"]) > 0
        assert product["report_object"]
        assert product["editorial_focus"]
        assert product["preferred_domains"]
        assert product["preferred_source_ids"]

    assert REPORT_PRODUCTS["daily"]["lookback_hours"] < REPORT_PRODUCTS["weekly"]["lookback_hours"]
    assert REPORT_PRODUCTS["weekly"]["lookback_hours"] < REPORT_PRODUCTS["monthly"]["lookback_hours"]
    assert REPORT_PRODUCTS["equity"]["preferred_domains"][0] == "股票市场"
    assert REPORT_PRODUCTS["equity"]["preferred_source_ids"][0] == "SEC"
    assert REPORT_PRODUCTS["futures"]["preferred_domains"][0] == "能源与商品"
    assert REPORT_PRODUCTS["futures"]["preferred_source_ids"][0] == "EIA"


def test_generation_uses_product_profile_and_requested_sources(tmp_path) -> None:
    service = DailyBriefService(tmp_path, NoLlm())
    calls: list[tuple[int, list[str] | None]] = []

    def search(lookback_hours: int, source_ids: list[str] | None = None):
        calls.append((lookback_hours, source_ids))
        return (
            [_item("energy", "能源与商品", 0.8)],
            [{"source_id": "EIA", "name": "美国能源信息署", "status": "成功", "items": "1"}],
        )

    service.search_agent.search = search
    result = service.generate(report_type="futures", source_ids=["EIA"])

    assert calls == [(REPORT_PRODUCTS["futures"]["lookback_hours"], ["EIA"])]
    assert result["report_type"] == "futures"
    assert result["report_label"] == "美国期货市场报告"
    assert result["report_object"] == REPORT_PRODUCTS["futures"]["report_object"]
    assert result["preferred_source_ids"][0] == "EIA"
    assert service.latest("futures") == result


def test_selection_agent_applies_report_domain_and_source_preferences() -> None:
    recent_macro = _item("macro", "宏观经济", 0.8)
    recent_macro["source_id"] = "BLS"
    slightly_older_energy = _item("energy", "能源与商品", 0.75)
    slightly_older_energy["source_id"] = "EIA"

    selected = DailyBriefSelectionAgent().select(
        [recent_macro, slightly_older_energy],
        limit=1,
        preferred_domains=REPORT_PRODUCTS["futures"]["preferred_domains"],
        preferred_source_ids=REPORT_PRODUCTS["futures"]["preferred_source_ids"],
    )

    assert selected[0]["item_id"] == "energy"


def test_llm_prompt_names_the_selected_report_object(tmp_path) -> None:
    llm = CapturingLlm()
    service = DailyBriefService(tmp_path, llm)
    rows = [_item("equity", "股票市场", 0.9)]
    rows[0]["source_id"] = "SEC"
    rows[0]["source_name"] = "美国证券交易委员会"
    service.search_agent.search = lambda _hours, _sources: (
        rows,
        [{"source_id": "SEC", "name": "美国证券交易委员会", "status": "成功", "items": "1"}],
    )

    result = service.generate(report_type="equity", source_ids=["SEC"])

    assert result["headline"] == "美股市场投资观点"
    assert "美股市场报告" in llm.system
    assert REPORT_PRODUCTS["equity"]["report_object"] in llm.system
    assert "不能把美股报告写成泛宏观日报" in llm.system
    assert "这不是新闻汇总" in llm.system
    assert "risk-on 必须写成“风险偏好上升”" in llm.system
    assert "禁止添加来源没有出现的价格点位、技术突破" in llm.system
    assert llm.payload["report_type"] == "equity"
    assert result["items"][0]["generation_mode"] == "跨来源投资观点综合"


def test_fallback_groups_multiple_news_items_into_one_domain_view(tmp_path) -> None:
    service = DailyBriefService(tmp_path, NoLlm())
    rows = [_item("one", "宏观经济", 0.9), _item("two", "宏观经济", 0.8)]
    rows[1]["source_id"] = "SECOND"
    rows[1]["source_name"] = "第二来源"

    result = service._fallback(rows, [], "weekly")

    assert len(result["items"]) == 1
    assert result["items"][0]["evidence_refs"] == ["one", "two"]
    assert result["items"][0]["source_refs"] == ["TEST", "SECOND"]


def test_latest_regenerates_old_news_card_cache(tmp_path) -> None:
    service = DailyBriefService(tmp_path, NoLlm())
    service.cache_path("daily").write_text(
        '{"schema_version":"0.5.0","report_type":"daily","items":[{"headline":"旧新闻卡"}]}',
        encoding="utf-8",
    )
    service.search_agent.search = lambda _lookback: (
        [_item("fresh", "债券与利率", 0.9)],
        [{"source_id": "TEST", "name": "测试来源", "status": "成功", "items": "1"}],
    )

    result = service.latest("daily")

    assert result["schema_version"] == "0.6.0"
    assert result["items"][0]["view_type"] == "investment_view"
