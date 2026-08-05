from __future__ import annotations

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

    if primary:
        headline = "；".join(primary[:2])
        direct_text = f"现有可执行证据整体更支持{headline}。"
        if aggregation.get("conflicts_retained"):
            direct_text += "不同证据之间仍有分歧，因此这是一项有条件的方向判断，而不是确定性预测。"
        if evidence_state == "ASSOCIATIONAL_ONLY":
            direct_text += "这一立场来自预测、时序与系统关联证据；严格因果效应及其幅度仍需独立识别。"
    elif answerability == "UNSUPPORTED":
        headline = "现有可执行证据不足以直接回答这一问题"
        direct_text = (
            "本轮没有获得足够、可验证的数据结果来形成方向判断，"
            "因此不应把基线宏观状态当作该问题的答案。"
        )
    else:
        headline = "当前证据给出有条件但不强烈的方向判断"
        direct_text = "现有分析没有形成足够强的一致方向，但可执行证据已被保留为条件性判断。"

    successful = [item for item in results if item.get("status") in {"SUCCESS", "WARNING"}]
    abstract_points = primary + context[:2]
    abstract_text = direct_text
    abstract_text += (
        f" 本轮实际完成 {len(successful)} 个数据或计量规格，覆盖度为 {aggregation.get('coverage')}，"
        f"综合置信度为 {aggregation.get('confidence')}。"
    )
    if context:
        abstract_text += " 作为背景证据，" + "；".join(context[:2]) + "。"

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
        empirical.append(
            {
                "node_id": node_id,
                "title": f"{METHOD_LABELS.get(recipe_id, result.get('method') or recipe_id)}：{factor_descriptions[0] if factor_descriptions else '主要宏观指标'}",
                "method": result.get("method") or METHOD_LABELS.get(recipe_id, recipe_id),
                "role": ROLE_LABELS.get(str(result.get("specification_role", "CORE")), str(result.get("specification_role", "CORE"))),
                "question_addressed": specification.get("estimand") or "检验该组数据对原问题相关经济状态的方向性证据。",
                "data_and_sample": _sample_text(result.get("sample")),
                "variables": factor_descriptions,
                "specification": specification.get("formula") or f"使用预注册的 {METHOD_LABELS.get(recipe_id, recipe_id)} 规格。",
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
        "title": "MacroTrace Research Report",
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
            "successful_runs": len(successful),
            "highlighted_runs": len(empirical),
            "additional_runs": max(0, len(successful) - len(empirical)),
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
