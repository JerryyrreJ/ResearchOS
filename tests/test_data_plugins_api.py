import json
from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, RefResolver

from researchos.application.data_plugins import (
    DataPluginRegistry,
    DatasetDescriptor,
    PluginDataset,
    PluginDescriptor,
)

ROOT = Path(__file__).parents[1]


class FakeProvider:
    descriptor = PluginDescriptor(
        plugin_id="fixture-data",
        name="Fixture Data",
        description="Deterministic plugin test provider",
        credential_kind="NONE",
        license_policy="PUBLIC",
    )
    available = True
    configured = True

    def list_datasets(self, query_text: str | None, limit: int) -> list[DatasetDescriptor]:
        row = DatasetDescriptor(
            dataset_id="monthly_macro",
            name="Monthly macro fixture",
            description="A deterministic two-row dataset",
            parameters=["revision"],
        )
        return [row] if not query_text or query_text.lower() in row.name.lower() else []

    def fetch(
        self,
        dataset_id: str,
        parameters: dict,
        row_limit: int,
    ) -> PluginDataset:
        assert dataset_id == "monthly_macro"
        content = b"date,value\n2026-06-01,4.1\n2026-07-01,4.2\n"
        return PluginDataset(
            content=content,
            filename="monthly-macro.csv",
            row_count=min(2, row_limit),
            truncated=False,
            provenance={
                "plugin_id": "fixture-data",
                "dataset_id": dataset_id,
                "parameters": parameters,
                "fields": ["date", "value"],
                "time_key": "date",
                "frequency": "M",
                "as_of_date": "2026-07-01",
                "license_policy": "PUBLIC",
                "schema_version": "fixture-v1",
                "field_types": {"date": "date", "value": "float64"},
                "lineage_refs": ["PLUGIN:FIXTURE:monthly_macro"],
            },
        )


def install_fixture_provider(app) -> None:
    app.state.data_plugin_registry = DataPluginRegistry([FakeProvider()])


def test_plugin_catalog_toggle_ingest_and_resolve(
    app,
    client: TestClient,
    workspace: dict,
) -> None:
    install_fixture_provider(app)

    catalog = client.get("/api/v1/data-plugins")
    assert catalog.status_code == 200
    assert catalog.json()[0]["enabled"] is False
    assert "api_key" not in json.dumps(catalog.json()).lower()

    enabled = client.put(
        "/api/v1/data-plugins/fixture-data",
        json={"enabled": True, "actor_id": "test-user"},
    )
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True

    datasets = client.get("/api/v1/data-plugins/fixture-data/datasets?q=monthly")
    assert datasets.status_code == 200
    assert datasets.json()[0]["dataset_id"] == "monthly_macro"

    ingested = client.post(
        "/api/v1/data-plugins/fixture-data/ingest",
        json={
            "workspace_id": workspace["id"],
            "actor_id": "test-user",
            "dataset_id": "monthly_macro",
            "parameters": {"revision": "first"},
            "row_limit": 100,
        },
    )
    assert ingested.status_code == 201, ingested.text
    result = ingested.json()
    assert result["resolution_status"] == "NEW_ASSET"
    assert result["data_ref"]["object_type"] == "DATASET"
    assert result["data_ref"]["data_schema"]["frequency"] == "M"

    request_payload = {
        "contract_version": "0.1.0-frozen",
        "request_id": "REQ_RESOLVE_FIXTURE_001",
        "dataset_ref": result["data_ref"],
        "required_schema": {
            "time_key": "date",
            "fields": ["date", "value"],
            "frequency": ["M"],
        },
        "as_of_date": "2026-08-05",
    }
    resolved = client.post("/api/v1/data/resolve", json=request_payload)
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "RESOLVED"

    contract_root = ROOT / "contracts" / "v1"
    schema = json.loads((contract_root / "data_resolve.schema.json").read_text())
    referenced = ["data_object_ref.schema.json", "api_error.schema.json"]
    store = {
        document["$id"]: document
        for name in referenced
        for document in [json.loads((contract_root / name).read_text())]
    }
    resolver = RefResolver.from_schema(schema, store=store)
    Draft202012Validator(schema, resolver=resolver).validate(resolved.json())

    content = client.get(resolved.json()["materialized_uri"])
    assert content.status_code == 200
    assert content.content.startswith(b"date,value")
    assert content.headers["x-researchos-content-sha256"] == result["data_ref"]["content_hash"]

    preview = client.get(f"/api/v1/asset-versions/{result['version_id']}/preview?limit=1")
    assert preview.status_code == 200
    assert preview.json() == {
        "version_id": result["version_id"],
        "content_hash": result["data_ref"]["content_hash"],
        "columns": ["date", "value"],
        "rows": [{"date": "2026-06-01", "value": "4.1"}],
        "returned_rows": 1,
        "truncated": True,
    }

    replay = client.post(
        "/api/v1/data-plugins/fixture-data/ingest",
        json={
            "workspace_id": workspace["id"],
            "actor_id": "test-user",
            "dataset_id": "monthly_macro",
            "parameters": {"revision": "first"},
        },
    )
    assert replay.json()["resolution_status"] == "EXACT_DUPLICATE"
    assert replay.json()["version_id"] == result["version_id"]


def test_resolve_preserves_failure_states(app, client: TestClient, workspace: dict) -> None:
    install_fixture_provider(app)
    client.put(
        "/api/v1/data-plugins/fixture-data",
        json={"enabled": True, "actor_id": "test-user"},
    )
    data_ref = client.post(
        "/api/v1/data-plugins/fixture-data/ingest",
        json={
            "workspace_id": workspace["id"],
            "actor_id": "test-user",
            "dataset_id": "monthly_macro",
            "parameters": {},
        },
    ).json()["data_ref"]
    base = {
        "contract_version": "0.1.0-frozen",
        "request_id": "REQ_FAILURE_001",
        "dataset_ref": data_ref,
        "required_schema": {"time_key": "date", "fields": ["date", "value"], "frequency": ["M"]},
        "as_of_date": "2026-08-05",
    }

    bad_hash = deepcopy(base)
    bad_hash["dataset_ref"]["content_hash"] = "0" * 64
    assert client.post("/api/v1/data/resolve", json=bad_hash).json()["status"] == "FAILED"

    bad_scope = deepcopy(base)
    bad_scope["dataset_ref"]["access_scope"] = "WORKSPACE:OTHER"
    assert (
        client.post("/api/v1/data/resolve", json=bad_scope).json()["status"] == "PERMISSION_BLOCKED"
    )

    bad_schema = deepcopy(base)
    bad_schema["required_schema"]["fields"].append("missing_column")
    assert (
        client.post("/api/v1/data/resolve", json=bad_schema).json()["status"] == "SCHEMA_MISMATCH"
    )

    future = deepcopy(base)
    future["as_of_date"] = "2026-06-01"
    assert client.post("/api/v1/data/resolve", json=future).json()["status"] == "NOT_FOUND"


def test_disabled_plugin_and_extra_fields_are_rejected(
    app,
    client: TestClient,
    workspace: dict,
) -> None:
    install_fixture_provider(app)
    disabled = client.post(
        "/api/v1/data-plugins/fixture-data/ingest",
        json={
            "workspace_id": workspace["id"],
            "actor_id": "test-user",
            "dataset_id": "monthly_macro",
            "parameters": {},
        },
    )
    assert disabled.status_code == 422

    invalid = client.put(
        "/api/v1/data-plugins/fixture-data",
        json={"enabled": True, "actor_id": "test-user", "api_key": "must-not-be-accepted"},
    )
    assert invalid.status_code == 422
