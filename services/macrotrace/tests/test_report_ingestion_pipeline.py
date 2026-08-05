from __future__ import annotations

import json
import shutil
from pathlib import Path

from jsonschema import Draft202012Validator

from backend.app.registry import RegistryStore
from backend.app.report_ingestion.contracts import PipelineState, ReportReverseRecord
from backend.app.report_ingestion.policy import audit_report_record
from backend.app.report_ingestion.service import ReportIngestionService


ROOT = Path(__file__).resolve().parents[1]


def _registry_copy(tmp_path: Path) -> Path:
    destination = tmp_path / "registry"
    shutil.copytree(ROOT / "registry" / "v2", destination)
    return destination


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_reviewed_report_batch(tmp_path: Path) -> tuple[ReportIngestionService, Path, Path]:
    registry_root = _registry_copy(tmp_path)
    service = ReportIngestionService(registry_root)
    source = tmp_path / "research-note.txt"
    source.write_text(
        "This report asks whether industrial production predicts near-term US growth. "
        "It estimates a predictive autoregression with lagged production and reports "
        "rolling out-of-sample RMSE plus residual serial-correlation checks.",
        encoding="utf-8",
    )
    batch_dir = service.init_batch("BATCH.TEST.001", [source], tmp_path / "batches")
    service.extract_batch(batch_dir)
    manifest = service.load_manifest(batch_dir)
    record_path = batch_dir / manifest.sources[0].record_path
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    report_id = payload["report_id"]
    payload.update(
        {
            "executive_summary": (
                "The report frames short-horizon US growth as a predictive production mechanism, "
                "defines the outcome and lagged indicator, and evaluates the model out of sample."
            ),
            "jurisdiction_fit": "US_DIRECT",
            "questions": [
                {
                    "question_id": "Q.TEST.GROWTH",
                    "question_text": "Does industrial production predict near-term US growth?",
                    "task_types": ["FORECAST"],
                    "horizon_text": "one quarter",
                    "target_variables": ["V.GROWTH"],
                    "evidence_ids": ["EV.TEST.QUESTION"],
                }
            ],
            "evidence": [
                {
                    "evidence_id": "EV.TEST.QUESTION",
                    "kind": "RESEARCH_QUESTION",
                    "page_start": 1,
                    "page_end": 1,
                    "page_basis": "FORM_FEED_PAGE",
                    "paraphrase": "The note asks whether lagged industrial production predicts near-term US growth.",
                    "supports": ["Q.TEST.GROWTH", "MR.TEST.AR"],
                    "extraction_confidence": 0.98,
                    "reviewer_verified": True,
                },
                {
                    "evidence_id": "EV.TEST.SPEC",
                    "kind": "MODEL_SPECIFICATION",
                    "page_start": 1,
                    "page_end": 1,
                    "page_basis": "FORM_FEED_PAGE",
                    "paraphrase": "The reported design is a predictive autoregression with rolling out-of-sample evaluation.",
                    "supports": ["MR.TEST.AR"],
                    "extraction_confidence": 0.95,
                    "reviewer_verified": True,
                },
            ],
            "variables": [
                {
                    "variable_id": "V.GROWTH",
                    "name": "US real growth",
                    "role": "DEPENDENT",
                    "definition": "Near-term real activity growth outcome.",
                    "unit": "percent",
                    "frequency": "quarterly",
                    "mapped_factor_id": "F.ACTIVITY.REAL_GDP",
                    "evidence_ids": ["EV.TEST.SPEC"],
                },
                {
                    "variable_id": "V.INDPRO",
                    "name": "Industrial production",
                    "role": "EXPOSURE",
                    "definition": "Lagged monthly industrial production growth.",
                    "unit": "percent",
                    "frequency": "monthly",
                    "mapped_factor_id": "F.ACTIVITY.INDPRO",
                    "evidence_ids": ["EV.TEST.SPEC"],
                },
            ],
            "method_routes": [
                {
                    "method_route_id": "MR.TEST.AR",
                    "research_question_id": "Q.TEST.GROWTH",
                    "lane_ref": "US.ACTIVITY",
                    "mechanism_ref": "MECH.ACTIVITY.PRODUCTION",
                    "node_ref": "N.ACTIVITY.PRODUCTION",
                    "method_family": "predictive autoregression",
                    "estimand": "out-of-sample conditional mean forecast",
                    "dependent_variable_ids": ["V.GROWTH"],
                    "independent_variable_ids": ["V.INDPRO"],
                    "control_variable_ids": [],
                    "identification_strategy": "predictive design; no causal estimand claimed",
                    "identifying_assumptions": ["time-ordering", "stable release convention"],
                    "sample_definition": "US monthly and quarterly observations available as of each forecast origin",
                    "formula": "growth_t = alpha + sum(beta_l * indpro_{t-l}) + error_t",
                    "diagnostic_requirements": ["residual Ljung-Box", "rolling OOS RMSE"],
                    "robustness_requirements": ["alternative lag windows", "equal-mean benchmark"],
                    "aggregation_role": "candidate predictive node",
                    "free_data_feasibility": "AVAILABLE",
                    "evidence_ids": ["EV.TEST.QUESTION", "EV.TEST.SPEC"],
                }
            ],
            "registry_changes": [
                {
                    "change_id": "CH.TEST.REPORT",
                    "operation": "ADD",
                    "registry": "reports",
                    "object_id": report_id,
                    "target_status": "reviewed",
                    "after_object": {
                        "report_id": report_id,
                        "title": "Synthetic production forecasting research note",
                        "institution": "Test institution",
                        "source_file": payload["source"]["source_file"],
                        "review_status": "reviewed",
                        "status": "reviewed",
                    },
                    "evidence_ids": ["EV.TEST.QUESTION", "EV.TEST.SPEC"],
                    "method_route_ids": ["MR.TEST.AR"],
                    "rationale": "Add the reviewed source record so future route evidence can reference its stable report ID.",
                }
            ],
            "reviews": [
                {
                    "review_id": "RV.TEST.CODEX",
                    "reviewer": "codex-reviewer",
                    "reviewer_type": "CODEX",
                    "review_run_id": "codex-review-pass-test",
                    "decision": "APPROVE_REVIEWED",
                    "scope_change_ids": ["CH.TEST.REPORT"],
                    "rationale": "Page evidence and the predictive interpretation were checked against the source.",
                }
            ],
        }
    )
    _write(record_path, payload)
    service.transition_record(
        record_path,
        PipelineState.CANDIDATE,
        actor="test-extractor",
        reason="Structured candidate completed.",
    )
    service.transition_record(
        record_path,
        PipelineState.REVIEWED,
        actor="test-reviewer",
        reason="Page evidence and method interpretation reviewed.",
    )
    service.transition_record(
        record_path,
        PipelineState.APPROVED,
        actor="test-reviewer",
        reason="Reviewed report record approved for staged registry addition.",
    )
    return service, batch_dir, record_path


def test_init_extract_and_exact_duplicate_detection(tmp_path: Path) -> None:
    registry_root = _registry_copy(tmp_path)
    service = ReportIngestionService(registry_root)
    source_a = tmp_path / "a.txt"
    source_b = tmp_path / "b.txt"
    source_a.write_text("same report contents", encoding="utf-8")
    source_b.write_text("same report contents", encoding="utf-8")

    batch_dir = service.init_batch("BATCH.DUP", [source_a, source_b], tmp_path / "batches")
    manifest = service.load_manifest(batch_dir)
    assert len(manifest.sources) == 2
    assert manifest.sources[0].duplicate_of == []
    assert manifest.sources[1].duplicate_of == [manifest.sources[0].report_id]
    duplicate = service.load_record(batch_dir / manifest.sources[1].record_path)
    assert duplicate.state == PipelineState.DUPLICATE

    result = service.extract_batch(batch_dir)
    assert result["results"][0]["status"] == "EXTRACTED"
    assert result["results"][1]["status"] == "SKIPPED_DUPLICATE"


def test_shallow_candidate_cannot_cross_candidate_gate(tmp_path: Path) -> None:
    registry_root = _registry_copy(tmp_path)
    service = ReportIngestionService(registry_root)
    source = tmp_path / "thin.txt"
    source.write_text("thin", encoding="utf-8")
    batch_dir = service.init_batch("BATCH.THIN", [source], tmp_path / "batches")
    service.extract_batch(batch_dir)
    manifest = service.load_manifest(batch_dir)
    record = service.load_record(batch_dir / manifest.sources[0].record_path)
    payload = record.model_dump(mode="json")
    payload["state"] = "CANDIDATE"
    payload["state_history"].append(
        {
            "from_state": "EXTRACTED",
            "to_state": "CANDIDATE",
            "actor": "bad-extractor",
            "reason": "Tried to promote an empty extraction.",
        }
    )
    candidate = ReportReverseRecord.model_validate(payload)
    audit = audit_report_record(candidate, RegistryStore(registry_root))
    codes = {item.code for item in audit.issues}
    assert {"SUMMARY_TOO_SHALLOW", "QUESTION_MISSING", "PAGE_EVIDENCE_MISSING", "METHOD_ROUTE_MISSING"} <= codes
    assert not audit.passed


def test_active_method_is_blocked_without_reproduction(tmp_path: Path) -> None:
    service, _batch_dir, record_path = _prepare_reviewed_report_batch(tmp_path)
    reviewed = service.load_record(record_path)
    payload = reviewed.model_dump(mode="json")
    payload["state"] = "APPROVED"
    payload["registry_changes"][0].update(
        {
            "change_id": "CH.TEST.ACTIVE.ROUTE",
            "registry": "routes",
            "object_id": "RT.TEST.UNREPRODUCED.V1",
            "target_status": "active",
            "after_object": {
                "route_id": "RT.TEST.UNREPRODUCED.V1",
                "question_patterns": ["test"],
                "lane_ids": ["US.ACTIVITY"],
                "node_ids": ["N.ACTIVITY.PRODUCTION"],
                "factor_ids": ["F.ACTIVITY.INDPRO"],
                "model_recipe_ids": ["M.UNIVARIATE_AR.V1"],
                "report_evidence": {reviewed.report_id: [1]},
                "status": "active",
            },
        }
    )
    payload["reviews"] = [
        {
            "review_id": "RV.TEST.ACTIVE",
            "reviewer": "test-reviewer",
            "reviewer_type": "CODEX",
            "review_run_id": "codex-active-review-pass-test",
            "decision": "APPROVE_ACTIVE",
            "scope_change_ids": ["CH.TEST.ACTIVE.ROUTE"],
            "rationale": "Activation requested only to exercise the reproduction gate.",
        }
    ]
    record = ReportReverseRecord.model_validate(payload)
    audit = audit_report_record(record, RegistryStore(service.registry_root))
    codes = {item.code for item in audit.issues}
    assert "ACTIVE_WITHOUT_REPRODUCTION" in codes
    assert "REPRODUCTION_EVIDENCE_INCOMPLETE" in codes
    assert not audit.can_activate


def test_changeset_is_non_mutating_then_requires_exact_codex_approval(tmp_path: Path) -> None:
    service, batch_dir, record_path = _prepare_reviewed_report_batch(tmp_path)
    report_id = service.load_record(record_path).report_id
    untouched_nodes = (service.registry_root / "nodes.json").read_bytes()
    assert report_id not in RegistryStore(service.registry_root).ids("reports")

    changeset_dir = service.build_changeset(batch_dir)
    assert report_id not in RegistryStore(service.registry_root).ids("reports")
    assert report_id in RegistryStore(changeset_dir / "registry").ids("reports")
    assert (changeset_dir / "registry" / "nodes.json").read_bytes() == untouched_nodes
    changeset_manifest = json.loads((changeset_dir / "manifest.json").read_text(encoding="utf-8"))
    assert changeset_manifest["registry_validation"] == "PASS"
    assert service.load_record(record_path).state == PipelineState.CHANGESET_READY

    approval_path = tmp_path / "approval.json"
    _write(
        approval_path,
        {
            "schema_version": "1.0.0",
            "changeset_id": changeset_manifest["changeset_id"],
            "content_hash": changeset_manifest["content_hash"],
            "decision": "APPROVE_APPLY",
            "reviewer": "release-reviewer",
            "reviewer_type": "CODEX",
            "rationale": "Exact staged registry documents and operation diff were reviewed.",
        },
    )
    receipt = service.apply_changeset(changeset_dir, approval_path)
    assert receipt.exists()
    assert report_id in RegistryStore(service.registry_root).ids("reports")
    assert (service.registry_root / "nodes.json").read_bytes() == untouched_nodes
    assert service.load_record(record_path).state == PipelineState.APPLIED


def test_numeric_aggregation_weights_from_extraction_are_rejected(tmp_path: Path) -> None:
    service, _batch_dir, record_path = _prepare_reviewed_report_batch(tmp_path)
    record = service.load_record(record_path)
    payload = record.model_dump(mode="json")
    change = payload["registry_changes"][0]
    change.update(
        {
            "change_id": "CH.TEST.WEIGHTS",
            "registry": "aggregations",
            "object_id": "AGG.TEST.LLM_WEIGHTS",
            "target_status": "reviewed",
            "after_object": {
                "aggregation_id": "AGG.TEST.LLM_WEIGHTS",
                "method": "weighted average",
                "weights": {"lane_a": 0.8, "lane_b": 0.2},
                "status": "reviewed",
            },
        }
    )
    payload["reviews"][0]["scope_change_ids"] = ["CH.TEST.WEIGHTS"]
    changed = ReportReverseRecord.model_validate(payload)
    audit = audit_report_record(changed, RegistryStore(service.registry_root))
    assert "LLM_NUMERIC_WEIGHT_FORBIDDEN" in {item.code for item in audit.issues}


def test_exported_json_schema_validates_the_candidate_example() -> None:
    schema = json.loads((ROOT / "schemas" / "report_ingestion.schema.json").read_text(encoding="utf-8"))
    example = json.loads(
        (ROOT / "report_pipeline" / "examples" / "report_record.example.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(example))
    assert errors == []


def test_inferred_only_evidence_cannot_support_a_registry_change(tmp_path: Path) -> None:
    service, _batch_dir, record_path = _prepare_reviewed_report_batch(tmp_path)
    record = service.load_record(record_path)
    payload = record.model_dump(mode="json")
    for evidence in payload["evidence"]:
        evidence["statement_status"] = "INFERRED"
    changed = ReportReverseRecord.model_validate(payload)
    audit = audit_report_record(changed, RegistryStore(service.registry_root))
    assert "CHANGE_WITHOUT_EXPLICIT_SOURCE" in {item.code for item in audit.issues}


def test_codex_extraction_pass_cannot_approve_itself(tmp_path: Path) -> None:
    service, _batch_dir, record_path = _prepare_reviewed_report_batch(tmp_path)
    record = service.load_record(record_path)
    payload = record.model_dump(mode="json")
    payload["reviews"][0]["review_run_id"] = payload["produced_by"]["producer_run_id"]
    changed = ReportReverseRecord.model_validate(payload)
    audit = audit_report_record(changed, RegistryStore(service.registry_root))
    assert "REVIEWED_STATE_WITHOUT_AUTHORIZED_REVIEW" in {item.code for item in audit.issues}
