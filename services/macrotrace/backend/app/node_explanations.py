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


def _as_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    output: list[str] = []
    for value in values:
        if isinstance(value, dict):
            value = value.get("factor_id") or value.get("variable_id") or value.get("definition")
        if value is not None and str(value).strip():
            output.append(str(value).strip())
    return output


def _factor_label(registry: RegistryStore, factor_id: Any) -> str:
    value = str(factor_id or "").strip()
    if not value:
        return "未登记变量"
    record = _registry_get(registry, "factors", value)
    definition = str(record.get("definition") or "").strip()
    return f"{value}（{definition}）" if definition else value


def _research_question(detail: dict[str, Any], metadata: dict[str, Any]) -> str:
    provenance = detail.get("provenance") or {}
    registry_metadata = provenance.get("registry_metadata") or {}
    for candidate in (
        detail.get("research_question"),
        detail.get("original_question"),
        metadata.get("research_question"),
        metadata.get("original_question"),
        registry_metadata.get("research_question"),
        registry_metadata.get("original_question"),
    ):
        if candidate is not None and str(candidate).strip():
            return " ".join(str(candidate).split())
    return ""


def _method_intention(method: str) -> str:
    normalized = method.lower()
    if "vector autoregression" in normalized or re.search(r"\bvar\b", normalized):
        return "VAR 用来联合刻画多个变量的动态先后关系并形成条件预测；除非另有已识别冲击，它不把变量排序升级为因果效应。"
    if "local projection" in normalized or "局部投影" in method:
        return "局部投影用来逐期估计响应路径；只有冲击识别合同成立时，响应才允许作因果解释。"
    if "growth-at-risk" in normalized or "quantile" in normalized or "分位" in method:
        return "分位数模型用来检验解释变量是否改变结果分布的下尾，而不是只比较均值。"
    if "dynamic factor" in normalized or "动态因子" in method:
        return "动态因子模型用来压缩多项同步指标的共同变化，并把共同状态桥接到目标量。"
    if "autoregressive" in normalized or "自回归" in method:
        return "自回归模型用目标变量自身的历史持续性建立预测基准，用于判断更复杂变量是否提供额外信息。"
    if "ols" in normalized or "regression" in normalized or "回归" in method:
        return "回归规格用来衡量给定控制条件下的统计关联或预测贡献；未注册识别设计时不能解释为因果效应。"
    return "该方法把已注册变量映射到明确估计目标，并受预先登记的诊断与解释边界约束。"


def _coefficient_interpretation(detail: dict[str, Any]) -> str:
    coefficient_columns = (detail.get("table") or {}).get("coefficients") or {}
    rows: list[dict[str, Any]] = []
    if isinstance(coefficient_columns, dict):
        for column in coefficient_columns.values():
            if isinstance(column, list):
                rows.extend(item for item in column if isinstance(item, dict))
    identified: list[tuple[str, float, float | None]] = []
    for item in rows:
        p_value = item.get("p_value")
        coefficient = item.get("coefficient", item.get("value"))
        try:
            p_number = float(p_value)
            coefficient_number = float(coefficient) if coefficient is not None else None
        except (TypeError, ValueError):
            continue
        label = str(item.get("label") or item.get("variable_id") or "已登记变量")
        identified.append((label, p_number, coefficient_number))
    if not identified:
        return ""
    def with_direction(label: str, coefficient: float | None) -> str:
        if coefficient is None or coefficient == 0:
            return label
        return f"{label}（{'正向' if coefficient > 0 else '负向'}）"

    significant = [with_direction(label, coefficient) for label, p_value, coefficient in identified if p_value < 0.05]
    not_significant = [with_direction(label, coefficient) for label, p_value, coefficient in identified if p_value >= 0.05]
    parts: list[str] = []
    if significant:
        parts.append(f"5% 阈值下可统计区分于零的系数包括：{'、'.join(dict.fromkeys(significant))}")
    if not_significant:
        parts.append(f"5% 阈值下尚不能统计区分于零的系数包括：{'、'.join(dict.fromkeys(not_significant))}")
    return "；".join(parts) + "。"


def _model_context(
    detail: dict[str, Any],
    metadata: dict[str, Any],
    registry: RegistryStore,
    title: str,
) -> dict[str, Any]:
    specification = detail.get("specification") or {}
    recipe_id = detail.get("model_recipe_id") or metadata.get("model_recipe_id")
    recipe = _registry_get(registry, "models", recipe_id)
    research_node_id = detail.get("research_node_id") or metadata.get("research_node_id") or metadata.get("node_id")
    research_node = _registry_get(registry, "nodes", research_node_id)
    mechanism_id = detail.get("mechanism_id") or metadata.get("mechanism_id") or research_node.get("mechanism_id")
    mechanism_record = _registry_get(registry, "mechanisms", mechanism_id)
    method = str(detail.get("method") or metadata.get("method") or recipe.get("method") or title)
    factor_ids = _as_string_list(detail.get("factor_ids") or metadata.get("factor_ids") or detail.get("variables") or [])
    dependent_id = specification.get("dependent_variable") or metadata.get("dependent_variable")
    independent_ids = _as_string_list(specification.get("independent_variables") or metadata.get("independent_variables") or [])
    if not independent_ids:
        independent_ids = [factor_id for factor_id in factor_ids if factor_id != dependent_id]
    controls = _as_string_list(specification.get("controls") or metadata.get("controls") or [])
    estimand = str(
        specification.get("estimand")
        or metadata.get("estimand")
        or research_node.get("intermediate_claim")
        or "估计目标未在该节点明细中单独登记"
    )
    return {
        "question": _research_question(detail, metadata),
        "method": method,
        "method_intention": _method_intention(method),
        "research_node_id": str(research_node_id or ""),
        "research_claim": str(research_node.get("intermediate_claim") or research_node_id or "对应中间命题"),
        "mechanism_name": str(mechanism_record.get("name") or mechanism_id or "已注册机制"),
        "mechanism_hypothesis": str(mechanism_record.get("hypothesis") or "机制假设未在该节点明细中单独登记"),
        "estimand": estimand,
        "dependent_variable": _factor_label(registry, dependent_id),
        "independent_variables": [_factor_label(registry, item) for item in independent_ids],
        "controls": [_factor_label(registry, item) for item in controls],
        "factor_ids": factor_ids,
        "causal_allowed": specification.get("causal_interpretation_allowed") is True
        or metadata.get("causal_interpretation_allowed") is True,
    }


def build_fixed_explanation(detail: dict[str, Any], registry: RegistryStore) -> dict[str, Any]:
    """Build the non-LLM explanation contract from registry and execution facts."""
    node_type = _node_type(detail)
    metadata = _metadata(detail)
    title = str(detail.get("title") or detail.get("label") or detail.get("node_id") or "研究节点")
    summary = str(detail.get("summary") or "").strip()
    specification = detail.get("specification") or {}
    sample_text = _sample_summary(detail)
    research_question = _research_question(detail, metadata)

    purpose = f"记录并执行“{title}”这一研究对象。"
    why = "它把研究过程拆成可检查的步骤，使最终结论能够沿图谱反向追溯。"
    mechanism = summary or "这是研究编译链中的结构化步骤，本身不额外创造经济结论。"
    data_summary = "本节点使用上游结构化输入，不直接运行新的宏观数据。"
    output_summary = "其结构化输出会传递给下游节点。"
    research_intent = ""
    estimand_text = "不适用"
    variable_roles: dict[str, Any] = {
        "dependent_variable": "不适用",
        "independent_variables": [],
        "controls": [],
    }
    result_interpretation = "该节点不直接产生模型估计结果。"
    interpretation_boundary = "只解释该节点已经登记或执行的事实，不额外推断方向、显著性或因果关系。"

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
        context = _model_context(detail, metadata, registry, title)
        question_text = f"用户问题“{context['question']}”" if context["question"] else "本次用户问题（根问题文本尚未传入该节点）"
        independent_text = "、".join(context["independent_variables"]) or "未单独登记解释变量"
        research_intent = (
            f"针对{question_text}，预先冻结 {context['method']}，用来检验“{context['mechanism_name']}”机制："
            f"{context['mechanism_hypothesis']} 估计目标为 {context['estimand']}；"
            f"因变量为 {context['dependent_variable']}，主要自变量为 {independent_text}。"
        )
        purpose = research_intent
        why = f"{context['method_intention']} 把规格与运行分开还能防止执行阶段临时换变量、换公式或改解释边界。"
        mechanism = (
            f"本规格服务于中间命题“{context['research_claim']}”，检验路径为："
            f"{independent_text} → {context['dependent_variable']}，目标量是 {context['estimand']}。"
        )
        factor_text = "、".join(_factor_label(registry, item) for item in context["factor_ids"]) or "未登记因子"
        data_summary = f"规格绑定 {factor_text}，并要求 {len(metadata.get('diagnostic_suite') or [])} 项方法专属诊断。"
        result_interpretation = "这是尚未执行的模型设定节点，不包含系数方向、显著性或预测结果；这些只能由对应 Model Run 报告。"
        interpretation_boundary = (
            "系数显著只表示在登记样本、变量与控制条件下可统计区分于零；不显著表示当前证据不足以区分于零，"
            "不等于证明变量没有作用。"
            + ("因果解释仍须满足该规格登记的识别假设与诊断。" if context["causal_allowed"] else "该规格未允许因果解释，任何结果都只能按预测性或关联性证据解读，不得升级为因果效应。")
        )
        estimand_text = context["estimand"]
        variable_roles = {
            "dependent_variable": context["dependent_variable"],
            "independent_variables": context["independent_variables"],
            "controls": context["controls"],
        }
        output_summary = "通过验证后才会生成一个 Model Run；受阻规格保留原因但不会伪造结果。"
    elif node_type == "MODEL_RUN":
        context = _model_context(detail, metadata, registry, title)
        question_text = f"用户问题“{context['question']}”" if context["question"] else "本次用户问题（根问题文本尚未传入该节点）"
        independent_text = "、".join(context["independent_variables"]) or "未单独登记解释变量"
        research_intent = (
            f"针对{question_text}，实际运行 {context['method']}，用来检验“{context['mechanism_name']}”机制："
            f"{context['mechanism_hypothesis']} 估计目标为 {context['estimand']}；"
            f"因变量为 {context['dependent_variable']}，主要自变量为 {independent_text}。"
        )
        purpose = research_intent
        why = f"{context['method_intention']} 本次运行因此服务于中间命题“{context['research_claim']}”，而不是为了展示模型名称。"
        formula = specification.get("formula")
        mechanism = (
            f"模型按预注册公式{f' {formula}' if formula else ''}，检验 {independent_text} 对 "
            f"{context['dependent_variable']} 的条件信息，并估计 {context['estimand']}。"
        )
        sample_suffix = f"；{sample_text}" if sample_text else ""
        factor_text = "、".join(_factor_label(registry, item) for item in context["factor_ids"]) or "未登记因子"
        data_summary = f"运行变量为 {factor_text}{sample_suffix}。数据快照和发布时间记录在 Provenance。"
        result_text = summary or detail.get("error") or "执行结果尚未生成"
        direction_text = f"汇总方向为 {detail.get('direction')}。" if detail.get("direction") else ""
        significance_text = _coefficient_interpretation(detail)
        result_interpretation = f"当前执行摘要：{result_text}。{direction_text}{significance_text}".strip()
        interpretation_boundary = (
            "显著系数只表示在本次样本、变量与控制条件下可统计区分于零；不显著系数表示当前证据不足以区分于零，"
            "不等于证明变量没有作用。"
            + ("因果解释还必须同时满足已注册识别假设与诊断。" if context["causal_allowed"] else "该模型未允许因果解释，方向、预测和显著性都不得升级为因果效应。")
        )
        estimand_text = context["estimand"]
        variable_roles = {
            "dependent_variable": context["dependent_variable"],
            "independent_variables": context["independent_variables"],
            "controls": context["controls"],
        }
        output_summary = f"输出回归/预测结果、方法专属诊断、稳健性结果和图表。{result_interpretation}"
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

    if not research_intent:
        research_intent = purpose
    plain_summary = (
        f"{research_intent} {result_interpretation} {interpretation_boundary}"
        if node_type in {"MODEL_SPECIFICATION", "MODEL_RUN"}
        else f"{purpose} {output_summary}"
    )
    return {
        "version": "1.0",
        "fact_source": "REGISTRY_AND_EXECUTION",
        "research_question": research_question or "根问题文本未随该节点传入",
        "research_intent": str(research_intent),
        "estimand": str(estimand_text),
        "variable_roles": variable_roles,
        "result_interpretation": str(result_interpretation),
        "interpretation_boundary": str(interpretation_boundary),
        "purpose": str(purpose),
        "why_it_exists": str(why),
        "mechanism": str(mechanism),
        "data_summary": str(data_summary),
        "output_summary": str(output_summary),
        "plain_summary": plain_summary,
    }


def ensure_fixed_explanation(detail: dict[str, Any], registry: RegistryStore) -> dict[str, Any]:
    explanation = detail.get("explanation")
    required = {"purpose", "why_it_exists", "mechanism", "data_summary", "output_summary"}
    if _node_type(detail) in {"MODEL_SPECIFICATION", "MODEL_RUN"}:
        required.update(
            {
                "research_question",
                "research_intent",
                "estimand",
                "variable_roles",
                "result_interpretation",
                "interpretation_boundary",
            }
        )
    if not isinstance(explanation, dict) or not all(explanation.get(key) for key in required):
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
        "research_question": detail["explanation"].get("research_question"),
        "fixed_facts": {
            key: detail["explanation"].get(key)
            for key in (
                "research_intent",
                "purpose",
                "why_it_exists",
                "mechanism",
                "estimand",
                "variable_roles",
                "data_summary",
                "result_interpretation",
                "interpretation_boundary",
                "output_summary",
            )
        },
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
            "grounding_fields": ["research_question", "research_intent", "mechanism", "interpretation_boundary"],
        }
        return detail

    payload = _safe_llm_payload(detail)
    system = """You are LLM-8, MacroTrace's node explanation editor. Explain only the supplied fixed facts in concise, natural Chinese.
You are a presentation layer, not an analyst: never add data, variables, numbers, causal claims, model results or mechanisms not present in the payload.
Do not modify, contradict, upgrade or hide limitations in fixed_facts. If the node is only semantic, governance or aggregation infrastructure, say so plainly.
Return one JSON object with exactly: narrative_summary, mechanism_walkthrough, grounding_fields.
narrative_summary: 1-2 sentences. For MODEL_SPECIFICATION and MODEL_RUN, answer the research intention first: quote or clearly identify the original research question, explain why this method is being used for that question, name the tested mechanism, estimand, dependent variable and main independent variables, then state only supplied direction/significance facts.
mechanism_walkthrough: 1-3 sentences explaining how its input becomes its output; distinguish economic mechanism from research/data-governance mechanism.
For non-causal specifications, explicitly preserve the predictive/associational boundary. A significant coefficient means distinguishable from zero under the supplied specification; a non-significant coefficient means insufficient evidence under that specification, not proof of no effect.
grounding_fields: a non-empty subset of [research_question, research_intent, purpose, why_it_exists, mechanism, estimand, variable_roles, data_summary, result_interpretation, interpretation_boundary, output_summary, registered_specification, variables, sample, numeric_result_summary].
No markdown."""
    try:
        output = llm.json_completion(system, json.dumps(payload, ensure_ascii=False), max_tokens=650)
        allowed_grounding = {"research_question", "research_intent", "purpose", "why_it_exists", "mechanism", "estimand", "variable_roles", "data_summary", "result_interpretation", "interpretation_boundary", "output_summary", "registered_specification", "variables", "sample", "numeric_result_summary"}
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
            "grounding_fields": ["research_question", "research_intent", "mechanism", "interpretation_boundary"],
        }
    return detail
