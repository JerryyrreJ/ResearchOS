from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, BinaryIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from researchos.domain.contracts import BlobStore
from researchos.domain.enums import (
    ActorType,
    BatchStatus,
    FormatKind,
    IngestItemStatus,
    ParseStatus,
    RepresentationType,
    ResolutionStatus,
    SourceKind,
)
from researchos.domain.exceptions import (
    InvariantViolationError,
    NotFoundError,
    UnsupportedFormatError,
)
from researchos.infrastructure.format_detection import detect_format
from researchos.infrastructure.metadata import extract_deterministic_metadata
from researchos.infrastructure.orm import (
    AssetRecord,
    AssetVersionRecord,
    AuditEventRecord,
    BlobRecord,
    FragmentRecord,
    IngestBatchRecord,
    IngestItemRecord,
    ParseRunRecord,
    RepresentationRecord,
    WorkspaceRecord,
)
from researchos.infrastructure.parsers import ParserRegistry


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class IngestOutcome:
    item_id: str
    asset_id: str | None
    version_id: str | None
    resolution_status: str | None
    status: str
    error: str | None


class IngestService:
    def __init__(
        self,
        session: Session,
        blob_store: BlobStore,
        parser_registry: ParserRegistry,
        *,
        max_upload_bytes: int,
    ) -> None:
        self.session = session
        self.blob_store = blob_store
        self.parser_registry = parser_registry
        self.max_upload_bytes = max_upload_bytes

    def create_workspace(
        self,
        *,
        name: str,
        actor_id: str,
        description: str | None = None,
    ) -> WorkspaceRecord:
        workspace = WorkspaceRecord(
            name=name.strip(),
            description=description,
            created_by=actor_id,
        )
        if not workspace.name:
            raise InvariantViolationError("workspace name cannot be empty")
        self.session.add(workspace)
        self.session.flush()
        self._audit(
            workspace_id=workspace.id,
            actor_id=actor_id,
            event_type="WORKSPACE_CREATED",
            subject_type="Workspace",
            subject_id=workspace.id,
            details={"name": workspace.name},
        )
        self.session.commit()
        return workspace

    def create_batch(self, *, workspace_id: str, actor_id: str) -> IngestBatchRecord:
        self._workspace(workspace_id)
        batch = IngestBatchRecord(
            workspace_id=workspace_id,
            uploaded_by=actor_id,
            status=BatchStatus.OPEN.value,
        )
        self.session.add(batch)
        self.session.flush()
        self._audit(
            workspace_id=workspace_id,
            actor_id=actor_id,
            event_type="INGEST_BATCH_CREATED",
            subject_type="IngestBatch",
            subject_id=batch.id,
            details={},
        )
        self.session.commit()
        return batch

    def ingest_item(
        self,
        *,
        batch_id: str,
        stream: BinaryIO,
        original_filename: str,
        actor_id: str,
        logical_name: str | None = None,
        asset_id: str | None = None,
        source_key: str | None = None,
        force_new_asset: bool = False,
    ) -> IngestOutcome:
        batch = self._batch(batch_id)
        if batch.status not in {BatchStatus.OPEN.value, BatchStatus.RUNNING.value}:
            raise InvariantViolationError("cannot add items to a completed ingest batch")

        safe_filename = Path(original_filename).name
        if not safe_filename:
            raise InvariantViolationError("original filename cannot be empty")

        item = IngestItemRecord(
            batch_id=batch.id,
            original_filename=safe_filename,
            source_key=source_key,
            status=IngestItemStatus.QUEUED.value,
        )
        batch.status = BatchStatus.RUNNING.value
        self.session.add(item)
        self.session.commit()

        try:
            stored = self.blob_store.put_stream(stream, max_bytes=self.max_upload_bytes)
            detected = detect_format(stored.path, safe_filename)
            metadata = extract_deterministic_metadata(
                detected.kind,
                stored.path,
                safe_filename,
            )

            blob = self._get_or_create_blob(
                content_hash=stored.sha256,
                storage_key=stored.storage_key,
                size_bytes=stored.size_bytes,
            )
            item.detected_mime = detected.mime_type
            item.format_kind = detected.kind.value
            item.blob_id = blob.id
            item.warnings_json = list(detected.warnings)
            item.status = IngestItemStatus.STORED.value
            self.session.commit()

            asset, version, resolution = self._resolve_version(
                workspace_id=batch.workspace_id,
                actor_id=actor_id,
                filename=safe_filename,
                logical_name=logical_name,
                asset_id=asset_id,
                source_key=source_key,
                force_new_asset=force_new_asset,
                blob=blob,
                detected_kind=detected.kind,
                mime_type=detected.mime_type,
                metadata=metadata,
            )
            item.resolved_asset_id = asset.id
            item.created_version_id = version.id
            item.resolution_status = resolution.value

            if resolution == ResolutionStatus.EXACT_DUPLICATE:
                item.status = IngestItemStatus.DUPLICATE.value
                item.completed_at = utc_now()
                self._audit(
                    workspace_id=batch.workspace_id,
                    actor_id=actor_id,
                    event_type="EXACT_DUPLICATE_DETECTED",
                    subject_type="AssetVersion",
                    subject_id=version.id,
                    details={"ingest_item_id": item.id, "content_hash": version.content_hash},
                )
                self.session.commit()
                return self._outcome(item)

            original_representation = RepresentationRecord(
                version_id=version.id,
                representation_type=RepresentationType.ORIGINAL.value,
                mime_type=version.mime_type,
                blob_id=blob.id,
                generator="upload",
                generator_version="1",
                metadata_json={"original_filename": safe_filename},
            )
            self.session.add(original_representation)
            self._audit(
                workspace_id=batch.workspace_id,
                actor_id=actor_id,
                event_type="ASSET_VERSION_CREATED",
                subject_type="AssetVersion",
                subject_id=version.id,
                details={
                    "asset_id": asset.id,
                    "parent_version_id": version.parent_version_id,
                    "content_hash": version.content_hash,
                },
            )
            self.session.commit()

            self._parse_version(
                batch=batch,
                item=item,
                version=version,
                source_path=stored.path,
                kind=detected.kind,
                actor_id=actor_id,
            )
            item.status = IngestItemStatus.COMPLETED.value
            item.completed_at = utc_now()
            self.session.commit()
            return self._outcome(item)
        except Exception as exc:
            self.session.rollback()
            failed_item = self.session.get(IngestItemRecord, item.id)
            if failed_item is not None:
                failed_item.status = IngestItemStatus.FAILED.value
                failed_item.error = f"{type(exc).__name__}: {exc}"
                failed_item.completed_at = utc_now()
                self.session.commit()
                return self._outcome(failed_item)
            raise

    def finalize_batch(self, *, batch_id: str, actor_id: str) -> IngestBatchRecord:
        batch = self._batch(batch_id)
        counts = dict(
            self.session.execute(
                select(IngestItemRecord.status, func.count(IngestItemRecord.id))
                .where(IngestItemRecord.batch_id == batch.id)
                .group_by(IngestItemRecord.status)
            ).all()
        )
        failed = counts.get(IngestItemStatus.FAILED.value, 0)
        succeeded = counts.get(IngestItemStatus.COMPLETED.value, 0) + counts.get(
            IngestItemStatus.DUPLICATE.value,
            0,
        )
        pending = counts.get(IngestItemStatus.QUEUED.value, 0) + counts.get(
            IngestItemStatus.STORED.value,
            0,
        )
        if pending:
            raise InvariantViolationError("cannot finalize a batch with pending items")
        if failed and succeeded:
            batch.status = BatchStatus.PARTIAL.value
        elif failed:
            batch.status = BatchStatus.FAILED.value
        else:
            batch.status = BatchStatus.COMPLETED.value
        batch.completed_at = utc_now()
        batch.auto_summary = f"{succeeded} item(s) completed or reused; {failed} item(s) failed"
        self._audit(
            workspace_id=batch.workspace_id,
            actor_id=actor_id,
            event_type="INGEST_BATCH_FINALIZED",
            subject_type="IngestBatch",
            subject_id=batch.id,
            details={"counts": counts, "status": batch.status},
        )
        self.session.commit()
        return batch

    def _resolve_version(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        filename: str,
        logical_name: str | None,
        asset_id: str | None,
        source_key: str | None,
        force_new_asset: bool,
        blob: BlobRecord,
        detected_kind: FormatKind,
        mime_type: str,
        metadata: dict[str, Any],
    ) -> tuple[AssetRecord, AssetVersionRecord, ResolutionStatus]:
        asset: AssetRecord | None = None

        if asset_id is not None:
            asset = self.session.get(AssetRecord, asset_id)
            if asset is None or asset.workspace_id != workspace_id:
                raise NotFoundError("target asset was not found in this workspace")
        elif source_key and not force_new_asset:
            asset = self.session.scalar(
                select(AssetRecord).where(
                    AssetRecord.workspace_id == workspace_id,
                    AssetRecord.source_key == source_key,
                )
            )

        if asset is None and not force_new_asset:
            duplicate = self.session.scalar(
                select(AssetVersionRecord)
                .join(AssetRecord, AssetVersionRecord.asset_id == AssetRecord.id)
                .where(
                    AssetRecord.workspace_id == workspace_id,
                    AssetVersionRecord.content_hash == blob.sha256,
                    AssetVersionRecord.source_filename == filename,
                )
                .order_by(AssetVersionRecord.created_at.desc())
            )
            if duplicate is not None:
                duplicate_asset = self.session.get(AssetRecord, duplicate.asset_id)
                if duplicate_asset is None:
                    raise InvariantViolationError("duplicate version has no parent asset")
                return duplicate_asset, duplicate, ResolutionStatus.EXACT_DUPLICATE

        if asset is not None and asset.current_version_id:
            current = self.session.get(AssetVersionRecord, asset.current_version_id)
            if current is not None and current.content_hash == blob.sha256:
                return asset, current, ResolutionStatus.EXACT_DUPLICATE

        if asset is None:
            asset = AssetRecord(
                workspace_id=workspace_id,
                logical_name=(logical_name or filename).strip(),
                source_key=source_key,
                created_by=actor_id,
            )
            if not asset.logical_name:
                raise InvariantViolationError("asset logical name cannot be empty")
            self.session.add(asset)
            self.session.flush()
            resolution = ResolutionStatus.NEW_ASSET
            parent_version_id = None
        else:
            resolution = ResolutionStatus.NEW_VERSION
            parent_version_id = asset.current_version_id

        version = AssetVersionRecord(
            asset_id=asset.id,
            parent_version_id=parent_version_id,
            blob_id=blob.id,
            content_hash=blob.sha256,
            mime_type=mime_type,
            format_kind=detected_kind.value,
            size_bytes=blob.size_bytes,
            source_kind=SourceKind.BROWSER_UPLOAD.value,
            source_filename=filename,
            deterministic_metadata=metadata,
            created_by=actor_id,
        )
        self.session.add(version)
        self.session.flush()
        asset.current_version_id = version.id
        self.session.commit()
        return asset, version, resolution

    def _parse_version(
        self,
        *,
        batch: IngestBatchRecord,
        item: IngestItemRecord,
        version: AssetVersionRecord,
        source_path: Path,
        kind: FormatKind,
        actor_id: str,
    ) -> None:
        try:
            parser = self.parser_registry.get(kind)
        except UnsupportedFormatError as exc:
            unsupported_run = ParseRunRecord(
                version_id=version.id,
                parser_name="unsupported",
                parser_version="1",
                status=ParseStatus.UNSUPPORTED.value,
                error=f"{type(exc).__name__}: {exc}",
                started_at=utc_now(),
                completed_at=utc_now(),
            )
            self.session.add(unsupported_run)
            self.session.flush()
            self._audit(
                workspace_id=batch.workspace_id,
                actor_id=actor_id,
                event_type="PARSE_UNSUPPORTED",
                subject_type="ParseRun",
                subject_id=unsupported_run.id,
                details={"version_id": version.id, "format_kind": kind.value},
            )
            self.session.commit()
            raise
        parse_run = ParseRunRecord(
            version_id=version.id,
            parser_name=parser.name,
            parser_version=parser.version,
            status=ParseStatus.RUNNING.value,
            started_at=utc_now(),
        )
        self.session.add(parse_run)
        self.session.commit()

        try:
            parsed = parser.parse(source_path)
            canonical_blob_data = self.blob_store.put_bytes(parsed.canonical_content)
            canonical_blob = self._get_or_create_blob(
                content_hash=canonical_blob_data.sha256,
                storage_key=canonical_blob_data.storage_key,
                size_bytes=canonical_blob_data.size_bytes,
            )
            representation = RepresentationRecord(
                version_id=version.id,
                representation_type=parsed.representation_type.value,
                mime_type=parsed.mime_type,
                blob_id=canonical_blob.id,
                generator=parser.name,
                generator_version=parser.version,
                metadata_json=parsed.metadata,
            )
            self.session.add(representation)
            self.session.flush()

            for ordinal, draft in enumerate(parsed.fragments):
                excerpt_hash = sha256(draft.text_or_value.encode("utf-8")).hexdigest()
                self.session.add(
                    FragmentRecord(
                        version_id=version.id,
                        representation_id=representation.id,
                        ordinal=ordinal,
                        fragment_type=draft.fragment_type.value,
                        locator_json=draft.locator,
                        text_or_value=draft.text_or_value,
                        excerpt_hash=excerpt_hash,
                        quality=draft.quality,
                    )
                )

            parse_run.status = ParseStatus.SUCCEEDED.value
            parse_run.representation_id = representation.id
            parse_run.completed_at = utc_now()
            self._audit(
                workspace_id=batch.workspace_id,
                actor_id=actor_id,
                event_type="PARSE_COMPLETED",
                subject_type="ParseRun",
                subject_id=parse_run.id,
                details={
                    "version_id": version.id,
                    "representation_id": representation.id,
                    "fragment_count": len(parsed.fragments),
                },
            )
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            failed_run = self.session.get(ParseRunRecord, parse_run.id)
            if failed_run is not None:
                failed_run.status = ParseStatus.FAILED.value
                failed_run.error = f"{type(exc).__name__}: {exc}"
                failed_run.completed_at = utc_now()
                self.session.commit()
            raise

    def _get_or_create_blob(
        self,
        *,
        content_hash: str,
        storage_key: str,
        size_bytes: int,
    ) -> BlobRecord:
        blob = self.session.scalar(select(BlobRecord).where(BlobRecord.sha256 == content_hash))
        if blob is not None:
            return blob
        blob = BlobRecord(
            sha256=content_hash,
            storage_key=storage_key,
            size_bytes=size_bytes,
        )
        self.session.add(blob)
        self.session.flush()
        return blob

    def _workspace(self, workspace_id: str) -> WorkspaceRecord:
        workspace = self.session.get(WorkspaceRecord, workspace_id)
        if workspace is None:
            raise NotFoundError("workspace not found")
        return workspace

    def _batch(self, batch_id: str) -> IngestBatchRecord:
        batch = self.session.get(IngestBatchRecord, batch_id)
        if batch is None:
            raise NotFoundError("ingest batch not found")
        return batch

    def _audit(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        event_type: str,
        subject_type: str,
        subject_id: str,
        details: dict[str, Any],
    ) -> None:
        self.session.add(
            AuditEventRecord(
                workspace_id=workspace_id,
                actor_type=ActorType.USER.value,
                actor_id=actor_id,
                event_type=event_type,
                subject_type=subject_type,
                subject_id=subject_id,
                details_json=details,
            )
        )

    @staticmethod
    def _outcome(item: IngestItemRecord) -> IngestOutcome:
        return IngestOutcome(
            item_id=item.id,
            asset_id=item.resolved_asset_id,
            version_id=item.created_version_id,
            resolution_status=item.resolution_status,
            status=item.status,
            error=item.error,
        )
