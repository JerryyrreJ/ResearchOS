from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PipelineState(str, Enum):
    INGESTED = "INGESTED"
    EXTRACTED = "EXTRACTED"
    CANDIDATE = "CANDIDATE"
    REVIEWED = "REVIEWED"
    REPRODUCTION_PENDING = "REPRODUCTION_PENDING"
    REPRODUCED = "REPRODUCED"
    APPROVED = "APPROVED"
    CHANGESET_READY = "CHANGESET_READY"
    APPLIED = "APPLIED"
    BLOCKED = "BLOCKED"
    EVIDENCE_ONLY = "EVIDENCE_ONLY"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"


class EvidenceKind(str, Enum):
    RESEARCH_QUESTION = "RESEARCH_QUESTION"
    CLAIM = "CLAIM"
    MECHANISM = "MECHANISM"
    VARIABLE_DEFINITION = "VARIABLE_DEFINITION"
    DATA_SOURCE = "DATA_SOURCE"
    MODEL_SPECIFICATION = "MODEL_SPECIFICATION"
    IDENTIFICATION = "IDENTIFICATION"
    DIAGNOSTIC = "DIAGNOSTIC"
    ROBUSTNESS = "ROBUSTNESS"
    RESULT = "RESULT"
    LIMITATION = "LIMITATION"
    AGGREGATION = "AGGREGATION"


class PageBasis(str, Enum):
    PDF_FILE_PAGE = "PDF_FILE_PAGE"
    PRINTED_PAGE = "PRINTED_PAGE"
    FORM_FEED_PAGE = "FORM_FEED_PAGE"


class SourceIdentity(StrictModel):
    source_id: str = Field(min_length=3)
    source_file: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    byte_size: int = Field(ge=1)
    media_type: str = "application/pdf"
    page_count: int | None = Field(default=None, ge=1)
    title: str = Field(min_length=1)
    institution: str | None = None
    publication_date: str | None = None
    jurisdiction_tags: list[str] = Field(default_factory=list)
    license_status: Literal[
        "PRIVATE_RESEARCH_INPUT", "PUBLIC", "RESTRICTED", "UNKNOWN"
    ] = "PRIVATE_RESEARCH_INPUT"
    copied_into_repository: Literal[False] = False


class PageEvidence(StrictModel):
    evidence_id: str = Field(min_length=5)
    kind: EvidenceKind
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    page_basis: PageBasis = PageBasis.PDF_FILE_PAGE
    statement_status: Literal["EXPLICIT", "INFERRED", "NOT_STATED"] = "EXPLICIT"
    locator_label: str | None = None
    paraphrase: str = ""
    verbatim_quote: str | None = Field(default=None, max_length=240)
    supports: list[str] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reviewer_verified: bool = False

    @model_validator(mode="after")
    def page_range_is_ordered(self) -> "PageEvidence":
        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self


class ResearchQuestion(StrictModel):
    question_id: str = Field(min_length=5)
    question_text: str = ""
    task_types: list[
        Literal["FORECAST", "NOWCAST", "DRIVER", "CAUSAL", "SCENARIO", "ASSET_TRANSMISSION"]
    ] = Field(default_factory=list)
    horizon_text: str | None = None
    as_of_text: str | None = None
    target_variables: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class VariableDefinition(StrictModel):
    variable_id: str = Field(min_length=3)
    name: str = ""
    role: Literal[
        "DEPENDENT",
        "OUTCOME",
        "EXPOSURE",
        "TREATMENT",
        "INSTRUMENT",
        "CONTROL",
        "STATE",
        "WEIGHT",
        "OTHER",
    ]
    definition: str = ""
    unit: str | None = None
    frequency: str | None = None
    provider: str | None = None
    table_or_series: str | None = None
    release_lag: str | None = None
    vintage_rule: str | None = None
    transformation: str | None = None
    lag: str | None = None
    mapped_factor_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class MethodRoute(StrictModel):
    method_route_id: str = Field(min_length=5)
    research_question_id: str = Field(min_length=5)
    lane_ref: str = ""
    mechanism_ref: str = ""
    node_ref: str = ""
    method_family: str = ""
    estimand: str = ""
    dependent_variable_ids: list[str] = Field(default_factory=list)
    independent_variable_ids: list[str] = Field(default_factory=list)
    control_variable_ids: list[str] = Field(default_factory=list)
    identification_strategy: str = ""
    identifying_assumptions: list[str] = Field(default_factory=list)
    sample_definition: str = ""
    formula: str = ""
    diagnostic_requirements: list[str] = Field(default_factory=list)
    robustness_requirements: list[str] = Field(default_factory=list)
    upstream_refs: list[str] = Field(default_factory=list)
    downstream_refs: list[str] = Field(default_factory=list)
    aggregation_role: str = ""
    free_data_feasibility: Literal["AVAILABLE", "PARTIAL", "UNAVAILABLE", "UNKNOWN"] = "UNKNOWN"
    evidence_ids: list[str] = Field(default_factory=list)


class NoveltyReview(StrictModel):
    compared_registry_ids: list[str] = Field(default_factory=list)
    overlap_analysis: str = ""
    boundary_statement: str = ""
    independent_workflow_paths: list[str] = Field(default_factory=list)
    decision: Literal["DISTINCT", "MERGE_EXISTING", "UNRESOLVED"] = "UNRESOLVED"
    reviewer: str = ""


RegistryName = Literal[
    "lanes",
    "datasets",
    "factors",
    "nodes",
    "workflows",
    "models",
    "parameter_policies",
    "aggregations",
    "claims",
    "routes",
    "reports",
    "mechanisms",
    "model_specifications",
    "evidence_budgets",
    "synthesis_policies",
    "evidence_mappings",
    "scenario_mappings",
]


class RegistryChange(StrictModel):
    change_id: str = Field(min_length=5)
    operation: Literal["ADD", "UPDATE"]
    registry: RegistryName
    object_id: str = Field(min_length=2)
    target_status: Literal["candidate", "reviewed", "active", "blocked", "evidence_only", "fixture"]
    after_object: dict[str, Any]
    expected_before_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    evidence_ids: list[str] = Field(default_factory=list)
    method_route_ids: list[str] = Field(default_factory=list)
    rationale: str = ""
    novelty_review: NoveltyReview | None = None


class ReproductionRecord(StrictModel):
    status: Literal["NOT_STARTED", "PLANNED", "PASSED", "FAILED", "NOT_APPLICABLE"] = "NOT_STARTED"
    code_artifact: str | None = None
    synthetic_test_ids: list[str] = Field(default_factory=list)
    real_data_smoke_test_ids: list[str] = Field(default_factory=list)
    data_snapshot: str | None = None
    result_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    notes: list[str] = Field(default_factory=list)


class ReviewDecision(StrictModel):
    review_id: str = Field(min_length=5)
    reviewer: str = Field(min_length=1)
    reviewer_type: Literal["CODEX", "HUMAN", "LLM", "AUTOMATED"]
    review_run_id: str | None = None
    decision: Literal[
        "APPROVE_CANDIDATE",
        "APPROVE_REVIEWED",
        "APPROVE_ACTIVE",
        "APPROVE_APPLY",
        "REQUEST_CHANGES",
        "BLOCK",
        "REJECT",
        "MARK_DUPLICATE",
    ]
    scope_change_ids: list[str] = Field(default_factory=lambda: ["ALL"])
    decided_at: datetime = Field(default_factory=utc_now)
    rationale: str = Field(min_length=1)


class BlockingIssue(StrictModel):
    issue_id: str = Field(min_length=3)
    severity: Literal["WARNING", "BLOCKING"]
    message: str = Field(min_length=1)
    resolution: str | None = None


class StateTransition(StrictModel):
    from_state: PipelineState | None
    to_state: PipelineState
    at: datetime = Field(default_factory=utc_now)
    actor: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ProducerIdentity(StrictModel):
    producer_type: Literal["CODEX", "HUMAN", "LLM", "HYBRID", "AUTOMATED"]
    producer_name: str = Field(min_length=1)
    producer_run_id: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None


class ReportReverseRecord(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: str = Field(min_length=5)
    batch_id: str = Field(min_length=3)
    report_id: str = Field(min_length=3)
    state: PipelineState
    source: SourceIdentity
    produced_by: ProducerIdentity
    executive_summary: str = ""
    jurisdiction_fit: Literal["US_DIRECT", "US_ADAPTABLE", "CONTEXT_ONLY", "OUT_OF_SCOPE", "UNKNOWN"] = "UNKNOWN"
    questions: list[ResearchQuestion] = Field(default_factory=list)
    evidence: list[PageEvidence] = Field(default_factory=list)
    variables: list[VariableDefinition] = Field(default_factory=list)
    method_routes: list[MethodRoute] = Field(default_factory=list)
    registry_changes: list[RegistryChange] = Field(default_factory=list)
    reproduction: ReproductionRecord = Field(default_factory=ReproductionRecord)
    reviews: list[ReviewDecision] = Field(default_factory=list)
    blockers: list[BlockingIssue] = Field(default_factory=list)
    state_history: list[StateTransition] = Field(default_factory=list)

    @model_validator(mode="after")
    def ids_are_unique_and_state_matches_history(self) -> "ReportReverseRecord":
        collections = {
            "evidence_id": [item.evidence_id for item in self.evidence],
            "question_id": [item.question_id for item in self.questions],
            "variable_id": [item.variable_id for item in self.variables],
            "method_route_id": [item.method_route_id for item in self.method_routes],
            "change_id": [item.change_id for item in self.registry_changes],
            "review_id": [item.review_id for item in self.reviews],
        }
        for label, values in collections.items():
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label}")
        if self.state_history and self.state_history[-1].to_state != self.state:
            raise ValueError("last state transition must end at current state")
        return self


class BatchSource(StrictModel):
    report_id: str
    record_path: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    duplicate_of: list[str] = Field(default_factory=list)


class BatchManifest(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    batch_id: str = Field(min_length=3)
    created_at: datetime = Field(default_factory=utc_now)
    sources: list[BatchSource]
    source_files_copied: Literal[False] = False
    notes: list[str] = Field(default_factory=list)


class ApplyApproval(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    changeset_id: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    decision: Literal["APPROVE_APPLY"]
    reviewer: str = Field(min_length=1)
    reviewer_type: Literal["CODEX", "HUMAN"]
    approved_at: datetime = Field(default_factory=utc_now)
    rationale: str = Field(min_length=1)
