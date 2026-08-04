from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np


CONFIDENCE_SCORE = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.35}
CLAIM_BY_RESEARCH_NODE = {
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
    "N.HOUSING.STATE_PANEL_FIXTURE": "C.PANEL.FIXTURE",
}


def forecast_combination(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        result for result in results
        if result.get("status") in {"SUCCESS", "WARNING"}
        and isinstance(result.get("aggregation_input"), dict)
        and result["aggregation_input"].get("point_forecast") is not None
        and result["aggregation_input"].get("oos_loss") not in {None, 0}
    ]
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for result in candidates:
        item = result["aggregation_input"]
        groups[(str(item["target"]), int(item["horizon"]))].append(result)
    combinations = []
    for (target, horizon), group in groups.items():
        if len(group) < 2:
            continue
        inverse_losses = np.array([1 / max(float(item["aggregation_input"]["oos_loss"]), 1e-12) for item in group])
        optimized = inverse_losses / inverse_losses.sum()
        equal = np.full(len(group), 1 / len(group))
        weights = 0.5 * optimized + 0.5 * equal
        point = float(sum(weight * float(item["aggregation_input"]["point_forecast"]) for weight, item in zip(weights, group, strict=True)))
        equal_point = float(np.mean([item["aggregation_input"]["point_forecast"] for item in group]))
        combinations.append({
            "target": target,
            "horizon": horizon,
            "method": "rolling-origin inverse-loss combination with 50% shrinkage toward equal weight",
            "loss_function": "squared error",
            "constraints": ["nonnegative", "sum_to_one", "training_period_only"],
            "weights": [{"node_id": item["node_id"], "model_recipe_id": item["model_recipe_id"], "weight": round(float(weight), 6), "oos_loss": item["aggregation_input"]["oos_loss"]} for weight, item in zip(weights, group, strict=True)],
            "point_forecast": round(point, 6),
            "equal_weight_forecast": round(equal_point, 6),
            "equal_weight_sensitivity": round(point - equal_point, 6),
            "stability": "PROVISIONAL" if len(group) < 3 else "REVIEWED",
        })
    if not combinations:
        return None
    return {"aggregation_id": "A.FORECAST_STACKING.V1", "combinations": combinations}


def _stance(score: float) -> str:
    if score > 0.2:
        return "UPSIDE_OR_ACCELERATION"
    if score < -0.2:
        return "DOWNSIDE_OR_DECELERATION"
    return "MIXED_OR_NEAR_NEUTRAL"


def _conditional_scenario_analysis(
    plan: dict[str, Any],
    results: list[dict[str, Any]],
    claim_summaries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    execution = plan.get("validation", {}).get("scenario_execution", {})
    raw_status = execution.get("status", "NOT_APPLICABLE")
    if raw_status == "NOT_APPLICABLE":
        return None
    # Old persisted plans used BASELINE_ONLY. If one is re-aggregated, migrate
    # it to the new explicit sensitivity contract instead of reviving the
    # product-level refusal that v0.3 removed.
    status = "SENSITIVITY_ENVELOPE" if raw_status == "BASELINE_ONLY" else raw_status
    requested_shock = execution.get("requested_shock")
    registered_shocks = set(execution.get("shock_factor_ids", []))
    response_profiles = []
    for result in results:
        if result.get("status") not in {"SUCCESS", "WARNING"}:
            continue
        scenario_response = result.get("aggregation_input", {}).get("scenario_response")
        if not isinstance(scenario_response, dict):
            continue
        path = scenario_response.get("response_path", [])
        finite_path = [
            item
            for item in path
            if isinstance(item, dict) and isinstance(item.get("effect"), (int, float))
        ]
        profile = {
            "node_id": result.get("node_id"),
            "research_node_id": result.get("research_node_id"),
            "specification_id": result.get("specification_id"),
            "model_recipe_id": result.get("model_recipe_id"),
            "confidence": result.get("confidence", "LOW"),
            **scenario_response,
            "peak_response": max(finite_path, key=lambda item: abs(float(item["effect"]))) if finite_path else None,
            "endpoint_response": finite_path[-1] if finite_path else None,
        }
        observed_scale = scenario_response.get("observed_shock_standard_deviation_pct")
        if (
            isinstance(requested_shock, dict)
            and requested_shock.get("unit") == "PERCENT"
            and scenario_response.get("shock_factor_id") in registered_shocks
            and isinstance(observed_scale, (int, float))
            and abs(float(observed_scale)) > 1e-12
        ):
            scale_multiplier = float(requested_shock["value"]) / float(observed_scale)
            scaled_path = []
            for item in finite_path:
                scaled = dict(item)
                for field in ("effect", "standard_error", "ci_low", "ci_high"):
                    if isinstance(scaled.get(field), (int, float)):
                        scaled[field] = round(float(scaled[field]) * scale_multiplier, 6)
                scaled_path.append(scaled)
            profile["requested_shock_scaling"] = {
                "requested_value": requested_shock["value"],
                "requested_unit": requested_shock["unit"],
                "registered_one_sd_value": round(float(observed_scale), 6),
                "scale_multiplier": round(scale_multiplier, 6),
                "method": "linear rescaling of the registered one-standard-deviation response path",
            }
            profile["scaled_response_path"] = scaled_path
            profile["scaled_peak_response"] = max(
                scaled_path, key=lambda item: abs(float(item["effect"]))
            ) if scaled_path else None
            profile["scaled_endpoint_response"] = scaled_path[-1] if scaled_path else None
        response_profiles.append(profile)
    sensitivity_axes = [
        {
            "claim_id": item["claim_id"],
            "label_zh": item["label_zh"],
            "directional_lean": item["directional_lean"],
            "ordinal_signal": item["ordinal_signal"],
            "model_count": item["model_count"],
        }
        for item in claim_summaries
    ]
    return {
        "status": status,
        "conditional_events": execution.get("conditional_events", []),
        "mapping_ids": execution.get("mapping_ids", []),
        "mapping_tiers": execution.get("mapping_tiers", []),
        "shock_factor_ids": execution.get("shock_factor_ids", []),
        "response_factor_ids": execution.get("response_factor_ids", []),
        "identification_strength": execution.get("identification_strength", []),
        "proxy_assumptions": execution.get("proxy_assumptions", []),
        "requested_shock": requested_shock,
        "interpretation_rule": execution.get("interpretation_rule"),
        "event_specific_effect_is_causal": False,
        "response_profiles": response_profiles,
        "sensitivity_axes": sensitivity_axes,
        "response_profile_count": len(response_profiles),
    }


def heterogeneous_ordinal_synthesis(
    plan: dict[str, Any],
    results: list[dict[str, Any]],
    synthesis_policy: dict[str, Any] | None = None,
    evidence_mappings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    synthesis_policy = synthesis_policy or {
        "policy_id": "SP.LEGACY.NODE_DEFAULT",
        "answer_mode": "MULTI_AXIS",
        "primary_claim_ids": [],
        "contextual_claim_ids": [],
        "claim_presentations": [],
    }
    mapping_by_specification = {
        item["specification_id"]: item for item in (evidence_mappings or [])
    }
    presentations = {
        item["claim_id"]: item for item in synthesis_policy.get("claim_presentations", [])
    }
    primary_claim_ids = list(synthesis_policy.get("primary_claim_ids", []))
    contextual_claim_ids = list(synthesis_policy.get("contextual_claim_ids", []))
    all_successful = [result for result in results if result.get("status") in {"SUCCESS", "WARNING"} and result.get("evidence_type") != "ASSOCIATIONAL_FIXTURE"]
    successful = [result for result in all_successful if result.get("specification_role", "CORE") == "CORE"]
    validation_runs = [result for result in all_successful if result.get("specification_role", "CORE") != "CORE"]
    failed = [result for result in results if result.get("status") not in {"SUCCESS", "WARNING"}]
    node_to_lane = {node["node_id"]: node["lane_id"] for node in plan.get("nodes", [])}
    grouped_by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unmapped = []
    normalized_evidence: list[dict[str, Any]] = []
    for result in successful:
        research_node_id = result.get("research_node_id")
        mapping = mapping_by_specification.get(result.get("specification_id"))
        claim_id = mapping["claim_id"] if mapping else CLAIM_BY_RESEARCH_NODE.get(research_node_id)
        if claim_id is None:
            unmapped.append(result)
            continue
        signal_multiplier = int(mapping.get("signal_multiplier", 1)) if mapping else 1
        normalized = {
            **result,
            "claim_id": claim_id,
            "lane_id": node_to_lane.get(research_node_id, "UNMAPPED"),
            "raw_signal": float(np.clip(result.get("signal", 0.0), -1, 1)),
            "normalized_signal": float(np.clip(result.get("signal", 0.0) * signal_multiplier, -1, 1)),
            "signal_multiplier": signal_multiplier,
            "evidence_mapping_id": mapping.get("mapping_id") if mapping else None,
            "mapping_status": "REGISTERED_SPECIFICATION" if mapping else "LEGACY_NODE_DEFAULT",
            "positive_meaning": mapping.get("positive_meaning") if mapping else None,
            "negative_meaning": mapping.get("negative_meaning") if mapping else None,
        }
        normalized_evidence.append(normalized)
        grouped_by_claim[claim_id].append(normalized)

    contributions = []
    claim_summaries = []
    for claim_id, group in grouped_by_claim.items():
        qualities = np.array([CONFIDENCE_SCORE.get(item.get("confidence", "LOW"), 0.35) for item in group], dtype=float)
        within_claim_weights = qualities / qualities.sum()
        signals = np.array([item["normalized_signal"] for item in group])
        claim_signal = float(np.dot(within_claim_weights, signals))
        claim_quality = float(np.mean(qualities))
        presentation = presentations.get(claim_id, {})
        if claim_signal > 0:
            lean = "POSITIVE"
            phrase = presentation.get("positive_zh", "正向")
        elif claim_signal < 0:
            lean = "NEGATIVE"
            phrase = presentation.get("negative_zh", "负向")
        else:
            lean = "BALANCED"
            phrase = presentation.get("balanced_zh", "接近平衡")
        role = "PRIMARY" if claim_id in primary_claim_ids else "CONTEXTUAL" if claim_id in contextual_claim_ids else "UNSPECIFIED"
        strength_zh = "方向较明确" if abs(claim_signal) > 0.2 else "仅为弱倾向"
        label_zh = presentation.get("label_zh", claim_id)
        claim_summaries.append({
            "claim_id": claim_id,
            "lane_ids": sorted({item["lane_id"] for item in group}),
            "role": role,
            "label_zh": label_zh,
            "ordinal_signal": round(claim_signal, 4),
            "directional_lean": lean,
            "decisiveness": "DIRECTIONAL" if abs(claim_signal) > 0.2 else "WEAK_OR_BALANCED",
            "finding_zh": f"{label_zh}：{phrase}（{strength_zh}，序数信号 {claim_signal:+.4f}）",
            "diagnostic_quality": round(claim_quality, 4),
            "model_count": len(group),
            "source_node_ids": [item["node_id"] for item in group],
            "within_claim_method": "registered diagnostic-tier normalization",
        })
        for weight, score, item, quality in zip(within_claim_weights, signals, group, qualities, strict=True):
            contributions.append({
                "node_id": item["node_id"],
                "research_node_id": item.get("research_node_id"),
                "claim_id": claim_id,
                "lane_id": item["lane_id"],
                "model_recipe_id": item["model_recipe_id"],
                "evidence_type": item["evidence_type"],
                "direction": item["direction"],
                "raw_ordinal_signal": round(item["raw_signal"], 4),
                "ordinal_signal": round(float(score), 4),
                "signal_multiplier": item["signal_multiplier"],
                "evidence_mapping_id": item["evidence_mapping_id"],
                "mapping_status": item["mapping_status"],
                "positive_meaning": item["positive_meaning"],
                "negative_meaning": item["negative_meaning"],
                "diagnostic_quality_tier": item.get("confidence", "LOW"),
                "quality_multiplier": float(quality),
                "within_claim_weight": round(float(weight), 6),
                "note": "Models are normalized within a registered intermediate claim before lane synthesis.",
            })

    grouped_by_lane: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for item in normalized_evidence:
        grouped_by_lane[item["lane_id"]][item["claim_id"]].append(item)
    lane_summaries = []
    for lane_id, claim_groups in grouped_by_lane.items():
        # Claims are distinct registered propositions. Equal weighting inside a
        # lane prevents another model or duplicate node from buying influence.
        lane_claim_signals = []
        for group in claim_groups.values():
            qualities = np.array([CONFIDENCE_SCORE.get(item.get("confidence", "LOW"), 0.35) for item in group], dtype=float)
            weights = qualities / qualities.sum()
            lane_claim_signals.append(float(np.dot(weights, [item["normalized_signal"] for item in group])))
        lane_signal = float(np.mean(lane_claim_signals))
        lane_summaries.append({"lane_id": lane_id, "ordinal_signal": round(lane_signal, 4), "claim_count": len(claim_groups), "within_lane_method": "equal registered claims"})
    # Lanes are likewise equal at the final ordinal stage. This is a transparent
    # policy synthesis, not a statistical estimate or learned probability.
    system_balance = float(np.mean([lane["ordinal_signal"] for lane in lane_summaries])) if lane_summaries else 0.0
    claim_by_id = {item["claim_id"]: item for item in claim_summaries}
    ordered_claims = [claim_by_id[claim_id] for claim_id in primary_claim_ids if claim_id in claim_by_id]
    primary_score = float(np.mean([item["ordinal_signal"] for item in ordered_claims])) if ordered_claims else None
    answer_mode = synthesis_policy.get("answer_mode", "MULTI_AXIS")
    scenario_analysis = _conditional_scenario_analysis(plan, results, claim_summaries)
    if scenario_analysis is not None and (contributions or scenario_analysis["response_profiles"]):
        stance = "CONDITIONAL_SCENARIO_EVIDENCE"
        answerability = "ANSWERABLE"
        evidence_state = "CONDITIONAL_SCENARIO"
    elif not contributions:
        stance = "UNSUPPORTED"
        answerability = "UNSUPPORTED"
        evidence_state = "NO_EXECUTABLE_EVIDENCE"
    elif answer_mode == "MULTI_AXIS":
        stance = "MULTI_AXIS_EVIDENCE"
        answerability = "ANSWERABLE"
        evidence_state = "MIXED" if len({item["directional_lean"] for item in claim_summaries}) > 1 else "DIRECTIONAL"
    elif primary_score is None:
        stance = "NO_PRIMARY_EVIDENCE"
        answerability = "CONDITIONAL"
        evidence_state = "CONTEXT_ONLY"
    else:
        stance = _stance(primary_score)
        answerability = "ANSWERABLE"
        evidence_state = "MIXED" if stance == "MIXED_OR_NEAR_NEUTRAL" else "DIRECTIONAL"
    completed = len(all_successful)
    planned = max(1, len(results))
    execution_coverage = completed / planned
    compiler_coverage = float(plan.get("coverage_score", 0))
    coverage_score = round(compiler_coverage * execution_coverage, 4)
    if coverage_score >= 0.85 and failed == []:
        coverage = "FULL"
    elif coverage_score > 0:
        coverage = "PARTIAL"
    else:
        coverage = "UNSUPPORTED"
    # High coverage is not the same thing as high evidential confidence.  A
    # synthesis can only inherit HIGH when every contributing model earned it.
    confidence = "HIGH" if coverage_score >= 0.85 and successful and all(item.get("confidence") == "HIGH" for item in successful) else "MEDIUM" if coverage_score >= 0.55 else "LOW"
    return {
        "aggregation_id": "A.HETEROGENEOUS_ORDINAL.V1",
        "synthesis_policy_id": synthesis_policy.get("policy_id"),
        "answer_mode": answer_mode,
        "method": "registered polarity normalization, claim-first synthesis, target-aware primary claims; equal-lane score retained as a secondary system-balance audit",
        "stance": stance,
        "ordinal_score": round(primary_score if primary_score is not None else system_balance, 4),
        "primary_score": round(primary_score, 4) if primary_score is not None else None,
        "system_balance_score": round(system_balance, 4),
        "answerability": answerability,
        "evidence_state": evidence_state,
        "confidence": confidence,
        "coverage": coverage,
        "coverage_score": coverage_score,
        "probability_output_allowed": False,
        "contributions": contributions,
        "claim_summaries": claim_summaries,
        "primary_findings": ordered_claims,
        "context_findings": [claim_by_id[claim_id] for claim_id in contextual_claim_ids if claim_id in claim_by_id],
        "lane_summaries": lane_summaries,
        "unmapped_evidence": [{"node_id": item.get("node_id"), "research_node_id": item.get("research_node_id")} for item in unmapped],
        "validation_runs": [{"node_id": item.get("node_id"), "specification_id": item.get("specification_id"), "role": item.get("specification_role"), "status": item.get("status"), "confidence": item.get("confidence")} for item in validation_runs],
        "conflicts_retained": len({1 if item["ordinal_signal"] > 0 else -1 if item["ordinal_signal"] < 0 else 0 for item in claim_summaries}) > 1,
        "failed_nodes": [{"node_id": result.get("node_id"), "reason": result.get("error", "execution failed")} for result in failed] + [{"node_id": item.get("node_id"), "reason": "No registered claim mapping"} for item in unmapped],
        "scenario_analysis": scenario_analysis,
    }


def synthesize(
    plan: dict[str, Any],
    results: list[dict[str, Any]],
    synthesis_policy: dict[str, Any] | None = None,
    evidence_mappings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if plan["workflow_id"] == "WF.US.PANEL_FIXTURE.V1":
        fixture = next((result for result in results if result.get("status") == "SUCCESS"), None)
        return {
            "aggregation_id": "A.NO_CROSS_LANE_FIXTURE.V1",
            "method": "no cross-lane synthesis",
            "stance": fixture.get("direction", "UNSUPPORTED") if fixture else "UNSUPPORTED",
            "ordinal_score": 0,
            "confidence": "LOW",
            "coverage": "PARTIAL" if fixture else "UNSUPPORTED",
            "coverage_score": 0.5 if fixture else 0,
            "probability_output_allowed": False,
            "answerability": "ANSWERABLE" if fixture else "UNSUPPORTED",
            "evidence_state": "ASSOCIATIONAL_ONLY" if fixture else "NO_EXECUTABLE_EVIDENCE",
            "primary_findings": [],
            "context_findings": [],
            "contributions": [],
            "conflicts_retained": False,
            "failed_nodes": [],
        }
    result = heterogeneous_ordinal_synthesis(plan, results, synthesis_policy, evidence_mappings)
    result["forecast_combination"] = forecast_combination(results)
    depth = plan.get("validation", {}).get("research_depth", {})
    identification_required = bool(depth.get("identification_required"))
    identification_active = bool(depth.get("identification_active"))
    if plan.get("complexity_class") == "CAUSAL_ATTRIBUTION" and not identification_active:
        # Lack of an identification design limits causal language; it does not
        # erase a legal directional synthesis produced by registered models.
        result["causal_status"] = (
            "UNSUPPORTED_CAUSAL" if identification_required else "DIRECTIONAL_ASSOCIATION_ONLY"
        )
        if result.get("answerability") != "UNSUPPORTED":
            result["answerability"] = "CONDITIONAL"
            result["evidence_state"] = "ASSOCIATIONAL_ONLY"
        if identification_required:
            result["coverage"] = "UNSUPPORTED"
        result["probability_output_allowed"] = False
    return result
