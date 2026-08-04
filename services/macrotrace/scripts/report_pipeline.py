"""Internal CLI for governed report reverse engineering.

This is a build-plane tool, not a public API surface.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.report_ingestion import ReportIngestionService  # noqa: E402
from backend.app.report_ingestion.contracts import PipelineState  # noqa: E402


def _service(registry_root: str | None) -> ReportIngestionService:
    return ReportIngestionService(
        Path(registry_root).resolve() if registry_root else ROOT / "registry" / "v2"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="MacroTrace report reverse-engineering pipeline")
    parser.add_argument("--registry-root", help="Registry v2 directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Fingerprint sources and create a private batch")
    init_parser.add_argument("--batch-id", required=True)
    init_parser.add_argument("--output-root", default=str(ROOT / "data" / "report_batches"))
    init_parser.add_argument("--actor", default="codex")
    init_parser.add_argument("sources", nargs="+")

    extract_parser = subparsers.add_parser("extract", help="Extract a private per-page text map")
    extract_parser.add_argument("batch_dir")
    extract_parser.add_argument("--actor", default="extractor-v1")

    audit_parser = subparsers.add_parser("audit", help="Validate schema, evidence and activation gates")
    audit_parser.add_argument("batch_dir")
    audit_parser.add_argument("--write", action="store_true", help="Write audit.json into the batch")

    transition_parser = subparsers.add_parser("transition", help="Append a policy-checked state transition")
    transition_parser.add_argument("record_path")
    transition_parser.add_argument("to_state", choices=[item.value for item in PipelineState])
    transition_parser.add_argument("--actor", required=True)
    transition_parser.add_argument("--reason", required=True)

    changeset_parser = subparsers.add_parser("build-changeset", help="Build and validate a non-mutating registry stage")
    changeset_parser.add_argument("batch_dir")

    apply_parser = subparsers.add_parser("apply", help="Apply an exact human-approved changeset transactionally")
    apply_parser.add_argument("changeset_dir")
    apply_parser.add_argument("--approval", required=True)

    schema_parser = subparsers.add_parser("export-schema", help="Export the current JSON Schema")
    schema_parser.add_argument("output_path")

    args = parser.parse_args()
    service = _service(args.registry_root)

    if args.command == "init":
        result: object = {
            "batch_dir": str(
                service.init_batch(
                    args.batch_id,
                    [Path(item) for item in args.sources],
                    Path(args.output_root),
                    actor=args.actor,
                )
            )
        }
    elif args.command == "extract":
        result = service.extract_batch(Path(args.batch_dir), actor=args.actor)
    elif args.command == "audit":
        result = service.audit_batch(Path(args.batch_dir))
        if args.write:
            output = Path(args.batch_dir).resolve() / "audit.json"
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result["audit_path"] = str(output)
    elif args.command == "transition":
        record = service.transition_record(
            Path(args.record_path),
            PipelineState(args.to_state),
            actor=args.actor,
            reason=args.reason,
        )
        result = record.model_dump(mode="json")
    elif args.command == "build-changeset":
        result = {"changeset_dir": str(service.build_changeset(Path(args.batch_dir)))}
    elif args.command == "apply":
        result = {
            "application_receipt": str(
                service.apply_changeset(Path(args.changeset_dir), Path(args.approval))
            )
        }
    else:
        service.export_schema(Path(args.output_path))
        result = {"schema_path": str(Path(args.output_path).resolve())}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
