from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from backend.app.registry import RegistryStore

from .contracts import (
    ApplyApproval,
    BatchManifest,
    BatchSource,
    PipelineState,
    ProducerIdentity,
    ReportReverseRecord,
    SourceIdentity,
    StateTransition,
)
from .policy import STATE_TRANSITIONS, audit_report_record, canonical_sha256


class ReportIngestionError(RuntimeError):
    pass


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


class ReportIngestionService:
    """Build-time report intake, audit, staging and guarded registry application."""

    def __init__(self, registry_root: Path) -> None:
        self.registry_root = registry_root.resolve()

    def init_batch(
        self,
        batch_id: str,
        source_paths: Iterable[Path],
        output_root: Path,
        *,
        actor: str = "codex",
    ) -> Path:
        batch_dir = output_root.resolve() / batch_id
        manifest_path = batch_dir / "manifest.json"
        if manifest_path.exists():
            raise ReportIngestionError(f"batch already exists: {batch_dir}")

        known_fingerprints = self._known_fingerprints(output_root.resolve())
        batch_sources: list[BatchSource] = []
        seen_in_batch: dict[str, str] = {}
        duplicate_counts: dict[str, int] = {}
        for source_path in source_paths:
            source = source_path.expanduser().resolve()
            if not source.is_file():
                raise ReportIngestionError(f"source file does not exist: {source}")
            source_hash = _file_sha256(source)
            base_report_id = f"RC.{source_hash[:12].upper()}"
            duplicate_of = list(known_fingerprints.get(source_hash, []))
            if source_hash in seen_in_batch:
                duplicate_of.append(seen_in_batch[source_hash])
                duplicate_counts[source_hash] = duplicate_counts.get(source_hash, 1) + 1
                report_id = f"{base_report_id}.DUP{duplicate_counts[source_hash]:02d}"
            else:
                report_id = base_report_id
                seen_in_batch[source_hash] = report_id
                duplicate_counts[source_hash] = 1

            media_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            record = ReportReverseRecord(
                record_id=f"REV.{source_hash[:16].upper()}.V1",
                batch_id=batch_id,
                report_id=report_id,
                state=PipelineState.DUPLICATE if duplicate_of else PipelineState.INGESTED,
                source=SourceIdentity(
                    source_id=f"SRC.{source_hash[:16].upper()}",
                    source_file=str(source),
                    source_sha256=source_hash,
                    byte_size=source.stat().st_size,
                    media_type=media_type,
                    title=source.stem,
                ),
                produced_by=ProducerIdentity(
                    producer_type="CODEX",
                    producer_name=actor,
                    producer_run_id=f"{batch_id}:intake",
                    prompt_version="report-reverse-v1",
                ),
                blockers=(
                    [
                        {
                            "issue_id": "DUPLICATE_SOURCE_SHA256",
                            "severity": "BLOCKING",
                            "message": f"Identical source already exists: {duplicate_of}",
                        }
                    ]
                    if duplicate_of
                    else []
                ),
                state_history=[
                    StateTransition(
                        from_state=None,
                        to_state=PipelineState.INGESTED,
                        actor=actor,
                        reason="Source fingerprinted and added to ingestion manifest.",
                    ),
                    *(
                        [
                            StateTransition(
                                from_state=PipelineState.INGESTED,
                                to_state=PipelineState.DUPLICATE,
                                actor="fingerprint-validator",
                                reason="Exact source SHA-256 already exists in this or an earlier batch.",
                            )
                        ]
                        if duplicate_of
                        else []
                    ),
                ],
            )
            relative_record = Path("records") / f"{report_id}.json"
            _write_json(batch_dir / relative_record, record.model_dump(mode="json"))
            batch_sources.append(
                BatchSource(
                    report_id=report_id,
                    record_path=relative_record.as_posix(),
                    source_sha256=source_hash,
                    duplicate_of=duplicate_of,
                )
            )

        if not batch_sources:
            raise ReportIngestionError("at least one source file is required")
        manifest = BatchManifest(
            batch_id=batch_id,
            sources=batch_sources,
            notes=[
                "Source files are fingerprinted by SHA-256 and are not copied into the repository.",
                "Raw extracted text stays under the gitignored batch workspace.",
            ],
        )
        _write_json(manifest_path, manifest.model_dump(mode="json"))
        return batch_dir

    def extract_batch(self, batch_dir: Path, *, actor: str = "extractor-v1") -> dict[str, Any]:
        batch_dir = batch_dir.resolve()
        manifest = self.load_manifest(batch_dir)
        results: list[dict[str, Any]] = []
        for source in manifest.sources:
            record_path = batch_dir / source.record_path
            record = self.load_record(record_path)
            if record.state == PipelineState.DUPLICATE:
                results.append({"report_id": record.report_id, "status": "SKIPPED_DUPLICATE"})
                continue
            if record.state != PipelineState.INGESTED:
                results.append({"report_id": record.report_id, "status": f"SKIPPED_{record.state.value}"})
                continue

            pages = self._extract_pages(Path(record.source.source_file), record.source.media_type)
            extraction_path = batch_dir / "extracted" / record.report_id / "pages.jsonl"
            extraction_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = extraction_path.with_name(".pages.jsonl.tmp")
            with temporary.open("w", encoding="utf-8") as handle:
                for number, text in enumerate(pages, start=1):
                    handle.write(
                        json.dumps(
                            {
                                "page": number,
                                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                                "character_count": len(text),
                                "text": text,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            os.replace(temporary, extraction_path)

            payload = record.model_dump(mode="json")
            payload["source"]["page_count"] = len(pages)
            payload["state"] = PipelineState.EXTRACTED.value
            payload["state_history"].append(
                StateTransition(
                    from_state=PipelineState.INGESTED,
                    to_state=PipelineState.EXTRACTED,
                    actor=actor,
                    reason="Per-page text map extracted into the private batch workspace.",
                ).model_dump(mode="json")
            )
            updated = ReportReverseRecord.model_validate(payload)
            _write_json(record_path, updated.model_dump(mode="json"))
            results.append(
                {
                    "report_id": record.report_id,
                    "status": "EXTRACTED",
                    "page_count": len(pages),
                    "page_map": str(extraction_path),
                }
            )
        return {"batch_id": manifest.batch_id, "results": results}

    def transition_record(
        self,
        record_path: Path,
        to_state: PipelineState,
        *,
        actor: str,
        reason: str,
    ) -> ReportReverseRecord:
        record_path = record_path.resolve()
        record = self.load_record(record_path)
        if to_state not in STATE_TRANSITIONS.get(record.state, set()):
            raise ReportIngestionError(f"illegal transition {record.state.value} -> {to_state.value}")
        payload = record.model_dump(mode="json")
        payload["state"] = to_state.value
        payload["state_history"].append(
            StateTransition(
                from_state=record.state,
                to_state=to_state,
                actor=actor,
                reason=reason,
            ).model_dump(mode="json")
        )
        updated = ReportReverseRecord.model_validate(payload)
        terminal = {
            PipelineState.BLOCKED,
            PipelineState.EVIDENCE_ONLY,
            PipelineState.DUPLICATE,
            PipelineState.REJECTED,
        }
        audit = audit_report_record(updated, RegistryStore(self.registry_root))
        if to_state not in terminal and not audit.passed:
            summary = "; ".join(f"{issue.code}: {issue.message}" for issue in audit.issues)
            raise ReportIngestionError(f"transition rejected by policy: {summary}")
        _write_json(record_path, updated.model_dump(mode="json"))
        return updated

    def audit_batch(self, batch_dir: Path) -> dict[str, Any]:
        batch_dir = batch_dir.resolve()
        manifest = self.load_manifest(batch_dir)
        registry = RegistryStore(self.registry_root)
        audits: list[dict[str, Any]] = []
        schema_failures: list[dict[str, str]] = []
        for source in manifest.sources:
            record_path = batch_dir / source.record_path
            try:
                record = self.load_record(record_path)
                audit = audit_report_record(record, registry)
                audits.append(audit.model_dump(mode="json"))
            except Exception as exc:
                schema_failures.append({"record_path": source.record_path, "error": str(exc)})
        passed = not schema_failures and all(
            not any(issue["severity"] in {"ERROR", "BLOCKING"} for issue in audit["issues"])
            for audit in audits
        )
        return {
            "batch_id": manifest.batch_id,
            "passed": passed,
            "record_count": len(manifest.sources),
            "audits": audits,
            "schema_failures": schema_failures,
        }

    def build_changeset(self, batch_dir: Path) -> Path:
        batch_dir = batch_dir.resolve()
        manifest = self.load_manifest(batch_dir)
        registry = RegistryStore(self.registry_root)
        records: list[tuple[Path, ReportReverseRecord]] = []
        operations: list[dict[str, Any]] = []
        object_keys: set[tuple[str, str]] = set()

        for source in manifest.sources:
            path = batch_dir / source.record_path
            record = self.load_record(path)
            if not record.registry_changes:
                continue
            audit = audit_report_record(record, registry)
            if not audit.can_build_changeset:
                issue_text = "; ".join(f"{issue.code}: {issue.message}" for issue in audit.issues)
                raise ReportIngestionError(
                    f"record {record.record_id} is not eligible for staging: {issue_text}"
                )
            records.append((path, record))
            for change in record.registry_changes:
                key = (change.registry, change.object_id)
                if key in object_keys:
                    raise ReportIngestionError(
                        f"multiple records propose changes to {change.registry}/{change.object_id}; merge and re-review first"
                    )
                object_keys.add(key)
                operations.append(
                    {
                        **change.model_dump(mode="json"),
                        "record_id": record.record_id,
                        "report_id": record.report_id,
                        "source_sha256": record.source.source_sha256,
                    }
                )

        if not operations:
            raise ReportIngestionError("batch has no approved registry changes")

        operation_hash = canonical_sha256(operations)
        changeset_id = f"CS.{manifest.batch_id}.{operation_hash[:12].upper()}"
        changeset_dir = batch_dir / "changesets" / changeset_id
        stage_registry = changeset_dir / "registry"
        if changeset_dir.exists():
            prior = changeset_dir / "manifest.json"
            if prior.exists() and _read_json(prior).get("operation_hash") == operation_hash:
                return changeset_dir
            raise ReportIngestionError(f"changeset path already exists with different content: {changeset_dir}")

        documents: dict[str, dict[str, Any]] = {
            name: _read_json(self.registry_root / filename)
            for name, filename in RegistryStore.FILES.items()
        }
        touched_registries = {operation["registry"] for operation in operations}
        for operation in operations:
            registry_name = operation["registry"]
            id_field = RegistryStore.ID_FIELDS[registry_name]
            items = documents[registry_name]["items"]
            if operation["operation"] == "ADD":
                items.append(operation["after_object"])
            else:
                for index, item in enumerate(items):
                    if item[id_field] == operation["object_id"]:
                        items[index] = operation["after_object"]
                        break
                else:
                    raise ReportIngestionError(
                        f"update target disappeared: {registry_name}/{operation['object_id']}"
                    )

        staged_hashes: dict[str, str] = {}
        for name, filename in RegistryStore.FILES.items():
            destination = stage_registry / filename
            if name in touched_registries:
                _write_json(destination, documents[name])
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.registry_root / filename, destination)
            staged_hashes[filename] = _file_sha256(destination)
        RegistryStore(stage_registry)

        content_hash = canonical_sha256(
            {"operation_hash": operation_hash, "staged_registry_sha256": staged_hashes}
        )
        changeset_manifest = {
            "schema_version": "1.0.0",
            "changeset_id": changeset_id,
            "batch_id": manifest.batch_id,
            "created_at": _utc_iso(),
            "operation_hash": operation_hash,
            "content_hash": content_hash,
            "record_paths": [str(path.relative_to(batch_dir).as_posix()) for path, _ in records],
            "operations": operations,
            "staged_registry_sha256": staged_hashes,
            "registry_validation": "PASS",
            "application_status": "NOT_APPLIED",
        }
        _write_json(changeset_dir / "manifest.json", changeset_manifest)
        diff_lines = [
            f"# Registry changeset {changeset_id}",
            "",
            f"- Batch: `{manifest.batch_id}`",
            f"- Content hash: `{content_hash}`",
            "- Registry validation: `PASS`",
            "- Application status: `NOT_APPLIED`",
            "",
            "## Operations",
            "",
        ]
        for operation in operations:
            diff_lines.append(
                f"- `{operation['operation']}` `{operation['registry']}/{operation['object_id']}` "
                f"→ `{operation['target_status']}` from `{operation['report_id']}`"
            )
        (changeset_dir / "diff.md").write_text("\n".join(diff_lines) + "\n", encoding="utf-8")

        for record_path, record in records:
            if record.state == PipelineState.APPROVED:
                self.transition_record(
                    record_path,
                    PipelineState.CHANGESET_READY,
                    actor="changeset-builder-v1",
                    reason=f"Validated staged registry changeset {changeset_id} created.",
                )
        return changeset_dir

    def apply_changeset(self, changeset_dir: Path, approval_path: Path) -> Path:
        changeset_dir = changeset_dir.resolve()
        manifest_path = changeset_dir / "manifest.json"
        manifest = _read_json(manifest_path)
        approval = ApplyApproval.model_validate(_read_json(approval_path.resolve()))
        if approval.changeset_id != manifest.get("changeset_id"):
            raise ReportIngestionError("approval changeset_id does not match staged changeset")
        if approval.content_hash != manifest.get("content_hash"):
            raise ReportIngestionError("approval content_hash does not match staged changeset")
        if manifest.get("application_status") == "APPLIED":
            raise ReportIngestionError("changeset is already applied")

        stage_registry = changeset_dir / "registry"
        RegistryStore(stage_registry)
        for filename, expected_hash in manifest["staged_registry_sha256"].items():
            if _file_sha256(stage_registry / filename) != expected_hash:
                raise ReportIngestionError(f"staged registry hash changed after approval: {filename}")

        rollback_dir = changeset_dir / "rollback" / "registry"
        rollback_dir.mkdir(parents=True, exist_ok=False)
        for filename in RegistryStore.FILES.values():
            shutil.copy2(self.registry_root / filename, rollback_dir / filename)

        try:
            for filename in RegistryStore.FILES.values():
                temporary = self.registry_root / f".{filename}.report-pipeline.tmp"
                shutil.copy2(stage_registry / filename, temporary)
                os.replace(temporary, self.registry_root / filename)
            RegistryStore(self.registry_root)
        except Exception as exc:
            for filename in RegistryStore.FILES.values():
                temporary = self.registry_root / f".{filename}.rollback.tmp"
                shutil.copy2(rollback_dir / filename, temporary)
                os.replace(temporary, self.registry_root / filename)
            RegistryStore(self.registry_root)
            raise ReportIngestionError(f"registry apply failed and was rolled back: {exc}") from exc

        receipt = {
            "changeset_id": manifest["changeset_id"],
            "content_hash": manifest["content_hash"],
            "applied_at": _utc_iso(),
            "reviewer": approval.reviewer,
            "approval_sha256": _file_sha256(approval_path.resolve()),
            "rollback_registry": str(rollback_dir),
            "registry_validation": "PASS",
        }
        receipt_path = changeset_dir / "application_receipt.json"
        _write_json(receipt_path, receipt)
        manifest["application_status"] = "APPLIED"
        manifest["application_receipt"] = receipt_path.name
        _write_json(manifest_path, manifest)

        batch_dir = changeset_dir.parents[1]
        for relative_path in manifest.get("record_paths", []):
            record_path = batch_dir / relative_path
            record = self.load_record(record_path)
            if record.state == PipelineState.CHANGESET_READY:
                self.transition_record(
                    record_path,
                    PipelineState.APPLIED,
                    actor="registry-transaction-v1",
                    reason=f"Approved changeset {manifest['changeset_id']} applied and validated.",
                )
        return receipt_path

    @staticmethod
    def load_manifest(batch_dir: Path) -> BatchManifest:
        return BatchManifest.model_validate(_read_json(batch_dir / "manifest.json"))

    @staticmethod
    def load_record(record_path: Path) -> ReportReverseRecord:
        return ReportReverseRecord.model_validate(_read_json(record_path))

    @staticmethod
    def export_schema(output_path: Path) -> None:
        _write_json(output_path.resolve(), ReportReverseRecord.model_json_schema())

    @staticmethod
    def _known_fingerprints(output_root: Path) -> dict[str, list[str]]:
        known: dict[str, list[str]] = {}
        if not output_root.exists():
            return known
        for manifest_path in output_root.glob("*/manifest.json"):
            try:
                manifest = BatchManifest.model_validate(_read_json(manifest_path))
            except Exception:
                continue
            for source in manifest.sources:
                known.setdefault(source.source_sha256, []).append(
                    f"{manifest.batch_id}/{source.report_id}"
                )
        return known

    @staticmethod
    def _extract_pages(source_path: Path, media_type: str) -> list[str]:
        suffix = source_path.suffix.lower()
        if suffix == ".pdf" or media_type == "application/pdf":
            try:
                from pypdf import PdfReader
            except ImportError as exc:
                raise ReportIngestionError(
                    "PDF extraction requires pypdf; install project requirements first"
                ) from exc
            reader = PdfReader(str(source_path))
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception as exc:
                    raise ReportIngestionError(f"encrypted PDF cannot be read: {source_path}") from exc
            return [(page.extract_text() or "") for page in reader.pages]
        if suffix in {".txt", ".md"} or media_type.startswith("text/"):
            text = source_path.read_text(encoding="utf-8", errors="replace")
            return text.split("\f")
        raise ReportIngestionError(
            f"unsupported report type {media_type} ({source_path.suffix}); convert it to PDF or UTF-8 text"
        )
