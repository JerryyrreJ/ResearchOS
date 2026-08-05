from __future__ import annotations

from datetime import date
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from jsonschema import Draft202012Validator

from backend.app.compiler import ResearchCompiler, extract_horizon
from backend.app.llm import DeepSeekClient
from backend.app.registry import RegistryError, RegistryStore
from backend.app.research_graph import GraphBuilder
from backend.app.schemas import ResearchJobCreate


ROOT = Path(__file__).resolve().parents[1]


def registry() -> RegistryStore:
    return RegistryStore(ROOT / "registry" / "v2")


def compiler() -> ResearchCompiler:
    return ResearchCompiler(registry(), DeepSeekClient("", "deepseek-chat", "https://api.deepseek.com"))


class HostileLlm:
    available = True

    def json_completion(self, *_args, **_kwargs) -> dict:
        return {"python": "import os", "node_ids": ["N.UNREGISTERED"]}


class ValidSelectorLlm:
    available = True

    def json_completion(self, _system: str, user: str, **_kwargs) -> dict:
        payload = json.loads(user)
        if "allowed_question_forms" in payload:
            return {"target_concepts": ["activity", "recession"], "question_form": "FORECAST", "conditional_events": [], "output_requirements": ["white-box graph"]}
        if "allowed_workflow_ids" in payload:
            return {"workflow_id": "WF.US.ACTIVITY_RISK.V1", "reason": "registered match"}
        if "allowed_lane_ids" in payload:
            return {"lanes": [{"lane_id": item, "priority": "CORE", "reason": "registered"} for item in payload["allowed_lane_ids"]]}
        if "allowed_node_ids" in payload:
            return {"node_ids": payload["allowed_node_ids"], "reason": "registered"}
        if "allowed_factor_ids" in payload:
            return {"factors": [{"factor_id": item, "role": "CORE" if index < 3 else "SUPPORTING", "reason": "registered"} for index, item in enumerate(payload["allowed_factor_ids"])]}
        if "compatible_models" in payload:
            return {"model_recipe_ids": [item["model_recipe_id"] for item in payload["compatible_models"]], "reason": "registered"}
        if "allowed_parameters" in payload:
            return {"values": payload["policy_default"]}
        raise AssertionError(f"unexpected compiler payload: {payload.keys()}")


def test_registry_is_versioned_and_reference_complete() -> None:
    summary = registry().summary()
    assert summary["validation"] == "PASS"
    assert summary["counts"]["models"] >= 7
    assert summary["counts"]["mechanisms"] >= 20
    assert summary["counts"]["model_specifications"] >= 50
    assert summary["counts"]["evidence_budgets"] >= 5
    assert summary["counts"]["scenario_mappings"] >= 8
    assert summary["counts"]["reports"] >= 20
    assert summary["arbitrary_code_allowed"] is False


def test_registry_rejects_missing_and_illegal_parameters() -> None:
    store = registry()
    with pytest.raises(RegistryError, match="missing required parameters"):
        store.validate_parameters("M.VAR_SYSTEM.V1", {"lags": 2})
    with pytest.raises(RegistryError, match="not allowed"):
        store.validate_parameters(
            "M.VAR_SYSTEM.V1",
            {"lags": 99, "forecast_horizon": 3, "identification": "REGISTERED_CHOLESKY", "estimation_window_years": 15},
        )
    with pytest.raises(RegistryError, match="unregistered parameters"):
        store.validate_parameters(
            "M.VAR_SYSTEM.V1",
            {"lags": 2, "forecast_horizon": 3, "identification": "REGISTERED_CHOLESKY", "estimation_window_years": 15, "python": "print(1)"},
        )


def test_natural_language_horizon_is_authoritative() -> None:
    explicit = extract_horizon("未来一到三个月美国通胀是否加速？", {"minimum": 1, "maximum": 6, "unit": "MONTHS"})
    assert (explicit.minimum, explicit.maximum, explicit.source) == (1, 3, "USER_EXPLICIT")
    default = extract_horizon("美国通胀当前怎么样？", {"minimum": 1, "maximum": 3, "unit": "MONTHS"})
    assert default.source == "POLICY_DEFAULT"
    assert default.raw_text is None


def test_calendar_month_is_not_misread_as_a_forecast_horizon() -> None:
    parsed = extract_horizon(
        "如果美国在7月15日恢复军事行动，会怎样影响美国经济？",
        {"minimum": 1, "maximum": 3, "unit": "MONTHS"},
    )
    assert parsed.source == "POLICY_DEFAULT"
    assert (parsed.minimum, parsed.maximum) == (1, 3)


def test_unidentified_scenario_uses_registered_proxy_path_instead_of_refusing() -> None:
    plan = compiler().compile(
        "如果美国对中国加征300%关税，会怎样影响美国经济？",
        date(2026, 7, 15),
    )
    assert plan.complexity_class == "STRUCTURAL_SCENARIO"
    scenario = plan.validation["scenario_execution"]
    assert scenario["status"] == "MODEL_CONDITIONAL"
    assert scenario["mapping_ids"] == ["SM.TRADE.TARIFF.V1"]
    assert scenario["conditional_events"]
    assert scenario["dynamic_response_model_count"] >= 1
    assert scenario["requested_shock"] == {
        "value": 300.0,
        "unit": "PERCENT",
        "raw_text": "300%",
        "source": "USER_EXPLICIT",
    }
    assert scenario["event_specific_effect_is_causal"] is False
    assert not any("baseline context only" in item for item in plan.unsupported_aspects)


def test_compiler_builds_allowlisted_open_question_plan() -> None:
    plan = compiler().compile(
        "美国经济当前是在走弱还是重新加速，未来三个月的衰退风险怎么样？",
        date(2026, 7, 13),
    )
    assert plan.workflow_id == "WF.US.ACTIVITY_RISK.V1"
    assert plan.query.horizon.maximum == 3
    assert plan.query.horizon.source == "USER_EXPLICIT"
    assert {model.model_recipe_id for model in plan.models} >= {
        "M.DFM_NOWCAST.V1",
        "M.VAR_SYSTEM.V1",
        "M.GROWTH_AT_RISK.V1",
    }
    assert plan.validation["arbitrary_code_allowed"] is False


def test_unsupported_trade_aspect_is_not_fabricated() -> None:
    plan = compiler().compile("未来六个月关税和进口会如何影响美国经济？", date(2026, 7, 13))
    assert plan.coverage == "PARTIAL"
    assert any("trade" in aspect.lower() for aspect in plan.unsupported_aspects)
    assert all("US.TRADE" != lane.lane_id for lane in plan.lanes)


def test_v2_request_rejects_legacy_horizon_and_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ResearchJobCreate.model_validate({"question": "美国通胀怎么样？", "horizon_months": 3})
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ResearchJobCreate.model_validate({"question": "美国通胀怎么样？", "python": "print(1)"})


def test_concurrent_compiler_traces_are_job_local() -> None:
    shared = compiler()
    questions = [
        "未来三个月美国经济和衰退风险怎么样？",
        "未来两个月美国通胀是否加速？",
    ]

    def compile_and_trace(question: str) -> list[dict]:
        shared.compile(question, date(2026, 7, 13))
        return shared.trace

    expected = []
    for question in questions:
        isolated = compiler()
        isolated.compile(question, date(2026, 7, 13))
        expected.append(isolated.trace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        actual = list(pool.map(compile_and_trace, questions))
    assert [len(trace) for trace in actual] == [len(trace) for trace in expected]
    assert all(sum(item["role"] == "LLM-0 Query Parser" for item in trace) == 1 for trace in actual)


def test_valid_llm_3_4_5_make_constrained_selections() -> None:
    constrained = ResearchCompiler(registry(), ValidSelectorLlm())
    plan = constrained.compile("未来三个月美国经济和衰退风险怎么样？", date(2026, 7, 13))
    roles = constrained.trace
    assert plan.models
    labor_dfm = next(
        model
        for model in plan.models
        if model.node_id == "N.LABOR.STATE" and model.model_recipe_id == "M.DFM_NOWCAST.V1"
    )
    assert len(labor_dfm.factor_ids) >= 3
    assert "F.LABOR.WAGES" in labor_dfm.factor_ids
    assert any(item["role"] == "LLM-3 Node Router" and item["status"] == "SUCCESS" for item in roles)
    assert any(item["role"] == "LLM-4 Factor Selector" and item["status"] == "SUCCESS" for item in roles)
    assert any(item["role"] == "LLM-5 Model Planner" and item["status"] == "SUCCESS" for item in roles)


def test_twice_invalid_llm_output_cannot_delete_registered_complex_research_programme() -> None:
    constrained = ResearchCompiler(registry(), HostileLlm())
    plan = constrained.compile("未来三个月美国经济和衰退风险怎么样？", date(2026, 7, 13))
    assert plan.models
    assert all(model.specification_id for model in plan.models)
    assert plan.coverage == "PARTIAL"
    assert plan.validation["research_depth"]["status"] == "PASS"
    assert any(item["status"] == "FALLBACK_AFTER_REPAIR" and item["detail"].get("nodes_removed") for item in constrained.trace)


def test_frozen_json_schema_accepts_public_request_and_actual_graph() -> None:
    schema = json.loads((ROOT / "schemas" / "research_job.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    validator.validate({"question": "美国经济未来三个月怎么样？", "display_mode": "ACADEMIC"})
    plan = compiler().compile("美国经济未来三个月怎么样？", date(2026, 7, 13))
    graph = GraphBuilder("JOB_SCHEMA_TEST", registry())
    graph.from_plan(plan)
    validator.validate(graph.export())
