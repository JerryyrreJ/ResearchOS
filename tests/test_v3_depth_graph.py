from __future__ import annotations

from datetime import date
from pathlib import Path

from backend.app.aggregation import heterogeneous_ordinal_synthesis
from backend.app.aggregation import synthesize
from backend.app.compiler import ResearchCompiler
from backend.app.llm import DeepSeekClient
from backend.app.node_explanations import add_llm_explanation, ensure_fixed_explanation
from backend.app.registry import RegistryStore
from backend.app.research_graph import GraphBuilder


ROOT = Path(__file__).resolve().parents[1]


def registry() -> RegistryStore:
    return RegistryStore(ROOT / "registry" / "v2")


def compiler() -> ResearchCompiler:
    return ResearchCompiler(registry(), DeepSeekClient("", "deepseek-chat", "https://api.deepseek.com"))


def test_system_question_meets_registered_depth_budget() -> None:
    plan = compiler().compile(
        "Is the US economy weakening or reaccelerating, and what is recession risk over the next 3 months?",
        date(2026, 7, 14),
    )
    depth = plan.validation["research_depth"]
    assert plan.complexity_class == "SYSTEM_FORECAST"
    assert depth["status"] == "PASS"
    assert len(plan.lanes) >= 4
    assert depth["lane_metrics"]["US.ACTIVITY"]["model_specifications"] >= 10
    assert depth["lane_metrics"]["US.LABOR"]["model_specifications"] >= 10
    assert depth["method_families"] >= 3
    assert len(plan.models) >= 30


def test_rates_attribution_question_runs_a_full_directional_programme() -> None:
    plan = compiler().compile(
        "Is expanding US federal debt increasing pressure on the 10-year Treasury yield?",
        date(2026, 7, 14),
    )
    depth = plan.validation["research_depth"]
    assert plan.workflow_id == "WF.US.RATES_TRANSMISSION.V1"
    assert plan.complexity_class == "CAUSAL_ATTRIBUTION"
    assert plan.coverage == "PARTIAL"
    assert depth["status"] == "PASS"
    assert depth["identification_required"] is False
    assert depth["identification_active"] is False
    assert len(plan.lanes) == 4
    assert len(plan.models) >= 40
    assert depth["planned_specifications"] >= 40
    assert all(
        depth["lane_metrics"][lane_id]["model_specifications"] >= 10
        for lane_id in ("US.MONETARY", "US.INFLATION", "US.FISCAL_TREASURY", "US.ACTIVITY")
    )


def test_missing_identification_keeps_a_legal_directional_stance() -> None:
    plan = {
        "workflow_id": "WF.US.RATES_TRANSMISSION.V1",
        "complexity_class": "CAUSAL_ATTRIBUTION",
        "coverage_score": 0.85,
        "nodes": [{"node_id": "N.FISCAL.SUPPLY", "lane_id": "US.FISCAL_TREASURY"}],
        "validation": {
            "research_depth": {
                "identification_required": False,
                "identification_active": False,
                "checks": {},
            }
        },
    }
    policy = next(
        item for item in registry().all("synthesis_policies")
        if item["workflow_id"] == "WF.US.RATES_TRANSMISSION.V1"
    )
    result = {
        "status": "SUCCESS",
        "node_id": "MR.FISCAL.YIELD",
        "research_node_id": "N.FISCAL.SUPPLY",
        "specification_id": "MS.RATES.FISCAL.VAR_SUPPLY.V1",
        "model_recipe_id": "M.VAR_SYSTEM.V1",
        "evidence_type": "PREDICTIVE_STRUCTURAL_PROXY",
        "direction": "UP",
        "signal": 0.55,
        "confidence": "MEDIUM",
        "specification_role": "CORE",
    }
    synthesis = synthesize(plan, [result], policy, registry().all("evidence_mappings"))
    assert synthesis["coverage"] != "UNSUPPORTED"
    assert synthesis["stance"] != "ASSOCIATIONAL_EVIDENCE_ONLY"
    assert synthesis["answerability"] == "CONDITIONAL"
    assert synthesis["evidence_state"] == "ASSOCIATIONAL_ONLY"
    assert synthesis["primary_findings"][0]["claim_id"] == "C.FISCAL.YIELD_PRESSURE"


def test_ai_causal_question_is_deep_but_causally_unsupported() -> None:
    plan = compiler().compile(
        "Has AI significantly increased US unemployment?",
        date(2026, 7, 14),
    )
    depth = plan.validation["research_depth"]
    ai = depth["lane_metrics"]["US.AI_PRODUCTIVITY"]
    labor = depth["lane_metrics"]["US.LABOR"]
    assert plan.workflow_id == "WF.US.AI_LABOR_CAUSAL.V1"
    assert plan.coverage == "UNSUPPORTED"
    assert depth["checks"]["identification"] is False
    assert ai["model_specifications"] >= 10
    assert ai["blocked_model_specifications"] >= 10
    assert labor["executable_model_specifications"] >= 10
    assert len(plan.models) >= 20


def test_graph_contains_full_lane_universe_and_white_box_details() -> None:
    store = registry()
    plan = compiler().compile("Has AI significantly increased US unemployment?", date(2026, 7, 14))
    graph = GraphBuilder("JOB_V3_GRAPH", store)
    graph.from_plan(plan)
    payload = graph.export()
    lane_nodes = [node for node in payload["nodes"] if node["node_type"] == "LANE"]
    assert len(lane_nodes) == len(store.all("lanes"))
    assert any(node["status"] == "NOT_ROUTED" for node in lane_nodes)
    assert sum(node["node_type"] == "MECHANISM" for node in payload["nodes"]) == len(store.all("mechanisms"))
    assert sum(node["node_type"] == "MODEL_SPECIFICATION" for node in payload["nodes"]) == len(store.all("model_specifications"))
    assert any(node["status"] == "BLOCKED" and node["node_type"] == "MODEL_SPECIFICATION" for node in payload["nodes"])
    assert all(node["detail_endpoint"] for node in payload["nodes"])
    details = graph.generic_details()
    assert set(details) == {node["node_id"] for node in payload["nodes"]}
    assert all({"overview", "specification", "results", "diagnostics", "robustness", "provenance"}.issubset(detail) for detail in details.values())
    required_explanation = {"purpose", "why_it_exists", "mechanism", "data_summary", "output_summary", "plain_summary"}
    assert all(required_explanation.issubset(detail["explanation"]) for detail in details.values())
    assert all(all(detail["explanation"][key] for key in required_explanation) for detail in details.values())


def test_executed_model_explanation_names_real_data_and_sample() -> None:
    detail = {
        "status": "SUCCESS",
        "node_id": "MR::01::N.ACTIVITY.PRODUCTION::M.UNIVARIATE_AR.V1",
        "model_recipe_id": "M.UNIVARIATE_AR.V1",
        "method": "Registered univariate autoregressive benchmark",
        "research_node_id": "N.ACTIVITY.PRODUCTION",
        "summary": "The registered forecast is positive.",
        "factor_ids": ["F.ACTIVITY.INDPRO"],
        "specification": {
            "formula": "y_{t+3}=alpha+phi(L)y_t+epsilon_t",
            "estimand": "3-month-ahead transformed value",
            "causal_interpretation_allowed": False,
        },
        "variables": [{"factor_id": "F.ACTIVITY.INDPRO", "definition": "Industrial production index"}],
        "sample": {"start": "2016-03-01", "end": "2026-02-01", "observations": 120, "frequency": "monthly"},
    }
    explained = ensure_fixed_explanation(detail, registry())
    data_summary = explained["explanation"]["data_summary"]
    assert "F.ACTIVITY.INDPRO" in data_summary
    assert "2016-03-01" in data_summary
    assert "120" in data_summary


def test_node_explanation_has_deterministic_fallback_without_llm_key() -> None:
    detail = ensure_fixed_explanation(
        {
            "status": "SUCCESS",
            "node_id": "QUERY",
            "node_type": "QUERY",
            "title": "SCENARIO · 1-3 months",
            "provenance": {
                "registry_metadata": {
                    "question_form": "SCENARIO",
                    "horizon": {"minimum": 1, "maximum": 3, "unit": "MONTHS"},
                    "conditional_events": ["oil price shock"],
                }
            },
        },
        registry(),
    )
    explained = add_llm_explanation(detail, DeepSeekClient("", "deepseek-chat", "https://api.deepseek.com"))
    assert explained["explanation"]["llm"]["status"] == "FALLBACK_NO_KEY"
    assert "条件效应" in explained["explanation"]["mechanism"]


def test_terminal_graph_marks_all_blocked_causal_lane_as_blocked() -> None:
    store = registry()
    plan = compiler().compile("Has AI significantly increased US unemployment?", date(2026, 7, 14))
    graph = GraphBuilder("JOB_V3_BLOCKED_LANE", store)
    graph.from_plan(plan)
    graph.attach_synthesis(
        {"method": "registered test synthesis", "coverage": "UNSUPPORTED", "confidence": "LOW", "contributions": []},
        {"headline": "Causal claim unsupported", "answer": "No identified causal evidence.", "falsifiers": []},
    )
    assert graph.nodes["LANE::US.AI_PRODUCTIVITY"]["status"] == "BLOCKED"


def test_runtime_and_synthesis_nodes_receive_the_same_explanation_contract() -> None:
    store = registry()
    plan = compiler().compile(
        "Is the US economy weakening or reaccelerating over the next 3 months?",
        date(2026, 7, 14),
    )
    graph = GraphBuilder("JOB_V3_RUNTIME_EXPLANATIONS", store)
    graph.from_plan(plan)
    decision = plan.models[0]
    model_run_id = graph.model_run_id(1, decision.node_id, decision.model_recipe_id)
    graph.attach_result(
        model_run_id,
        {
            "status": "SUCCESS",
            "title": "Registered model result",
            "summary": "A registered signal was estimated.",
            "evidence_type": "PREDICTIVE_ASSOCIATION",
            "direction": "INCREASING",
            "confidence": "MEDIUM",
            "signal": 0.2,
            "diagnostics": [{"name": "Registered diagnostic", "status": "PASS"}],
        },
    )
    graph.attach_synthesis(
        {
            "method": "Registered ordinal synthesis",
            "coverage": "PARTIAL",
            "confidence": "MEDIUM",
            "contributions": [{"node_id": model_run_id, "ordinal_signal": 0.2, "quality_multiplier": 1.0}],
        },
        {"headline": "Registered final claim", "answer": "Evidence remains conditional.", "falsifiers": ["Future official data reverse the signal."]},
    )
    details = graph.generic_details()
    runtime_types = {"DIAGNOSTIC", "EVIDENCE", "LANE_SIGNAL", "AGGREGATION", "FINAL_CLAIM", "FALSIFIER"}
    actual_types = {detail["node_type"] for detail in details.values()}
    assert runtime_types.issubset(actual_types)
    assert all(
        all(detail["explanation"].get(key) for key in ("purpose", "why_it_exists", "mechanism", "data_summary", "output_summary"))
        for detail in details.values()
        if detail["node_type"] in runtime_types
    )


def test_robustness_specification_does_not_buy_claim_weight() -> None:
    plan = {
        "coverage_score": 1.0,
        "nodes": [{"node_id": "N.ACTIVITY.NOWCAST", "lane_id": "US.ACTIVITY"}],
    }
    core = {
        "status": "SUCCESS",
        "node_id": "MR.CORE",
        "research_node_id": "N.ACTIVITY.NOWCAST",
        "model_recipe_id": "M.BRIDGE_OLS.V1",
        "evidence_type": "PREDICTIVE_ASSOCIATION",
        "direction": "INCREASING",
        "signal": 0.5,
        "confidence": "MEDIUM",
        "specification_role": "CORE",
    }
    robustness = {
        **core,
        "node_id": "MR.ROBUSTNESS",
        "signal": 1.0,
        "specification_role": "ROBUSTNESS",
    }
    synthesis = heterogeneous_ordinal_synthesis(plan, [core, robustness])
    assert synthesis["claim_summaries"][0]["model_count"] == 1
    assert synthesis["claim_summaries"][0]["ordinal_signal"] == 0.5
    assert synthesis["validation_runs"][0]["role"] == "ROBUSTNESS"
