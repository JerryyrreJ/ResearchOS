import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, RefResolver

from apps.researchos_api.app.thesis.compiler import ThesisCompiler
from apps.researchos_api.app.thesis.models import EvidenceBundle, ThesisBuild

ROOT = Path(__file__).parents[3]


def load(name: str):
    return json.loads((ROOT / "fixtures" / "contracts" / name).read_text(encoding="utf-8"))


def validate_contract(name: str, value: dict):
    path = ROOT / "contracts" / "v1" / name
    schema = json.loads(path.read_text(encoding="utf-8"))
    store = {}
    for schema_path in path.parent.glob("*.schema.json"):
        child = json.loads(schema_path.read_text(encoding="utf-8"))
        store[child["$id"]] = child
    resolver = RefResolver.from_schema(schema, store=store)
    Draft202012Validator(schema, resolver=resolver).validate(value)


def test_initial_compile_exposes_real_blockers_and_matches_contract():
    result = ThesisCompiler().compile(ThesisBuild.model_validate(load("sample_thesis_build.json")))
    assert result["conclusion_state"] == "COMPILE_FAILED"
    assert {"DEF001", "HORIZON001"} <= {x["code"] for x in result["issues"]}
    assert {"DEF001", "HORIZON001", "CLAIM_LANG001", "VAR001", "FALS001"} <= {x["code"] for x in result["issues"]}
    validate_contract("compile_result.schema.json", result)


def test_associational_evidence_never_upgrades_causal_claim():
    compiler = ThesisCompiler()
    thesis = ThesisBuild.model_validate(load("sample_thesis_build.json"))
    thesis.definitions = [d.model_copy(update={"definition": d.term + "的可操作定义", "status": "DEFINED"}) for d in thesis.definitions]
    thesis.scope["horizon_text"] = "未来 90 天"
    evidence = EvidenceBundle.model_validate(load("sample_evidence_bundle.json"))
    result = compiler.compile(thesis, evidence)
    assert result["language_policy"]["allowed_level"] == "ASSOCIATIONAL"
    assert result["language_policy"]["requested_level"] == "CAUSAL"
    assert any(x["code"] == "CLAIM_LANG001" for x in result["issues"])
    assert "因果" in result["compiled_claim"]
    validate_contract("compile_result.schema.json", result)


def test_tool_request_matches_frozen_contract():
    value = ThesisCompiler().tool_request(ThesisBuild.model_validate(load("sample_thesis_build.json")))
    validate_contract("tool_request.schema.json", value)


def ready_thesis() -> ThesisBuild:
    thesis = ThesisBuild.model_validate(load("sample_thesis_build.json"))
    thesis.definitions = [d.model_copy(update={"definition": d.term + "的可操作定义", "status": "DEFINED"}) for d in thesis.definitions]
    thesis.scope["horizon_text"] = "未来 90 天"
    thesis.metadata.update({"competition_controls": ["policy_rate"], "falsifiers_registered": True, "tool_route_status": "READY"})
    return thesis


@pytest.mark.parametrize("coverage,status", [("PARTIAL", "COMPLETE"), ("FULL", "PARTIAL"), ("UNSUPPORTED", "COMPLETE")])
def test_incomplete_coverage_is_evidence_insufficient(coverage, status):
    evidence = EvidenceBundle.model_validate(load("sample_evidence_bundle.json"))
    evidence.coverage = coverage
    evidence.status = status
    result = ThesisCompiler().compile(ready_thesis(), evidence)
    assert result["conclusion_state"] == "EVIDENCE_INSUFFICIENT"


def test_blocking_diagnostic_is_evidence_insufficient():
    evidence = EvidenceBundle.model_validate(load("sample_evidence_bundle.json"))
    evidence.evidence_type = "CAUSAL_IDENTIFIED"
    evidence.diagnostics = [{"diagnostic_id": "D1", "status": "FAIL", "blocking": True, "interpretation": "unstable"}]
    result = ThesisCompiler().compile(ready_thesis(), evidence)
    assert result["conclusion_state"] == "EVIDENCE_INSUFFICIENT"
    assert "DIAG001" in {x["code"] for x in result["issues"]}


def test_triggered_falsifier_and_support_is_conflict():
    evidence = EvidenceBundle.model_validate(load("sample_evidence_bundle.json"))
    evidence.evidence_type = "CAUSAL_IDENTIFIED"
    evidence.falsifiers = [{"falsifier_id": "F1", "status": "TRIGGERED"}]
    result = ThesisCompiler().compile(ready_thesis(), evidence)
    assert result["conclusion_state"] == "EVIDENCE_CONFLICT"


def test_result_hash_is_reproducible_for_immutable_payload(monkeypatch):
    compiler = ThesisCompiler()
    thesis = ready_thesis()
    first = compiler.compile(thesis)
    second = dict(first)
    result_hash = second.pop("result_hash")
    from apps.researchos_api.app.thesis.compiler import _hash
    assert result_hash == _hash(second)
