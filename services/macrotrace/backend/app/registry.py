from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class RegistryDocument:
    registry_type: str
    registry_version: str
    items: tuple[dict[str, Any], ...]


class RegistryStore:
    """Loads immutable, versioned v0.2 registry documents and enforces ID references."""

    FILES = {
        "lanes": "lanes.json",
        "datasets": "datasets.json",
        "factors": "factors.json",
        "nodes": "nodes.json",
        "workflows": "workflows.json",
        "models": "models.json",
        "parameter_policies": "parameter_policies.json",
        "aggregations": "aggregations.json",
        "claims": "claims.json",
        "routes": "routes.json",
        "reports": "reports.json",
        "mechanisms": "mechanisms.json",
        "model_specifications": "model_specifications.json",
        "evidence_budgets": "evidence_budgets.json",
        "synthesis_policies": "synthesis_policies.json",
        "evidence_mappings": "evidence_mappings.json",
        "scenario_mappings": "scenario_mappings.json",
    }

    ID_FIELDS = {
        "lanes": "lane_id",
        "datasets": "dataset_id",
        "factors": "factor_id",
        "nodes": "node_id",
        "workflows": "workflow_id",
        "models": "recipe_id",
        "parameter_policies": "policy_id",
        "aggregations": "aggregation_id",
        "claims": "claim_id",
        "routes": "route_id",
        "reports": "report_id",
        "mechanisms": "mechanism_id",
        "model_specifications": "specification_id",
        "evidence_budgets": "budget_id",
        "synthesis_policies": "policy_id",
        "evidence_mappings": "mapping_id",
        "scenario_mappings": "scenario_mapping_id",
    }

    def __init__(self, root: Path) -> None:
        self.root = root
        self._documents: dict[str, RegistryDocument] = {}
        self._indexes: dict[str, dict[str, dict[str, Any]]] = {}
        self.reload()

    def reload(self) -> None:
        documents: dict[str, RegistryDocument] = {}
        indexes: dict[str, dict[str, dict[str, Any]]] = {}
        for name, filename in self.FILES.items():
            path = self.root / filename
            if not path.exists():
                raise RegistryError(f"missing registry document: {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("registry_type") != name:
                raise RegistryError(f"registry_type mismatch in {path}")
            if payload.get("registry_version") != "0.2.0":
                raise RegistryError(f"unsupported registry version in {path}")
            items = tuple(payload.get("items", []))
            id_field = self.ID_FIELDS[name]
            index: dict[str, dict[str, Any]] = {}
            for item in items:
                item_id = item.get(id_field)
                if not isinstance(item_id, str) or not item_id:
                    raise RegistryError(f"missing {id_field} in {path}")
                if item_id in index:
                    raise RegistryError(f"duplicate {item_id} in {path}")
                index[item_id] = item
            documents[name] = RegistryDocument(name, payload["registry_version"], items)
            indexes[name] = index
        self._documents = documents
        self._indexes = indexes
        self.validate_references()

    def all(self, name: str, *, status: str | None = None) -> list[dict[str, Any]]:
        items = list(self._documents[name].items)
        if status is not None:
            items = [item for item in items if item.get("status") == status]
        return items

    def ids(self, name: str, *, status: str | None = None) -> set[str]:
        field = self.ID_FIELDS[name]
        return {item[field] for item in self.all(name, status=status)}

    def get(self, name: str, item_id: str) -> dict[str, Any]:
        try:
            return self._indexes[name][item_id]
        except KeyError as exc:
            raise RegistryError(f"unknown {name} id: {item_id}") from exc

    def require_ids(self, name: str, values: Iterable[str]) -> None:
        unknown = sorted(set(values) - self.ids(name))
        if unknown:
            raise RegistryError(f"unknown {name} ids: {', '.join(unknown)}")

    def validate_parameters(self, recipe_id: str, values: dict[str, Any]) -> None:
        recipe = self.get("models", recipe_id)
        allowed = recipe.get("allowed_parameters", {})
        unknown = set(values) - set(allowed)
        missing = set(allowed) - set(values)
        if unknown:
            raise RegistryError(f"unregistered parameters for {recipe_id}: {sorted(unknown)}")
        if missing:
            raise RegistryError(f"missing required parameters for {recipe_id}: {sorted(missing)}")
        for key, value in values.items():
            rule = allowed[key]
            if isinstance(rule, list) and value not in rule:
                raise RegistryError(f"{key}={value!r} is not allowed for {recipe_id}")
            if isinstance(rule, dict):
                if isinstance(value, (int, float)):
                    if "min" in rule and value < rule["min"]:
                        raise RegistryError(f"{key} below minimum for {recipe_id}")
                    if "max" in rule and value > rule["max"]:
                        raise RegistryError(f"{key} above maximum for {recipe_id}")

    def validate_references(self) -> None:
        lane_ids = self.ids("lanes")
        dataset_ids = self.ids("datasets")
        factor_ids = self.ids("factors")
        node_ids = self.ids("nodes")
        model_ids = self.ids("models")
        aggregation_ids = self.ids("aggregations")
        report_ids = self.ids("reports")
        mechanism_ids = self.ids("mechanisms")
        workflow_ids = self.ids("workflows")
        evidence_budget_ids = self.ids("evidence_budgets")
        claim_ids = self.ids("claims")
        specification_ids = self.ids("model_specifications")

        for factor in self.all("factors"):
            if factor["dataset_id"] not in dataset_ids:
                raise RegistryError(f"factor {factor['factor_id']} references unknown dataset")
            if factor["lane_id"] not in lane_ids:
                raise RegistryError(f"factor {factor['factor_id']} references unknown lane")
        for node in self.all("nodes"):
            if node["lane_id"] not in lane_ids:
                raise RegistryError(f"node {node['node_id']} references unknown lane")
            self.require_ids("factors", node.get("factor_pool", []))
            self.require_ids("models", node.get("model_pool", []))
            self.require_ids("nodes", node.get("allowed_upstream", []))
            if node.get("mechanism_id") and node["mechanism_id"] not in mechanism_ids:
                raise RegistryError(f"node {node['node_id']} references unknown mechanism")
        for workflow in self.all("workflows"):
            self.require_ids("lanes", workflow.get("lane_pool", []))
            self.require_ids("nodes", workflow.get("node_pool", []))
            if workflow["aggregation_id"] not in aggregation_ids:
                raise RegistryError(f"workflow {workflow['workflow_id']} has unknown aggregation")
            if workflow.get("evidence_budget_id") and workflow["evidence_budget_id"] not in evidence_budget_ids:
                raise RegistryError(f"workflow {workflow['workflow_id']} has unknown evidence budget")
        for route in self.all("routes"):
            self.require_ids("lanes", route.get("lane_ids", []))
            self.require_ids("nodes", route.get("node_ids", []))
            self.require_ids("factors", route.get("factor_ids", []))
            self.require_ids("models", route.get("model_recipe_ids", []))
            unknown_reports = set(route.get("report_evidence", {}).keys()) - report_ids
            if unknown_reports:
                raise RegistryError(f"route {route['route_id']} has unknown report evidence")

        for model in self.all("models"):
            self.require_ids("factors", model.get("factor_pool", []))
            self.require_ids("datasets", model.get("dataset_dependencies", []))
            minimum_factor_count = model.get("minimum_factor_count", 1)
            if not isinstance(minimum_factor_count, int) or minimum_factor_count < 1:
                raise RegistryError(f"model {model['recipe_id']} has invalid minimum_factor_count")
            if minimum_factor_count > len(model.get("factor_pool", [])):
                raise RegistryError(f"model {model['recipe_id']} minimum_factor_count exceeds its factor pool")

        for mechanism in self.all("mechanisms"):
            if mechanism["lane_id"] not in lane_ids:
                raise RegistryError(f"mechanism {mechanism['mechanism_id']} references unknown lane")
            self.require_ids("factors", mechanism.get("factor_pool", []))
            unknown_reports = set(mechanism.get("report_evidence", {})) - report_ids
            if unknown_reports:
                raise RegistryError(f"mechanism {mechanism['mechanism_id']} has unknown report evidence")

        for specification in self.all("model_specifications"):
            if specification["lane_id"] not in lane_ids:
                raise RegistryError(f"specification {specification['specification_id']} references unknown lane")
            if specification["mechanism_id"] not in mechanism_ids:
                raise RegistryError(f"specification {specification['specification_id']} references unknown mechanism")
            if specification["node_id"] not in node_ids:
                raise RegistryError(f"specification {specification['specification_id']} references unknown node")
            self.require_ids("workflows", specification.get("workflow_ids", []))
            self.require_ids("factors", specification.get("factor_ids", []))
            self.require_ids("reports", specification.get("report_ids", []))
            recipe_id = specification.get("model_recipe_id")
            if recipe_id is None:
                if specification.get("execution_status") != "BLOCKED":
                    raise RegistryError(f"specification {specification['specification_id']} lacks an executable recipe")
            else:
                if recipe_id not in model_ids:
                    raise RegistryError(f"specification {specification['specification_id']} references unknown model")
                if specification.get("execution_status") == "ACTIVE":
                    recipe = self.get("models", recipe_id)
                    if not set(specification.get("factor_ids", [])).issubset(set(recipe.get("factor_pool", []))):
                        raise RegistryError(f"specification {specification['specification_id']} uses factors outside the model recipe")
                    self.validate_parameters(recipe_id, specification.get("parameters", {}))
            if not set(specification.get("workflow_ids", [])).issubset(workflow_ids):
                raise RegistryError(f"specification {specification['specification_id']} references unknown workflow")

        policies_by_workflow: dict[str, str] = {}
        for policy in self.all("synthesis_policies"):
            workflow_id = policy["workflow_id"]
            if workflow_id not in workflow_ids:
                raise RegistryError(f"synthesis policy {policy['policy_id']} references unknown workflow")
            if workflow_id in policies_by_workflow:
                raise RegistryError(f"workflow {workflow_id} has multiple synthesis policies")
            policies_by_workflow[workflow_id] = policy["policy_id"]
            referenced_claims = set(policy.get("primary_claim_ids", [])) | set(policy.get("contextual_claim_ids", []))
            referenced_claims |= {item.get("claim_id") for item in policy.get("claim_presentations", [])}
            unknown_claims = referenced_claims - claim_ids
            if unknown_claims:
                raise RegistryError(f"synthesis policy {policy['policy_id']} references unknown claims: {sorted(unknown_claims)}")
            if set(policy.get("primary_claim_ids", [])) & set(policy.get("contextual_claim_ids", [])):
                raise RegistryError(f"synthesis policy {policy['policy_id']} repeats a claim across primary and context")

        missing_policies = {
            item["workflow_id"] for item in self.all("workflows") if item.get("status") in {"active", "fixture"}
        } - set(policies_by_workflow)
        if missing_policies:
            raise RegistryError(f"workflows missing synthesis policy: {sorted(missing_policies)}")

        mapped_specifications: set[str] = set()
        for mapping in self.all("evidence_mappings"):
            specification_id = mapping["specification_id"]
            if specification_id not in specification_ids:
                raise RegistryError(f"evidence mapping {mapping['mapping_id']} references unknown specification")
            if specification_id in mapped_specifications:
                raise RegistryError(f"specification {specification_id} has multiple evidence mappings")
            mapped_specifications.add(specification_id)
            if mapping["claim_id"] not in claim_ids:
                raise RegistryError(f"evidence mapping {mapping['mapping_id']} references unknown claim")
            if mapping.get("signal_multiplier") not in {-1, 1}:
                raise RegistryError(f"evidence mapping {mapping['mapping_id']} must use signal_multiplier -1 or 1")

        required_mappings = {
            item["specification_id"]
            for item in self.all("model_specifications")
            if item.get("execution_status") == "ACTIVE" and item.get("role") == "CORE"
        }
        if required_mappings - mapped_specifications:
            raise RegistryError(f"active CORE specifications missing evidence mappings: {sorted(required_mappings - mapped_specifications)}")

        fallback_scenarios = 0
        for mapping in self.all("scenario_mappings"):
            self.require_ids("factors", mapping.get("shock_factor_ids", []))
            self.require_ids("factors", mapping.get("response_factor_ids", []))
            self.require_ids("models", mapping.get("model_recipe_ids", []))
            if mapping.get("mapping_tier") not in {
                "DIRECT_DYNAMIC",
                "STRUCTURAL_PROXY",
                "TRANSMISSION_PROXY",
                "SENSITIVITY_ENVELOPE",
            }:
                raise RegistryError(
                    f"scenario mapping {mapping['scenario_mapping_id']} has an invalid mapping_tier"
                )
            if mapping.get("is_fallback"):
                fallback_scenarios += 1
        if fallback_scenarios != 1:
            raise RegistryError("scenario mappings must define exactly one fallback")

    def summary(self) -> dict[str, Any]:
        return {
            "registry_version": "0.2.0+v0.3-depth-extension",
            "counts": {name: len(document.items) for name, document in self._documents.items()},
            "arbitrary_code_allowed": False,
            "validation": "PASS",
        }
