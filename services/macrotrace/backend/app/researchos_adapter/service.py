from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
from threading import Lock
from typing import Any

from .contracts import FrozenContractRegistry, cap_evidence_type


TERMINAL_STATUSES = {"COMPLETE", "PARTIAL", "FAILED", "CANCELLED"}
SCENARIOS = {"COMPLETE", "PARTIAL", "FAILED", "CANCELLED", "UNSUPPORTED", "OUT_OF_SCOPE"}


class ToolRunNotFound(LookupError):
    pass


class RequestIdConflict(ValueError):
    pass


class InvalidFixtureScenario(ValueError):
    pass


class UnsafeArtifactReference(ValueError):
    pass


def canonical_json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _without_runtime_identity(value: Any) -> Any:
    if isinstance(value, dict):
        excluded = {"bundle_id", "request_id", "research_job_id", "result_hash", "trace_ref", "uri", "timestamp", "created_at", "updated_at"}
        return {
            key: _without_runtime_identity(item)
            for key, item in sorted(value.items())
            if key not in excluded
        }
    if isinstance(value, list):
        return [_without_runtime_identity(item) for item in value]
    return value


def canonical_evidence_hash(bundle: dict[str, Any]) -> str:
    return canonical_json_hash(_without_runtime_identity(bundle))


def _safe_relative_artifact_uri(uri: str | None) -> None:
    if uri is None:
        return
    if "://" in uri or uri.startswith(("/", "\\")):
        raise UnsafeArtifactReference("Fixture artifacts must use repository-relative paths")
    path = PurePosixPath(uri.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise UnsafeArtifactReference("Fixture artifact path escapes the owned fixture directory")
    if not path.parts or path.parts[:2] != ("fixtures", "evidence"):
        raise UnsafeArtifactReference("Fixture artifact path must stay under fixtures/evidence")


class FixtureToolRunService:
    """Deterministic, in-process adapter used only for the first integration slice."""

    mode = "FIXTURE"

    def __init__(self, contracts: FrozenContractRegistry | None = None) -> None:
        self.contracts = contracts or FrozenContractRegistry()
        self.fixture_dir = self.contracts.repo_root / "fixtures" / "evidence"
        self._lock = Lock()
        self._runs: dict[str, dict[str, Any]] = {}
        self._request_fingerprints: dict[str, str] = {}

    def health(self) -> dict[str, Any]:
        return {
            "status": "ready",
            "mode": self.mode,
            "contract_version": "0.1.0-frozen",
            "arbitrary_code_allowed": False,
            "real_execution_enabled": False,
        }

    def _scenario(self, request: dict[str, Any]) -> str:
        metadata = request.get("metadata") or {}
        scenario = str(metadata.get("fixture_scenario", "COMPLETE")).strip().upper()
        if scenario not in SCENARIOS:
            raise InvalidFixtureScenario(scenario)
        return scenario

    def _load_template(self, scenario: str) -> dict[str, Any]:
        template_name = scenario.lower()
        if scenario in {"CANCELLED", "UNSUPPORTED", "OUT_OF_SCOPE"}:
            template_name = "failed" if scenario == "CANCELLED" else "partial"
        path = self.fixture_dir / f"evidence_bundle_{template_name}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError(f"Fixture bundle must be a JSON object: {path.name}")
        return payload

    def _materialize_bundle(
        self,
        request: dict[str, Any],
        scenario: str,
        tool_run_id: str,
    ) -> dict[str, Any]:
        bundle = copy.deepcopy(self._load_template(scenario))
        suffix = tool_run_id.rsplit("_", 1)[-1]
        bundle["bundle_id"] = f"EVIDENCE_FIXTURE_{suffix}"
        bundle["request_id"] = request["request_id"]
        bundle["research_job_id"] = f"JOB_FIXTURE_{suffix}"
        bundle["input_object_refs"] = copy.deepcopy(request["input_object_refs"])

        if scenario == "CANCELLED":
            bundle.update(status="CANCELLED", coverage="PARTIAL", engine_claim=None)
            bundle["limitations"] = [
                "Fixture run was cancelled before empirical completion.",
                *bundle.get("limitations", []),
            ]
        elif scenario == "UNSUPPORTED":
            bundle.update(status="PARTIAL", coverage="UNSUPPORTED", engine_claim=None)
            bundle["limitations"] = [
                "The registered fixture workflow does not cover this request.",
                *bundle.get("limitations", []),
            ]
        elif scenario == "OUT_OF_SCOPE":
            bundle.update(status="PARTIAL", coverage="OUT_OF_SCOPE", engine_claim=None)
            bundle["limitations"] = [
                "The request is outside the US macro and macro-to-assets scope.",
                *bundle.get("limitations", []),
            ]

        requested_type = request["requested_evidence_type"]
        bundle["evidence_type"] = cap_evidence_type(bundle["evidence_type"], requested_type)
        for model_run in bundle["model_runs"]:
            model_run["evidence_type"] = cap_evidence_type(model_run["evidence_type"], requested_type)

        bundle["falsifiers"] = [
            {
                "falsifier_id": f"FALSIFIER_FIXTURE_{index:02d}",
                "requirement": requirement,
                "status": "UNTESTED",
            }
            for index, requirement in enumerate(request["falsifier_requirements"], start=1)
        ]
        bundle["metadata"] = {
            **bundle.get("metadata", {}),
            "mode": self.mode,
            "fixture_only": True,
            "fixture_scenario": scenario,
            "requested_evidence_type": requested_type,
            "request_specification_hash": canonical_json_hash(
                {key: value for key, value in request.items() if key != "request_id"}
            ),
        }
        for artifact in bundle["artifacts"]:
            _safe_relative_artifact_uri(artifact.get("uri"))
        bundle["result_hash"] = canonical_evidence_hash(bundle)
        self.contracts.validate_evidence_bundle(bundle)
        return bundle

    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        self.contracts.validate_tool_request(request)
        scenario = self._scenario(request)
        fingerprint = canonical_json_hash(request)
        request_id = request["request_id"]

        with self._lock:
            prior = self._request_fingerprints.get(request_id)
            if prior is not None:
                if prior != fingerprint:
                    raise RequestIdConflict(request_id)
                return copy.deepcopy(self._runs[request_id])

            tool_run_id = f"MTR_FIXTURE_{hashlib.sha256(request_id.encode('utf-8')).hexdigest()[:16].upper()}"
            bundle = self._materialize_bundle(request, scenario, tool_run_id)
            envelope = {
                "contract_version": "0.1.0-frozen",
                "tool_run_id": tool_run_id,
                "request_id": request_id,
                "status": bundle["status"],
                "progress": 100,
                "mode": self.mode,
                "links": {
                    "self": f"/v1/tool-runs/{tool_run_id}",
                    "graph": f"/v1/tool-runs/{tool_run_id}/graph",
                    "artifacts": f"/v1/tool-runs/{tool_run_id}/artifacts",
                },
                "evidence_bundle": bundle,
                "error": None if bundle["status"] != "FAILED" else {
                    "code": "FIXTURE_EMPIRICAL_FAILURE",
                    "message": "Fixture failure retained for consumer-path testing.",
                },
            }
            self._request_fingerprints[request_id] = fingerprint
            self._runs[request_id] = envelope
            return copy.deepcopy(envelope)

    def get(self, tool_run_id: str) -> dict[str, Any]:
        with self._lock:
            for envelope in self._runs.values():
                if envelope["tool_run_id"] == tool_run_id:
                    return copy.deepcopy(envelope)
        raise ToolRunNotFound(tool_run_id)

    def graph(self, tool_run_id: str) -> dict[str, Any]:
        envelope = self.get(tool_run_id)
        bundle = envelope["evidence_bundle"]
        question_node = {
            "node_id": "QUESTION_FIXTURE",
            "node_type": "QUESTION",
            "status": "SUCCESS",
            "label": "Validated ToolRequest",
            "fixture_only": True,
        }
        model_nodes = [
            {
                "node_id": run["model_run_id"],
                "node_type": "MODEL_RUN",
                "status": run["status"],
                "label": run["model_recipe_id"],
                "evidence_type": run["evidence_type"],
                "fixture_only": True,
            }
            for run in bundle["model_runs"]
        ]
        evidence_node = {
            "node_id": bundle["bundle_id"],
            "node_type": "EVIDENCE",
            "status": bundle["status"],
            "label": "Fixture EvidenceBundle",
            "fixture_only": True,
        }
        edges = [
            {"source": question_node["node_id"], "target": node["node_id"], "relation": "ROUTES_TO"}
            for node in model_nodes
        ] + [
            {"source": node["node_id"], "target": evidence_node["node_id"], "relation": "CONTRIBUTES_TO"}
            for node in model_nodes
        ]
        return {
            "schema_version": "researchos-macrotrace-fixture-0.1.0",
            "tool_run_id": tool_run_id,
            "mode": self.mode,
            "fixture_only": True,
            "status": bundle["status"],
            "nodes": [question_node, *model_nodes, evidence_node],
            "edges": edges,
        }

    def artifacts(self, tool_run_id: str) -> dict[str, Any]:
        envelope = self.get(tool_run_id)
        artifacts = copy.deepcopy(envelope["evidence_bundle"]["artifacts"])
        for artifact in artifacts:
            _safe_relative_artifact_uri(artifact.get("uri"))
        return {
            "tool_run_id": tool_run_id,
            "mode": self.mode,
            "fixture_only": True,
            "inline_content": False,
            "items": artifacts,
        }
