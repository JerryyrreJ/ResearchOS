from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from .llm import DeepSeekClient
from .registry import RegistryStore


def _registry_get(registry: RegistryStore, collection: str, item_id: Any) -> dict[str, Any]:
    if not isinstance(item_id, str) or not item_id:
        return {}
    try:
        return registry.get(collection, item_id)
    except Exception:
        return {}


def _metadata(detail: dict[str, Any]) -> dict[str, Any]:
    provenance = detail.get("provenance") or {}
    return provenance.get("registry_metadata") or detail.get("metadata") or {}


def _node_type(detail: dict[str, Any]) -> str:
    explicit = detail.get("node_type")
    if explicit:
        return str(explicit)
    node_id = str(detail.get("node_id") or "")
    if node_id.startswith("MR::"):
        return "MODEL_RUN"
    return node_id.split("::", 1)[0] if node_id else "RESEARCH_OBJECT"


def _factor_list(values: list[Any], limit: int = 4) -> str:
    ids: list[str] = []
    for value in values:
        factor_id = value.get("factor_id") if isinstance(value, dict) else value
        if factor_id:
            ids.append(str(factor_id))
    if not ids:
        return "未绑定宏观序列"
    shown = "、".join(ids[:limit])
    return f"{shown} 等 {len(ids)} 个因子" if len(ids) > limit else shown


def _sample_summary(detail: dict[str, Any]) -> str:
    sample = detail.get("sample") or {}
    if not sample:
        return ""
    start = sample.get("start") or "起点未记录"
    end = sample.get("end") or "终点未记录"
    observations = sample.get("observations")
    frequency = sample.get("frequency") or "频率未记录"
    count = f"，共 {observations} 个观测" if observations is not None else ""
    return f"样本期 {start} 至 {end}，{frequency}{count}"


def build_fixed_explanation(detail: dict[str, Any], registry: RegistryStore) -> dict[str, Any]:
    """Build the non-LLM explanation contract from registry and execution facts."""
    node_type = _node_type(detail)
    metadata = _metadata(detail)
    title = str(detail.get("title") or detail.get("label") or detail.get("node_id") or "研究节点")
    summary = str(detail.get("summary") or "").strip()
    specification = detail.get("specification") or {}
    variables = detail.get("variables") or []
    sample_text = _sample_summary(detail)
    node_id = str(detail.get("node_id") or "")

    purpose = f"记录并执行“{title}”这一研究对象。"
    why = "它把研究过程拆成可检查的步骤，使最终结论能够沿图谱反向追溯。"
    mechanism = summary or "这是研究编译链中的结构化步骤，本身不额外创造经济结论。"
    data_summary = "本节点使用上游结构化输入，不直接运行新的宏观数据。"
    output_summary = "其结构化输出会传递给下游节点。"

    if node_type == "QUESTION":
        purpose = "原样保存用户提出的自然语言宏观问题，作为整条研究链的根节点。"
        why = "所有路由、模型和结论都必须能回到这句话，避免后续分析偏离用户真正想问的问题。"
        mechanism = "这是语义与审计锚点，不进行经济估计，也不产生方向或概率。"
        data_summary = "输入只有用户问题文本；这里没有调用宏观序列或统计模型。"
        output_summary = "问题文本被交给 Query Parser 转换为受约束的研究任务。"
    elif node_type == "QUERY":
        form = metadata.get("question_form") or title.split("·", 1)[0].strip()
        horizon = metadata.get("horizon") or {}
        horizon_text = f"{horizon.get('minimum')}–{horizon.get('maximum')} {str(horizon.get('unit') or '').lower()}" if horizon.get("minimum") is not None else "未记录期限"
        conditions = metadata.get("conditional_events") or []
        purpose = f"把自然语言问题编译成可验证的 {form} 任务，并固定研究期限、as-of 日期与输出要求。"
        why = "Python 后端不能直接执行含义模糊的自由文本；先结构化后，泳道路由和模型选择才有明确边界。"
        if form == "SCENARIO":
            mechanism = "该节点只识别“在某个条件事件发生时要评估什么”和评估期限，不在这里估计冲击效应；条件效应由下游已注册模型承担。"
        else:
            mechanism = "它执行受 Schema 约束的语义解析，把目标、任务形式和期限交给后续研究工作流，不替代任何实证模型。"
        condition_text = f"，并识别 {len(conditions)} 个条件事件" if conditions else ""
        data_summary = f"读取问题文本、as-of 日期与 {horizon_text} 的研究期限{condition_text}；不运行宏观时间序列。"
        output_summary = "输出结构化 Query，供深度门槛、泳道路由和节点路由共同使用。"
    elif node_type == "RESEARCH_DEPTH_GATE":
        purpose = "检查当前研究计划是否达到与问题复杂度相匹配的实证深度。"
        why = "它防止大型宏观问题只靠少数描述统计或几个模型就直接形成结论。"
        mechanism = "按照 Registry 的证据预算核对泳道、机制、因子、模型规格、方法家族和识别设计数量。"
        data_summary = f"读取编译后的计划计数：{summary or '计划、可执行与受阻规格'}；不运行新的经济数据。"
        output_summary = "输出通过、警告或失败状态，并把缺口暴露给后续执行与覆盖率判断。"
    elif node_type == "LANE":
        lane_mechanism = metadata.get("mechanism") or summary
        counts = metadata.get("universe_counts") or {}
        purpose = f"把总问题隔离为“{title}”这一条宏观传导泳道，并汇集该领域的机制证据。"
        why = "复杂宏观结论通常跨越多个传导领域；分泳道可以分别检验后再聚合，避免用单一模型包打天下。"
        mechanism = lane_mechanism or "该泳道承载一个已注册的宏观传导领域。"
        data_summary = f"该泳道 Registry 内含 {counts.get('mechanisms', 0)} 个机制、{counts.get('factors', 0)} 个因子和 {counts.get('model_specifications', 0)} 个模型规格；本节点自身不直接回归。"
        output_summary = "下游机制与模型证据将被归一为一条 lane signal，再进入跨泳道综合。"
    elif node_type == "MECHANISM":
        factor_pool = metadata.get("factor_pool") or []
        purpose = f"把泳道拆成一个可被数据检验的机制假设：{title}。"
        why = "它连接抽象的经济叙事与可观测变量，明确下面的因子和模型究竟在检验哪条传导链。"
        mechanism = metadata.get("hypothesis") or summary or "该机制的假设尚未在 Registry 中记录。"
        data_summary = f"允许从 {_factor_list(factor_pool)} 中取数，并对应 {metadata.get('model_specification_count', 0)} 个预注册模型规格；本节点不直接估计参数。"
        output_summary = "机制向下展开为研究节点、因子和模型规格，并最终形成可支持或反驳的中间命题。"
    elif node_type == "RESEARCH_NODE":
        mechanism_record = _registry_get(registry, "mechanisms", metadata.get("mechanism_id"))
        factor_pool = metadata.get("factor_pool") or []
        model_pool = metadata.get("model_pool") or []
        purpose = metadata.get("purpose") or summary or purpose
        why = f"它负责形成一个独立的中间命题“{metadata.get('intermediate_claim') or title}”，使证据先在局部闭合，再进入总聚合。"
        mechanism = mechanism_record.get("hypothesis") or "该节点按照已注册的研究边界把机制转成可执行证据。"
        data_summary = f"可从 {_factor_list(factor_pool)} 中选择输入，并只允许使用 {len(model_pool)} 个注册模型配方。"
        output_summary = "模型结果先映射为 Evidence，再支持或反驳该节点对应的 Claim。"
    elif node_type == "CLAIM":
        purpose = f"保存待证据支持或反驳的中间命题：{title}。"
        why = "先在命题层聚合可以避免把不可比的系数、预测值和诊断分数直接相加。"
        mechanism = "该节点不做估计；它按支持、反驳与证据类型接收已经完成诊断的 Evidence。"
        data_summary = "输入是上游模型生成的结构化证据对象，不直接读取原始宏观序列。"
        output_summary = "形成可比较的命题级方向与可信度，供泳道聚合使用。"
    elif node_type == "FACTOR":
        dataset = _registry_get(registry, "datasets", metadata.get("dataset_id"))
        purpose = f"把机制落到一个可观测宏观变量：{metadata.get('definition') or title}。"
        why = "经济机制只有映射到定义、单位、频率和发布时间明确的变量，才可能被复现和检验。"
        mechanism = f"该因子在 {metadata.get('lane_id') or '对应'} 泳道中充当模型输入；允许的变换被限制在 Registry 白名单。"
        data_summary = f"使用 {dataset.get('source') or metadata.get('dataset_id') or '已注册数据源'} 的 {metadata.get('series_id') or '已注册序列'}，频率 {metadata.get('frequency') or '未记录'}，单位 {metadata.get('unit') or '未记录'}。"
        output_summary = "原始观测经允许的 Transform 处理后进入具体模型规格。"
    elif node_type == "DATASET":
        series_ids = metadata.get("series_ids") or []
        purpose = f"定义“{title}”数据入口及其许可、频率、vintage 和修订规则。"
        why = "同一个指标可能被修订；数据集节点保证历史 as-of 研究不会偷偷读到未来发布的数据。"
        mechanism = "这是数据治理与复现机制，不代表经济传导关系。"
        data_summary = f"该数据集登记 {len(series_ids)} 个序列，频率 {metadata.get('frequency') or '未记录'}，vintage 规则为 {metadata.get('vintage') or '未记录'}。"
        output_summary = "向 Factor 节点提供带来源和时间截面的官方观测。"
    elif node_type == "TRANSFORM":
        transforms = metadata.get("allowed_transforms") or []
        purpose = "把原始因子转换为与注册模型相容的尺度、增长率或平稳表示。"
        why = "直接把趋势、频率或单位不一致的序列塞进模型会产生误导性关系，因此变换必须先被限制。"
        mechanism = "具体模型只能从 Factor Registry 的变换白名单中选择，不能由 LLM 临时改写处理代码。"
        data_summary = f"处理因子 {metadata.get('factor_id') or '未记录'}；可选变换为 {', '.join(map(str, transforms)) or '未记录'}。"
        output_summary = "输出可直接进入模型设计矩阵的结构化时间序列。"
    elif node_type == "MODEL_SPECIFICATION":
        factors = metadata.get("factor_ids") or specification.get("factor_ids") or []
        mechanism_record = _registry_get(registry, "mechanisms", metadata.get("mechanism_id"))
        purpose = f"冻结“{title}”的实证设计，包括模型配方、变量角色、参数边界和诊断套件。"
        why = "把 specification 与 run 分开，可以保证 AI 只能选积木和参数，不能在执行时改公式或底层代码。"
        mechanism = mechanism_record.get("hypothesis") or f"使用 {metadata.get('method') or title} 将已注册因子映射为可检验估计。"
        data_summary = f"规格绑定 {_factor_list(factors)}，并要求 {len(metadata.get('diagnostic_suite') or [])} 项方法专属诊断。"
        output_summary = "通过验证后生成一个 Model Run；受阻规格则保留原因但不会伪造结果。"
    elif node_type == "MODEL_RUN":
        recipe = _registry_get(registry, "models", detail.get("model_recipe_id") or metadata.get("model_recipe_id"))
        research_node_id = detail.get("research_node_id") or metadata.get("research_node_id")
        research_node = _registry_get(registry, "nodes", research_node_id)
        factors = detail.get("factor_ids") or variables or metadata.get("factor_ids") or []
        method = detail.get("method") or recipe.get("method") or title
        purpose = f"实际执行 {method}，为“{research_node.get('intermediate_claim') or research_node_id or '对应中间命题'}”产生定量证据。"
        why = "它是研究图中真正运行 Python 统计代码的步骤；没有这一层，机制叙事不能转化为可审计证据。"
        formula = specification.get("formula")
        estimand = specification.get("estimand")
        mechanism = f"模型按照预注册公式{f' {formula}' if formula else ''}估计{estimand or '目标量'}；是否允许因果解释由规格合同单独限定。"
        sample_suffix = f"；{sample_text}" if sample_text else ""
        data_summary = f"运行 {_factor_list(factors)}{sample_suffix}。数据快照和发布时间记录在 Provenance。"
        result_text = summary or detail.get("error") or "执行结果尚未生成"
        output_summary = f"输出回归/预测结果、方法专属诊断、稳健性结果和图表。当前摘要：{result_text}"
    elif node_type == "DIAGNOSTIC":
        items = metadata.get("items") or detail.get("diagnostics") or []
        failed = metadata.get("failed", sum(item.get("status") in {"FAIL", "FAILED"} for item in items if isinstance(item, dict)))
        warnings = metadata.get("warnings", sum(item.get("status") == "WARNING" for item in items if isinstance(item, dict)))
        purpose = "检验上游模型的假设、残差、稳定性、识别或样本外表现是否足以支持使用该结果。"
        why = "系数或预测值本身不等于可信证据；诊断决定它能否进入聚合以及需要怎样降权。"
        mechanism = "诊断套件由 ModelRecipe 指定，每一项都报告统计量、判断与对可信度的影响。"
        data_summary = f"复用上游模型的残差、拟合值或回测误差，共执行 {len(items)} 项检验；其中 {failed} 项失败、{warnings} 项警告。"
        output_summary = "输出通过、警告或失败状态，并约束证据的质量乘数。"
    elif node_type == "EVIDENCE":
        purpose = "把一个模型运行结果标准化为可被 Claim 和聚合器读取的证据对象。"
        why = "不同方法会产生系数、预测值、冲击响应或分位数；证据层负责保留方法边界并统一传递方向和可信度。"
        mechanism = f"保留证据类型 {detail.get('role') or metadata.get('evidence_type') or '未记录'}、方向 {metadata.get('direction') or detail.get('direction') or '未记录'} 与置信度 {metadata.get('confidence') or detail.get('confidence') or '未记录'}，不重新计算模型。"
        data_summary = "使用父 Model Run 的结构化结果与诊断，不读取新的原始数据。"
        output_summary = "向对应中间 Claim 提供支持或反驳关系。"
    elif node_type == "LANE_SIGNAL":
        contributions = metadata.get("contributions") or []
        purpose = "把同一泳道内多个已诊断的命题证据汇总为一个泳道级信号。"
        why = "跨泳道综合前，需要先回答每条经济机制链自身给出了什么方向以及证据质量如何。"
        mechanism = "只使用注册的证据映射和质量乘数计算 ordinal signal；LLM 不生成数值权重。"
        data_summary = f"聚合 {len(contributions)} 个结构化贡献项，不额外调用宏观序列。"
        output_summary = "输出泳道方向、得分和贡献明细，进入跨泳道 Aggregation。"
    elif node_type == "AGGREGATION":
        contributions = metadata.get("contributions") or []
        purpose = "把不同泳道、不同证据类型的中间结论综合成与原问题对应的总体判断。"
        why = "复杂宏观问题不能由任一单独模型回答；总判断必须同时反映证据方向、质量、覆盖率和不可比边界。"
        mechanism = f"采用 {metadata.get('method') or title}，按 Registry 映射聚合结构化证据；数值权重不由 LLM 生成。"
        data_summary = f"读取 {len(contributions)} 个已完成诊断的贡献项以及 coverage、confidence 和敏感性结果；不运行新回归。"
        output_summary = "生成 Final Claim 所需的总体方向、置信度、覆盖缺口与贡献分解。"
    elif node_type == "FINAL_CLAIM":
        purpose = "把跨泳道综合结果表述为用户可以直接阅读的主要结论。"
        why = "它是研究链的回答端点，但仍保留到每条证据、模型、变量和数据快照的完整 lineage。"
        mechanism = "只解释已经形成的结构化综合结果，不重新计算模型、不改变权重，也不把 limitation 冒充主结论。"
        data_summary = "使用 Aggregation 的方向、覆盖率、置信度和贡献明细；不读取新的宏观数据。"
        output_summary = f"输出主结论、解释、限制和证伪条件。当前结论：{summary or title}"
    elif node_type == "FALSIFIER":
        purpose = f"记录一条可能推翻或显著削弱当前结论的可观察条件：{title}。"
        why = "可证伪条件让结论保持科学边界，避免把当前样本下的判断写成永远正确的叙事。"
        mechanism = "当未来官方观测满足该条件时，应重新运行相关节点并下调或反转现有结论。"
        data_summary = "当前不运行数据；它等待未来官方发布或新的已注册证据进行核验。"
        output_summary = "输出结论失效条件，供后续更新和监测。"

    return {
        "version": "1.0",
        "fact_source": "REGISTRY_AND_EXECUTION",
        "purpose": str(purpose),
        "why_it_exists": str(why),
        "mechanism": str(mechanism),
        "data_summary": str(data_summary),
        "output_summary": str(output_summary),
        "plain_summary": f"{purpose} {output_summary}",
    }


def ensure_fixed_explanation(detail: dict[str, Any], registry: RegistryStore) -> dict[str, Any]:
    explanation = detail.get("explanation")
    if not isinstance(explanation, dict) or not all(explanation.get(key) for key in ("purpose", "why_it_exists", "mechanism", "data_summary", "output_summary")):
        explanation = {**(explanation or {}), **build_fixed_explanation(detail, registry)}
        detail["explanation"] = explanation
    return detail


def _safe_llm_payload(detail: dict[str, Any]) -> dict[str, Any]:
    variables = []
    for variable in detail.get("variables") or []:
        if not isinstance(variable, dict):
            continue
        variables.append({key: variable.get(key) for key in ("factor_id", "definition", "series_id", "unit", "frequency", "dataset_id")})
    specification = detail.get("specification") or {}
    return {
        "node_id": detail.get("node_id"),
        "node_type": _node_type(detail),
        "title": detail.get("title"),
        "status": detail.get("status"),
        "fixed_facts": {key: detail["explanation"][key] for key in ("purpose", "why_it_exists", "mechanism", "data_summary", "output_summary")},
        "registered_specification": {key: specification.get(key) for key in ("formula", "estimand", "dependent_variable", "independent_variables", "controls", "causal_interpretation_allowed")},
        "variables": variables,
        "sample": detail.get("sample"),
        "numeric_result_summary": detail.get("summary"),
    }


def add_llm_explanation(detail: dict[str, Any], llm: DeepSeekClient) -> dict[str, Any]:
    """Add a cached prose layer. It can explain fixed facts but never replace them."""
    explanation = detail["explanation"]
    cached = explanation.get("llm")
    if isinstance(cached, dict) and (cached.get("status") != "FALLBACK_NO_KEY" or not llm.available):
        return detail
    if not llm.available:
        explanation["llm"] = {
            "status": "FALLBACK_NO_KEY",
            "narrative_summary": explanation["plain_summary"],
            "mechanism_walkthrough": explanation["mechanism"],
            "grounding_fields": ["purpose", "mechanism", "data_summary"],
        }
        return detail

    payload = _safe_llm_payload(detail)
    system = """You are LLM-8, MacroTrace's node explanation editor. Explain only the supplied fixed facts in concise, natural Chinese.
You are a presentation layer, not an analyst: never add data, variables, numbers, causal claims, model results or mechanisms not present in the payload.
Do not modify, contradict, upgrade or hide limitations in fixed_facts. If the node is only semantic, governance or aggregation infrastructure, say so plainly.
Return one JSON object with exactly: narrative_summary, mechanism_walkthrough, grounding_fields.
narrative_summary: 1-2 sentences answering what this node does and why it exists.
mechanism_walkthrough: 1-3 sentences explaining how its input becomes its output; distinguish economic mechanism from research/data-governance mechanism.
grounding_fields: a non-empty subset of [purpose, why_it_exists, mechanism, data_summary, output_summary, registered_specification, variables, sample, numeric_result_summary].
No markdown."""
    try:
        output = llm.json_completion(system, json.dumps(payload, ensure_ascii=False), max_tokens=650)
        allowed_grounding = {"purpose", "why_it_exists", "mechanism", "data_summary", "output_summary", "registered_specification", "variables", "sample", "numeric_result_summary"}
        narrative = str(output.get("narrative_summary") or "").strip()
        walkthrough = str(output.get("mechanism_walkthrough") or "").strip()
        grounding = output.get("grounding_fields") or []
        if not narrative or not walkthrough or len(narrative) > 360 or len(walkthrough) > 600:
            raise ValueError("invalid explanation length")
        if not isinstance(grounding, list) or not grounding or not set(grounding).issubset(allowed_grounding):
            raise ValueError("invalid grounding fields")
        source_numbers = set(re.findall(r"\d+(?:\.\d+)?", json.dumps(payload, ensure_ascii=False)))
        output_numbers = set(re.findall(r"\d+(?:\.\d+)?", narrative + walkthrough))
        if not output_numbers.issubset(source_numbers):
            raise ValueError("ungrounded numeric claim")
        causal_allowed = (payload.get("registered_specification") or {}).get("causal_interpretation_allowed") is True
        if not causal_allowed and any(term in narrative + walkthrough for term in ("证明了因果", "因果效应为", "必然导致", "已经证明")):
            raise ValueError("unregistered causal claim")
        explanation["llm"] = {
            "status": "SUCCESS",
            "role": "LLM-8 Node Explanation Editor",
            "model": llm.model,
            "generated_at": datetime.now(UTC).isoformat(),
            "narrative_summary": narrative,
            "mechanism_walkthrough": walkthrough,
            "grounding_fields": grounding,
        }
    except Exception as exc:
        explanation["llm"] = {
            "status": "FALLBACK_AFTER_VALIDATION",
            "error_type": type(exc).__name__,
            "narrative_summary": explanation["plain_summary"],
            "mechanism_walkthrough": explanation["mechanism"],
            "grounding_fields": ["purpose", "mechanism", "data_summary"],
        }
    return detail
