import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from apps.researchos_api.app.main import app
from apps.researchos_api.app.orchestration.store import store

ROOT = Path(__file__).parents[3]
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    store.theses.clear(); store.builds.clear(); store.by_thesis.clear(); store.events.clear(); store.evidence_builds.clear()


def fixture(name: str):
    return json.loads((ROOT / "fixtures" / "contracts" / name).read_text(encoding="utf-8"))


def test_full_fixture_workflow_and_sse():
    thesis = fixture("sample_thesis_build.json")
    assert client.post("/v1/theses", json=thesis).status_code == 201
    first = client.post(f"/v1/theses/{thesis['thesis_id']}/compile").json()
    assert first["compile_result"]["conclusion_state"] == "COMPILE_FAILED"
    events = client.get(f"/v1/jobs/{first['job_id']}/events")
    assert events.status_code == 200 and "event: COMPILING" in events.text
    verified = client.post(f"/v1/theses/{thesis['thesis_id']}/verify", json={"evidence_bundle": fixture("sample_evidence_bundle.json")})
    assert verified.status_code == 200
    versions = client.get(f"/v1/theses/{thesis['thesis_id']}/versions").json()
    assert len(versions) == 2 and versions[1]["parent_build_id"] == versions[0]["build_id"]


def test_health():
    assert client.get("/health").json() == {"status": "ok", "contract_version": "0.1.0-frozen"}


def test_duplicate_evidence_bundle_is_idempotent():
    thesis = fixture("sample_thesis_build.json")
    client.post("/v1/theses", json=thesis)
    body = {"evidence_bundle": fixture("sample_evidence_bundle.json")}
    first = client.post(f"/v1/theses/{thesis['thesis_id']}/verify", json=body).json()
    second = client.post(f"/v1/theses/{thesis['thesis_id']}/verify", json=body).json()
    assert second["idempotent_replay"] is True
    assert second["compile_result"]["build_id"] == first["compile_result"]["build_id"]
    assert len(client.get(f"/v1/theses/{thesis['thesis_id']}/versions").json()) == 1


def test_thesis_version_is_immutable():
    thesis = fixture("sample_thesis_build.json")
    assert client.post("/v1/theses", json=thesis).status_code == 201
    thesis["raw_claim"] = "同一版本被篡改后的论点"
    assert client.post("/v1/theses", json=thesis).status_code == 409


def test_contract_version_mismatch_is_rejected():
    thesis = fixture("sample_thesis_build.json")
    thesis["contract_version"] = "wrong"
    assert client.post("/v1/theses", json=thesis).status_code == 422


def test_sse_sequences_are_monotonic():
    thesis = fixture("sample_thesis_build.json")
    client.post("/v1/theses", json=thesis)
    compiled = client.post(f"/v1/theses/{thesis['thesis_id']}/compile").json()
    lines = [line for line in client.get(f"/v1/jobs/{compiled['job_id']}/events").text.splitlines() if line.startswith("id: ")]
    assert [int(line.removeprefix("id: ")) for line in lines] == [1, 2, 3]
