from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from researchos.api.data_schemas import (
    DataPluginIngestRequest,
    DataPluginIngestResponse,
    DataPluginToggle,
    DataPluginView,
    DataResolveRequest,
    DataResolveResponse,
    DatasetDescriptorView,
    DatasetPreviewView,
)
from researchos.api.dependencies import get_data_plugin_service, get_data_resolve_service
from researchos.application.data_plugins import DataPluginService
from researchos.application.data_resolve import DataResolveService

router = APIRouter(prefix="/api/v1")
PluginServiceDep = Annotated[DataPluginService, Depends(get_data_plugin_service)]
ResolveServiceDep = Annotated[DataResolveService, Depends(get_data_resolve_service)]


@router.get("/data-plugins", response_model=list[DataPluginView])
def list_data_plugins(service: PluginServiceDep) -> list[dict]:
    return service.list_plugins()


@router.put("/data-plugins/{plugin_id}", response_model=DataPluginView)
def configure_data_plugin(
    plugin_id: str,
    payload: DataPluginToggle,
    service: PluginServiceDep,
) -> dict:
    return service.set_enabled(plugin_id, payload.enabled, payload.actor_id)


@router.get(
    "/data-plugins/{plugin_id}/datasets",
    response_model=list[DatasetDescriptorView],
)
def list_plugin_datasets(
    plugin_id: str,
    service: PluginServiceDep,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[dict]:
    return service.list_datasets(plugin_id, q, limit)


@router.post(
    "/data-plugins/{plugin_id}/ingest",
    response_model=DataPluginIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_plugin_dataset(
    plugin_id: str,
    payload: DataPluginIngestRequest,
    service: PluginServiceDep,
) -> dict:
    return service.ingest(plugin_id=plugin_id, **payload.model_dump())


@router.post("/data/resolve", response_model=DataResolveResponse)
def resolve_data(
    payload: DataResolveRequest,
    service: ResolveServiceDep,
) -> dict:
    return service.resolve(payload.model_dump())


@router.get("/asset-versions/{version_id}/content")
def materialize_asset_version(
    version_id: str,
    service: ResolveServiceDep,
) -> FileResponse:
    content = service.content(version_id)
    if content is None:
        raise HTTPException(status_code=404, detail="asset version content not found")
    return FileResponse(
        path=content.path,
        media_type=content.media_type,
        filename=content.filename,
        headers={"X-ResearchOS-Content-SHA256": content.content_hash},
    )


@router.get(
    "/asset-versions/{version_id}/preview",
    response_model=DatasetPreviewView,
)
def preview_asset_version(
    version_id: str,
    service: ResolveServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict:
    preview = service.preview(version_id, limit)
    if preview is None:
        raise HTTPException(
            status_code=404,
            detail="CSV dataset preview is unavailable for this asset version",
        )
    return preview
