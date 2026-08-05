from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from researchos.api.routes import router
from researchos.config import Settings
from researchos.domain.exceptions import (
    InvariantViolationError,
    NotFoundError,
    ResearchOSError,
    UploadTooLargeError,
)
from researchos.infrastructure.blob_store import LocalContentAddressedBlobStore
from researchos.infrastructure.db import Base, build_engine, build_session_factory
from researchos.infrastructure.parsers import ParserRegistry


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    engine = build_engine(resolved_settings)
    session_factory = build_session_factory(engine)
    blob_store = LocalContentAddressedBlobStore(resolved_settings.blob_root)
    parser_registry = ParserRegistry()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if resolved_settings.database_url.startswith("sqlite"):
            Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="ResearchOS API",
        version="0.1.0",
        description="Deterministic M1 asset foundation",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.blob_store = blob_store
    app.state.parser_registry = parser_registry
    app.include_router(router)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": str(exc)},
        )

    @app.exception_handler(UploadTooLargeError)
    async def upload_too_large_handler(
        _: Request,
        exc: UploadTooLargeError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content={"code": "UPLOAD_TOO_LARGE", "message": str(exc)},
        )

    @app.exception_handler(InvariantViolationError)
    async def invariant_handler(
        _: Request,
        exc: InvariantViolationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"code": "INVARIANT_VIOLATION", "message": str(exc)},
        )

    @app.exception_handler(ResearchOSError)
    async def domain_error_handler(_: Request, exc: ResearchOSError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": type(exc).__name__, "message": str(exc)},
        )

    return app


app = create_app()
