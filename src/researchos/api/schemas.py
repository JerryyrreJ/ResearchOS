from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    actor_id: str = Field(min_length=1, max_length=128)


class WorkspaceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    created_by: str
    created_at: datetime
    status: str


class BatchCreate(BaseModel):
    actor_id: str = Field(min_length=1, max_length=128)


class BatchFinalize(BaseModel):
    actor_id: str = Field(min_length=1, max_length=128)


class IngestItemView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    batch_id: str
    original_filename: str
    source_key: str | None
    detected_mime: str | None
    format_kind: str | None
    blob_id: str | None
    resolved_asset_id: str | None
    created_version_id: str | None
    resolution_status: str | None
    status: str
    warnings_json: list[str]
    error: str | None
    created_at: datetime
    completed_at: datetime | None


class BatchView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    uploaded_by: str
    started_at: datetime
    completed_at: datetime | None
    status: str
    auto_summary: str | None
    items: list[IngestItemView] = Field(default_factory=list)


class IngestOutcomeView(BaseModel):
    item_id: str
    asset_id: str | None
    version_id: str | None
    resolution_status: str | None
    status: str
    error: str | None


class AssetSummaryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    logical_name: str
    source_key: str | None
    current_version_id: str | None
    status: str
    created_by: str
    created_at: datetime


class VersionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    parent_version_id: str | None
    blob_id: str
    content_hash: str
    mime_type: str
    format_kind: str
    size_bytes: int
    source_kind: str
    source_filename: str
    deterministic_metadata: dict[str, Any]
    created_by: str
    created_at: datetime


class RepresentationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_id: str
    representation_type: str
    mime_type: str
    blob_id: str
    generator: str
    generator_version: str
    metadata_json: dict[str, Any]
    created_at: datetime


class FragmentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_id: str
    representation_id: str
    ordinal: int
    fragment_type: str
    locator_json: dict[str, Any]
    text_or_value: str | None
    excerpt_hash: str
    quality: float
    created_at: datetime


class ParseRunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_id: str
    parser_name: str
    parser_version: str
    status: str
    representation_id: str | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None


class AssetDetailView(AssetSummaryView):
    versions: list[VersionView]


class ObjectReferenceView(BaseModel):
    """Version-pinned object reference exposed by the M1 query projection."""

    contract_version: Literal["0.1.0-m1"] = "0.1.0-m1"
    object_id: str
    version_id: str
    object_type: Literal["SOURCE_FILE"] = "SOURCE_FILE"
    name: str
    representation: str
    schema_version: str = "m1.asset.v1"
    content_hash: str
    access_scope: str
    source_filename: str
    mime_type: str
    format_kind: str
    size_bytes: int
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObjectSummaryView(BaseModel):
    object_id: str
    workspace_id: str
    name: str
    current_version_id: str | None
    status: str
    created_by: str
    created_at: datetime
    version_count: int
    representation_count: int
    fragment_count: int
    current_version: ObjectReferenceView | None = None


class ObjectDetailProjectionView(BaseModel):
    summary: ObjectSummaryView
    versions: list[ObjectReferenceView]


class GraphNodeView(BaseModel):
    node_id: str
    ref: ObjectReferenceView
    label: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeView(BaseModel):
    edge_id: str
    source_ref: str
    target_ref: str
    relation_type: Literal["NEW_VERSION_OF"]
    state: Literal["SYSTEM_DERIVED"] = "SYSTEM_DERIVED"
    created_by: Literal["SYSTEM"] = "SYSTEM"
    metadata: dict[str, Any] = Field(default_factory=dict)


class OntologyGraphView(BaseModel):
    contract_version: Literal["0.1.0-m1"] = "0.1.0-m1"
    workspace_id: str
    generated_at: datetime
    nodes: list[GraphNodeView]
    edges: list[GraphEdgeView]


class ProjectStateView(BaseModel):
    workspace_id: str
    asset_count: int
    version_count: int
    representation_count: int
    fragment_count: int
    parse_run_counts: dict[str, int]
    ingest_item_counts: dict[str, int]


class VersionDetailView(VersionView):
    representations: list[RepresentationView]
    fragments: list[FragmentView]
    parse_runs: list[ParseRunView]


class HealthView(BaseModel):
    status: str
    version: str


class ApiError(BaseModel):
    code: str
    message: str
