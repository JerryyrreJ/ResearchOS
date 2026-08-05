from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """All v0.2 contracts fail closed on fields outside the frozen schema."""

    model_config = ConfigDict(extra="forbid")


class Coverage(StrEnum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    PARSING_QUERY = "PARSING_QUERY"
    CLASSIFYING_WORKFLOW = "CLASSIFYING_WORKFLOW"
    ROUTING_LANES = "ROUTING_LANES"
    ROUTING_NODES = "ROUTING_NODES"
    SELECTING_FACTORS = "SELECTING_FACTORS"
    PLANNING_MODELS = "PLANNING_MODELS"
    SELECTING_PARAMETERS = "SELECTING_PARAMETERS"
    VALIDATING_PLAN = "VALIDATING_PLAN"
    EXECUTING_MODELS = "EXECUTING_MODELS"
    AGGREGATING_LANES = "AGGREGATING_LANES"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_JOB_STATUSES = {
    JobStatus.COMPLETE,
    JobStatus.PARTIAL,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
}


class GraphNodeType(StrEnum):
    QUESTION = "QUESTION"
    QUERY = "QUERY"
    CLAIM = "CLAIM"
    LANE = "LANE"
    MECHANISM = "MECHANISM"
    RESEARCH_NODE = "RESEARCH_NODE"
    FACTOR = "FACTOR"
    DATASET = "DATASET"
    TRANSFORM = "TRANSFORM"
    MODEL_RUN = "MODEL_RUN"
    MODEL_SPECIFICATION = "MODEL_SPECIFICATION"
    RESEARCH_DEPTH_GATE = "RESEARCH_DEPTH_GATE"
    DIAGNOSTIC = "DIAGNOSTIC"
    EVIDENCE = "EVIDENCE"
    LANE_SIGNAL = "LANE_SIGNAL"
    AGGREGATION = "AGGREGATION"
    FINAL_CLAIM = "FINAL_CLAIM"
    FALSIFIER = "FALSIFIER"


class ResearchJobCreate(StrictModel):
    question: str = Field(min_length=3, max_length=4000)
    as_of_date: date | None = None
    display_mode: Literal["STANDARD", "COMPACT", "ACADEMIC"] = "STANDARD"


class ResearchRequest(BaseModel):
    """Legacy request. horizon_months is accepted only for v0.1 compatibility."""

    question: str = Field(min_length=3, max_length=4000)
    as_of_date: date | None = None
    horizon_months: int | None = Field(default=None, ge=1, le=60)


class HorizonSpec(StrictModel):
    minimum: int = Field(ge=0, le=240)
    maximum: int = Field(ge=0, le=240)
    unit: Literal["DAYS", "WEEKS", "MONTHS", "QUARTERS", "YEARS"] = "MONTHS"
    source: Literal["USER_EXPLICIT", "POLICY_DEFAULT"]
    raw_text: str | None = None

    @model_validator(mode="after")
    def ordered(self) -> "HorizonSpec":
        if self.maximum < self.minimum:
            raise ValueError("horizon maximum must be >= minimum")
        return self


class StructuredQuery(StrictModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    jurisdiction: Literal["US", "CN", "GLOBAL", "OTHER"] = "US"
    domain: Literal[
        "MACRO",
        "EQUITY_INDEX",
        "SINGLE_EQUITY",
        "BOND",
        "INDUSTRY",
        "COMMODITY",
        "CROSS_ASSET",
        "OTHER",
    ] = "MACRO"
    question: str
    as_of_date: date
    target_concepts: list[str] = Field(default_factory=list, max_length=12)
    question_form: Literal[
        "FORECAST",
        "NOWCAST",
        "DRIVER",
        "CAUSAL",
        "SCENARIO",
        "ASSET_TRANSMISSION",
        "STATE_ASSESSMENT",
    ]
    horizon: HorizonSpec
    conditional_events: list[str] = Field(default_factory=list, max_length=8)
    output_requirements: list[str] = Field(default_factory=list, max_length=8)
    policy_defaults: list[str] = Field(default_factory=list)


class LaneDecision(StrictModel):
    lane_id: str
    priority: Literal["CORE", "SUPPORTING", "LOW"]
    reason: str


class NodeDecision(StrictModel):
    node_id: str
    lane_id: str
    depends_on: list[str] = Field(default_factory=list)
    reason: str


class FactorDecision(StrictModel):
    factor_id: str
    node_id: str
    role: Literal["CORE", "SUPPORTING", "BACKGROUND"]
    reason: str


class ParameterSelection(StrictModel):
    model_recipe_id: str
    values: dict[str, Any]
    source: Literal["LLM_ALLOWLIST", "POLICY_DEFAULT", "FALLBACK"]


class ModelDecision(StrictModel):
    specification_id: str | None = None
    model_recipe_id: str
    node_id: str
    factor_ids: list[str]
    parameters: ParameterSelection
    reason: str
    role: Literal["CORE", "BENCHMARK", "ROBUSTNESS", "FALSIFICATION"] = "CORE"


class MechanismDecision(StrictModel):
    mechanism_id: str
    lane_id: str
    role: Literal["CORE", "SUPPORTING", "LOW"]
    reason: str


class ModelSpecificationDecision(StrictModel):
    specification_id: str
    lane_id: str
    mechanism_id: str
    node_id: str
    model_recipe_id: str | None = None
    factor_ids: list[str]
    parameters: dict[str, Any] = Field(default_factory=dict)
    role: Literal["CORE", "BENCHMARK", "ROBUSTNESS", "FALSIFICATION", "BLOCKED"]
    execution_status: Literal["ACTIVE", "BLOCKED"]
    blocked_reason: str | None = None


class ResearchPlan(StrictModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    workflow_id: str
    complexity_class: Literal["SIMPLE_MEASUREMENT", "STANDARD_FORECAST", "SYSTEM_FORECAST", "CAUSAL_ATTRIBUTION", "STRUCTURAL_SCENARIO"] = "STANDARD_FORECAST"
    evidence_budget_id: str | None = None
    query: StructuredQuery
    lanes: list[LaneDecision]
    excluded_lanes: list[dict[str, str]] = Field(default_factory=list)
    mechanisms: list[MechanismDecision] = Field(default_factory=list)
    nodes: list[NodeDecision]
    factors: list[FactorDecision]
    model_specifications: list[ModelSpecificationDecision] = Field(default_factory=list)
    models: list[ModelDecision]
    coverage: Coverage
    coverage_score: float = Field(ge=0, le=1)
    unsupported_aspects: list[str] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)


class GraphNode(StrictModel):
    node_id: str
    node_type: GraphNodeType
    label: str
    status: Literal["NOT_ROUTED", "PLANNED", "BLOCKED", "PENDING", "RUNNING", "SUCCESS", "WARNING", "FAILED", "SKIPPED"] = "PENDING"
    lane_id: str | None = None
    role: str | None = None
    summary: str | None = None
    detail_endpoint: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(StrictModel):
    edge_id: str
    source: str
    target: str
    relation: Literal[
        "PARSES_TO",
        "DECOMPOSES_TO",
        "ROUTES_TO",
        "USES",
        "TRANSFORMS_TO",
        "ESTIMATES",
        "DIAGNOSES",
        "SUPPORTS",
        "REFUTES",
        "AGGREGATES_TO",
        "FALSIFIED_BY",
    ]


class ResearchGraph(StrictModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    job_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    updated_at: datetime


class DiagnosticResult(StrictModel):
    diagnostic_id: str
    name: str
    statistic: float | str | None = None
    p_value: float | None = None
    status: Literal["PASS", "WARNING", "FAIL", "NOT_APPLICABLE"]
    interpretation: str
    credibility_impact: str


class TableCoefficient(StrictModel):
    variable_id: str
    label: str
    coefficient: float
    standard_error: float
    p_value: float
    ci_low: float
    ci_high: float
    stars: str = ""


class AcademicTable(StrictModel):
    table_id: str
    title: str
    dependent_variable: str
    columns: list[str]
    coefficients: dict[str, list[TableCoefficient]]
    statistics: dict[str, list[str | int | float | None]]
    notes: list[str] = Field(default_factory=list)


class PanelConfig(BaseModel):
    """Legacy fixture configuration retained for the v0.1 compatibility runner."""

    start_year: int = Field(default=2010, ge=2000, le=2026)
    fixed_effects: Literal["ENTITY", "TIME", "TWO_WAY"] = "TWO_WAY"
    covariance: Literal["HC1", "CLUSTER_ENTITY"] = "CLUSTER_ENTITY"


class ParsedQuery(BaseModel):
    """Legacy v0.1 routing contract retained during the migration window."""

    jurisdiction: Literal["US"] = "US"
    horizon_months: int = Field(default=3, ge=1, le=60)
    intent: Literal[
        "INFLATION",
        "ACTIVITY",
        "LABOR",
        "RATES",
        "FISCAL",
        "ENERGY",
        "HOUSING_PANEL",
        "GENERAL_MACRO",
    ] = "GENERAL_MACRO"
    selected_modules: list[str]
    panel_config: PanelConfig = Field(default_factory=PanelConfig)
    coverage: Literal["FULL", "PARTIAL", "UNSUPPORTED"] = "PARTIAL"
    unsupported_aspects: list[str] = Field(default_factory=list)
    reasoning: str = ""


class ArtifactMetadata(StrictModel):
    artifact_id: str
    job_id: str
    node_id: str
    artifact_type: Literal["JSON", "CSV", "HTML", "LATEX", "CHART", "DATA_SNAPSHOT"]
    title: str
    media_type: str
    sha256: str
    relative_path: str
    created_at: datetime
