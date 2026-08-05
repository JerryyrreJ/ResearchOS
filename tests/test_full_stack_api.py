import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.researchos_api.app.orchestration.store import store

ROOT = Path(__file__).parents[1]


def fixture(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / "contracts" / name).read_text(encoding="utf-8"))


def test_a_b_c_routes_share_one_browser_api(client: TestClient) -> None:
    store.theses.clear()
    store.builds.clear()
    store.by_thesis.clear()
    store.events.clear()
    store.evidence_builds.clear()

    thesis = fixture("sample_thesis_build.json")
    created = client.post("/api/v1/theses", json=thesis)
    assert created.status_code == 201, created.text

    compiled = client.post(f"/api/v1/theses/{thesis['thesis_id']}/compile")
    assert compiled.status_code == 200, compiled.text
    compile_payload = compiled.json()
    assert compile_payload["compile_result"]["conclusion_state"] == "COMPILE_FAILED"

    tool_run = client.post(
        "/api/v1/tool-runs/macrotrace",
        json=compile_payload["tool_request"],
    )
    assert tool_run.status_code == 202, tool_run.text
    run_payload = tool_run.json()
    assert run_payload["mode"] == "FIXTURE"
    assert run_payload["evidence_bundle"]["status"] == "COMPLETE"

    verified = client.post(
        f"/api/v1/theses/{thesis['thesis_id']}/verify",
        json={"evidence_bundle": run_payload["evidence_bundle"]},
    )
    assert verified.status_code == 200, verified.text
    verified_payload = verified.json()
    assert verified_payload["compile_result"]["compiled_claim"]
    assert verified_payload["compile_result"]["language_policy"]["allowed_level"] == "ASSOCIATIONAL"

    versions = client.get(f"/api/v1/theses/{thesis['thesis_id']}/versions").json()
    assert len(versions) == 2
    diff = client.get(
        f"/api/v1/thesis-versions/{versions[0]['build_id']}/diff/{versions[1]['build_id']}"
    )
    assert diff.status_code == 200, diff.text
    assert diff.json()["affected_claims"] == [thesis["thesis_id"]]

    graph = client.get(f"/api/v1/tool-runs/{run_payload['tool_run_id']}/graph")
    artifacts = client.get(f"/api/v1/tool-runs/{run_payload['tool_run_id']}/artifacts")
    assert graph.status_code == 200
    assert artifacts.status_code == 200
