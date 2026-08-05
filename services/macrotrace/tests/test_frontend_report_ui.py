from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (ROOT / "frontend" / name).read_text(encoding="utf-8")


def test_reader_facing_report_sections_follow_required_order() -> None:
    html = _read("index.html")

    assert "直接结论 / 研究报告" in html
    assert "REGISTERED SYNTHESIS" not in html
    ordered_ids = ["reportAbstract", "mechanismList", "empiricalList", "reportConclusion"]
    positions = [html.index(f'id="{section_id}"') for section_id in ordered_ids]
    assert positions == sorted(positions)


def test_daily_brief_is_the_first_product_stage_and_can_route_to_research() -> None:
    html = _read("index.html")
    javascript = _read("app.js")

    assert html.index('id="dailyBrief"') < html.index('id="researchForm"')
    assert "01 研究报告" in html
    assert "02 研究工作台" in html
    assert "selectionResearchButton" in html
    assert "compileSelectedExcerpt" in javascript
    assert '$("#selectionResearchButton").addEventListener' in javascript


def test_daily_source_picker_prefers_backend_chinese_names() -> None:
    javascript = _read("app.js")

    assert "source.name_zh || source.display_name || source.name || localDisplayName" in javascript
    assert 'source_id: "STLFED"' in javascript
    assert 'source_id: "ATL_GDPNOW"' in javascript
    assert 'source_id: "CFTC"' in javascript
    assert 'source_id: "CENSUS"' in javascript


def test_frontend_prefers_structured_report_and_links_evidence_nodes() -> None:
    javascript = _read("app.js")

    assert "result.report || synthesis.report" in javascript
    assert "function renderResearchReport(report)" in javascript
    assert 'report?.direct_answer?.headline' in javascript
    assert 'report?.direct_answer?.text' in javascript
    assert 'data-report-node=' in javascript
    assert "打开模型、回归表与诊断" in javascript


def test_ui_uses_readable_report_and_graph_scale() -> None:
    css = _read("styles.css")
    javascript = _read("app.js")

    assert ".research-report" in css
    assert ".report-lead { max-width: 1120px; font: 400 18px/1.95" in css
    assert ".query-console textarea { min-height: 164px;" in css
    assert ".graph-node { width: 246px; min-height: 94px;" in css
    assert "column * 282" in javascript
    assert "index * 116" in javascript
