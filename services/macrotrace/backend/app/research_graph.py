from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .node_explanations import ensure_fixed_explanation
from .registry import RegistryStore
from .schemas import ResearchPlan


class GraphBuilder:
    def __init__(self, job_id: str, registry: RegistryStore) -> None:
        self.job_id = job_id
        self.registry = registry
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[str, dict[str, Any]] = {}

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        *,
        status: str = "PENDING",
        lane_id: str | None = None,
        role: str | None = None,
        summary: str | None = None,
        detail_endpoint: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if detail_endpoint is None:
            detail_endpoint = f"/v1/research-jobs/{self.job_id}/nodes/{node_id}"
        self.nodes[node_id] = {
            "node_id": node_id,
            "node_type": node_type,
            "label": label,
            "status": status,
            "lane_id": lane_id,
            "role": role,
            "summary": summary,
            "detail_endpoint": detail_endpoint,
            "metadata": metadata or {},
        }
        return node_id

    def add_edge(self, source: str, target: str, relation: str) -> None:
        edge_id = f"E{len(self.edges) + 1:04d}"
        self.edges[edge_id] = {"edge_id": edge_id, "source": source, "target": target, "relation": relation}

    def set_status(self, node_id: str, status: str, summary: str | None = None) -> None:
        if node_id not in self.nodes:
            return
        self.nodes[node_id]["status"] = status
        if summary is not None:
            self.nodes[node_id]["summary"] = summary

    def from_plan(self, plan: ResearchPlan) -> None:
        question_id = self.add_node("QUESTION", "QUESTION", plan.query.question, status="SUCCESS", summary="Natural-language research question")
        query_id = self.add_node(
            "QUERY",
            "QUERY",
            f"{plan.query.question_form} · {plan.query.horizon.minimum}-{plan.query.horizon.maximum} {plan.query.horizon.unit.lower()}",
            status="SUCCESS",
            summary=f"Horizon source: {plan.query.horizon.source}",
            metadata=plan.query.model_dump(mode="json"),
        )
        self.add_edge(question_id, query_id, "PARSES_TO")
        depth = plan.validation.get("research_depth", {})
        depth_status = "SUCCESS" if depth.get("status") == "PASS" else "WARNING" if depth.get("status") == "FAIL" else "SKIPPED"
        depth_id = self.add_node(
            "RESEARCH_DEPTH_GATE",
            "RESEARCH_DEPTH_GATE",
            f"{plan.complexity_class} empirical completeness gate",
            status=depth_status,
            summary=f"{depth.get('planned_specifications', 0)} planned / {depth.get('executable_specifications', 0)} executable / {depth.get('blocked_specifications', 0)} blocked",
            metadata=depth,
        )
        self.add_edge(query_id, depth_id, "DIAGNOSES")

        # Build the complete data universe before routing.  This lets the UI
        # render Part A as a persistent grey evidence layer and then light up
        # only the datasets actually selected by the empirical compiler.
        for dataset in self.registry.all("datasets"):
            dataset_status = "BLOCKED" if dataset.get("status") == "blocked" else "NOT_ROUTED"
            self.add_node(
                f"DATASET::{dataset['dataset_id']}",
                "DATASET",
                dataset["source"],
                status=dataset_status,
                summary=dataset["dataset_id"],
                metadata={**dataset, "routed": False},
            )

        routed_lanes = {lane.lane_id: lane for lane in plan.lanes}
        mechanism_counts: dict[str, int] = {}
        selected_mechanism_counts: dict[str, int] = {}
        factor_counts: dict[str, int] = {}
        specification_counts: dict[str, int] = {}
        for mechanism in self.registry.all("mechanisms"):
            mechanism_counts[mechanism["lane_id"]] = mechanism_counts.get(mechanism["lane_id"], 0) + 1
        for mechanism in plan.mechanisms:
            selected_mechanism_counts[mechanism.lane_id] = selected_mechanism_counts.get(mechanism.lane_id, 0) + 1
        for factor in self.registry.all("factors"):
            factor_counts[factor["lane_id"]] = factor_counts.get(factor["lane_id"], 0) + 1
        for specification in self.registry.all("model_specifications"):
            specification_counts[specification["lane_id"]] = specification_counts.get(specification["lane_id"], 0) + 1

        for lane_item in self.registry.all("lanes"):
            lane_id = lane_item["lane_id"]
            selected = routed_lanes.get(lane_id)
            lane_node_id = f"LANE::{lane_id}"
            self.add_node(
                lane_node_id,
                "LANE",
                lane_item["name"],
                status="PENDING" if selected else "NOT_ROUTED",
                lane_id=lane_id,
                role=selected.priority if selected else "NOT_ROUTED",
                summary=selected.reason if selected else "Registered lane not routed for this question.",
                metadata={
                    **lane_item,
                    "routed": selected is not None,
                    "universe_counts": {
                        "mechanisms": mechanism_counts.get(lane_id, 0),
                        "factors": factor_counts.get(lane_id, 0),
                        "model_specifications": specification_counts.get(lane_id, 0),
                    },
                    "selected_mechanisms": selected_mechanism_counts.get(lane_id, 0),
                },
            )
            self.add_edge(query_id, lane_node_id, "ROUTES_TO")

        routed_mechanisms = {mechanism.mechanism_id: mechanism for mechanism in plan.mechanisms}
        for item in self.registry.all("mechanisms"):
            decision = routed_mechanisms.get(item["mechanism_id"])
            if decision is None:
                status = "NOT_ROUTED"
            elif item.get("status") == "blocked":
                status = "BLOCKED"
            else:
                status = "PLANNED"
            mechanism_id = f"MECHANISM::{item['mechanism_id']}"
            related_specs = [spec for spec in self.registry.all("model_specifications") if spec["mechanism_id"] == item["mechanism_id"]]
            self.add_node(
                mechanism_id,
                "MECHANISM",
                item["name"],
                status=status,
                lane_id=item["lane_id"],
                role=decision.role if decision else "NOT_ROUTED",
                summary=item["hypothesis"],
                metadata={
                    **item,
                    "factor_count": len(item.get("factor_pool", [])),
                    "model_specification_count": len(related_specs),
                    "active_specification_count": sum(spec.get("execution_status") == "ACTIVE" for spec in related_specs),
                    "blocked_specification_count": sum(spec.get("execution_status") == "BLOCKED" for spec in related_specs),
                },
            )
            self.add_edge(f"LANE::{item['lane_id']}", mechanism_id, "DECOMPOSES_TO")

        factor_instances: dict[tuple[str, str], str] = {}
        for decision in plan.nodes:
            item = self.registry.get("nodes", decision.node_id)
            research_id = f"RN::{decision.node_id}"
            node_status = "BLOCKED" if item.get("status") == "blocked" else "PLANNED"
            self.add_node(research_id, "RESEARCH_NODE", decision.node_id, status=node_status, lane_id=decision.lane_id, summary=item["purpose"], metadata={**item, "intermediate_claim": item["intermediate_claim"]})
            mechanism_id = item.get("mechanism_id")
            self.add_edge(f"MECHANISM::{mechanism_id}" if mechanism_id else f"LANE::{decision.lane_id}", research_id, "DECOMPOSES_TO")
            claim_id = f"CLAIM::{decision.node_id}"
            self.add_node(claim_id, "CLAIM", item["intermediate_claim"], status=node_status, lane_id=decision.lane_id, metadata={"research_node_id": decision.node_id, "estimand_boundary": "Only registered evidence types may support this intermediate claim."})
            self.add_edge(research_id, claim_id, "ESTIMATES")
            for upstream in decision.depends_on:
                self.add_edge(f"RN::{upstream}", research_id, "ROUTES_TO")

        # Keep the complete registered research-node universe visible. Nodes
        # selected for this question light up above; valid but unused nodes stay
        # grey, while unavailable designs remain explicitly blocked. This is
        # essential to the white-box contract: absence from the active route
        # must not look like absence from the research system.
        selected_research_node_ids = {decision.node_id for decision in plan.nodes}
        for item in self.registry.all("nodes"):
            if item["node_id"] in selected_research_node_ids:
                continue
            research_id = f"RN::{item['node_id']}"
            node_status = "BLOCKED" if item.get("status") == "blocked" else "NOT_ROUTED"
            self.add_node(
                research_id,
                "RESEARCH_NODE",
                item["node_id"],
                status=node_status,
                lane_id=item["lane_id"],
                role="NOT_ROUTED",
                summary=item["purpose"],
                metadata={**item, "intermediate_claim": item["intermediate_claim"], "routed": False},
            )
            mechanism_id = item.get("mechanism_id")
            self.add_edge(
                f"MECHANISM::{mechanism_id}" if mechanism_id else f"LANE::{item['lane_id']}",
                research_id,
                "DECOMPOSES_TO",
            )
            claim_id = f"CLAIM::{item['node_id']}"
            self.add_node(
                claim_id,
                "CLAIM",
                item["intermediate_claim"],
                status=node_status,
                lane_id=item["lane_id"],
                role="NOT_ROUTED",
                metadata={"research_node_id": item["node_id"], "routed": False},
            )
            self.add_edge(research_id, claim_id, "ESTIMATES")
            for upstream in item.get("allowed_upstream", []):
                self.add_edge(f"RN::{upstream}", research_id, "ROUTES_TO")
        for factor in plan.factors:
            item = self.registry.get("factors", factor.factor_id)
            factor_node_id = f"FACTOR::{factor.node_id}::{factor.factor_id}"
            factor_instances[(factor.node_id, factor.factor_id)] = factor_node_id
            factor_status = "BLOCKED" if item.get("status") == "blocked" else "PLANNED"
            self.add_node(factor_node_id, "FACTOR", item["definition"], status=factor_status, lane_id=item["lane_id"], role=factor.role, summary=factor.reason, metadata=item)
            self.add_edge(f"RN::{factor.node_id}", factor_node_id, "USES")
            dataset_id = f"DATASET::{item['dataset_id']}"
            if dataset_id not in self.nodes:
                dataset = self.registry.get("datasets", item["dataset_id"])
                dataset_status = "BLOCKED" if dataset.get("status") == "blocked" else "PLANNED"
                self.add_node(dataset_id, "DATASET", dataset["source"], status=dataset_status, summary=item["dataset_id"], metadata=dataset)
            elif self.nodes[dataset_id]["status"] != "BLOCKED":
                self.set_status(dataset_id, "PLANNED", item["dataset_id"])
                self.nodes[dataset_id]["metadata"]["routed"] = True
            self.add_edge(dataset_id, factor_node_id, "USES")
            transform_id = f"TRANSFORM::{factor.node_id}::{factor.factor_id}"
            self.add_node(transform_id, "TRANSFORM", "Registered stationary transform", status=factor_status, lane_id=item["lane_id"], metadata={"factor_id": factor.factor_id, "allowed_transforms": item["transform_pool"], "selection_policy": "Model recipe chooses only from this allow-list."})
            self.add_edge(factor_node_id, transform_id, "TRANSFORMS_TO")

        selected_factor_ids = {factor.factor_id for factor in plan.factors}
        mechanism_by_factor: dict[str, str] = {}
        for mechanism in self.registry.all("mechanisms"):
            for factor_id in mechanism.get("factor_pool", []):
                mechanism_by_factor.setdefault(factor_id, mechanism["mechanism_id"])
        for item in self.registry.all("factors"):
            if item["factor_id"] in selected_factor_ids:
                continue
            factor_node_id = f"FACTOR::UNIVERSE::{item['factor_id']}"
            self.add_node(factor_node_id, "FACTOR", item["definition"], status="NOT_ROUTED", lane_id=item["lane_id"], role="NOT_ROUTED", summary="Registered factor not selected for this question.", metadata=item)
            dataset_id = f"DATASET::{item['dataset_id']}"
            if dataset_id in self.nodes:
                self.add_edge(dataset_id, factor_node_id, "USES")
            mechanism_id = mechanism_by_factor.get(item["factor_id"])
            self.add_edge(f"MECHANISM::{mechanism_id}" if mechanism_id else f"LANE::{item['lane_id']}", factor_node_id, "USES")

        selected_specs = {item.specification_id: item for item in plan.model_specifications}
        selected_research_nodes = {node.node_id for node in plan.nodes}
        for item in self.registry.all("model_specifications"):
            decision = selected_specs.get(item["specification_id"])
            if decision is None:
                status = "NOT_ROUTED"
            elif decision.execution_status == "BLOCKED":
                status = "BLOCKED"
            else:
                status = "PLANNED"
            spec_node_id = f"MODEL_SPEC::{item['specification_id']}"
            recipe = self.registry.get("models", item["model_recipe_id"]) if item.get("model_recipe_id") else None
            self.add_node(
                spec_node_id,
                "MODEL_SPECIFICATION",
                recipe["method"] if recipe else item["specification_id"],
                status=status,
                lane_id=item["lane_id"],
                role=item["role"],
                summary=item.get("blocked_reason") or f"Pre-registered {item['role'].lower()} specification.",
                metadata={
                    **item,
                    "method": recipe.get("method") if recipe else "Identification design not yet activated",
                    "diagnostic_suite": recipe.get("diagnostic_suite", []) if recipe else [],
                    "failure_conditions": recipe.get("failure_conditions", []) if recipe else [],
                    "code_artifact": recipe.get("artifact") if recipe else None,
                },
            )
            if item["node_id"] in selected_research_nodes:
                self.add_edge(f"RN::{item['node_id']}", spec_node_id, "ESTIMATES")
            else:
                self.add_edge(f"MECHANISM::{item['mechanism_id']}", spec_node_id, "ESTIMATES")

        for index, model in enumerate(plan.models, start=1):
            model_run_id = self.model_run_id(index, model.node_id, model.model_recipe_id)
            recipe = self.registry.get("models", model.model_recipe_id)
            self.add_node(
                model_run_id,
                "MODEL_RUN",
                recipe["method"],
                status="PENDING",
                lane_id=self.registry.get("nodes", model.node_id)["lane_id"],
                summary=model.reason,
                detail_endpoint=f"/v1/research-jobs/{self.job_id}/nodes/{model_run_id}",
                metadata={"research_node_id": model.node_id, "factor_ids": model.factor_ids, "specification_id": model.specification_id, "specification_role": model.role, "model_recipe_id": model.model_recipe_id, "parameters": model.parameters.model_dump(mode="json"), "evidence_type": recipe["evidence_type"], "report_ids": recipe["report_ids"], "diagnostic_suite": recipe["diagnostic_suite"], "failure_conditions": recipe["failure_conditions"]},
            )
            self.add_edge(f"MODEL_SPEC::{model.specification_id}" if model.specification_id else f"RN::{model.node_id}", model_run_id, "ESTIMATES")
            for factor_id in model.factor_ids:
                instance = factor_instances.get((model.node_id, factor_id))
                if instance:
                    self.add_edge(f"TRANSFORM::{model.node_id}::{factor_id}", model_run_id, "USES")

    def generic_details(self) -> dict[str, dict[str, Any]]:
        details: dict[str, dict[str, Any]] = {}
        research_question = str(self.nodes.get("QUESTION", {}).get("label") or "").strip()
        for node_id, node in self.nodes.items():
            metadata = node.get("metadata", {})
            report_ids = metadata.get("report_ids", [])
            report_evidence = metadata.get("report_evidence", {})
            provenance = []
            for report_id in report_ids:
                try:
                    report = self.registry.get("reports", report_id)
                except Exception:
                    continue
                provenance.append({"report_id": report_id, "title": report["title"], "pages": report_evidence.get(report_id, [])})
            detail = {
                "status": node["status"],
                "node_id": node_id,
                "node_type": node["node_type"],
                "title": node["label"],
                "summary": node.get("summary"),
                "research_question": research_question,
                "overview": {
                    "lane_id": node.get("lane_id"),
                    "role": node.get("role"),
                    "status": node["status"],
                    "research_question": research_question,
                    "upstream": [edge["source"] for edge in self.edges.values() if edge["target"] == node_id],
                    "downstream": [edge["target"] for edge in self.edges.values() if edge["source"] == node_id],
                },
                "specification": {
                    "hypothesis": metadata.get("hypothesis"),
                    "intermediate_claim": metadata.get("intermediate_claim"),
                    "method": metadata.get("method"),
                    "parameters": metadata.get("parameters", {}),
                    "factor_ids": metadata.get("factor_ids", []),
                    "estimand": metadata.get("estimand"),
                    "dependent_variable": metadata.get("dependent_variable"),
                    "independent_variables": metadata.get("independent_variables", []),
                    "controls": metadata.get("controls", []),
                    "causal_interpretation_allowed": metadata.get("causal_interpretation_allowed", False),
                    "estimand_boundary": metadata.get("estimand_boundary"),
                },
                "variables": [metadata] if node["node_type"] == "FACTOR" else [],
                "results": {"execution_status": node["status"], "note": "Detailed numeric results appear only after a registered Python model run."},
                "diagnostics": metadata.get("items", metadata.get("diagnostic_suite", [])),
                "robustness": {"failure_conditions": metadata.get("failure_conditions", []), "blocked_reason": metadata.get("blocked_reason")},
                "provenance": {"registry_metadata": metadata, "report_evidence": provenance},
            }
            details[node_id] = ensure_fixed_explanation(detail, self.registry)
        return details

    @staticmethod
    def model_run_id(index: int, node_id: str, recipe_id: str) -> str:
        return f"MR::{index:02d}::{node_id}::{recipe_id}"

    def attach_result(self, model_run_id: str, result: dict[str, Any]) -> None:
        self.set_status(model_run_id, "SUCCESS" if result.get("status") == "SUCCESS" else "WARNING", result.get("summary"))
        specification_id = self.nodes[model_run_id].get("metadata", {}).get("specification_id")
        if specification_id:
            self.set_status(f"MODEL_SPEC::{specification_id}", "SUCCESS" if result.get("status") == "SUCCESS" else "WARNING", result.get("summary"))
        lane_id = self.nodes[model_run_id].get("lane_id")
        diagnostics = result.get("diagnostics", [])
        if diagnostics:
            diagnostic_id = f"DIAGNOSTIC::{model_run_id}"
            statuses = {item.get("status") for item in diagnostics}
            graph_status = "FAILED" if "FAIL" in statuses or "FAILED" in statuses else "WARNING" if "WARNING" in statuses else "SUCCESS"
            failed = sum(item.get("status") in {"FAIL", "FAILED"} for item in diagnostics)
            warnings = sum(item.get("status") == "WARNING" for item in diagnostics)
            self.add_node(
                diagnostic_id,
                "DIAGNOSTIC",
                f"{len(diagnostics)} method-specific diagnostics",
                status=graph_status,
                lane_id=lane_id,
                summary=f"{failed} failed, {warnings} warnings; expand for statistics, p-values and credibility impact.",
                metadata={"count": len(diagnostics), "failed": failed, "warnings": warnings, "items": diagnostics},
            )
            self.add_edge(model_run_id, diagnostic_id, "DIAGNOSES")
        evidence_id = f"EVIDENCE::{model_run_id}"
        self.add_node(evidence_id, "EVIDENCE", result.get("title", model_run_id), status="SUCCESS", lane_id=lane_id, role=result.get("evidence_type"), summary=result.get("summary"), metadata={"direction": result.get("direction"), "confidence": result.get("confidence"), "signal": result.get("signal")})
        self.add_edge(model_run_id, evidence_id, "ESTIMATES")
        research_node_id = self.nodes[model_run_id]["metadata"]["model_recipe_id"]
        del research_node_id  # metadata kept for the detail view; claim edge is found below
        parts = model_run_id.split("::")
        registered_node = parts[2]
        self.add_edge(evidence_id, f"CLAIM::{registered_node}", "SUPPORTS")
        self.set_status(f"RN::{registered_node}", "SUCCESS")
        self.set_status(f"CLAIM::{registered_node}", "SUCCESS")
        if lane_id:
            self.set_status(f"LANE::{lane_id}", "RUNNING")

    def attach_failure(self, model_run_id: str, error_type: str) -> None:
        self.set_status(model_run_id, "FAILED", f"Execution failed: {error_type}")
        specification_id = self.nodes.get(model_run_id, {}).get("metadata", {}).get("specification_id")
        if specification_id:
            self.set_status(f"MODEL_SPEC::{specification_id}", "FAILED", f"Execution failed: {error_type}")

    def attach_synthesis(self, synthesis: dict[str, Any], interpretation: dict[str, Any]) -> None:
        lane_contributions: dict[str, list[dict[str, Any]]] = {}
        for contribution in synthesis.get("contributions", []):
            node = self.nodes.get(contribution["node_id"])
            if not node or not node.get("lane_id"):
                continue
            lane_contributions.setdefault(node["lane_id"], []).append(contribution)
        for lane_id, contributions in lane_contributions.items():
            lane_signal_id = f"LANE_SIGNAL::{lane_id}"
            score = sum(item["ordinal_signal"] * item["quality_multiplier"] for item in contributions) / max(sum(item["quality_multiplier"] for item in contributions), 1e-9)
            self.add_node(lane_signal_id, "LANE_SIGNAL", f"{lane_id} lane signal", status="SUCCESS", lane_id=lane_id, summary=f"Registered ordinal score {score:.3f}", metadata={"score": round(score, 6), "contributions": contributions})
            for contribution in contributions:
                self.add_edge(f"EVIDENCE::{contribution['node_id']}", lane_signal_id, "AGGREGATES_TO")
            self.set_status(f"LANE::{lane_id}", "SUCCESS")
        # A routed lane with no executable evidence must not remain visually
        # PENDING after the job is terminal.  Preserve the blocked research in
        # place and make the lane-level reason explicit.
        for node_id, node in list(self.nodes.items()):
            if node.get("node_type") != "LANE" or node.get("status") in {"SUCCESS", "NOT_ROUTED"}:
                continue
            lane_id = node.get("lane_id")
            selected_specs = [
                item
                for item in self.nodes.values()
                if item.get("node_type") == "MODEL_SPECIFICATION"
                and item.get("lane_id") == lane_id
                and item.get("status") != "NOT_ROUTED"
            ]
            if selected_specs and all(item.get("status") == "BLOCKED" for item in selected_specs):
                self.set_status(node_id, "BLOCKED", "All routed specifications in this lane are registry-blocked.")
            elif selected_specs:
                self.set_status(node_id, "WARNING", "The routed lane produced no aggregable evidence in this run.")
        aggregation_id = self.add_node("AGGREGATION", "AGGREGATION", synthesis["method"], status="SUCCESS", summary=f"Coverage {synthesis['coverage']} · confidence {synthesis['confidence']}", metadata=synthesis)
        for lane_id in lane_contributions:
            self.add_edge(f"LANE_SIGNAL::{lane_id}", aggregation_id, "AGGREGATES_TO")
        final_claim_id = self.add_node("FINAL_CLAIM", "FINAL_CLAIM", interpretation["headline"], status="SUCCESS", summary=interpretation["answer"], metadata={"confidence": synthesis["confidence"], "coverage": synthesis["coverage"]})
        self.add_edge(aggregation_id, final_claim_id, "AGGREGATES_TO")
        for index, falsifier in enumerate(interpretation.get("falsifiers", []), start=1):
            falsifier_id = f"FALSIFIER::{index:02d}"
            self.add_node(falsifier_id, "FALSIFIER", falsifier, status="SUCCESS")
            self.add_edge(final_claim_id, falsifier_id, "FALSIFIED_BY")

    def export(self) -> dict[str, Any]:
        return {
            "schema_version": "0.2.0",
            "job_id": self.job_id,
            "nodes": list(self.nodes.values()),
            "edges": list(self.edges.values()),
            "updated_at": datetime.now(UTC).isoformat(),
        }
