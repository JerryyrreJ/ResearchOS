from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from researchos.api.main import create_app
from researchos.config import Settings


@pytest.fixture
def app(tmp_path: Path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'researchos-test.db'}",
        blob_root=tmp_path / "blobs",
        max_upload_bytes=10 * 1024 * 1024,
        inline_jobs=True,
    )
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def workspace(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "Deterministic Research",
            "description": "M1 tests",
            "actor_id": "user-test",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_batch(client: TestClient, workspace_id: str) -> dict:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/ingest-batches",
        json={"actor_id": "user-test"},
    )
    assert response.status_code == 201
    return response.json()


def upload_bytes(
    client: TestClient,
    batch_id: str,
    *,
    filename: str,
    content: bytes,
    content_type: str,
    source_key: str | None = None,
    asset_id: str | None = None,
    force_new_asset: bool = False,
) -> dict:
    data: dict[str, str] = {
        "actor_id": "user-test",
        "force_new_asset": str(force_new_asset).lower(),
    }
    if source_key is not None:
        data["source_key"] = source_key
    if asset_id is not None:
        data["asset_id"] = asset_id
    response = client.post(
        f"/api/v1/ingest-batches/{batch_id}/items",
        data=data,
        files={"file": (filename, content, content_type)},
    )
    assert response.status_code == 201, response.text
    return response.json()
