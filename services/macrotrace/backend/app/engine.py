from __future__ import annotations

import json
from datetime import UTC, date, datetime
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from .aggregation import synthesize
from .analytics.serious_models import MODEL_RUNNERS
from .artifacts import ArtifactStore
from .compiler import ResearchCompiler
from .config import Settings
from .credentials import LocalCredentialStore
from .llm import DeepSeekClient
from .node_explanations import add_llm_explanation, ensure_fixed_explanation
from .registry import RegistryStore
from .research_report import build_research_report, merge_llm_report_language
from .research_graph import GraphBuilder
from .storage import MacroStore


class JobCancelled(RuntimeError):
    pass


ProgressCallback = Callable[[str, float, dict[str, Any], dict[str, Any] | None], None]


STATUS_PROGRESS = {
    "PARSING_QUERY": 0.05,
    "CLASSIFYING_WORKFLOW": 0.10,
    "ROUTING_LANES": 0.16,
    "ROUTING_NODES": 0.22,
    "SELECTING_FACTORS": 0.28,
    "PLANNING_MODELS": 0.34,
    "SELECTING_PARAMETERS": 0.40,
    "VALIDATING_PLAN": 0.45,
    "EXECUTING_MODELS": 0.50,
    "AGGREGATING_LANES": 0.86,
    "SYNTHESIZING": 0.93,
}


def _compact_finding(finding: dict[str, Any]) -> str:
    text = str(finding.get("finding_zh") or "").split("（", 1)[0].strip(" 。；")
    return text.replace("方向：", "").replace("：", "")


def conclusion_headline(findings: list[dict[str, Any]], fallback: str) -> str:
    """Keep the display headline about the result, never about its limitations."""
    parts = [_compact_finding(item) for item in findings]
    parts = [item for item in parts if item]
    return "；".join(parts[:2]) or fallback


class ResearchEngine:
    def __init__(
        self,
        settings: Settings,
        store: MacroStore,
        credentials: LocalCredentialStore | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.credentials = credentials
        self.llm = DeepSeekClient(
            settings.deepseek_api_key,
            settings.deepseek_model,
            settings.deepseek_base_url,
            config_resolver=credentials.llm_config if credentials else None,
        )
        self.registry = RegistryStore(settings.project_root / "registry" / "v2")
        self.compiler = ResearchCompiler(self.registry, self.llm)
        self.artifacts = ArtifactStore(settings.artifact_dir)

    def explain_node_detail(self, job_id: str, node_id: str, detail: dict[str, Any]) -> dict[str, Any]:
        """Add a deterministic fact card and a cached, grounded prose layer on demand."""
        enriched = ensure_fixed_explanation(dict(detail), self.registry)
        enriched = add_llm_explanation(enriched, self.llm)
        stored = {key: value for key, value in enriched.items() if key not in {"node_status", "updated_at"}}
        self.store.save_node_detail(job_id, node_id, str(enriched.get("status") or enriched.get("node_status") or "PENDING"), stored)
        return enriched

    def _provenance(self, research_node_id: str, recipe_id: str, factor_ids: list[str], as_of_date: date) -> dict[str, Any]:
        report_evidence: dict[str, list[int]] = {}
        for route in self.registry.all("routes"):
            if research_node_id in route.get("node_ids", []) and recipe_id in route.get("model_recipe_ids", []):
                report_evidence.update(route.get("report_evidence", {}))
        series_ids = [self.registry.get("factors", factor_id)["series_id"] for factor_id in factor_ids]
        lineage = self.store.series_lineage([series_id for series_id in series_ids if not series_id.startswith("STATE_")], as_of_date)
        recipe = self.registry.get("models", recipe_id)
        return {
            "report_evidence": [{"report_id": report_id, "pages": pages, "title": self.registry.get("reports", report_id)["title"]} for report_id, pages in report_evidence.items()],
            "registry_version": "0.2.0+v0.3-depth-extension",
            "model_recipe_id": recipe_id,
            "code_artifact": recipe["artifact"],
            "parameter_policy_ids": ["P.TIME_WINDOW.V1", "P.COVARIANCE.V1", "P.TRANSFORMS.V1", "P.MISSING.V1"],
            "data_lineage": lineage,
            "data_snapshot_hash_note": "Each exported artifact has a SHA-256; source snapshots are identified here by immutable snapshot_id.",
        }

    def _interpret(self, question: str, plan: dict[str, Any], results: list[dict[str, Any]], aggregation: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        stance_labels = {
            "ASSOCIATIONAL_EVIDENCE_ONLY": "现有证据只能支持描述性、预测性或关联性判断，不能支持 AI 导致失业上升的因果结论",
            "UPSIDE_OR_ACCELERATION": "现有证据整体偏向上行或重新加速",
            "DOWNSIDE_OR_DECELERATION": "现有证据整体偏向下行或继续走弱",
            "MIXED_OR_NEAR_NEUTRAL": "现有证据相互冲突，暂时接近中性",
            "NEGATIVE_ASSOCIATION": "面板 fixture 显示负向条件相关",
            "POSITIVE_ASSOCIATION": "面板 fixture 显示正向条件相关",
            "UNSUPPORTED": "当前 Registry 无法覆盖该问题",
        }
        claim_by_node = {
            "N.ACTIVITY.NOWCAST": "C.ACTIVITY.DIRECTION",
            "N.ACTIVITY.PRODUCTION": "C.ACTIVITY.DIRECTION",
            "N.ACTIVITY.HOUSEHOLD_DEMAND": "C.ACTIVITY.DIRECTION",
            "N.ACTIVITY.TAIL_RISK": "C.ACTIVITY.DOWNSIDE",
            "N.INFLATION.DYNAMICS": "C.INFLATION.DIRECTION",
            "N.INFLATION.ENERGY_PASS": "C.ENERGY.PASS_THROUGH",
            "N.MONETARY.CONDITIONS": "C.MONETARY.CONDITIONS",
            "N.LABOR.STATE": "C.LABOR.STATE",
            "N.LABOR.VACANCIES": "C.LABOR.STATE",
            "N.LABOR.DISPLACEMENT": "C.LABOR.STATE",
            "N.LABOR.WAGE_ADJUSTMENT": "C.LABOR.STATE",
            "N.LABOR.COHORT_INCIDENCE": "C.LABOR.STATE",
            "N.LABOR.AI_SECTORS": "C.LABOR.STATE",
            "N.HOUSING.CYCLE": "C.ACTIVITY.DIRECTION",
            "N.FIN.CREDIT": "C.MONETARY.CONDITIONS",
            "N.FISCAL.SUPPLY": "C.FISCAL.SUPPLY",
            "N.MONETARY.POLICY_EXPECTATIONS": "C.FISCAL.YIELD_PRESSURE",
            "N.MONETARY.REAL_RATE": "C.FISCAL.YIELD_PRESSURE",
            "N.MONETARY.LIQUIDITY": "C.FISCAL.YIELD_PRESSURE",
            "N.INFLATION.EXPECTATIONS": "C.FISCAL.YIELD_PRESSURE",
            "N.INFLATION.COMPENSATION": "C.FISCAL.YIELD_PRESSURE",
            "N.INFLATION.DEMAND_PRESSURE": "C.FISCAL.YIELD_PRESSURE",
            "N.FISCAL.DEBT_TRAJECTORY": "C.FISCAL.YIELD_PRESSURE",
            "N.FISCAL.BALANCE": "C.FISCAL.YIELD_PRESSURE",
            "N.FISCAL.TERM_PREMIUM": "C.FISCAL.YIELD_PRESSURE",
            "N.EQUITY.PRICE_DIRECTION": "C.EQUITY.DIRECTION",
            "N.EQUITY.VOLATILITY": "C.EQUITY.RISK_APPETITE",
            "N.EQUITY.DISCOUNT_RATE": "C.EQUITY.DIRECTION",
            "N.COMMODITY.PRICE_DIRECTION": "C.COMMODITY.DIRECTION",
            "N.COMMODITY.SUPPLY_BALANCE": "C.COMMODITY.SUPPLY_BALANCE",
            "N.COMMODITY.MACRO_TRANSMISSION": "C.COMMODITY.DIRECTION",
            "N.HOUSING.STATE_PANEL_FIXTURE": "C.PANEL.FIXTURE",
        }
        fallback_falsifiers = []
        for node in plan.get("nodes", [])[:4]:
            item = self.registry.get("nodes", node["node_id"])
            claim_id = claim_by_node.get(node["node_id"])
            if claim_id:
                fallback_falsifiers.append(self.registry.get("claims", claim_id)["falsifier_template"])
            else:
                fallback_falsifiers.append(f"若后续真实数据与“{item['intermediate_claim']}”持续反向，则需要推翻本轮综合。")
        fallback_falsifiers = list(dict.fromkeys(fallback_falsifiers))
        primary_findings = aggregation.get("primary_findings", [])
        context_findings = aggregation.get("context_findings", [])
        scenario_analysis = aggregation.get("scenario_analysis") or {}
        headline_findings = primary_findings or aggregation.get("claim_summaries", [])
        if headline_findings:
            deterministic_headline = conclusion_headline(
                headline_findings,
                stance_labels.get(aggregation["stance"], "已形成可追溯的方向判断"),
            )
        elif aggregation.get("answerability") == "UNSUPPORTED":
            deterministic_headline = "本轮未形成可验证的研究结论"
        else:
            deterministic_headline = stance_labels.get(aggregation["stance"], "已形成可追溯的方向判断")

        finding_parts = []
        if primary_findings:
            finding_parts.append("主命题：" + "；".join(item["finding_zh"] for item in primary_findings))
        if context_findings:
            finding_parts.append("辅助背景：" + "；".join(item["finding_zh"] for item in context_findings))
        if not finding_parts and aggregation.get("claim_summaries"):
            finding_parts.append("已执行命题：" + "；".join(item["finding_zh"] for item in aggregation["claim_summaries"]))
        finding_parts.append(
            f"覆盖度为 {aggregation['coverage']}，置信度为 {aggregation['confidence']}。"
            f"主命题分数为 {aggregation.get('primary_score')}；等泳道系统平衡分 {aggregation.get('system_balance_score', aggregation.get('ordinal_score'))} 仅作为审计指标，不再替代用户问题的答案。"
        )
        if aggregation.get("evidence_state") in {"CONDITIONAL_SCENARIO", "BASELINE_ONLY"}:
            events = scenario_analysis.get("conditional_events", [])
            if events:
                finding_parts.append("条件事件：" + "；".join(str(item) for item in events[:3]) + "。")
            profiles = scenario_analysis.get("response_profiles", [])
            if profiles:
                profile_parts = []
                for profile in profiles[:6]:
                    peak = profile.get("scaled_peak_response") or profile.get("peak_response") or {}
                    effect = peak.get("effect")
                    horizon = peak.get("horizon")
                    scale_label = "按用户冲击尺度的" if profile.get("scaled_peak_response") else ""
                    effect_text = f"，{scale_label}峰值响应 {float(effect):+.4f}（h={horizon}）" if isinstance(effect, (int, float)) else ""
                    profile_parts.append(
                        f"{profile.get('shock_factor_id')} → {profile.get('response_factor_id')}"
                        f"（{profile.get('identification_strength')}）{effect_text}"
                    )
                finding_parts.append("条件响应：" + "；".join(profile_parts) + "。")
            else:
                axes = scenario_analysis.get("sensitivity_axes", [])
                if axes:
                    finding_parts.append(
                        "敏感性轴："
                        + "；".join(
                            f"{item.get('label_zh')}={item.get('directional_lean')}"
                            for item in axes[:8]
                        )
                        + "。"
                    )
        interpretation_limitations = list(plan.get("unsupported_aspects", []))
        evidence_state = aggregation.get("evidence_state")
        if evidence_state in {"CONDITIONAL_SCENARIO", "BASELINE_ONLY"}:
            interpretation_limitations.append(
                "情景响应依赖已注册冲击、代理映射与识别假设，不自动等同于因果效应。"
            )
        elif evidence_state == "ASSOCIATIONAL_ONLY":
            interpretation_limitations.append(
                "现有模型提供描述性、预测性或关联性证据，不能据此识别因果效应。"
            )
        elif aggregation.get("answerability") == "UNSUPPORTED":
            interpretation_limitations.append(
                "当前 Registry 没有可执行且可映射到目标命题的有效证据。"
            )
        interpretation_limitations.append("模型结果受当前数据 vintage、样本窗口和已注册方法覆盖范围限制。")
        limitations = list(dict.fromkeys(interpretation_limitations))
        falsifiers = fallback_falsifiers or ["新增官方数据使主要模型的方向一致反转。"]
        report_fallback = build_research_report(
            question,
            plan,
            results,
            aggregation,
            self.registry,
            limitations=limitations,
            falsifiers=falsifiers,
        )
        fallback = {
            "headline": report_fallback["direct_answer"]["headline"],
            "answer": report_fallback["abstract"]["text"],
            "limitations": limitations,
            "falsifiers": falsifiers,
            "source_node_ids": [result["node_id"] for result in results if result.get("status") in {"SUCCESS", "WARNING"}],
            "report": report_fallback,
        }
        if not self.llm.available:
            return fallback, {"role": "LLM-7 Synthesis Interpreter", "status": "FALLBACK_NO_KEY"}
        system = """
You are LLM-7, the evidence-bound research-report editor in MacroTrace. Rewrite only the prose fields in the supplied deterministic report. Do not calculate, change any number, weight, method, variable, sample, diagnostic, source link, limitation, or falsifier. Do not add facts, models, causality, probabilities, point forecasts, or price targets.

The reader must receive a direct directional answer to the exact original question before any background. Use natural Chinese research prose. Never use these internal engineering expressions in reader-facing prose: 主命题, 注册命题, 序数信号, 系统平衡分, 等泳道, Registry, claim_id, lane_id. Never write “直接回答是”. Copy the supplied deterministic direct_answer.headline exactly; it is an immutable aggregation result. When causal identification is unavailable, keep the directional stance and explain the identification limit only in the supporting prose.

Return exactly one JSON object with exactly these top-level keys:
direct_answer, abstract, mechanism_explanations, empirical_explanations, conclusion.
direct_answer must contain exactly headline and text.
abstract must contain exactly text and key_points (a string array).
mechanism_explanations must contain one object for every supplied mechanism, in the same order, with exactly mechanism_id, explanation, transmission_chain.
empirical_explanations must contain one object for every supplied empirical item, in the same order, with exactly node_id, title, question_addressed, finding, implication.
conclusion must contain exactly text.

First read deterministic_report.research_context and use the language of that domain: macro questions discuss economic states; equity-index and single-equity questions answer the named security or index first; bond questions discuss yield, duration, term premium and spreads; industry questions discuss demand, capacity, price, margins and cycle; commodity questions discuss supply, demand, inventories and pass-through. Never force every question into generic macro language.

The direct answer should be 2-4 sentences and must begin with the stance on the exact object asked about, not a limitation. The abstract should synthesize the major result, conflict, coverage, and confidence. For each mechanism, name the actual mechanism or model first, then explain its transmission chain. For empirical work, state what data was used, what model was run, the sample, what the numerical result says, and an explicit interpretation. Preserve uncertainty and conflicts. If no registered predictive model produced a percentage or price range, do not invent one. Do not rewrite deterministic method/sample/diagnostic fields because they will be merged separately.
""".strip()
        payload = {
            "question": question,
            "query": plan["query"],
            "answerability": aggregation.get("answerability"),
            "evidence_state": aggregation.get("evidence_state"),
            "conflicts_retained": aggregation.get("conflicts_retained"),
            "deterministic_report": report_fallback,
        }
        errors = []
        for attempt in range(2):
            try:
                output = self.llm.json_completion(system, json.dumps(payload, ensure_ascii=False), max_tokens=4200)
                if not isinstance(output, dict):
                    raise ValueError("interpreter output must be an object")
                report = merge_llm_report_language(report_fallback, output)
                interpretation = {
                    "headline": report["direct_answer"]["headline"],
                    "answer": report["abstract"]["text"],
                    "limitations": fallback["limitations"],
                    "falsifiers": fallback["falsifiers"],
                    "source_node_ids": fallback["source_node_ids"],
                    "report": report,
                }
                return interpretation, {"role": "LLM-7 Synthesis Interpreter", "status": "SUCCESS" if attempt == 0 else "REPAIRED", "model": self.llm.model}
            except Exception as exc:
                errors.append(type(exc).__name__)
                payload["repair"] = (
                    "Return the exact requested JSON keys and one update for every supplied mechanism and empirical node. "
                    "Use plain reader-facing Chinese, preserve all evidence limits, and remove every internal engineering term."
                )
        return fallback, {"role": "LLM-7 Synthesis Interpreter", "status": "FALLBACK_AFTER_REPAIR", "errors": errors}

    def execute(
        self,
        job_id: str,
        question: str,
        as_of_date: date | None = None,
        progress: ProgressCallback | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        as_of_date = as_of_date or date.today()
        progress = progress or (lambda _status, _progress, _detail, _graph: None)
        cancelled = cancelled or (lambda: False)
        execution_trace: list[dict[str, Any]] = []

        def compiler_emit(status: str, detail: dict[str, Any]) -> None:
            if cancelled():
                raise JobCancelled("cancelled during compilation")
            progress(status, STATUS_PROGRESS[status], detail, None)

        plan_model = self.compiler.compile(question, as_of_date, compiler_emit)
        compiler_trace = self.compiler.trace
        plan = plan_model.model_dump(mode="json")
        graph = GraphBuilder(job_id, self.registry)
        graph.from_plan(plan_model)
        for node_id, detail in graph.generic_details().items():
            self.store.save_node_detail(job_id, node_id, detail["status"], detail)
        progress("VALIDATING_PLAN", STATUS_PROGRESS["VALIDATING_PLAN"], {"validator": plan["validation"], "models": len(plan["models"]), "plan_snapshot": plan}, graph.export())
        if cancelled():
            raise JobCancelled("cancelled before model execution")

        results: list[dict[str, Any]] = []
        total = max(1, len(plan_model.models))
        for index, decision in enumerate(plan_model.models, start=1):
            if cancelled():
                raise JobCancelled("cancelled during model execution")
            model_run_id = graph.model_run_id(index, decision.node_id, decision.model_recipe_id)
            graph.set_status(model_run_id, "RUNNING")
            model_progress = 0.50 + 0.34 * ((index - 1) / total)
            progress("EXECUTING_MODELS", model_progress, {"node_id": model_run_id, "model_recipe_id": decision.model_recipe_id, "index": index, "total": total}, graph.export())
            started = perf_counter()
            try:
                runner = MODEL_RUNNERS[decision.model_recipe_id]
                result = runner(
                    self.store,
                    self.registry,
                    as_of_date,
                    model_run_id,
                    decision.factor_ids,
                    decision.parameters.values,
                )
                result["research_node_id"] = decision.node_id
                result["specification_id"] = decision.specification_id
                result["specification_role"] = decision.role
                result["factor_ids"] = decision.factor_ids
                result["parameters"] = decision.parameters.model_dump(mode="json")
                result["provenance"] = self._provenance(decision.node_id, decision.model_recipe_id, decision.factor_ids, as_of_date)
                result = ensure_fixed_explanation(result, self.registry)
                artifacts = self.artifacts.save_model_result(job_id, model_run_id, result)
                for artifact in artifacts:
                    self.store.save_artifact(artifact)
                result["artifacts"] = artifacts
                graph.attach_result(model_run_id, result)
                execution_trace.append({"node_id": model_run_id, "status": result["status"], "duration_ms": round((perf_counter() - started) * 1000), "model_recipe_id": decision.model_recipe_id})
            except Exception as exc:  # one failed registered model must not fabricate or abort unrelated lanes
                result = {
                    "status": "FAILED",
                    "node_id": model_run_id,
                    "research_node_id": decision.node_id,
                    "model_recipe_id": decision.model_recipe_id,
                    "specification_id": decision.specification_id,
                    "specification_role": decision.role,
                    "evidence_type": "NONE",
                    "title": self.registry.get("models", decision.model_recipe_id)["method"],
                    "error": "Registered model execution failed.",
                    "error_type": type(exc).__name__,
                    "parameters": decision.parameters.model_dump(mode="json"),
                    "provenance": self._provenance(decision.node_id, decision.model_recipe_id, decision.factor_ids, as_of_date),
                    "diagnostics": [],
                    "charts": [],
                    "artifacts": [],
                }
                graph.attach_failure(model_run_id, type(exc).__name__)
                execution_trace.append({"node_id": model_run_id, "status": "FAILED", "duration_ms": round((perf_counter() - started) * 1000), "model_recipe_id": decision.model_recipe_id, "error_type": type(exc).__name__})
                result = ensure_fixed_explanation(result, self.registry)
            results.append(result)
            self.store.save_node_detail(job_id, model_run_id, result["status"], result)
            progress("EXECUTING_MODELS", 0.50 + 0.34 * (index / total), {"node_id": model_run_id, "status": result["status"]}, graph.export())

        if cancelled():
            raise JobCancelled("cancelled before aggregation")
        progress("AGGREGATING_LANES", STATUS_PROGRESS["AGGREGATING_LANES"], {"successful_models": sum(result["status"] in {"SUCCESS", "WARNING"} for result in results), "failed_models": sum(result["status"] == "FAILED" for result in results)}, graph.export())
        synthesis_policy = next(
            item for item in self.registry.all("synthesis_policies")
            if item["workflow_id"] == plan["workflow_id"]
        )
        aggregation = synthesize(plan, results, synthesis_policy, self.registry.all("evidence_mappings"))
        if cancelled():
            raise JobCancelled("cancelled before synthesis")
        progress("SYNTHESIZING", STATUS_PROGRESS["SYNTHESIZING"], {"role": "LLM-7", "numeric_recomputation_allowed": False}, graph.export())
        interpretation, language_trace = self._interpret(question, plan, results, aggregation)
        graph.attach_synthesis(aggregation, interpretation)
        final_graph = graph.export()
        for node_id, detail in graph.generic_details().items():
            if self.store.get_node_detail(job_id, node_id) is None:
                self.store.save_node_detail(job_id, node_id, detail["status"], detail)

        successful = sum(result["status"] in {"SUCCESS", "WARNING"} for result in results)
        terminal_status = "COMPLETE" if aggregation["coverage"] == "FULL" and successful == len(results) else "PARTIAL" if successful else "FAILED"
        synthesis = {
            **aggregation,
            **interpretation,
            "unsupported_aspects": plan["unsupported_aspects"],
        }
        result = {
            "schema_version": "0.2.0",
            "job_id": job_id,
            "run_id": job_id,
            "status": terminal_status,
            "question": question,
            "as_of_date": as_of_date.isoformat(),
            "horizon": plan["query"]["horizon"],
            "horizon_months": plan["query"]["horizon"]["maximum"] if plan["query"]["horizon"]["unit"] == "MONTHS" else None,
            "query": plan["query"],
            "parsed_query": plan["query"],
            "plan": plan,
            "graph": final_graph,
            "synthesis": synthesis,
            "report": interpretation["report"],
            "model_results": [{key: value for key, value in model.items() if key not in {"table", "charts", "diagnostics", "variables"}} for model in results],
            "modules": [{**model, "module_id": model["model_recipe_id"]} for model in results],
            "trace": [
                {"step": "COMPILER", "status": "SUCCESS", "detail": {"roles": compiler_trace}},
                {"step": "MODEL_EXECUTION", "status": terminal_status, "detail": execution_trace},
                {"step": "CROSS_LANE_SYNTHESIS", "status": "SUCCESS", "detail": {"deterministic": True, "language_layer": language_trace}},
            ],
            "governance": {
                "llm_roles": ["LLM-0", "LLM-1", "LLM-2", "LLM-3", "LLM-4", "LLM-5", "LLM-6", "LLM-7"],
                "numeric_analysis_by_llm": False,
                "numeric_weights_by_llm": False,
                "arbitrary_code_allowed": False,
                "registry_version": "0.2.0+v0.3-depth-extension",
                "probability_output_allowed": aggregation["probability_output_allowed"],
                "vintage_note": "Every model requires a snapshot whose realtime_start or fetch date is on/before the job as-of date. A missing eligible vintage fails that model rather than falling forward to revised data.",
            },
            "completed_at": datetime.now(UTC).isoformat(),
        }
        # The job manager owns the terminal transition.  Keeping the engine at a
        # non-terminal finalising state prevents SSE clients from observing a
        # COMPLETE event before result_json has been committed atomically.
        progress("SYNTHESIZING", 0.99, {"stage": "FINALIZING", "coverage": aggregation["coverage"], "coverage_score": aggregation["coverage_score"], "confidence": aggregation["confidence"]}, final_graph)
        return result

    def run(
        self,
        question: str,
        as_of_date: date | None = None,
        horizon_months: int | None = None,
    ) -> dict[str, Any]:
        """Synchronous compatibility entry point. The legacy horizon is ignored by v0.2."""
        as_of_date = as_of_date or date.today()
        run_id = "RUN_" + datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid4().hex[:6].upper()
        result = self.execute(run_id, question, as_of_date)
        if horizon_months is not None:
            result["governance"]["legacy_horizon_ignored"] = True
        self.store.save_research_run(run_id, question, as_of_date, result["status"], result["query"], result["plan"], result)
        return result
