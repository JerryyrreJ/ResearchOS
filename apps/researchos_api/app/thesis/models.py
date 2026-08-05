from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "0.1.0-frozen"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["0.1.0-frozen"] = CONTRACT_VERSION


class Definition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    term: str
    definition: str | None = None
    status: str = "MISSING"
    source_refs: list[str] = Field(default_factory=list)


class ThesisBuild(ContractModel):
    thesis_id: str
    project_id: str
    version_id: str
    parent_version_id: str | None = None
    raw_claim: str
    normalized_claim: str
    as_of_date: str
    language_level: Literal["DESCRIPTIVE", "PREDICTIVE", "ASSOCIATIONAL", "STRUCTURAL_PROXY", "CAUSAL"]
    scope: dict[str, Any] = Field(default_factory=dict)
    definitions: list[Definition]
    required_evidence_types: list[str]
    falsifier_requirements: list[str]
    input_object_refs: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompileIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    severity: Literal["ERROR", "WARNING", "INFO"]
    blocking: bool
    message: str
    related_refs: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceBundle(ContractModel):
    bundle_id: str
    request_id: str
    research_job_id: str
    status: Literal["COMPLETE", "PARTIAL", "FAILED", "CANCELLED"]
    coverage: Literal["FULL", "PARTIAL", "UNSUPPORTED", "OUT_OF_SCOPE"]
    evidence_type: Literal["DESCRIPTIVE", "PREDICTIVE", "ASSOCIATIONAL", "DYNAMIC_ASSOCIATION", "STRUCTURAL_PROXY", "CAUSAL_IDENTIFIED"]
    engine_claim: str | None
    model_runs: list[dict[str, Any]]
    diagnostics: list[dict[str, Any]]
    robustness: list[dict[str, Any]]
    evidence_items: list[dict[str, Any]]
    falsifiers: list[dict[str, Any]]
    limitations: list[str]
    input_object_refs: list[dict[str, Any]]
    registry_version: str
    result_hash: str
    artifacts: list[dict[str, Any]]
    trace_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerifyRequest(BaseModel):
    evidence_bundle: EvidenceBundle
