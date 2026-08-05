from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.registry import RegistryStore
from backend.app.research_report import (
    _directional_headline,
    build_research_report,
    merge_llm_direct_answer,
    merge_llm_report_language,
)


ROOT = Path(__file__).resolve().parents[1]


def _registry() -> RegistryStore:
    return RegistryStore(ROOT / "registry" / "v2")


def _plan() -> dict:
    return {
        "query": {
            "question": "美国经济当前是在走弱还是重新加速，未来三个月衰退风险怎么样？",
            "question_form": "STATE_ASSESSMENT",
            "target_concepts": ["activity", "recession"],
        },
        "mechanisms": [
            {"mechanism_id": "MECH.ACTIVITY.BROAD_STATE", "lane_id": "US.ACTIVITY", "role": "CORE", "reason": "Broad state"},
            {"mechanism_id": "MECH.ACTIVITY.TAIL_RISK", "lane_id": "US.ACTIVITY", "role": "CORE", "reason": "Tail risk"},
        ],
        "model_specifications": [
            {"mechanism_id": "MECH.ACTIVITY.BROAD_STATE", "node_id": "N.ACTIVITY.NOWCAST"},
            {"mechanism_id": "MECH.ACTIVITY.TAIL_RISK", "node_id": "N.ACTIVITY.TAIL_RISK"},
        ],
    }


def _results() -> list[dict]:
    return [
        {
            "status": "SUCCESS",
            "node_id": "MR.ACT.VAR",
            "research_node_id": "N.ACTIVITY.NOWCAST",
            "model_recipe_id": "M.VAR_SYSTEM.V1",
            "method": "Registered vector autoregression",
            "specification_role": "CORE",
            "factor_ids": ["F.ACTIVITY.INDPRO", "F.LABOR.UNEMPLOYMENT", "F.MONETARY.NFCI"],
            "sample": {"start": "2010-01-01", "end": "2025-12-01", "observations": 180, "frequency": "monthly"},
            "specification": {"estimand": "three-month activity forecast", "formula": "y_{t+3}=VAR(L)X_t"},
            "summary": "The VAR projects a small decline in industrial production at month three.",
            "direction": "DOWN",
            "diagnostics": [{"status": "PASS"}, {"status": "WARNING"}],
        },
        {
            "status": "SUCCESS",
            "node_id": "MR.ACT.GAR",
            "research_node_id": "N.ACTIVITY.TAIL_RISK",
            "model_recipe_id": "M.GROWTH_AT_RISK.V1",
            "method": "Quantile Growth-at-Risk",
            "specification_role": "CORE",
            "factor_ids": ["F.ACTIVITY.REAL_GDP", "F.MONETARY.NFCI"],
            "sample": {"start": "1990-01-01", "end": "2025-10-01", "observations": 144, "frequency": "quarterly"},
            "specification": {"estimand": "conditional lower growth quantile", "formula": "Q_tau(g_{t+1}|X_t)"},
            "summary": "The conditional fifth percentile is negative while the median remains positive.",
            "direction": "DOWN",
            "diagnostics": [{"status": "PASS"}],
        },
    ]


def _aggregation() -> dict:
    return {
        "answerability": "ANSWERABLE",
        "evidence_state": "MIXED",
        "coverage": "FULL",
        "confidence": "MEDIUM",
        "conflicts_retained": True,
        "primary_findings": [
            {"finding_zh": "实体活动方向：偏向重新加速（方向较明确，序数信号 +0.2910）"},
            {"finding_zh": "增长下行风险：偏向升高（仅为弱倾向，序数信号 -0.1738）"},
        ],
        "context_findings": [{"finding_zh": "劳动力市场：偏强（仅为弱倾向）"}],
        "contributions": [
            {
                "node_id": "MR.ACT.VAR",
                "ordinal_signal": 0.3,
                "quality_multiplier": 0.7,
                "within_claim_weight": 0.5,
                "positive_meaning": "Stronger activity is supported.",
                "negative_meaning": "Weaker activity is supported.",
            },
            {
                "node_id": "MR.ACT.GAR",
                "ordinal_signal": -0.2,
                "quality_multiplier": 0.7,
                "within_claim_weight": 1.0,
                "positive_meaning": "Downside is contained.",
                "negative_meaning": "Downside risk is elevated.",
            },
        ],
    }


def test_report_directly_answers_question_and_orders_reader_sections() -> None:
    report = build_research_report(
        "美国经济当前是在走弱还是重新加速，未来三个月衰退风险怎么样？",
        _plan(),
        _results(),
        _aggregation(),
        _registry(),
        limitations=["数据 vintage 会影响结果。"],
        falsifiers=["后续活动数据一致反转。"],
    )

    assert report["schema_version"] == "0.3.0"
    assert "直接回答是" not in report["direct_answer"]["text"]
    assert report["direct_answer"]["text"].startswith("对“美国经济当前是在走弱还是重新加速")
    assert "实体活动方向" in report["direct_answer"]["headline"]
    assert report["abstract"]["text"]
    assert len(report["economic_mechanisms"]) == 2
    assert len(report["empirical_evidence"]) == 2
    assert report["empirical_evidence"][0]["data_and_sample"]
    assert report["empirical_evidence"][0]["diagnostics"]
    assert report["method_summary"] == {"successful_runs": 2, "highlighted_runs": 2, "additional_runs": 0}
    assert report["conclusion"]["limitations"] == ["数据 vintage 会影响结果。"]


def test_llm_merge_only_changes_prose_and_preserves_empirical_contract() -> None:
    fallback = build_research_report(
        "美国经济当前是在走弱还是重新加速，未来三个月衰退风险怎么样？",
        _plan(),
        _results(),
        _aggregation(),
        _registry(),
        limitations=["数据 vintage 会影响结果。"],
        falsifiers=["后续活动数据一致反转。"],
    )
    output = {
        "direct_answer": {"headline": fallback["direct_answer"]["headline"], "text": "直接来看，美国经济的中心状态更接近温和重新加速；与此同时，未来三个月的增长下行尾部风险仍高于平静时期。两者并不矛盾。"},
        "abstract": {"text": "多数活动指标仍有韧性，但尾部模型保留了明显的下行情景，因此结论是中心路径温和、风险分布偏左。", "key_points": ["中心活动状态略有改善", "下行尾部风险仍需警惕"]},
        "mechanism_explanations": [
            {"mechanism_id": "MECH.ACTIVITY.BROAD_STATE", "explanation": "生产、消费和就业共同刻画当前商业周期位置。", "transmission_chain": "需求改善会先进入生产与用工，再反映到总体活动。"},
            {"mechanism_id": "MECH.ACTIVITY.TAIL_RISK", "explanation": "金融条件会非对称地改变未来增长分布的下尾。", "transmission_chain": "融资收紧会放大较差状态下的增长损失。"},
        ],
        "empirical_explanations": [
            {"node_id": "MR.ACT.VAR", "title": "活动、失业与金融条件的 VAR", "question_addressed": "检验未来三个月实体活动的中心方向。", "finding": "VAR 给出的工业生产三个月响应略为负值。", "implication": "它对重新加速判断构成谨慎约束。"},
            {"node_id": "MR.ACT.GAR", "title": "增长尾部风险分位数模型", "question_addressed": "检验未来增长分布下尾是否恶化。", "finding": "第五分位增长为负，而中位数仍为正。", "implication": "中心预测不差并不意味着衰退尾部已经消失。"},
        ],
        "conclusion": {"text": "综合来看，基准路径偏向温和扩张，但风险管理上仍应保留下行情景。"},
    }
    merged = merge_llm_report_language(fallback, output)

    assert merged["direct_answer"]["headline"] == fallback["direct_answer"]["headline"]
    assert merged["empirical_evidence"][0]["method"] == fallback["empirical_evidence"][0]["method"]
    assert merged["empirical_evidence"][0]["data_and_sample"] == fallback["empirical_evidence"][0]["data_and_sample"]
    assert merged["conclusion"]["limitations"] == fallback["conclusion"]["limitations"]


def test_llm_report_rejects_engineering_language() -> None:
    fallback = build_research_report(
        "美国经济是否重新加速？",
        _plan(),
        _results(),
        _aggregation(),
        _registry(),
        limitations=[],
        falsifiers=[],
    )
    invalid = {
        "direct_answer": {"headline": "主命题偏向上行", "text": "主命题已经给出方向，但这个文本仍然属于工程语言。"},
        "abstract": {"text": "摘要文本足够长，但仍然没有解决工程语言泄漏。", "key_points": ["测试"]},
        "mechanism_explanations": [],
        "empirical_explanations": [],
        "conclusion": {"text": "结论"},
    }
    with pytest.raises(ValueError, match="engineering jargon"):
        merge_llm_report_language(fallback, invalid)


def test_identification_limit_never_replaces_an_available_stance() -> None:
    aggregation = _aggregation()
    aggregation["answerability"] = "CONDITIONAL"
    aggregation["evidence_state"] = "ASSOCIATIONAL_ONLY"
    report = build_research_report(
        "美国联邦债务扩张是否正在增加10年期收益率压力？",
        _plan(),
        _results(),
        aggregation,
        _registry(),
        limitations=["现有模型不能单独识别严格因果幅度。"],
        falsifiers=["新增官方数据使方向反转。"],
    )
    assert "证据不足" not in report["direct_answer"]["headline"]
    assert "不能确认" not in report["direct_answer"]["headline"]
    assert "严格因果效应" in report["direct_answer"]["text"]
    assert "直接回答是" not in report["direct_answer"]["text"]


def test_market_headline_preserves_a_weak_but_explicit_direction() -> None:
    headline = _directional_headline(
        "Will the S&P 500 rise or fall over the next week?",
        {"query": {"domain": "EQUITY_INDEX"}},
        {"primary_score": -0.03},
        ["方向证据接近中性"],
    )

    assert "边际偏向下跌" in headline
    assert "接近中性" not in headline


def test_new_york_fed_ai_question_remains_the_final_answer_anchor() -> None:
    question = (
        "纽约联储的研究观点是否成立：AI技术应用是否显著重塑了劳动力市场结构与招聘行为？"
        "其传导机制（如岗位技能需求变化、招聘渠道与筛选流程变革）是什么？影响幅度有多大，持续时间多长，预测期限如何？"
        "在不同行业、地区、企业规模及劳动者群体间是否存在异质性？在何种条件下该观点可能不成立或效果减弱？"
    )
    plan = _plan()
    plan["query"] = {"question": question, "domain": "MACRO", "question_form": "HYPOTHESIS_TEST"}
    aggregation = _aggregation()
    aggregation["primary_score"] = 0.04
    aggregation["primary_findings"] = [{"finding_zh": "劳动力市场：偏强"}]

    report = build_research_report(
        question,
        plan,
        _results(),
        aggregation,
        _registry(),
        limitations=["现有结果不能单独识别 AI 应用的严格因果效应。"],
        falsifiers=["直接招聘证据与当前方向相反。"],
    )

    headline = report["direct_answer"]["headline"]
    assert "纽约联储" in headline
    assert "AI技术应用" in headline
    assert "较支持该观点成立" in headline
    assert headline != "劳动力市场：偏强"
    assert report["direct_answer"]["text"].startswith(headline)

    edited = merge_llm_direct_answer(
        report,
        {
            "headline": f"对“{question[:30]}…”，现有证据仅初步支持纽约联储关于人工智能重塑招聘与劳动力结构的观点",
            "direct_answer": "现有证据提供了初步支持，但主要来自劳动力状态与招聘相关背景，尚不足以确认人工智能应用造成了结构性变化。",
            "abstract": "当前结果应理解为对纽约联储观点的有限支持：方向证据可以作为研究线索，因果机制、影响幅度、持续时间与群体异质性仍需直接数据验证。",
            "key_points": ["劳动力偏强只是背景证据，不能单独证明人工智能重塑招聘结构", "现有识别边界要求保留条件性结论"],
        },
    )
    assert "纽约联储" in edited["direct_answer"]["headline"]
    assert "有限支持" in edited["abstract"]["text"]
