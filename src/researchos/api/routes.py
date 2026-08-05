from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from researchos import __version__
from researchos.api.dependencies import get_ingest_service, get_session
from researchos.api.schemas import (
    AssetDetailView,
    AssetSummaryView,
    BatchCreate,
    BatchFinalize,
    BatchView,
    FragmentView,
    GraphEdgeView,
    GraphNodeView,
    HealthView,
    IngestItemView,
    IngestOutcomeView,
    ObjectDetailProjectionView,
    ObjectReferenceView,
    ObjectSummaryView,
    OntologyGraphView,
    ParseRunView,
    ProjectStateView,
    RepresentationView,
    VersionDetailView,
    VersionView,
    WorkspaceCreate,
    WorkspaceView,
)
from researchos.application.ingest import IngestService
from researchos.application.ontology import OntologyQueryService
from researchos.infrastructure.orm import (
    AssetRecord,
    AssetVersionRecord,
    FragmentRecord,
    IngestBatchRecord,
    IngestItemRecord,
    ParseRunRecord,
    RepresentationRecord,
    WorkspaceRecord,
)

router = APIRouter(prefix="/api/v1")
SessionDep = Annotated[Session, Depends(get_session)]
ServiceDep = Annotated[IngestService, Depends(get_ingest_service)]


def _representation_name(format_kind: str) -> str:
    return {
        "MARKDOWN": "MARKDOWN",
        "DOCX": "DOCX",
        "XLSX": "XLSX",
        "CSV": "CSV",
        "PDF_TEXT": "PDF",
    }.get(format_kind, "BINARY")


def _ref_key(object_id: str, version_id: str) -> str:
    return f"{object_id}@{version_id}"


def _object_ref(
    asset: AssetRecord,
    version: AssetVersionRecord,
    access_scope: str,
) -> ObjectReferenceView:
    return ObjectReferenceView(
        object_id=asset.id,
        version_id=version.id,
        name=asset.logical_name,
        representation=_representation_name(version.format_kind),
        content_hash=version.content_hash,
        access_scope=access_scope,
        source_filename=version.source_filename,
        mime_type=version.mime_type,
        format_kind=version.format_kind,
        size_bytes=version.size_bytes,
        created_at=version.created_at,
        metadata=dict(version.deterministic_metadata or {}),
    )


@router.get("/health", response_model=HealthView)
def health() -> HealthView:
    return HealthView(status="ok", version=__version__)


@router.post(
    "/workspaces",
    response_model=WorkspaceView,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(payload: WorkspaceCreate, service: ServiceDep) -> WorkspaceRecord:
    return service.create_workspace(
        name=payload.name,
        description=payload.description,
        actor_id=payload.actor_id,
    )


@router.get("/workspaces", response_model=list[WorkspaceView])
def list_workspaces(session: SessionDep) -> list[WorkspaceRecord]:
    return list(session.scalars(select(WorkspaceRecord).order_by(WorkspaceRecord.created_at)))


@router.post(
    "/workspaces/{workspace_id}/ingest-batches",
    response_model=BatchView,
    status_code=status.HTTP_201_CREATED,
)
def create_ingest_batch(
    workspace_id: str,
    payload: BatchCreate,
    service: ServiceDep,
) -> BatchView:
    batch = service.create_batch(workspace_id=workspace_id, actor_id=payload.actor_id)
    return BatchView.model_validate(batch)


@router.post(
    "/ingest-batches/{batch_id}/items",
    response_model=IngestOutcomeView,
    status_code=status.HTTP_201_CREATED,
)
def upload_ingest_item(
    batch_id: str,
    service: ServiceDep,
    file: Annotated[UploadFile, File()],
    actor_id: Annotated[str, Form()],
    logical_name: Annotated[str | None, Form()] = None,
    asset_id: Annotated[str | None, Form()] = None,
    source_key: Annotated[str | None, Form()] = None,
    force_new_asset: Annotated[bool, Form()] = False,
) -> IngestOutcomeView:
    outcome = service.ingest_item(
        batch_id=batch_id,
        stream=file.file,
        original_filename=file.filename or "unnamed",
        actor_id=actor_id,
        logical_name=logical_name,
        asset_id=asset_id,
        source_key=source_key,
        force_new_asset=force_new_asset,
    )
    return IngestOutcomeView.model_validate(outcome, from_attributes=True)


@router.post("/ingest-batches/{batch_id}/finalize", response_model=BatchView)
def finalize_ingest_batch(
    batch_id: str,
    payload: BatchFinalize,
    service: ServiceDep,
    session: SessionDep,
) -> BatchView:
    batch = service.finalize_batch(batch_id=batch_id, actor_id=payload.actor_id)
    items = list(
        session.scalars(
            select(IngestItemRecord)
            .where(IngestItemRecord.batch_id == batch.id)
            .order_by(IngestItemRecord.created_at)
        )
    )
    return BatchView(
        **BatchView.model_validate(batch).model_dump(exclude={"items"}),
        items=[IngestItemView.model_validate(item) for item in items],
    )


@router.get("/ingest-batches/{batch_id}", response_model=BatchView)
def get_ingest_batch(batch_id: str, session: SessionDep) -> BatchView:
    batch = session.get(IngestBatchRecord, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="ingest batch not found")
    items = list(
        session.scalars(
            select(IngestItemRecord)
            .where(IngestItemRecord.batch_id == batch.id)
            .order_by(IngestItemRecord.created_at)
        )
    )
    return BatchView(
        **BatchView.model_validate(batch).model_dump(exclude={"items"}),
        items=[IngestItemView.model_validate(item) for item in items],
    )


@router.get(
    "/workspaces/{workspace_id}/assets",
    response_model=list[AssetSummaryView],
)
def list_assets(workspace_id: str, session: SessionDep) -> list[AssetRecord]:
    if session.get(WorkspaceRecord, workspace_id) is None:
        raise HTTPException(status_code=404, detail="workspace not found")
    return list(
        session.scalars(
            select(AssetRecord)
            .where(AssetRecord.workspace_id == workspace_id)
            .order_by(AssetRecord.created_at)
        )
    )


@router.get(
    "/workspaces/{workspace_id}/objects",
    response_model=list[ObjectSummaryView],
)
def list_objects(
    workspace_id: str,
    session: SessionDep,
    q: str | None = None,
) -> list[ObjectSummaryView]:
    """Return version-aware object summaries for the browser workspace."""
    query_service = OntologyQueryService(session)
    try:
        assets = query_service.list_assets(workspace_id, query=q)
        graph = query_service.build_graph(workspace_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    versions_by_asset: dict[str, list[AssetVersionRecord]] = {}
    for version in graph.versions:
        versions_by_asset.setdefault(version.asset_id, []).append(version)
    representations_by_version = graph.representations_by_version

    summaries: list[ObjectSummaryView] = []
    for asset in assets:
        versions = versions_by_asset.get(asset.id, [])
        current = next(
            (version for version in versions if version.id == asset.current_version_id),
            None,
        )
        representation_count = sum(
            len(representations_by_version.get(version.id, [])) for version in versions
        )
        fragment_count = sum(graph.fragments_by_version.get(version.id, 0) for version in versions)
        summaries.append(
            ObjectSummaryView(
                object_id=asset.id,
                workspace_id=asset.workspace_id,
                name=asset.logical_name,
                current_version_id=asset.current_version_id,
                status=asset.status,
                created_by=asset.created_by,
                created_at=asset.created_at,
                version_count=len(versions),
                representation_count=representation_count,
                fragment_count=fragment_count,
                current_version=(
                    _object_ref(asset, current, workspace_id) if current is not None else None
                ),
            )
        )
    return summaries


@router.get(
    "/objects/{object_id}",
    response_model=ObjectDetailProjectionView,
)
def get_object(object_id: str, session: SessionDep) -> ObjectDetailProjectionView:
    query_service = OntologyQueryService(session)
    try:
        asset, versions = query_service.get_asset(object_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    representations = list(
        session.scalars(
            select(RepresentationRecord).where(
                RepresentationRecord.version_id.in_([version.id for version in versions])
            )
        )
    ) if versions else []
    fragments = list(
        session.scalars(
            select(FragmentRecord).where(
                FragmentRecord.version_id.in_([version.id for version in versions])
            )
        )
    ) if versions else []
    current = next(
        (version for version in versions if version.id == asset.current_version_id),
        None,
    )
    summary = ObjectSummaryView(
        object_id=asset.id,
        workspace_id=asset.workspace_id,
        name=asset.logical_name,
        current_version_id=asset.current_version_id,
        status=asset.status,
        created_by=asset.created_by,
        created_at=asset.created_at,
        version_count=len(versions),
        representation_count=len(representations),
        fragment_count=len(fragments),
        current_version=(_object_ref(asset, current, asset.workspace_id) if current else None),
    )
    return ObjectDetailProjectionView(
        summary=summary,
        versions=[_object_ref(asset, version, asset.workspace_id) for version in versions],
    )


@router.get(
    "/objects/{object_id}/versions",
    response_model=list[ObjectReferenceView],
)
def list_object_versions(object_id: str, session: SessionDep) -> list[ObjectReferenceView]:
    query_service = OntologyQueryService(session)
    try:
        asset, versions = query_service.get_asset(object_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_object_ref(asset, version, asset.workspace_id) for version in versions]


@router.get(
    "/workspaces/{workspace_id}/ontology/graph",
    response_model=OntologyGraphView,
)
def get_ontology_graph(workspace_id: str, session: SessionDep) -> OntologyGraphView:
    query_service = OntologyQueryService(session)
    try:
        graph = query_service.build_graph(workspace_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    assets_by_id = {asset.id: asset for asset in graph.assets}
    nodes: list[GraphNodeView] = []
    edges: list[GraphEdgeView] = []
    for version in graph.versions:
        asset = assets_by_id[version.asset_id]
        node_id = _ref_key(asset.id, version.id)
        nodes.append(
            GraphNodeView(
                node_id=node_id,
                ref=_object_ref(asset, version, workspace_id),
                label=asset.logical_name,
                metadata={
                    "is_current": asset.current_version_id == version.id,
                    "representation_count": len(
                        graph.representations_by_version.get(version.id, [])
                    ),
                    "fragment_count": graph.fragments_by_version.get(version.id, 0),
                },
            )
        )
        if version.parent_version_id:
            edges.append(
                GraphEdgeView(
                    edge_id=f"edge:{version.id}:parent",
                    source_ref=node_id,
                    target_ref=_ref_key(asset.id, version.parent_version_id),
                    relation_type="NEW_VERSION_OF",
                    metadata={"projection": "deterministic_asset_version"},
                )
            )
    return OntologyGraphView(
        workspace_id=workspace_id,
        generated_at=datetime.now(UTC),
        nodes=nodes,
        edges=edges,
    )


@router.get(
    "/workspaces/{workspace_id}/project-state",
    response_model=ProjectStateView,
)
def get_project_state(workspace_id: str, session: SessionDep) -> ProjectStateView:
    query_service = OntologyQueryService(session)
    try:
        state = query_service.project_state(workspace_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProjectStateView(workspace_id=workspace_id, **state)


@router.get("/assets/{asset_id}", response_model=AssetDetailView)
def get_asset(asset_id: str, session: SessionDep) -> AssetDetailView:
    asset = session.get(AssetRecord, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    versions = list(
        session.scalars(
            select(AssetVersionRecord)
            .where(AssetVersionRecord.asset_id == asset.id)
            .order_by(AssetVersionRecord.created_at)
        )
    )
    return AssetDetailView(
        **AssetSummaryView.model_validate(asset).model_dump(),
        versions=[VersionView.model_validate(version) for version in versions],
    )


@router.get("/asset-versions/{version_id}", response_model=VersionDetailView)
def get_asset_version(version_id: str, session: SessionDep) -> VersionDetailView:
    version = session.get(AssetVersionRecord, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="asset version not found")
    representations = list(
        session.scalars(
            select(RepresentationRecord)
            .where(RepresentationRecord.version_id == version.id)
            .order_by(RepresentationRecord.created_at)
        )
    )
    fragments = list(
        session.scalars(
            select(FragmentRecord)
            .where(FragmentRecord.version_id == version.id)
            .order_by(FragmentRecord.representation_id, FragmentRecord.ordinal)
        )
    )
    parse_runs = list(
        session.scalars(
            select(ParseRunRecord)
            .where(ParseRunRecord.version_id == version.id)
            .order_by(ParseRunRecord.started_at)
        )
    )
    return VersionDetailView(
        **VersionView.model_validate(version).model_dump(),
        representations=[
            RepresentationView.model_validate(representation) for representation in representations
        ],
        fragments=[FragmentView.model_validate(fragment) for fragment in fragments],
        parse_runs=[ParseRunView.model_validate(parse_run) for parse_run in parse_runs],
    )
