from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from backend.app.report_ingestion.contracts import ReportReverseRecord
from backend.app.report_ingestion.policy import audit_report_record
from backend.app.registry import RegistryStore


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "report_pipeline" / "corpus30"
DOSSIERS = (
    CORPUS / "reverse_foundations.jsonl",
    CORPUS / "reverse_reports.jsonl",
    CORPUS / "reverse_web.jsonl",
)


def _catalog() -> dict:
    return json.loads((CORPUS / "source_catalog.json").read_text(encoding="utf-8"))


def _dossier_entries() -> list[dict]:
    entries: list[dict] = []
    for path in DOSSIERS:
        entries.extend(
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return entries


def test_corpus30_catalog_is_balanced_unique_and_primary_source_only() -> None:
    payload = _catalog()
    sources = payload["sources"]

    assert payload["catalog_id"] == "CORPUS30.20260715"
    assert len(sources) == 30
    assert len({item["source_id"] for item in sources}) == 30
    assert Counter(item["category"] for item in sources) == {
        "INSTITUTIONAL_REPORT_PDF": 10,
        "METHOD_WEB": 10,
        "FOUNDATION_PDF": 10,
    }
    assert all(item["source_url"].startswith("https://") for item in sources)
    assert all(item["jurisdiction_fit"] in {"US_DIRECT", "US_ADAPTABLE"} for item in sources)
    assert all(item["coverage"] for item in sources)
    assert all(item["expected_registry_value"] for item in sources)


def test_semantic_dossiers_cover_every_source_without_shallow_shortcuts() -> None:
    catalog_ids = {item["source_id"] for item in _catalog()["sources"]}
    entries = _dossier_entries()
    dossier_ids = {item["source_id"] for item in entries}

    assert len(entries) == 30
    assert dossier_ids == catalog_ids
    for item in entries:
        assert len(item["summary"]) >= 120
        assert len(item["question"]) >= 30
        assert len(item["evidence"]) >= 4
        assert len(item["variables"]) >= 4
        assert item["routes"]
        assert len(item["candidate_objects"]) >= 4
        assert "verbatim_quote" not in json.dumps(item, ensure_ascii=False)
        serialized = json.dumps(item, ensure_ascii=False).lower()
        assert "word frequency" not in serialized
        assert "词频" not in serialized

        variable_keys = {variable["key"] for variable in item["variables"]}
        for evidence in item["evidence"]:
            assert evidence["pages"][0] >= 1
            assert evidence["pages"][1] >= evidence["pages"][0]
            assert len(evidence["paraphrase"]) >= 40
        for route in item["routes"]:
            referenced = set(route["dv"] + route["iv"] + route.get("controls", []))
            assert referenced <= variable_keys
            assert route["estimand"]
            assert route["identification"]
            assert route["assumptions"]
            assert route["formula"]
            assert route["diagnostics"]
            assert route["robustness"]
            assert route["free_data"] in {"AVAILABLE", "PARTIAL", "UNAVAILABLE", "UNKNOWN"}


def test_exported_reverse_records_are_page_grounded_and_independently_reviewed() -> None:
    paths = sorted((CORPUS / "reverse_records").glob("*.json"))
    assert len(paths) == 30
    registry = RegistryStore(ROOT / "registry" / "v2")

    for path in paths:
        record = ReportReverseRecord.model_validate_json(path.read_text(encoding="utf-8"))
        assert record.source.source_file == f"LOCAL_SNAPSHOT:{path.stem}"
        assert record.source.copied_into_repository is False
        assert record.produced_by.producer_type == "CODEX"
        assert record.produced_by.producer_run_id
        assert len(record.evidence) >= 4
        assert all(evidence.reviewer_verified for evidence in record.evidence)
        assert all(evidence.page_end <= record.source.page_count for evidence in record.evidence)
        assert all(evidence.verbatim_quote is None for evidence in record.evidence)
        assert record.reviews
        assert all(review.reviewer_type == "CODEX" for review in record.reviews)
        assert all(review.review_run_id for review in record.reviews)
        assert all(
            review.review_run_id != record.produced_by.producer_run_id
            for review in record.reviews
        )
        assert record.reproduction.status == "NOT_APPLICABLE"
        assert all(change.registry == "reports" for change in record.registry_changes)
        assert all(change.target_status == "reviewed" for change in record.registry_changes)

        audit = audit_report_record(record, registry)
        assert audit.passed, audit.model_dump(mode="json")
        assert audit.can_build_changeset
        assert not audit.can_activate
