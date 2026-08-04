from __future__ import annotations

import copy
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.researchos_adapter.contracts import FrozenContractRegistry


client = TestClient(app)
contracts = FrozenContractRegistry()


def _request(sample_request: dict[str, Any], scenario: str) -> dict[str, Any]:
    request = copy.deepcopy(sample_request)
    request["request_id"] = f"TOOL_REQ_INTEGRATION_{scenario}"
    request["metadata"]["fixture_scenario"] = scenario
    return request


def _forbidden_keys(value: Any) -> set[str]:
    forbidden = {"conclusion_state", "supported_probability", "investment_rating", "buy_sell_signal"}
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in forbidden:
                found.add(key)
            found.update(_forbidden_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_forbidden_keys(item))
    return found


@pytest.mark.parametrize(
    ("scenario", "status", "coverage"),
    [
        ("COMPLETE", "COMPLETE", "FULL"),
        ("PARTIAL", "PARTIAL", "PARTIAL"),
        ("FAILED", "FAILED", "UNSUPPORTED"),
        ("CANCELLED", "CANCELLED", "PARTIAL"),
        ("UNSUPPORTED", "PARTIAL", "UNSUPPORTED"),
        ("OUT_OF_SCOPE", "PARTIAL", "OUT_OF_SCOPE"),
    ],
)
def test_fixture_states_validate(sample_request, scenario: str, status: str, coverage: str) -> None:
    response = client.post("/v1/tool-runs/macrotrace", json=_request(sample_request, scenario))
    assert response.status_code == 202
    envelope = response.json()
    assert envelope["mode"] == "FIXTURE"
    assert envelope["status"] == status
    bundle = envelope["evidence_bundle"]
    assert bundle["status"] == status
    assert bundle["coverage"] == coverage
    assert bundle["metadata"]["fixture_only"] is True
    contracts.validate_evidence_bundle(bundle)
    assert not _forbidden_keys(envelope)


def test_partial_and_failed_models_remain_visible(sample_request) -> None:
    response = client.post("/v1/tool-runs/macrotrace", json=_request(sample_request, "PARTIAL"))
    bundle = response.json()["evidence_bundle"]
    assert any(run["status"] == "FAILED" for run in bundle["model_runs"])
    assert bundle["limitations"]
    assert any(item["status"] == "FAIL" for item in bundle["diagnostics"])


def test_graph_and_artifact_routes_are_stable_and_non_inline(sample_request) -> None:
    envelope = client.post("/v1/tool-runs/macrotrace", json=_request(sample_request, "FAILED")).json()
    run_id = envelope["tool_run_id"]

    status_response = client.get(f"/v1/tool-runs/{run_id}")
    assert status_response.status_code == 200
    assert status_response.json()["tool_run_id"] == run_id

    graph_response = client.get(f"/v1/tool-runs/{run_id}/graph")
    assert graph_response.status_code == 200
    graph = graph_response.json()
    assert graph["fixture_only"] is True
    assert any(node["status"] == "FAILED" for node in graph["nodes"])

    artifact_response = client.get(f"/v1/tool-runs/{run_id}/artifacts")
    assert artifact_response.status_code == 200
    artifacts = artifact_response.json()
    assert artifacts["inline_content"] is False
    assert all("content" not in item for item in artifacts["items"])


def test_evidence_type_cannot_be_upgraded(sample_request) -> None:
    request = _request(sample_request, "COMPLETE")
    request["requested_evidence_type"] = "DESCRIPTIVE"
    request["request_id"] = "TOOL_REQ_INTEGRATION_EVIDENCE_CAP"
    bundle = client.post("/v1/tool-runs/macrotrace", json=request).json()["evidence_bundle"]
    assert bundle["evidence_type"] == "DESCRIPTIVE"
    assert {run["evidence_type"] for run in bundle["model_runs"]} == {"DESCRIPTIVE"}


def test_request_id_idempotency_and_content_conflict(sample_request) -> None:
    request = _request(sample_request, "COMPLETE")
    request["request_id"] = "TOOL_REQ_INTEGRATION_IDEMPOTENT"
    first = client.post("/v1/tool-runs/macrotrace", json=request)
    second = client.post("/v1/tool-runs/macrotrace", json=request)
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()

    changed = copy.deepcopy(request)
    changed["question"] = "A different question with the same request id"
    conflict = client.post("/v1/tool-runs/macrotrace", json=changed)
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "REQUEST_ID_CONFLICT"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda request: request.update(extra_field=True),
        lambda request: request.update(contract_version="wrong"),
        lambda request: request.update(timeout_seconds=4),
        lambda request: request["metadata"].update(python="print('blocked')"),
        lambda request: request["metadata"].update(formula="y ~ x"),
    ],
)
def test_invalid_requests_are_rejected(sample_request, mutation) -> None:
    request = _request(sample_request, "COMPLETE")
    request["request_id"] += f"_{id(mutation)}"
    mutation(request)
    response = client.post("/v1/tool-runs/macrotrace", json=request)
    assert response.status_code == 422


def test_unknown_tool_run_returns_404() -> None:
    for suffix in ("", "/graph", "/artifacts"):
        response = client.get(f"/v1/tool-runs/DOES_NOT_EXIST{suffix}")
        assert response.status_code == 404


def test_health_exposes_fixture_boundary() -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200
    adapter = response.json()["researchos_adapter"]
    assert adapter["mode"] == "FIXTURE"
    assert adapter["arbitrary_code_allowed"] is False
    assert adapter["real_execution_enabled"] is False
