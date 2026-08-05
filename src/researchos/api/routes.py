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
    HealthView,
    IngestItemView,
    IngestOutcomeView,
    ParseRunView,
    RepresentationView,
    VersionDetailView,
    VersionView,
    WorkspaceCreate,
    WorkspaceView,
)
from researchos.application.ingest import IngestService
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
