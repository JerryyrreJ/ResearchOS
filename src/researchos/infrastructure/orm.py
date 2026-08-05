from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.orm import Mapped, mapped_column

from researchos.domain.enums import (
    ActorType,
    AssetStatus,
    BatchStatus,
    IngestItemStatus,
    ParseStatus,
    RepresentationType,
    SourceKind,
)
from researchos.domain.exceptions import InvariantViolationError
from researchos.infrastructure.db import Base
from researchos.infrastructure.ids import new_id


def utc_now() -> datetime:
    return datetime.now(UTC)


class WorkspaceRecord(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ws"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    status: Mapped[str] = mapped_column(String(32), default=AssetStatus.ACTIVE.value)


class BlobRecord(Base):
    __tablename__ = "blobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("blob"))
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_mode: Mapped[str] = mapped_column(String(32), default="FULL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AssetRecord(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("workspace_id", "source_key", name="uq_asset_workspace_source"),
        Index("ix_assets_workspace_name", "workspace_id", "logical_name"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("asset"))
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )
    logical_name: Mapped[str] = mapped_column(String(512))
    source_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    current_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default=AssetStatus.ACTIVE.value)
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AssetVersionRecord(Base):
    __tablename__ = "asset_versions"
    __table_args__ = (
        UniqueConstraint("asset_id", "content_hash", name="uq_asset_version_content"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ver"))
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"),
        index=True,
    )
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("asset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    blob_id: Mapped[str] = mapped_column(ForeignKey("blobs.id"), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    mime_type: Mapped[str] = mapped_column(String(255))
    format_kind: Mapped[str] = mapped_column(String(32))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    source_kind: Mapped[str] = mapped_column(
        String(32),
        default=SourceKind.BROWSER_UPLOAD.value,
    )
    source_filename: Mapped[str] = mapped_column(String(1024))
    deterministic_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RepresentationRecord(Base):
    __tablename__ = "representations"
    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "representation_type",
            "generator",
            "generator_version",
            name="uq_representation_generator",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rep"))
    version_id: Mapped[str] = mapped_column(
        ForeignKey("asset_versions.id", ondelete="CASCADE"),
        index=True,
    )
    representation_type: Mapped[str] = mapped_column(
        String(32),
        default=RepresentationType.ORIGINAL.value,
    )
    mime_type: Mapped[str] = mapped_column(String(255))
    blob_id: Mapped[str] = mapped_column(ForeignKey("blobs.id"), index=True)
    generator: Mapped[str] = mapped_column(String(128))
    generator_version: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FragmentRecord(Base):
    __tablename__ = "fragments"
    __table_args__ = (
        UniqueConstraint("representation_id", "ordinal", name="uq_fragment_ordinal"),
        Index("ix_fragments_version_representation", "version_id", "representation_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("frag"))
    version_id: Mapped[str] = mapped_column(
        ForeignKey("asset_versions.id", ondelete="CASCADE"),
        index=True,
    )
    representation_id: Mapped[str] = mapped_column(
        ForeignKey("representations.id", ondelete="CASCADE"),
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    fragment_type: Mapped[str] = mapped_column(String(32))
    locator_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    text_or_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    excerpt_hash: Mapped[str] = mapped_column(String(64), index=True)
    quality: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IngestBatchRecord(Base):
    __tablename__ = "ingest_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("batch"))
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )
    uploaded_by: Mapped[str] = mapped_column(String(128))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=BatchStatus.OPEN.value)
    auto_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class IngestItemRecord(Base):
    __tablename__ = "ingest_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("item"))
    batch_id: Mapped[str] = mapped_column(
        ForeignKey("ingest_batches.id", ondelete="CASCADE"),
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(1024))
    source_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    detected_mime: Mapped[str | None] = mapped_column(String(255), nullable=True)
    format_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    blob_id: Mapped[str | None] = mapped_column(ForeignKey("blobs.id"), nullable=True)
    resolved_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("assets.id"),
        nullable=True,
    )
    created_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("asset_versions.id"),
        nullable=True,
    )
    resolution_status: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=IngestItemStatus.QUEUED.value,
    )
    warnings_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ParseRunRecord(Base):
    __tablename__ = "parse_runs"
    __table_args__ = (
        UniqueConstraint("version_id", "parser_name", "parser_version", name="uq_parse_run"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("parse"))
    version_id: Mapped[str] = mapped_column(
        ForeignKey("asset_versions.id", ondelete="CASCADE"),
        index=True,
    )
    parser_name: Mapped[str] = mapped_column(String(128))
    parser_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default=ParseStatus.QUEUED.value)
    representation_id: Mapped[str | None] = mapped_column(
        ForeignKey("representations.id"),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_workspace_created", "workspace_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("audit"))
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )
    actor_type: Mapped[str] = mapped_column(String(32), default=ActorType.SYSTEM.value)
    actor_id: Mapped[str] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(128))
    subject_type: Mapped[str] = mapped_column(String(64))
    subject_id: Mapped[str] = mapped_column(String(64))
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


@event.listens_for(AssetVersionRecord, "before_update")
def prevent_asset_version_mutation(_mapper, _connection, target: AssetVersionRecord) -> None:
    state = inspect(target)
    changed = [attribute.key for attribute in state.attrs if attribute.history.has_changes()]
    if changed:
        raise InvariantViolationError(
            "AssetVersion is immutable; create a new version instead "
            f"(changed fields: {', '.join(sorted(changed))})"
        )
