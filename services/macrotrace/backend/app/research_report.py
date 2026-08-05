from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from .registry import RegistryStore


METHOD_LABELS = {
    "M.DFM_NOWCAST.V1": "动态因子与桥接预测",
    "M.VAR_SYSTEM.V1": "向量自回归（VAR）",
    "M.LOCAL_PROJECTION.V1": "局部投影与动态响应",
    "M.GROWTH_AT_RISK.V1": "增长尾部风险分位数模型",
    "M.UNIVARIATE_AR.V1": "单变量时间序列基准",
    "M.BRIDGE_OLS.V1": "多指标桥接回归",
    "M.PANEL_FE_FIXTURE.V1": "面板固定效应",
}

ROLE_LABELS = {
    "CORE": "主要分析",
    "BENCHMARK": "基准比较",
    "ROBUSTNESS": "稳健性检验",
    "FALSIFICATION": "反证规格",
}

FORBIDDEN_PUBLIC_TERMS = (
    "主命题",
    "注册命题",
    "序数信号",
    "系统平衡分",
    "等泳道",
    "Registry",
    "claim_id",
    "lane_id",
    "直接回答是",
)


def _clean_finding(item: dict[str, Any]) -> str:
    text = str(item.get("finding_zh") or item.get("label_zh") or "").strip()
    if "（" in text:
        text = text.split("（", 1)[0]
    return text.rstrip("。； ")


def _question_stem(question: str, limit: int = 110) -> str:
    value = " ".join(str(question).strip().split()).rstrip("？?")
    return value if len(value) <= limit else value[: limit - 1] + "…"


DOMAIN_LABELS = {
    "MACRO": "宏观经济",
    "EQUITY_INDEX": "股票指数",
    "SINGLE_EQUITY": "个股",
    "BOND": "债券与利率",
    "INDUSTRY": "行业景气",
    "COMMODITY": "商品",
    "CROSS_ASSET": "跨资产",
    "OTHER": "综合研究",
}


def _directional_headline(question: str, plan: dict[str, Any], aggregation: dict[str, Any], primary: list[str]) -> str:
    “””Generate a concise, question-anchored headline that directly answers the research question.

    Instead of a structured label like “劳动力市场偏强”, the headline must sound like a
    researcher's bottom line: it names the object, states the direction, and cites the
    strongest piece of evidence — in one sentence the reader can quote.
    “””
    query = plan.get(“query”) or {}
    domain = str(query.get(“domain”) or “MACRO”)
    score = aggregation.get(“primary_score”)
    if not isinstance(score, (int, float)):
        score = aggregation.get(“ordinal_score”)
    stem = _question_stem(question, 80)
    top_evidence = primary[0] if primary else “”
    second_evidence = primary[1] if len(primary) > 1 else “”

    if re.search(r”是否|是不是|能否|会不会|有没有”, question):
        if isinstance(score, (int, float)) and score < 0:
            verdict = “证据较不支持这一判断”
        elif isinstance(score, (int, float)) and score > 0:
            verdict = “证据较支持这一判断”
        else:
            stance = str(aggregation.get(“stance”) or “”)
            verdict = “证据较不支持” if “DOWNSIDE” in stance or “NEGATIVE” in stance else “证据较支持” if “UPSIDE” in stance or “POSITIVE” in stance else “现有证据尚不足以确认”
        if top_evidence:
            return f”针对”{stem}”，{verdict}。核心信号来自{top_evidence}”
        return f”针对”{stem}”，{verdict}”

    if top_evidence:
        if isinstance(score, (int, float)):
            if score >= 0.08:
                return f”{top_evidence}指向偏强方向——针对”{stem}”，数据整体支持这一判断”
            elif score > 0:
                return f”针对”{stem}”，{top_evidence}提供边际支持，但方向优势尚弱”
            elif score <= -0.08:
                return f”{top_evidence}指向偏弱方向——针对”{stem}”，数据整体支持这一判断”
            elif score < 0:
                return f”针对”{stem}”，{top_evidence}提供边际偏弱信号，但方向优势尚弱”
            else:
                return f”针对”{stem}”，当前可执行数据未形成可辨认的方向优势”
        else:
            stance = str(aggregation.get(“stance”) or “”)
            direction = “上行” if “UPSIDE” in stance or “POSITIVE” in stance else “下行” if “DOWNSIDE” in stance or “NEGATIVE” in stance else “中性”
            return f”针对”{stem}”，{top_evidence}指向{second_evidence if second_evidence else ''}方向为{direction}”
    return f”针对”{stem}”，当前可执行证据{score:+d if isinstance(score,(int,float)) else '缺少明确方向'}”


def _safe_get(registry: RegistryStore, registry_name: str, object_id: str) -> dict[str, Any]:
    try:
        return registry.get(registry_name, object_id)
    except Exception:
        return {}


def _factor_descriptions(registry: RegistryStore, factor_ids: list[str]) -> list[str]:
    descriptions = []
    for factor_id in factor_ids:
        factor = _safe_get(registry, "factors", factor_id)
        definition = factor.get("definition") or factor_id
        unit = factor.get("unit")
        descriptions.append(f"{definition}（{unit}）" if unit else str(definition))
    return descriptions


def _sample_text(sample: dict[str, Any] | None) -> str:
    sample = sample or {}
    start = sample.get("start")
    end = sample.get("end")
    observations = sample.get("observations")
    frequency = sample.get("frequency")
    parts = []
    if start or end:
        parts.append(f"样本期 {start or '未记录'} 至 {end or '未记录'}")
    if observations is not None:
        parts.append(f"{observations} 个观测")
    if frequency:
        parts.append(f"频率为 {frequency}")
    return "，".join(parts) or "样本窗口记录在节点的数据与溯源页签中"


def _diagnostic_text(diagnostics: list[dict[str, Any]] | None) -> str:
    diagnostics = diagnostics or []
    counts = {"PASS": 0, "WARNING": 0, "FAIL": 0, "NOT_APPLICABLE": 0}
    for diagnostic in diagnostics:
        status = str(diagnostic.get("status") or "WARNING")
        counts[status] = counts.get(status, 0) + 1
    if not diagnostics:
        return "该结果没有返回可展示的诊断统计。"
    return (
        f"共运行 {len(diagnostics)} 项方法专属诊断："
        f"{counts.get('PASS', 0)} 项通过，{counts.get('WARNING', 0)} 项警告，"
        f"{counts.get('FAIL', 0)} 项失败，{counts.get('NOT_APPLICABLE', 0)} 项不适用。"
    )


def _result_implication(result: dict[str, Any], contribution: dict[str, Any] | None) -> str:
    if contribution:
        score = float(contribution.get("ordinal_signal", 0.0))
        if score > 0:
            meaning = contribution.get("positive_meaning")
        elif score < 0:
            meaning = contribution.get("negative_meaning")
        else:
            meaning = "这一项没有形成明确方向，需要与其他证据共同解释。"
        if meaning:
            return str(meaning)
    direction = str(result.get("direction") or "").upper()
    if direction in {"UP", "INCREASING", "POSITIVE"}:
        return "这一结果为相应经济指标提供偏上行的证据，但仍受模型诊断和样本外表现约束。"
    if direction in {"DOWN", "DECREASING", "NEGATIVE"}:
        return "这一结果为相应经济指标提供偏下行的证据，但仍受模型诊断和样本外表现约束。"
    return "这一结果主要用于交叉验证其他分析，没有单独决定最终结论。"


def _rank_results(results: list[dict[str, Any]], aggregation: dict[str, Any]) -> list[dict[str, Any]]:
    by_node = {str(item.get("node_id")): item for item in results}
    ranked: list[tuple[float, dict[str, Any]]] = []
    seen: set[str] = set()
    for contribution in aggregation.get("contributions", []):
        node_id = str(contribution.get("node_id"))
        result = by_node.get(node_id)
        if result is None or node_id in seen:
            continue
        importance = (
            abs(float(contribution.get("ordinal_signal", 0.0)))
            * float(contribution.get("quality_multiplier", 0.35))
            * max(float(contribution.get("within_claim_weight", 0.1)), 0.05)
        )
        ranked.append((importance, {**result, "_contribution": contribution}))
        seen.add(node_id)
    for result in results:
        node_id = str(result.get("node_id"))
        if (
            node_id not in seen
            and result.get("status") in {"SUCCESS", "WARNING"}
            and result.get("specification_role", "CORE") == "CORE"
        ):
            ranked.append((0.0, {**result, "_contribution": None}))
            seen.add(node_id)
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in ranked]


def build_research_report(
    question: str,
    plan: dict[str, Any],
    results: list[dict[str, Any]],
    aggregation: dict[str, Any],
    registry: RegistryStore,
    *,
    limitations: list[str],
    falsifiers: list[str],
) -> dict[str, Any]:
    """Build an evidence-bound, reader-facing report without engineering jargon."""
    question_text = _question_stem(question)
    primary = [_clean_finding(item) for item in aggregation.get("primary_findings", [])]
    primary = [item for item in primary if item]
    context = [_clean_finding(item) for item in aggregation.get("context_findings", [])]
    context = [item for item in context if item]
    evidence_state = aggregation.get("evidence_state")
    answerability = aggregation.get("answerability")

    domain = str((plan.get(“query”) or {}).get(“domain”) or “MACRO”)
    domain_label = DOMAIN_LABELS.get(domain, “综合研究”)
    if primary:
        headline = _directional_headline(question, plan, aggregation, primary)
        # Direct answer: respond to the question head-on, not with a structured label.
        direct_text = f”{headline}。”
        if len(primary) >= 2:
            direct_text += f” 主要依据：{primary[0]}；{primary[1]}。”
        elif primary:
            direct_text += f” 主要依据：{primary[0]}。”
        if aggregation.get(“conflicts_retained”):
            direct_text += “不同证据之间仍有分歧，结论为有条件的方向判断。”
        if evidence_state == “ASSOCIATIONAL_ONLY”:
            direct_text += “当前证据等级为关联性，尚未达到因果识别标准。”
    elif answerability == “UNSUPPORTED”:
        headline = f”针对”{question_text}”，当前可执行数据不足以形成方向性判断”
        direct_text = (
            “现有已注册数据与模型没有形成足以支持上行或下行的稳定合力。”
            “这不等于问题无解，而是目前最符合证据的答案是暂不做强方向押注。”
        )
    else:
        headline = f”针对”{question_text}”，当前证据倾向中性”
        direct_text = “现有分析没有形成足够强的一致方向，可执行证据已被保留为条件性判断。”

    successful = [item for item in results if item.get(“status”) in {“SUCCESS”, “WARNING”}]
    # Build abstract that synthesizes evidence into a natural-language answer.
    abstract_points = primary + context[:2]
    abstract_text = direct_text
    abstract_text += (
        f” 本轮实际运行 {len(successful)} 个实证规格，覆盖度为 {aggregation.get('coverage')}，”
        f”综合置信度为 {aggregation.get('confidence')}。”
    )
    if context:
        abstract_text += “ 背景证据：” + “；”.join(context[:2]) + “。”
    # Append a one-line “bottom line” that the reader can skim.
    if primary:
        bottom = “综合判断：” + “；”.join(primary[:3])
        abstract_text += f” {bottom}。”

    result_nodes_by_research: dict[str, list[str]] = {}
    for result in successful:
        result_nodes_by_research.setdefault(str(result.get("research_node_id")), []).append(str(result.get("node_id")))
    specs_by_mechanism: dict[str, list[dict[str, Any]]] = {}
    for specification in plan.get("model_specifications", []):
        specs_by_mechanism.setdefault(str(specification.get("mechanism_id")), []).append(specification)

    mechanism_decisions = [
        decision for decision in plan.get("mechanisms", [])
        if decision.get("role") in {"CORE", "SUPPORTING"}
    ]
    mechanism_decisions.sort(
        key=lambda decision: (
            0 if decision.get("role") == "CORE" else 1,
            -len(specs_by_mechanism.get(str(decision.get("mechanism_id")), [])),
            str(decision.get("mechanism_id")),
        )
    )
    mechanisms = []
    for decision in mechanism_decisions:
        mechanism_id = str(decision.get("mechanism_id"))
        mechanism = _safe_get(registry, "mechanisms", mechanism_id)
        lane = _safe_get(registry, "lanes", str(decision.get("lane_id")))
        linked_nodes: list[str] = []
        for specification in specs_by_mechanism.get(mechanism_id, []):
            linked_nodes.extend(result_nodes_by_research.get(str(specification.get("node_id")), []))
        linked_nodes = list(dict.fromkeys(linked_nodes))
        mechanisms.append(
            {
                "mechanism_id": mechanism_id,
                "lane_id": decision.get("lane_id"),
                "title": mechanism.get("name") or lane.get("name") or mechanism_id,
                "explanation": mechanism.get("hypothesis") or decision.get("reason") or lane.get("mechanism"),
                "transmission_chain": (
                    f"{lane.get('name') or decision.get('lane_id')}中的状态变化，"
                    f"通过{mechanism.get('name') or '该机制'}影响问题所关心的结果。"
                ),
                "role": decision.get("role"),
                "source_node_ids": linked_nodes,
                "registry_refs": [mechanism_id, str(decision.get("lane_id"))],
            }
        )
        if len(mechanisms) >= 8:
            break

    ranked_results = _rank_results(results, aggregation)
    empirical = []
    for result in ranked_results[:12]:
        node_id = str(result.get("node_id"))
        recipe_id = str(result.get("model_recipe_id"))
        contribution = result.get("_contribution")
        specification = result.get("specification") or {}
        factor_ids = list(result.get("factor_ids") or [])
        factor_descriptions = _factor_descriptions(registry, factor_ids)
        # Build a question-aware purpose: why this model matters for the research question.
        method_label = METHOD_LABELS.get(recipe_id, result.get("method") or recipe_id)
        role_label = ROLE_LABELS.get(str(result.get("specification_role", "CORE")), str(result.get("specification_role", "CORE")))
        target_var = factor_descriptions[0] if factor_descriptions else "主要宏观指标"
        if role_label == "主要分析":
            purpose = (
                f"针对"{_question_stem(question, 50)}"，核心任务是检验{target_var}的方向与显著性。"
                f"如果{target_var}在此规格中显著，则它构成回答原问题的主要实证依据。"
            )
        elif role_label == "稳健性检验":
            purpose = (
                f"为检验主要分析结论是否对模型设定敏感，使用{method_label}重新估计{target_var}的效应。"
                f"如果结论与主要分析一致，则说明结果对规格选择具有稳健性。"
            )
        elif role_label == "基准比较":
            purpose = (
                f"使用{method_label}建立{target_var}的基准预测，"
                f"为更复杂模型提供比较锚点。"
            )
        elif role_label == "反证规格":
            purpose = (
                f"如果{target_var}在此反证规格下不再显著或方向反转，"
                f"则主要分析的结论需要限制适用范围或降级置信度。"
            )
        else:
            purpose = f"通过{method_label}估计{target_var}，为"{_question_stem(question, 40)}"提供{role_label}证据。"
        empirical.append(
            {
                "node_id": node_id,
                "title": f"{method_label}：{target_var}",
                "method": result.get("method") or method_label,
                "role": role_label,
                "question_addressed": purpose,
                "data_and_sample": _sample_text(result.get("sample")),
                "variables": factor_descriptions,
                "specification": specification.get("formula") or f"使用预注册的 {method_label} 规格。",
                "finding": result.get("summary") or "模型完成运行，但没有返回简明结果摘要。",
                "implication": _result_implication(result, contribution),
                "diagnostics": _diagnostic_text(result.get("diagnostics")),
                "source_node_ids": [node_id],
            }
        )

    conclusion_text = direct_text
    if aggregation.get("conflicts_retained"):
        conclusion_text += " 由于主要模型之间并非完全同向，最终判断保留了证据分歧。"
    conclusion_text += (
        f" 结论置信度为 {aggregation.get('confidence')}，覆盖度为 {aggregation.get('coverage')}；"
        "后续官方数据若触发下列证伪条件，应重新运行并修订结论。"
    )
    source_node_ids = [str(item.get("node_id")) for item in successful]
    return {
        "schema_version": "0.3.0",
        "title": f"实证研究报告：{_question_stem(question, 40)}",
        "research_context": {
            "domain": domain,
            "domain_label": domain_label,
            "jurisdiction": (plan.get("query") or {}).get("jurisdiction", "US"),
            "answer_style": "对象优先、方向优先、证据约束",
        },
        "question": question,
        "direct_answer": {
            "headline": headline,
            "text": direct_text,
            "source_node_ids": source_node_ids,
        },
        "abstract": {
            "title": "摘要",
            "text": abstract_text,
            "key_points": abstract_points[:5],
            "source_node_ids": source_node_ids,
        },
        "economic_mechanisms": mechanisms,
        "empirical_evidence": empirical,
        "method_summary": {
            "purpose": f"针对"{question_text}"，依次完成经济机制拆解、计量规格配置、模型执行、诊断与证据综合。每个模型都回答原问题的一个侧面，而非独立的技术演示。",
            "successful_runs": len(successful),
            "highlighted_runs": len(empirical),
            "additional_runs": max(0, len(successful) - len(empirical)),
            "pipeline": "机制 → 规格 → 执行 → 诊断 → 证据综合",
        },
        "conclusion": {
            "title": "总结",
            "text": conclusion_text,
            "confidence": aggregation.get("confidence"),
            "coverage": aggregation.get("coverage"),
            "limitations": list(dict.fromkeys(limitations)),
            "falsifiers": list(dict.fromkeys(falsifiers)),
            "source_node_ids": source_node_ids,
        },
    }


def merge_llm_report_language(fallback: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    """Merge prose only; all methods, samples, variables and lineage stay deterministic."""
    report = deepcopy(fallback)
    required = {"direct_answer", "abstract", "mechanism_explanations", "empirical_explanations", "conclusion"}
    if set(output) != required:
        raise ValueError("report language output has an invalid top-level contract")

    direct = output["direct_answer"]
    abstract = output["abstract"]
    conclusion = output["conclusion"]
    if set(direct) != {"headline", "text"} or set(abstract) != {"text", "key_points"} or set(conclusion) != {"text"}:
        raise ValueError("report language output has an invalid section contract")
    if not isinstance(abstract["key_points"], list) or not all(isinstance(item, str) for item in abstract["key_points"]):
        raise ValueError("abstract key_points must be a string array")

    public_text = " ".join(
        [str(direct["headline"]), str(direct["text"]), str(abstract["text"]), str(conclusion["text"])]
        + [str(item) for item in abstract["key_points"]]
        + [str(item) for item in output["mechanism_explanations"]]
        + [str(item) for item in output["empirical_explanations"]]
    )
    if any(term.lower() in public_text.lower() for term in FORBIDDEN_PUBLIC_TERMS):
        raise ValueError("engineering jargon leaked into the reader-facing report")
    if len(str(direct["headline"]).strip()) < 8 or len(str(direct["text"]).strip()) < 30:
        raise ValueError("direct answer is too shallow")

    # The headline is a deterministic synthesis artifact.  The language model
    # may improve the explanatory prose, but cannot turn an identification
    # limit back into the product's dominant conclusion.
    if str(direct["headline"]).strip() != str(fallback["direct_answer"]["headline"]).strip():
        raise ValueError("direct-answer headline must preserve the deterministic stance")
    report["direct_answer"]["text"] = str(direct["text"]).strip()[:1200]
    report["abstract"]["text"] = str(abstract["text"]).strip()[:2400]
    report["abstract"]["key_points"] = [str(item).strip()[:300] for item in abstract["key_points"] if str(item).strip()][:6]
    report["conclusion"]["text"] = str(conclusion["text"]).strip()[:1800]

    mechanisms = {item["mechanism_id"]: item for item in report["economic_mechanisms"]}
    mechanism_updates = output["mechanism_explanations"]
    if not isinstance(mechanism_updates, list):
        raise ValueError("mechanism_explanations must be an array")
    for item in mechanism_updates:
        if set(item) != {"mechanism_id", "explanation", "transmission_chain"}:
            raise ValueError("invalid mechanism explanation contract")
        target = mechanisms.get(str(item["mechanism_id"]))
        if target is None:
            raise ValueError("unknown mechanism id")
        target["explanation"] = str(item["explanation"]).strip()[:900]
        target["transmission_chain"] = str(item["transmission_chain"]).strip()[:700]

    empirical = {item["node_id"]: item for item in report["empirical_evidence"]}
    empirical_updates = output["empirical_explanations"]
    if not isinstance(empirical_updates, list):
        raise ValueError("empirical_explanations must be an array")
    for item in empirical_updates:
        if set(item) != {"node_id", "title", "question_addressed", "finding", "implication"}:
            raise ValueError("invalid empirical explanation contract")
        target = empirical.get(str(item["node_id"]))
        if target is None:
            raise ValueError("unknown empirical node id")
        target["title"] = str(item["title"]).strip()[:240]
        target["question_addressed"] = str(item["question_addressed"]).strip()[:700]
        target["finding"] = str(item["finding"]).strip()[:900]
        target["implication"] = str(item["implication"]).strip()[:700]
    return report


def merge_llm_direct_answer(fallback: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    """Merge a question-anchored second-pass answer without changing evidence or methods."""
    if set(output) != {"headline", "direct_answer", "abstract", "key_points"}:
        raise ValueError("direct-answer editor has an invalid contract")
    if not isinstance(output["key_points"], list) or not all(isinstance(item, str) for item in output["key_points"]):
        raise ValueError("direct-answer key_points must be a string array")
    headline = str(output["headline"]).strip()
    direct_answer = str(output["direct_answer"]).strip()
    abstract = str(output["abstract"]).strip()
    key_points = [str(item).strip() for item in output["key_points"] if str(item).strip()]
    public_text = " ".join([headline, direct_answer, abstract, *key_points])
    if any(term.lower() in public_text.lower() for term in FORBIDDEN_PUBLIC_TERMS):
        raise ValueError("engineering jargon leaked into the direct answer")
    if len(headline) < 12 or len(direct_answer) < 30 or len(abstract) < 30 or not key_points:
        raise ValueError("direct-answer editor output is too shallow")
    question_value = " ".join(str(fallback.get("question") or "").strip().split()).rstrip("？?")
    question_anchor = question_value[: min(24, len(question_value))]
    if question_anchor and question_anchor not in headline:
        raise ValueError("direct-answer headline lost the original question anchor")
    evidence_text = json.dumps(fallback, ensure_ascii=False)
    for number in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?", public_text):
        if number not in evidence_text:
            raise ValueError("direct-answer editor invented a number")
    if any(term in public_text for term in ("目标价", "保证收益", "必然导致", "确定会涨", "确定会跌")):
        raise ValueError("direct-answer editor added an unsupported claim")
    report = deepcopy(fallback)
    report["direct_answer"]["headline"] = headline[:260]
    report["direct_answer"]["text"] = direct_answer[:1200]
    report["abstract"]["text"] = abstract[:2400]
    report["abstract"]["key_points"] = [item[:300] for item in key_points[:6]]
    report["conclusion"]["text"] = direct_answer[:1200] + " " + report["conclusion"]["text"]
    return report
