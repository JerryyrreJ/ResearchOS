from conftest import create_batch, upload_bytes
from fastapi.testclient import TestClient


def test_object_projection_and_structural_graph_are_real(
    client: TestClient,
    workspace: dict,
) -> None:
    first = upload_bytes(
        client,
        create_batch(client, workspace["id"])["id"],
        filename="research-note.md",
        content=b"# First\n\nInitial material.\n",
        content_type="text/markdown",
        source_key="drive:research-note",
    )
    second = upload_bytes(
        client,
        create_batch(client, workspace["id"])["id"],
        filename="research-note-v2.md",
        content=b"# Second\n\nUpdated material.\n",
        content_type="text/markdown",
        source_key="drive:research-note",
    )

    objects = client.get(f"/api/v1/workspaces/{workspace['id']}/objects")
    assert objects.status_code == 200
    object_payload = objects.json()
    assert len(object_payload) == 1
    assert object_payload[0]["object_id"] == first["asset_id"]
    assert object_payload[0]["current_version_id"] == second["version_id"]
    assert object_payload[0]["version_count"] == 2
    assert object_payload[0]["current_version"]["content_hash"]

    searched = client.get(
        f"/api/v1/workspaces/{workspace['id']}/objects",
        params={"q": "research-note"},
    )
    assert searched.status_code == 200
    assert len(searched.json()) == 1

    detail = client.get(f"/api/v1/objects/{first['asset_id']}")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["summary"]["object_id"] == first["asset_id"]
    assert [item["version_id"] for item in detail_payload["versions"]] == [
        first["version_id"],
        second["version_id"],
    ]

    versions = client.get(f"/api/v1/objects/{first['asset_id']}/versions")
    assert versions.status_code == 200
    assert len(versions.json()) == 2

    graph = client.get(f"/api/v1/workspaces/{workspace['id']}/ontology/graph")
    assert graph.status_code == 200
    graph_payload = graph.json()
    assert graph_payload["contract_version"] == "0.1.0-m1"
    assert {node["ref"]["version_id"] for node in graph_payload["nodes"]} == {
        first["version_id"],
        second["version_id"],
    }
    assert graph_payload["edges"] == [
        {
            "edge_id": f"edge:{second['version_id']}:parent",
            "source_ref": f"{first['asset_id']}@{second['version_id']}",
            "target_ref": f"{first['asset_id']}@{first['version_id']}",
            "relation_type": "NEW_VERSION_OF",
            "state": "SYSTEM_DERIVED",
            "created_by": "SYSTEM",
            "metadata": {"projection": "deterministic_asset_version"},
        }
    ]

    project_state = client.get(
        f"/api/v1/workspaces/{workspace['id']}/project-state"
    )
    assert project_state.status_code == 200
    assert project_state.json()["asset_count"] == 1
    assert project_state.json()["version_count"] == 2
