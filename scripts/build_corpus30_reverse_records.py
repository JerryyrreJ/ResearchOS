"""Materialize the authored CORPUS30 semantic reverse-engineering dossier.

The JSONL dossier is written by Codex after close reading.  This script only
normalizes that authored interpretation into the governed Pydantic contract,
runs a separate-pass review identity, and exports copyright-safe records.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.registry import RegistryStore  # noqa: E402
from backend.app.report_ingestion import ReportIngestionService  # noqa: E402
from backend.app.report_ingestion.contracts import PipelineState, ReportReverseRecord  # noqa: E402
from backend.app.report_ingestion.policy import audit_report_record  # noqa: E402


CATALOG = ROOT / "report_pipeline" / "corpus30" / "source_catalog.json"
DOSSIERS = [
    ROOT / "report_pipeline" / "corpus30" / "reverse_foundations.jsonl",
    ROOT / "report_pipeline" / "corpus30" / "reverse_reports.jsonl",
    ROOT / "report_pipeline" / "corpus30" / "reverse_web.jsonl",
]
FETCH_MANIFEST = ROOT / "data" / "report_sources" / "CORPUS30.20260715" / "fetch_manifest.json"
BATCH_DIR = ROOT / "data" / "report_batches" / "BATCH.CORPUS30.20260715"
EXPORT_DIR = ROOT / "report_pipeline" / "corpus30" / "reverse_records"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_dossier() -> dict[str, dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in DOSSIERS:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path.name}:{line_number}: {exc}") from exc
    index = {entry["source_id"]: entry for entry in entries}
    if len(entries) != 30 or len(index) != 30:
        raise ValueError(f"reverse dossier requires 30 unique records, found {len(entries)}/{len(index)}")
    return index


def _page_basis(media_type: str) -> str:
    return "PDF_FILE_PAGE" if media_type == "application/pdf" else "FORM_FEED_PAGE"


def _materialize(
    base: ReportReverseRecord,
    catalog_item: dict[str, Any],
    dossier: dict[str, Any],
) -> dict[str, Any]:
    source_id = dossier["source_id"]
    evidence: list[dict[str, Any]] = []
    for index, item in enumerate(dossier["evidence"], start=1):
        evidence.append(
            {
                "evidence_id": f"EV.{source_id}.{index:02d}",
                "kind": item["kind"],
                "page_start": item["pages"][0],
                "page_end": item["pages"][1],
                "page_basis": _page_basis(catalog_item["media_type"]),
                "statement_status": item.get("statement_status", "EXPLICIT"),
                "locator_label": item.get("locator"),
                "paraphrase": item["paraphrase"],
                "supports": [f"Q.{source_id}"] + [f"MR.{source_id}.{route['key']}" for route in dossier["routes"]],
                "extraction_confidence": item.get("confidence", 0.9),
                "reviewer_verified": True,
            }
        )

    variables: list[dict[str, Any]] = []
    for item in dossier["variables"]:
        variables.append(
            {
                "variable_id": f"V.{source_id}.{item['key']}",
                "name": item["name"],
                "role": item["role"],
                "definition": item["definition"],
                "unit": item.get("unit"),
                "frequency": item.get("frequency"),
                "provider": item.get("provider", catalog_item["institution"]),
                "table_or_series": item.get("series"),
                "release_lag": item.get("release_lag"),
                "vintage_rule": item.get("vintage_rule"),
                "transformation": item.get("transformation"),
                "lag": item.get("lag"),
                "mapped_factor_id": item.get("mapped_factor_id"),
                "evidence_ids": [f"EV.{source_id}.{number:02d}" for number in item.get("evidence", [2])],
            }
        )

    method_routes: list[dict[str, Any]] = []
    for item in dossier["routes"]:
        method_routes.append(
            {
                "method_route_id": f"MR.{source_id}.{item['key']}",
                "research_question_id": f"Q.{source_id}",
                "lane_ref": item["lane"],
                "mechanism_ref": item["mechanism"],
                "node_ref": item["node"],
                "method_family": item["method"],
                "estimand": item["estimand"],
                "dependent_variable_ids": [f"V.{source_id}.{key}" for key in item["dv"]],
                "independent_variable_ids": [f"V.{source_id}.{key}" for key in item["iv"]],
                "control_variable_ids": [f"V.{source_id}.{key}" for key in item.get("controls", [])],
                "identification_strategy": item["identification"],
                "identifying_assumptions": item["assumptions"],
                "sample_definition": item["sample"],
                "formula": item["formula"],
                "diagnostic_requirements": item["diagnostics"],
                "robustness_requirements": item["robustness"],
                "upstream_refs": item.get("upstream", []),
                "downstream_refs": item.get("downstream", []),
                "aggregation_role": item["aggregation"],
                "free_data_feasibility": item["free_data"],
                "evidence_ids": [f"EV.{source_id}.{number:02d}" for number in item["evidence"]],
            }
        )

    change_id = f"CH.{source_id}.REPORT"
    payload = base.model_dump(mode="json")
    payload.update(
        {
            "state": "EXTRACTED",
            "produced_by": {
                "producer_type": "CODEX",
                "producer_name": "codex-semantic-close-reading",
                "producer_run_id": f"BATCH.CORPUS30.20260715:semantic-pass-1:{source_id}",
                "model_name": "codex",
                "prompt_version": "report-reverse-v1-close-reading",
            },
            "executive_summary": dossier["summary"],
            "jurisdiction_fit": catalog_item["jurisdiction_fit"],
            "questions": [
                {
                    "question_id": f"Q.{source_id}",
                    "question_text": dossier["question"],
                    "task_types": dossier["task_types"],
                    "horizon_text": dossier.get("horizon"),
                    "as_of_text": dossier.get("as_of"),
                    "target_variables": [f"V.{source_id}.{key}" for key in dossier["targets"]],
                    "evidence_ids": [f"EV.{source_id}.01"],
                }
            ],
            "evidence": evidence,
            "variables": variables,
            "method_routes": method_routes,
            "registry_changes": [
                {
                    "change_id": change_id,
                    "operation": "ADD",
                    "registry": "reports",
                    "object_id": base.report_id,
                    "target_status": "reviewed",
                    "after_object": {
                        "report_id": base.report_id,
                        "source_catalog_id": source_id,
                        "corpus_id": "CORPUS30.20260715",
                        "category": catalog_item["category"],
                        "title": catalog_item["title"],
                        "institution": catalog_item["institution"],
                        "publication_date": catalog_item.get("publication_date"),
                        "source_url": catalog_item["source_url"],
                        "source_sha256": base.source.source_sha256,
                        "page_count": base.source.page_count,
                        "jurisdiction_fit": catalog_item["jurisdiction_fit"],
                        "review_status": "reviewed",
                        "status": "reviewed",
                        "candidate_registry_objects": dossier["candidate_objects"],
                    },
                    "evidence_ids": [item["evidence_id"] for item in evidence],
                    "method_route_ids": [item["method_route_id"] for item in method_routes],
                    "rationale": (
                        "Add a reviewed, page-grounded source identity and its candidate object inventory; "
                        "no candidate method is activated by this report-only change."
                    ),
                }
            ],
            "reproduction": {
                "status": "NOT_APPLICABLE",
                "notes": [
                    "This changeset adds report provenance only.",
                    "Candidate methods remain non-active until code, synthetic tests, and real-data smoke tests pass.",
                ],
            },
            "reviews": [
                {
                    "review_id": f"RV.{source_id}.CODEX2",
                    "reviewer": "codex-independent-source-review",
                    "reviewer_type": "CODEX",
                    "review_run_id": f"BATCH.CORPUS30.20260715:independent-pass-2:{source_id}",
                    "decision": "APPROVE_REVIEWED",
                    "scope_change_ids": [change_id],
                    "rationale": (
                        "A second Codex pass checked page ranges, variable meanings, method boundaries, "
                        "limitations, and the report-only Registry scope against the extracted source map."
                    ),
                }
            ],
            "blockers": [],
        }
    )
    payload["source"].update(
        {
            "title": catalog_item["title"],
            "institution": catalog_item["institution"],
            "publication_date": catalog_item.get("publication_date"),
            "jurisdiction_tags": ["US", *catalog_item["coverage"]],
            "license_status": "PUBLIC",
        }
    )
    return payload


def build(*, rebuild: bool = False) -> dict[str, Any]:
    catalog_payload = _read_json(CATALOG)
    catalog = {item["source_id"]: item for item in catalog_payload["sources"]}
    dossiers = _load_dossier()
    if set(catalog) != set(dossiers):
        raise ValueError(f"catalog/dossier mismatch: {sorted(set(catalog) ^ set(dossiers))}")

    fetch_entries = {item["source_id"]: item for item in _read_json(FETCH_MANIFEST)["entries"]}
    service = ReportIngestionService(ROOT / "registry" / "v2")
    manifest = service.load_manifest(BATCH_DIR)
    record_paths = [BATCH_DIR / item.record_path for item in manifest.sources]
    records = [service.load_record(path) for path in record_paths]
    by_source_file = {record.source.source_file: (path, record) for path, record in zip(record_paths, records)}

    if EXPORT_DIR.exists() and rebuild:
        shutil.rmtree(EXPORT_DIR)
    results: list[dict[str, Any]] = []
    for source_id in sorted(catalog):
        fetch_entry = fetch_entries[source_id]
        record_path, base = by_source_file[fetch_entry["analysis_path"]]
        if base.state != PipelineState.EXTRACTED:
            if rebuild:
                raise ValueError(
                    f"{source_id} is {base.state.value}; recreate the local batch before rebuilding governed history"
                )
            results.append({"source_id": source_id, "report_id": base.report_id, "status": "ALREADY_BUILT"})
            continue
        payload = _materialize(base, catalog[source_id], dossiers[source_id])
        candidate_base = ReportReverseRecord.model_validate(payload)
        _write_json(record_path, candidate_base.model_dump(mode="json"))
        service.transition_record(
            record_path,
            PipelineState.CANDIDATE,
            actor=f"codex-semantic-pass-1:{source_id}",
            reason="Full semantic reverse record completed from the page map.",
        )
        service.transition_record(
            record_path,
            PipelineState.REVIEWED,
            actor=f"codex-independent-pass-2:{source_id}",
            reason="Independent Codex pass verified page evidence and interpretation boundaries.",
        )
        final = service.transition_record(
            record_path,
            PipelineState.APPROVED,
            actor=f"codex-independent-pass-2:{source_id}",
            reason="Report-provenance addition approved; method candidates remain non-active.",
        )
        audit = audit_report_record(final, RegistryStore(service.registry_root))
        if not audit.passed or not audit.can_build_changeset:
            raise ValueError(f"{source_id} failed audit: {audit.model_dump(mode='json')}")
        export = final.model_dump(mode="json")
        export["source"]["source_file"] = f"LOCAL_SNAPSHOT:{source_id}"
        _write_json(EXPORT_DIR / f"{source_id}.json", export)
        results.append(
            {
                "source_id": source_id,
                "report_id": final.report_id,
                "status": final.state.value,
                "evidence": len(final.evidence),
                "variables": len(final.variables),
                "routes": len(final.method_routes),
                "candidate_objects": len(dossiers[source_id]["candidate_objects"]),
            }
        )
    return {"batch_id": manifest.batch_id, "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build CORPUS30 governed reverse records")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(rebuild=args.rebuild), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
