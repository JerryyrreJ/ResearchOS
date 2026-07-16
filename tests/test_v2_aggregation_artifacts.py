from __future__ import annotations

import json
from pathlib import Path

from backend.app.aggregation import forecast_combination, heterogeneous_ordinal_synthesis
from backend.app.artifacts import ArtifactStore, table_to_csv, table_to_html, table_to_latex
from backend.app.engine import conclusion_headline
from backend.app.registry import RegistryStore


ROOT = Path(__file__).resolve().parents[1]


def sample_result(node_id: str, forecast: float, loss: float, signal: float = 0.2) -> dict:
    return {
        "status": "SUCCESS",
        "node_id": node_id,
        "research_node_id": "N.ACTIVITY.NOWCAST" if node_id == "N1" else "N.ACTIVITY.TAIL_RISK",
        "model_recipe_id": "M.TEST",
        "evidence_type": "PREDICTIVE",
        "direction": "UP" if signal > 0 else "DOWN",
        "signal": signal,
        "confidence": "MEDIUM",
        "aggregation_input": {
            "target": "F.TEST",
            "horizon": 3,
            "point_forecast": forecast,
            "oos_loss": loss,
            "baseline_oos_loss": 4.0,
        },
    }


def sample_table() -> dict:
    coefficient = {
        "variable_id": "x",
        "label": "Registered factor X",
        "coefficient": 0.5,
        "standard_error": 0.1,
        "p_value": 0.002,
        "ci_low": 0.304,
        "ci_high": 0.696,
        "stars": "***",
    }
    return {
        "table_id": "T.TEST",
        "title": "Test regression",
        "dependent_variable": "y",
        "columns": ["(1)", "(2)"],
        "coefficients": {"(1)": [coefficient], "(2)": [{**coefficient, "coefficient": 0.4}]},
        "statistics": {"Observations": [100, 100], "R-squared": [0.4, 0.5]},
        "notes": ["Clustered standard errors.", "*** p<0.01."],
    }


def test_display_headline_uses_findings_instead_of_a_limitation() -> None:
    findings = [
        {"finding_zh": "实体活动方向：偏向重新加速（方向较明确，序数信号 +0.2910）"},
        {"finding_zh": "增长下行风险：偏向升高（仅为弱倾向，序数信号 -0.1738）"},
    ]
    assert conclusion_headline(findings, "当前只能回答基线宏观状态") == (
        "实体活动偏向重新加速；增长下行风险偏向升高"
    )


def test_forecast_combination_weights_are_constrained_and_shrunk() -> None:
    aggregation = forecast_combination([sample_result("N1", 1.0, 1.0), sample_result("N2", 3.0, 4.0)])
    assert aggregation is not None
    combination = aggregation["combinations"][0]
    weights = [item["weight"] for item in combination["weights"]]
    assert all(weight >= 0 for weight in weights)
    assert abs(sum(weights) - 1) < 1e-6
    assert 1.0 < combination["point_forecast"] < combination["equal_weight_forecast"]


def test_heterogeneous_evidence_never_outputs_uncalibrated_probability() -> None:
    plan = {"coverage_score": 1.0, "nodes": [{"node_id": "N.ACTIVITY.NOWCAST", "lane_id": "US.ACTIVITY"}, {"node_id": "N.ACTIVITY.TAIL_RISK", "lane_id": "US.ACTIVITY"}]}
    output = heterogeneous_ordinal_synthesis(plan, [sample_result("N1", 1.0, 1.0), sample_result("N2", -1.0, 1.2, -0.2)])
    assert output["probability_output_allowed"] is False
    assert output["conflicts_retained"] is True
    assert all("quality_multiplier" in contribution for contribution in output["contributions"])


def test_registered_polarity_and_primary_claims_prevent_false_neutrality() -> None:
    registry = RegistryStore(ROOT / "registry" / "v2")
    policy = next(
        item for item in registry.all("synthesis_policies")
        if item["workflow_id"] == "WF.US.ACTIVITY_RISK.V1"
    )
    plan = {
        "workflow_id": "WF.US.ACTIVITY_RISK.V1",
        "coverage_score": 1.0,
        "validation": {"scenario_execution": {"status": "NOT_APPLICABLE"}},
        "nodes": [
            {"node_id": "N.ACTIVITY.PRODUCTION", "lane_id": "US.ACTIVITY"},
            {"node_id": "N.LABOR.STATE", "lane_id": "US.LABOR"},
        ],
    }
    activity = {
        "status": "SUCCESS", "node_id": "MR.ACT", "research_node_id": "N.ACTIVITY.PRODUCTION",
        "model_recipe_id": "M.UNIVARIATE_AR.V1", "specification_id": "MS.ACT.PRODUCTION.AR_INDPRO.V1",
        "specification_role": "CORE", "evidence_type": "PREDICTIVE", "direction": "UP",
        "signal": 0.4, "confidence": "MEDIUM",
    }
    unemployment = {
        "status": "SUCCESS", "node_id": "MR.LAB", "research_node_id": "N.LABOR.STATE",
        "model_recipe_id": "M.VAR_SYSTEM.V1", "specification_id": "MS.LABOR.STATE.VAR.V1",
        "specification_role": "CORE", "evidence_type": "PREDICTIVE", "direction": "UP",
        "signal": 0.9, "confidence": "MEDIUM",
    }
    output = heterogeneous_ordinal_synthesis(
        plan, [activity, unemployment], policy, registry.all("evidence_mappings")
    )
    assert output["stance"] == "UPSIDE_OR_ACCELERATION"
    assert output["primary_score"] == 0.4
    assert output["system_balance_score"] == -0.25
    labor = next(item for item in output["claim_summaries"] if item["claim_id"] == "C.LABOR.STATE")
    assert labor["ordinal_signal"] == -0.9
    assert output["answerability"] == "ANSWERABLE"


def test_scenario_proxy_results_are_answerable_without_causal_overclaim() -> None:
    registry = RegistryStore(ROOT / "registry" / "v2")
    policy = next(
        item for item in registry.all("synthesis_policies")
        if item["workflow_id"] == "WF.US.ACTIVITY_RISK.V1"
    )
    plan = {
        "workflow_id": "WF.US.ACTIVITY_RISK.V1",
        "coverage_score": 0.8,
        "validation": {"scenario_execution": {
            "status": "MODEL_CONDITIONAL",
            "conditional_events": ["If tariffs rise"],
            "mapping_ids": ["SM.TRADE.TARIFF.V1"],
            "mapping_tiers": ["TRANSMISSION_PROXY"],
            "shock_factor_ids": ["F.ACTIVITY.INDPRO"],
            "response_factor_ids": ["F.LABOR.UNEMPLOYMENT"],
            "identification_strength": ["PROXY_SENSITIVITY"],
            "proxy_assumptions": ["Tariffs are represented by an activity innovation."],
            "requested_shock": {"value": 20.0, "unit": "PERCENT", "raw_text": "20%", "source": "USER_EXPLICIT"},
            "interpretation_rule": "Conditional proxy only.",
        }},
        "nodes": [{"node_id": "N.ACTIVITY.PRODUCTION", "lane_id": "US.ACTIVITY"}],
    }
    result = {
        "status": "SUCCESS", "node_id": "MR.ACT", "research_node_id": "N.ACTIVITY.PRODUCTION",
        "model_recipe_id": "M.UNIVARIATE_AR.V1", "specification_id": "MS.ACT.PRODUCTION.AR_INDPRO.V1",
        "specification_role": "CORE", "evidence_type": "PREDICTIVE", "direction": "UP",
        "signal": 0.4, "confidence": "MEDIUM",
        "aggregation_input": {"scenario_response": {
            "response_factor_id": "F.LABOR.UNEMPLOYMENT",
            "shock_factor_id": "F.ACTIVITY.INDPRO",
            "shock_definition": "one-standard-deviation registered innovation",
            "observed_shock_standard_deviation_pct": 10.0,
            "identification_strength": "STRUCTURAL_PROXY",
            "response_horizon": 3,
            "response_path": [
                {"horizon": 0, "effect": 0.1},
                {"horizon": 1, "effect": 0.3},
                {"horizon": 2, "effect": 0.2},
            ],
            "interpretation": "Conditional response, not causal.",
        }},
    }
    output = heterogeneous_ordinal_synthesis(plan, [result], policy, registry.all("evidence_mappings"))
    assert output["stance"] == "CONDITIONAL_SCENARIO_EVIDENCE"
    assert output["evidence_state"] == "CONDITIONAL_SCENARIO"
    assert output["answerability"] == "ANSWERABLE"
    assert output["scenario_analysis"]["response_profile_count"] == 1
    assert output["scenario_analysis"]["event_specific_effect_is_causal"] is False
    profile = output["scenario_analysis"]["response_profiles"][0]
    assert profile["requested_shock_scaling"]["scale_multiplier"] == 2.0
    assert profile["scaled_peak_response"]["effect"] == 0.6


def test_academic_table_exports_csv_html_latex_and_hashes(tmp_path) -> None:
    table = sample_table()
    assert "p_value" in table_to_csv(table)
    assert "border-top:2px" in table_to_html(table)
    assert "\\toprule" in table_to_latex(table)
    result = {
        "title": "Test model",
        "table": table,
        "charts": [{"chart_id": "C1", "title": "Chart", "kind": "line", "series": []}],
    }
    artifacts = ArtifactStore(tmp_path).save_model_result("JOB_TEST", "NODE_TEST", result)
    assert {artifact["artifact_type"] for artifact in artifacts} == {"JSON", "CSV", "HTML", "LATEX", "CHART"}
    assert all(len(artifact["sha256"]) == 64 for artifact in artifacts)
    json_path = tmp_path / next(item["relative_path"] for item in artifacts if item["artifact_type"] == "JSON")
    assert json.loads(json_path.read_text(encoding="utf-8"))["title"] == "Test model"
