from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .contracts import ContractViolation, UnsafeControlField
from .service import (
    FixtureToolRunService,
    InvalidFixtureScenario,
    RequestIdConflict,
    ToolRunNotFound,
    UnsafeArtifactReference,
)


router = APIRouter(tags=["ResearchOS MacroTrace Tool Adapter"])
service = FixtureToolRunService()


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "TOOL_RUN_NOT_FOUND", "message": "Tool run not found."})


@router.post("/v1/tool-runs/macrotrace", status_code=202)
def create_macrotrace_tool_run(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        return service.create(payload)
    except ContractViolation as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_TOOL_REQUEST", "contract": exc.contract_name, "errors": list(exc.errors)},
        ) from None
    except UnsafeControlField as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "FORBIDDEN_EXECUTION_CONTROL", "field_path": exc.path},
        ) from None
    except InvalidFixtureScenario:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_FIXTURE_SCENARIO", "message": "Fixture scenario is not registered."},
        ) from None
    except RequestIdConflict:
        raise HTTPException(
            status_code=409,
            detail={"code": "REQUEST_ID_CONFLICT", "message": "request_id was already used with different content."},
        ) from None
    except UnsafeArtifactReference:
        raise HTTPException(
            status_code=500,
            detail={"code": "UNSAFE_FIXTURE_ARTIFACT", "message": "Fixture artifact failed boundary validation."},
        ) from None


@router.get("/v1/tool-runs/{tool_run_id}")
def get_macrotrace_tool_run(tool_run_id: str) -> dict[str, Any]:
    try:
        return service.get(tool_run_id)
    except ToolRunNotFound:
        raise _not_found() from None


@router.get("/v1/tool-runs/{tool_run_id}/graph")
def get_macrotrace_tool_graph(tool_run_id: str) -> dict[str, Any]:
    try:
        return service.graph(tool_run_id)
    except ToolRunNotFound:
        raise _not_found() from None


@router.get("/v1/tool-runs/{tool_run_id}/artifacts")
def get_macrotrace_tool_artifacts(tool_run_id: str) -> dict[str, Any]:
    try:
        return service.artifacts(tool_run_id)
    except ToolRunNotFound:
        raise _not_found() from None
    except UnsafeArtifactReference:
        raise HTTPException(
            status_code=500,
            detail={"code": "UNSAFE_FIXTURE_ARTIFACT", "message": "Fixture artifact failed boundary validation."},
        ) from None
