from __future__ import annotations

import json
from pathlib import Path

import pytest
from backend.app.registry import RegistryStore
from scripts.import_sidecar_reverse_bundle import import_bundle

ROOT = Path(__file__).resolve().parents[1]


def _candidate_record(report_id: str, state: str = "CANDIDATE") -> dict:
    return {
        "schema_version": "1.0.0",
        "record_id": f"REV.{report_id}.V1",
        "batch_id": "BATCH.SIDECAR.TEST",
        "report_id": report_id,
        "state": state,
        "source": {
            "source_id": f"SRC.{report_id}",
            "source_file": "<private-source>/report.pdf",
            "source_sha256": "a" * 64,
            "byte_size": 100,
            "media_type": "application/pdf",
            "page_count": 1,
            "title": "Sidecar report",
            "institution": "Research institute",
            "publication_date": "2026-08-05",
            "jurisdiction_tags": ["US_METHOD_ADAPTATION"],
            "license_status": "PRIVATE_RESEARCH_INPUT",
            "copied_into_repository": False,
        },
        "produced_by": {
            "producer_type": "CODEX",
            "producer_name": "sidecar-extractor",
            "producer_run_id": "sidecar-extraction-pass",
        },
        "executive_summary": "A page-grounded report with a reusable descriptive research route.",
        "jurisdiction_fit": "US_ADAPTABLE",
        "questions": [
            {
                "question_id": "Q.SIDECAR.TEST",
                "question_text": "What does the research route measure?",
                "task_types": ["DRIVER"],
                "target_variables": ["V.SIDECAR.TEST"],
                "evidence_ids": ["EV.SIDECAR.TEST"],
            }
        ],
        "evidence": [
            {
                "evidence_id": "EV.SIDECAR.TEST",
                "kind": "MODEL_SPECIFICATION",
                "page_start": 1,
                "page_end": 1,
                "page_basis": "PDF_FILE_PAGE",
                "statement_status": "EXPLICIT",
                "paraphrase": "The page defines a descriptive index and its inputs.",
                "supports": ["MR.SIDECAR.TEST"],
                "extraction_confidence": 0.95,
                "reviewer_verified": True,
            }
        ],
        "variables": [
            {
                "variable_id": "V.SIDECAR.TEST",
                "name": "Descriptive index",
                "role": "STATE",
                "definition": "A page-defined state index.",
                "unit": "index",
                "frequency": "monthly",
                "evidence_ids": ["EV.SIDECAR.TEST"],
            }
        ],
        "method_routes": [
            {
                "method_route_id": "MR.SIDECAR.TEST",
                "research_question_id": "Q.SIDECAR.TEST",
                "lane_ref": "US.ACTIVITY",
                "mechanism_ref": "MECH.ACTIVITY.BROAD_STATE",
                "node_ref": "N.ACTIVITY.NOWCAST",
                "method_family": "descriptive index",
                "estimand": "current activity state",
                "dependent_variable_ids": ["V.SIDECAR.TEST"],
                "independent_variable_ids": [],
                "control_variable_ids": [],
                "identification_strategy": "descriptive; no causal claim",
                "identifying_assumptions": ["definition is stable"],
                "sample_definition": "monthly observations",
                "formula": "index = standardized input",
                "diagnostic_requirements": ["definition reconciliation"],
                "robustness_requirements": ["equal-weight baseline"],
                "aggregation_role": "background evidence",
                "free_data_feasibility": "AVAILABLE",
                "evidence_ids": ["EV.SIDECAR.TEST"],
            }
        ],
        "registry_changes": [],
        "reproduction": {"status": "NOT_STARTED"},
        "reviews": [
            {
                "review_id": "REVIEW.SIDECAR.PASS2",
                "reviewer": "sidecar-reviewer",
                "reviewer_type": "CODEX",
                "review_run_id": "sidecar-review-pass-2",
                "decision": "APPROVE_CANDIDATE",
                "scope_change_ids": [],
                "rationale": "The page evidence was checked in a separate sidecar pass.",
            }
        ],
        "blockers": [],
        "state_history": [
            {
                "from_state": None,
                "to_state": "INGESTED",
                "actor": "sidecar-intake",
                "reason": "Source fingerprinted in the private sidecar batch.",
            },
            {
                "from_state": "INGESTED",
                "to_state": "EXTRACTED",
                "actor": "sidecar-extractor",
                "reason": "Private page map extracted without copying source files.",
            },
            {
                "from_state": "EXTRACTED",
                "to_state": state,
                "actor": "sidecar-reviewer",
                "reason": "Sidecar candidate review completed.",
            },
        ],
    }


def test_sidecar_import_promotes_only_report_source(tmp_path: Path) -> None:
    jsonl = tmp_path / "records.jsonl"
    jsonl.write_text(json.dumps(_candidate_record("RC.TEST")) + "\n", encoding="utf-8")
    adjudication = tmp_path / "adjudication.json"
    adjudication.write_text(
        json.dumps(
            {
                "batch_id": "BATCH.SIDECAR.TEST",
                "review_run_id": "main-registry-review-pass",
                "reviewer": "codex-main-reviewer",
                "source_registry_decisions": [
                    {"report_id": "RC.TEST", "action": "ADD_REVIEWED_REPORT"}
                ],
            }
        ),
        encoding="utf-8",
    )
    registry_root = tmp_path / "registry"
    import shutil

    shutil.copytree(ROOT / "registry" / "v2", registry_root)
    result = import_bundle(
        records_jsonl=jsonl,
        adjudication_path=adjudication,
        output_root=tmp_path / "batches",
        registry_root=registry_root,
    )
    assert result["audit_passed"] is True
    assert result["live_registry_modified"] is False
    assert "RC.TEST" not in RegistryStore(registry_root).ids("reports")
    record = json.loads(
        (Path(result["batch_dir"]) / "records" / "RC.TEST.json").read_text(encoding="utf-8")
    )
    assert record["state"] == "APPROVED"
    assert record["source"]["source_file"] == "report.pdf"
    assert record["registry_changes"][0]["registry"] == "reports"
    assert all(change["registry"] == "reports" for change in record["registry_changes"])


def test_sidecar_import_rejects_absolute_source_path(tmp_path: Path) -> None:
    payload = _candidate_record("RC.BAD")
    payload["source"]["source_file"] = "C:/Users/private/report.pdf"
    jsonl = tmp_path / "records.jsonl"
    jsonl.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    adjudication = tmp_path / "adjudication.json"
    adjudication.write_text(
        json.dumps(
            {
                "batch_id": "BATCH.SIDECAR.TEST",
                "review_run_id": "main-registry-review-pass",
                "reviewer": "codex-main-reviewer",
                "source_registry_decisions": [
                    {"report_id": "RC.BAD", "action": "ADD_REVIEWED_REPORT"}
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="absolute source path"):
        import_bundle(
            records_jsonl=jsonl,
            adjudication_path=adjudication,
            output_root=tmp_path / "batches",
            registry_root=ROOT / "registry" / "v2",
        )


def test_candidate_ids_are_not_accidentally_live() -> None:
    adjudication = json.loads(
        (ROOT / "report_pipeline" / "sidecar15" / "registry_adjudication.json").read_text(
            encoding="utf-8"
        )
    )
    registry = RegistryStore(ROOT / "registry" / "v2")
    live_ids = {item for name in RegistryStore.FILES for item in registry.ids(name)}
    candidate_ids = {
        item
        for decision in adjudication["method_decisions"]
        for item in decision.get("candidate_registry_ids", [])
    }
    assert candidate_ids
    assert candidate_ids.isdisjoint(live_ids)
