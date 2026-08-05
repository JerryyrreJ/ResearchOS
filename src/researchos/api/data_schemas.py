from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataPluginView(StrictModel):
    plugin_id: str
    name: str
    description: str
    credential_kind: str
    license_policy: str
    supports_catalog: bool
    available: bool
    configured: bool
    enabled: bool


class DataPluginToggle(StrictModel):
    enabled: bool
    actor_id: str = Field(min_length=1, max_length=128)


class DatasetDescriptorView(StrictModel):
    dataset_id: str
    name: str
    description: str
    parameters: list[str]


class DataPluginIngestRequest(StrictModel):
    workspace_id: str = Field(min_length=3, max_length=160)
    actor_id: str = Field(min_length=1, max_length=128)
    dataset_id: str = Field(min_length=1, max_length=160)
    parameters: dict[str, Any] = Field(default_factory=dict)
    logical_name: str | None = Field(default=None, max_length=512)
    row_limit: int | None = Field(default=None, ge=1, le=1_000_000)


class DataObjectRef(StrictModel):
    contract_version: Literal["0.1.0-frozen"]
    object_id: str
    version_id: str
    object_type: Literal[
        "SOURCE_FILE",
        "CANONICAL_REPRESENTATION",
        "DATASET",
        "REPORT_RECORD",
        "MODEL_SPEC",
        "MODEL_RUN",
        "EVIDENCE_PACKAGE",
        "CLAIM",
        "ARTIFACT",
    ]
    name: str | None = None
    representation: Literal[
        "MARKDOWN", "DOCUMENT_JSON", "CSV", "PARQUET", "JSON", "PDF", "DOCX", "XLSX", "BINARY"
    ]
    schema_version: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    license_policy: Literal["PUBLIC", "INTERNAL_ONLY", "DERIVED_ONLY", "NO_PERSIST"]
    access_scope: str
    content_uri: str | None = None
    as_of_date: str | None = None
    data_schema: dict[str, Any] | None = None
    lineage_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataPluginIngestResponse(StrictModel):
    plugin_id: str
    dataset_id: str
    batch_id: str
    asset_id: str
    version_id: str
    status: str
    resolution_status: str | None
    row_count: int
    truncated: bool
    data_ref: DataObjectRef


class DatasetPreviewView(StrictModel):
    version_id: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    columns: list[str]
    rows: list[dict[str, str | None]]
    returned_rows: int
    truncated: bool


class RequiredDataSchema(StrictModel):
    time_key: str | None = None
    fields: list[str]
    frequency: list[str] = Field(default_factory=list)


class DataResolveRequest(StrictModel):
    contract_version: Literal["0.1.0-frozen"]
    request_id: str
    dataset_ref: DataObjectRef
    required_schema: RequiredDataSchema
    as_of_date: str


class ApiErrorView(StrictModel):
    contract_version: Literal["0.1.0-frozen"]
    error_code: str
    message: str
    retryable: bool
    related_refs: list[str]
    details: dict[str, Any] = Field(default_factory=dict)


class DataResolveResponse(StrictModel):
    contract_version: Literal["0.1.0-frozen"]
    request_id: str
    status: Literal["RESOLVED", "SCHEMA_MISMATCH", "PERMISSION_BLOCKED", "NOT_FOUND", "FAILED"]
    resolved_ref: DataObjectRef
    materialized_uri: str | None
    content_hash: str | None
    resolved_schema: dict[str, Any]
    lineage: list[str]
    error: ApiErrorView | None = None
