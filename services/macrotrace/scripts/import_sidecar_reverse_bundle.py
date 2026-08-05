"""Import a privacy-clean sidecar reverse bundle into the governed local batch plane.

This tool never reads PDFs, never writes the live Registry, and only promotes source
records when an explicit Codex/Human adjudication file says to do so. Registry staging
and application remain separate report_pipeline.py commands.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.report_ingestion import ReportIngestionService  # noqa: E402
from backend.app.report_ingestion.contracts import (  # noqa: E402
    BatchManifest,
    BatchSource,
    PipelineState,
    RegistryChange,
    ReportReverseRecord,
    ReviewDecision,
)

ALLOWED_ACTIONS = {"ADD_REVIEWED_REPORT", "KEEP_PRIVATE_EVIDENCE_ONLY"}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _source_basename(source_file: str) -> str:
    normalized = source_file.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", normalized) or normalized.startswith("/"):
        raise ValueError(f"absolute source path is forbidden: {source_file}")
    name = PurePosixPath(normalized).name
    if not name or name in {".", ".."}:
        raise ValueError(f"invalid source filename: {source_file}")
    return name


def _load_records(jsonl_path: Path) -> list[ReportReverseRecord]:
    records: list[ReportReverseRecord] = []
    for line_number, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = ReportReverseRecord.model_validate(json.loads(line))
        except Exception as exc:  # pragma: no cover - Pydantic supplies detail
            raise ValueError(f"invalid record at JSONL line {line_number}: {exc}") from exc
        if record.source.copied_into_repository is not False:
            raise ValueError(f"source copy flag must remain false: {record.report_id}")
        _source_basename(record.source.source_file)
        records.append(record)
    if not records:
        raise ValueError("sidecar JSONL contains no records")
    report_ids = [record.report_id for record in records]
    if len(report_ids) != len(set(report_ids)):
        raise ValueError("duplicate report_id in sidecar JSONL")
    return records


def import_bundle(
    *,
    records_jsonl: Path,
    adjudication_path: Path,
    output_root: Path,
    registry_root: Path,
) -> dict[str, Any]:
    records = _load_records(records_jsonl.resolve())
    adjudication = _read_json(adjudication_path.resolve())
    batch_ids = {record.batch_id for record in records}
    if batch_ids != {adjudication["batch_id"]}:
        raise ValueError(
            f"batch mismatch: records={sorted(batch_ids)} adjudication={adjudication['batch_id']}"
        )

    decisions = adjudication.get("source_registry_decisions", [])
    decision_by_report: dict[str, str] = {}
    for item in decisions:
        report_id = item["report_id"]
        action = item["action"]
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"unsupported action {action} for {report_id}")
        if report_id in decision_by_report:
            raise ValueError(f"duplicate adjudication for {report_id}")
        decision_by_report[report_id] = action
    record_ids = {record.report_id for record in records}
    if set(decision_by_report) != record_ids:
        raise ValueError(
            "adjudication must cover every report exactly once; "
            f"missing={sorted(record_ids - set(decision_by_report))} "
            f"extra={sorted(set(decision_by_report) - record_ids)}"
        )

    batch_id = adjudication["batch_id"]
    batch_dir = output_root.resolve() / batch_id
    if batch_dir.exists():
        raise FileExistsError(f"batch already exists: {batch_dir}")
    records_dir = batch_dir / "records"
    records_dir.mkdir(parents=True)

    service = ReportIngestionService(registry_root.resolve())
    manifest_sources: list[BatchSource] = []
    promoted: list[str] = []
    retained: list[str] = []

    for original in records:
        payload = original.model_dump(mode="json")
        payload["source"]["source_file"] = _source_basename(original.source.source_file)
        action = decision_by_report[original.report_id]
        if action == "ADD_REVIEWED_REPORT":
            if original.state != PipelineState.CANDIDATE:
                raise ValueError(
                    f"only CANDIDATE records can propose reviewed report sources: "
                    f"{original.report_id} is {original.state.value}"
                )
            change_id = f"CH.{original.report_id}.REPORT.SOURCE"
            explicit_evidence_ids = [
                item.evidence_id
                for item in original.evidence
                if item.statement_status == "EXPLICIT"
            ]
            payload["registry_changes"].append(
                RegistryChange(
                    change_id=change_id,
                    operation="ADD",
                    registry="reports",
                    object_id=original.report_id,
                    target_status="reviewed",
                    after_object={
                        "report_id": original.report_id,
                        "title": original.source.title,
                        "institution": original.source.institution or "Unknown",
                        "source_file": _source_basename(original.source.source_file),
                        "review_status": "reviewed",
                        "status": "reviewed",
                    },
                    evidence_ids=explicit_evidence_ids,
                    method_route_ids=[item.method_route_id for item in original.method_routes],
                    rationale=(
                        "Register the page-grounded source and stable report identifier after the "
                        "main Registry match pass; this does not activate any extracted method."
                    ),
                ).model_dump(mode="json")
            )
            payload["reviews"].append(
                ReviewDecision(
                    review_id=f"REVIEW.{original.report_id}.MAIN_REGISTRY_MATCH",
                    reviewer=adjudication["reviewer"],
                    reviewer_type="CODEX",
                    review_run_id=adjudication["review_run_id"],
                    decision="APPROVE_REVIEWED",
                    scope_change_ids=[change_id],
                    rationale=(
                        "The source identity, page-grounded route record and latest Registry "
                        "conflict decision were reviewed independently from the sidecar "
                        "extraction pass."
                    ),
                ).model_dump(mode="json")
            )
            promoted.append(original.report_id)
        else:
            if original.state != PipelineState.EVIDENCE_ONLY:
                raise ValueError(
                    "private evidence-only action requires EVIDENCE_ONLY state: "
                    f"{original.report_id}"
                )
            retained.append(original.report_id)

        record = ReportReverseRecord.model_validate(payload)
        relative_path = Path("records") / f"{record.report_id}.json"
        record_path = batch_dir / relative_path
        _write_json(record_path, record.model_dump(mode="json"))
        manifest_sources.append(
            BatchSource(
                report_id=record.report_id,
                record_path=relative_path.as_posix(),
                source_sha256=record.source.source_sha256,
            )
        )

    manifest = BatchManifest(
        batch_id=batch_id,
        sources=manifest_sources,
        source_files_copied=False,
        notes=[
            "Imported from a privacy-clean sidecar JSONL; PDFs and page text were not copied.",
            f"Registry adjudication: {adjudication_path.resolve()}",
        ],
    )
    _write_json(batch_dir / "manifest.json", manifest.model_dump(mode="json"))

    for report_id in promoted:
        record_path = records_dir / f"{report_id}.json"
        service.transition_record(
            record_path,
            PipelineState.REVIEWED,
            actor=adjudication["reviewer"],
            reason="Independent main-Registry match approved the source record only.",
        )
        service.transition_record(
            record_path,
            PipelineState.APPROVED,
            actor=adjudication["reviewer"],
            reason="Reviewed source record approved for non-mutating Registry staging.",
        )

    audit = service.audit_batch(batch_dir)
    _write_json(batch_dir / "audit.json", audit)
    if not audit["passed"]:
        raise ValueError(f"imported batch failed policy audit: {batch_dir / 'audit.json'}")
    return {
        "batch_dir": str(batch_dir),
        "record_count": len(records),
        "promoted_report_sources": promoted,
        "private_evidence_only": retained,
        "audit_passed": True,
        "live_registry_modified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a governed sidecar reverse bundle")
    parser.add_argument("--records-jsonl", required=True)
    parser.add_argument("--adjudication", required=True)
    parser.add_argument("--output-root", default=str(ROOT / "data" / "report_batches"))
    parser.add_argument("--registry-root", default=str(ROOT / "registry" / "v2"))
    args = parser.parse_args()
    result = import_bundle(
        records_jsonl=Path(args.records_jsonl),
        adjudication_path=Path(args.adjudication),
        output_root=Path(args.output_root),
        registry_root=Path(args.registry_root),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
