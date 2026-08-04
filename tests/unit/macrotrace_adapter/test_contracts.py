from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from backend.app.researchos_adapter.contracts import (
    ContractViolation,
    FrozenContractRegistry,
    UnsafeControlField,
    cap_evidence_type,
)
from backend.app.researchos_adapter.service import (
    FixtureToolRunService,
    RequestIdConflict,
    UnsafeArtifactReference,
    _safe_relative_artifact_uri,
    canonical_evidence_hash,
)


FIXTURE_SCHEMAS = {
    "sample_compile_result.json": "compile_result.schema.json",
    "sample_context_pack.json": "context_pack.schema.json",
    "sample_data_object_ref.json": "data_object_ref.schema.json",
    "sample_evidence_bundle.json": "evidence_bundle.schema.json",
    "sample_ontology_relation.json": "ontology_relation.schema.json",
    "sample_thesis_build.json": "thesis_build.schema.json",
    "sample_tool_request.json": "tool_request.schema.json",
    "sample_version_diff.json": "version_diff.schema.json",
}


def test_all_shared_fixtures_validate(repo_root: Path) -> None:
    contracts = FrozenContractRegistry(repo_root)
    for fixture_name, schema_name in FIXTURE_SCHEMAS.items():
        payload = json.loads((repo_root / "fixtures" / "contracts" / fixture_name).read_text(encoding="utf-8"))
        contracts.validate(schema_name, payload)


@pytest.mark.parametrize(
    ("mutation", "exception"),
    [
        (lambda request: request.update(extra_field=True), ContractViolation),
        (lambda request: request.update(contract_version="0.2.0"), ContractViolation),
        (lambda request: request.update(timeout_seconds=901), ContractViolation),
        (lambda request: request["metadata"].update(python_code="print('no')"), UnsafeControlField),
        (lambda request: request["metadata"].update(sql="select * from private"), UnsafeControlField),
        (lambda request: request["metadata"].update(registry_patch={"models": []}), UnsafeControlField),
    ],
)
def test_invalid_or_unsafe_tool_request_is_rejected(sample_request, mutation, exception) -> None:
    request = copy.deepcopy(sample_request)
    mutation(request)
    with pytest.raises(exception):
        FrozenContractRegistry().validate_tool_request(request)


def test_evidence_type_is_capped() -> None:
    assert cap_evidence_type("CAUSAL_IDENTIFIED", "ASSOCIATIONAL") == "ASSOCIATIONAL"
    assert cap_evidence_type("PREDICTIVE", "CAUSAL_IDENTIFIED") == "PREDICTIVE"


def test_request_id_is_idempotent_and_conflicts_on_changed_content(sample_request) -> None:
    service = FixtureToolRunService()
    first = service.create(sample_request)
    second = service.create(copy.deepcopy(sample_request))
    assert first == second

    changed = copy.deepcopy(sample_request)
    changed["question"] = "A different valid macro question"
    with pytest.raises(RequestIdConflict):
        service.create(changed)


def test_canonical_result_hash_excludes_runtime_identity(sample_request) -> None:
    service = FixtureToolRunService()
    first = service.create(sample_request)["evidence_bundle"]
    second = copy.deepcopy(first)
    second["bundle_id"] = "ANOTHER_BUNDLE"
    second["request_id"] = "ANOTHER_REQUEST"
    second["research_job_id"] = "ANOTHER_JOB"
    second["trace_ref"] = "ANOTHER_TRACE"
    second["artifacts"][0]["uri"] = "fixtures/evidence/artifacts/another.json"
    assert canonical_evidence_hash(first) == canonical_evidence_hash(second)


@pytest.mark.parametrize("uri", ["../../secret.txt", "/absolute/file", "C:\\secret.txt", "https://example.com/file"])
def test_artifact_path_escape_is_rejected(uri: str) -> None:
    with pytest.raises(UnsafeArtifactReference):
        _safe_relative_artifact_uri(uri)


def test_owned_fixture_artifact_path_is_allowed() -> None:
    _safe_relative_artifact_uri("fixtures/evidence/artifacts/table_complete.json")


def test_fixture_artifact_hashes_match_files(repo_root: Path) -> None:
    fixture_dir = repo_root / "fixtures" / "evidence"
    for bundle_path in fixture_dir.glob("evidence_bundle_*.json"):
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        for artifact in bundle["artifacts"]:
            artifact_path = repo_root / artifact["uri"]
            assert artifact_path.is_file()
            assert hashlib.sha256(artifact_path.read_bytes()).hexdigest() == artifact["sha256"]
