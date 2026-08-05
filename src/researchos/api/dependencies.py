from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from researchos.application.ingest import IngestService


def get_session(request: Request) -> Iterator[Session]:
    factory = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_ingest_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> IngestService:
    return IngestService(
        session=session,
        blob_store=request.app.state.blob_store,
        parser_registry=request.app.state.parser_registry,
        max_upload_bytes=request.app.state.settings.max_upload_bytes,
    )
