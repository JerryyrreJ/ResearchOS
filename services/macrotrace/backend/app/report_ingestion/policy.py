from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field

from backend.app.registry import RegistryStore

from .contracts import PipelineState, ReportReverseRecord, StrictModel


class PolicyIssue(StrictModel):
    code: str
    severity: str
    path: str
    message: str
    remediation: str


class ReportPolicyAudit(StrictModel):
    record_id: str
    report_id: str
    current_state: PipelineState
    max_permitted_state: PipelineState
    issues: list[PolicyIssue] = Field(default_factory=list)
    can_build_changeset: bool = False
    can_activate: bool = False

    @property
    def passed(self) -> bool:
        return not any(issue.severity in {"ERROR", "BLOCKING"} for issue in self.issues)


STATE_TRANSITIONS: dict[PipelineState | None, set[PipelineState]] = {
    None: {PipelineState.INGESTED},
    PipelineState.INGESTED: {
        PipelineState.EXTRACTED,
        PipelineState.DUPLICATE,
        PipelineState.BLOCKED,
        PipelineState.REJECTED,
    },
    PipelineState.EXTRACTED: {
        PipelineState.CANDIDATE,
        PipelineState.EVIDENCE_ONLY,
        PipelineState.BLOCKED,
        PipelineState.REJECTED,
    },
    PipelineState.CANDIDATE: {
        PipelineState.REVIEWED,
        PipelineState.EVIDENCE_ONLY,
        PipelineState.DUPLICATE,
        PipelineState.BLOCKED,
        PipelineState.REJECTED,
    },
    PipelineState.REVIEWED: {
        PipelineState.REPRODUCTION_PENDING,
        PipelineState.APPROVED,
        PipelineState.EVIDENCE_ONLY,
        PipelineState.BLOCKED,
        PipelineState.REJECTED,
    },
    PipelineState.REPRODUCTION_PENDING: {
        PipelineState.REPRODUCED,
        PipelineState.BLOCKED,
    },
    PipelineState.REPRODUCED: {
        PipelineState.APPROVED,
        PipelineState.BLOCKED,
    },
    PipelineState.APPROVED: {
        PipelineState.CHANGESET_READY,
        PipelineState.BLOCKED,
    },
    PipelineState.CHANGESET_READY: {
        PipelineState.APPLIED,
        PipelineState.BLOCKED,
    },
    PipelineState.APPLIED: set(),
    PipelineState.BLOCKED: set(),
    PipelineState.EVIDENCE_ONLY: set(),
    PipelineState.DUPLICATE: set(),
    PipelineState.REJECTED: set(),
}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _has_authorized_review(record: ReportReverseRecord, decision: str, change_id: str) -> bool:
    for review in record.reviews:
        if review.decision != decision or not (
            "ALL" in review.scope_change_ids or change_id in review.scope_change_ids
        ):
            continue
        if review.reviewer_type == "HUMAN":
            return True
        if review.reviewer_type == "CODEX":
            if not review.review_run_id:
                continue
            if (
                record.produced_by.producer_run_id
                and review.review_run_id == record.produced_by.producer_run_id
            ):
                continue
            return True
    return False


def audit_report_record(
    record: ReportReverseRecord, registry: RegistryStore | None = None
) -> ReportPolicyAudit:
    issues: list[PolicyIssue] = []

    def add(code: str, severity: str, path: str, message: str, remediation: str) -> None:
        issues.append(
            PolicyIssue(
                code=code,
                severity=severity,
                path=path,
                message=message,
                remediation=remediation,
            )
        )

    # State history is append-only and must follow the explicit state machine.
    previous: PipelineState | None = None
    for index, transition in enumerate(record.state_history):
        if transition.from_state != previous or transition.to_state not in STATE_TRANSITIONS.get(previous, set()):
            add(
                "ILLEGAL_STATE_TRANSITION",
                "BLOCKING",
                f"state_history[{index}]",
                f"Illegal transition {transition.from_state!s} -> {transition.to_state!s}.",
                "Append only a transition allowed by the published state machine.",
            )
        previous = transition.to_state

    evidence_ids = {item.evidence_id for item in record.evidence}
    evidence_by_id = {item.evidence_id: item for item in record.evidence}
    question_ids = {item.question_id for item in record.questions}
    variable_ids = {item.variable_id for item in record.variables}
    route_ids = {item.method_route_id for item in record.method_routes}
    change_ids = {item.change_id for item in record.registry_changes}

    if record.source.copied_into_repository:
        add(
            "SOURCE_COPIED_TO_REPOSITORY",
            "BLOCKING",
            "source.copied_into_repository",
            "Source reports must remain outside the code repository.",
            "Keep only a local pointer, fingerprint and short page evidence paraphrases.",
        )

    candidate_states = {
        PipelineState.CANDIDATE,
        PipelineState.REVIEWED,
        PipelineState.REPRODUCTION_PENDING,
        PipelineState.REPRODUCED,
        PipelineState.APPROVED,
        PipelineState.CHANGESET_READY,
        PipelineState.APPLIED,
    }
    reviewed_states = {
        PipelineState.REVIEWED,
        PipelineState.REPRODUCTION_PENDING,
        PipelineState.REPRODUCED,
        PipelineState.APPROVED,
        PipelineState.CHANGESET_READY,
        PipelineState.APPLIED,
    }

    if record.state in reviewed_states:
        for change in record.registry_changes:
            reviewed = _has_authorized_review(record, "APPROVE_REVIEWED", change.change_id)
            active = _has_authorized_review(record, "APPROVE_ACTIVE", change.change_id)
            if not reviewed and not active:
                add(
                    "REVIEWED_STATE_WITHOUT_AUTHORIZED_REVIEW",
                    "BLOCKING",
                    "reviews",
                    f"Change {change.change_id} reached a reviewed state without an authorized decision.",
                    "Add a separate-pass CODEX or HUMAN APPROVE_REVIEWED/APPROVE_ACTIVE review scoped to the change.",
                )

    if record.state in candidate_states:
        if record.source.page_count is None:
            add(
                "PAGE_COUNT_MISSING",
                "ERROR",
                "source.page_count",
                "A candidate record requires a stable PDF page count.",
                "Record the file page count before extracting page evidence.",
            )
        if len(record.executive_summary.strip()) < 30:
            add(
                "SUMMARY_TOO_SHALLOW",
                "ERROR",
                "executive_summary",
                "The reverse-engineering summary is missing or too short.",
                "Summarize the question, mechanism, empirical design and limitations.",
            )
        if not record.questions:
            add(
                "QUESTION_MISSING",
                "ERROR",
                "questions",
                "No source research question was recorded.",
                "Add at least one page-grounded research question.",
            )
        if not record.evidence:
            add(
                "PAGE_EVIDENCE_MISSING",
                "ERROR",
                "evidence",
                "No page evidence was recorded.",
                "Add typed page evidence with a paraphrase and page basis.",
            )
        if not record.method_routes:
            add(
                "METHOD_ROUTE_MISSING",
                "ERROR",
                "method_routes",
                "No question-to-method route was reconstructed.",
                "Map the question through lane, mechanism, node, variables and method.",
            )

    if record.state == PipelineState.EVIDENCE_ONLY:
        if not record.evidence or len(record.executive_summary.strip()) < 30:
            add(
                "EVIDENCE_ONLY_UNGROUNDED",
                "ERROR",
                "evidence",
                "Evidence-only records still require a grounded summary and page evidence.",
                "Add page evidence or reject the report instead.",
            )

    page_count = record.source.page_count
    for index, evidence in enumerate(record.evidence):
        if page_count is not None and evidence.page_end > page_count:
            add(
                "PAGE_OUT_OF_RANGE",
                "ERROR",
                f"evidence[{index}]",
                f"Evidence ends on page {evidence.page_end}, beyond page count {page_count}.",
                "Correct the page basis or the page range.",
            )
        if record.state in candidate_states and len(evidence.paraphrase.strip()) < 20:
            add(
                "EVIDENCE_PARAPHRASE_TOO_SHALLOW",
                "ERROR",
                f"evidence[{index}].paraphrase",
                "Page evidence needs a substantive paraphrase.",
                "Describe what the page establishes without copying a long passage.",
            )
        if record.state in reviewed_states and not evidence.reviewer_verified:
            add(
                "EVIDENCE_NOT_VERIFIED",
                "BLOCKING",
                f"evidence[{index}].reviewer_verified",
                "Reviewed records cannot rely on unverified page evidence.",
                "A separate Codex review pass or human reviewer must compare the paraphrase with the referenced page.",
            )

    for index, question in enumerate(record.questions):
        missing = set(question.evidence_ids) - evidence_ids
        if missing or not question.evidence_ids:
            add(
                "QUESTION_EVIDENCE_INVALID",
                "ERROR",
                f"questions[{index}].evidence_ids",
                f"Question has missing or empty evidence references: {sorted(missing)}.",
                "Link the question to valid page evidence IDs.",
            )

    for index, variable in enumerate(record.variables):
        missing = set(variable.evidence_ids) - evidence_ids
        if missing or not variable.evidence_ids:
            add(
                "VARIABLE_EVIDENCE_INVALID",
                "ERROR",
                f"variables[{index}].evidence_ids",
                f"Variable definition has missing or empty evidence references: {sorted(missing)}.",
                "Link every variable definition to the pages that define or use it.",
            )

    for index, route in enumerate(record.method_routes):
        if route.research_question_id not in question_ids:
            add(
                "ROUTE_QUESTION_UNKNOWN",
                "ERROR",
                f"method_routes[{index}].research_question_id",
                "Method route references an unknown research question.",
                "Use a question_id defined in this record.",
            )
        missing_evidence = set(route.evidence_ids) - evidence_ids
        missing_variables = (
            set(route.dependent_variable_ids)
            | set(route.independent_variable_ids)
            | set(route.control_variable_ids)
        ) - variable_ids
        if missing_evidence or not route.evidence_ids:
            add(
                "ROUTE_EVIDENCE_INVALID",
                "ERROR",
                f"method_routes[{index}].evidence_ids",
                f"Method route has missing or empty evidence references: {sorted(missing_evidence)}.",
                "Link the route to question, mechanism and specification pages.",
            )
        if missing_variables:
            add(
                "ROUTE_VARIABLE_UNKNOWN",
                "ERROR",
                f"method_routes[{index}]",
                f"Method route references unknown variables: {sorted(missing_variables)}.",
                "Define each variable before using it in a route.",
            )
        if record.state in candidate_states:
            required_text = {
                "lane_ref": route.lane_ref,
                "mechanism_ref": route.mechanism_ref,
                "node_ref": route.node_ref,
                "method_family": route.method_family,
                "estimand": route.estimand,
                "identification_strategy": route.identification_strategy,
                "sample_definition": route.sample_definition,
                "formula": route.formula,
                "aggregation_role": route.aggregation_role,
            }
            missing_text = sorted(key for key, value in required_text.items() if not value.strip())
            if missing_text:
                add(
                    "ROUTE_CONTRACT_INCOMPLETE",
                    "ERROR",
                    f"method_routes[{index}]",
                    f"Method route is missing fields: {missing_text}.",
                    "Complete the empirical specification; use explicit 'not applicable' where justified.",
                )

    active_sensitive_registries = set(RegistryStore.FILES) - {"reports"}
    for index, change in enumerate(record.registry_changes):
        path = f"registry_changes[{index}]"
        missing_evidence = set(change.evidence_ids) - evidence_ids
        missing_routes = set(change.method_route_ids) - route_ids
        if missing_evidence or not change.evidence_ids:
            add(
                "CHANGE_EVIDENCE_INVALID",
                "ERROR",
                f"{path}.evidence_ids",
                f"Registry change has missing or empty evidence references: {sorted(missing_evidence)}.",
                "Link every changed object to report page evidence.",
            )
        referenced_evidence = [
            evidence_by_id[evidence_id]
            for evidence_id in change.evidence_ids
            if evidence_id in evidence_by_id
        ]
        if referenced_evidence and not any(
            evidence.statement_status == "EXPLICIT" for evidence in referenced_evidence
        ):
            add(
                "CHANGE_WITHOUT_EXPLICIT_SOURCE",
                "BLOCKING",
                f"{path}.evidence_ids",
                "A Registry change cannot be supported only by inferred or not-stated evidence.",
                "Add at least one page where the report explicitly establishes the proposed object.",
            )
        if missing_routes:
            add(
                "CHANGE_ROUTE_INVALID",
                "ERROR",
                f"{path}.method_route_ids",
                f"Registry change references unknown method routes: {sorted(missing_routes)}.",
                "Use method_route_ids from this report record.",
            )
        if len(change.rationale.strip()) < 20:
            add(
                "CHANGE_RATIONALE_TOO_SHALLOW",
                "ERROR",
                f"{path}.rationale",
                "Registry changes require a substantive rationale.",
                "Explain the economic boundary, reuse value and compatibility impact.",
            )

        id_field = RegistryStore.ID_FIELDS[change.registry]
        if change.after_object.get(id_field) != change.object_id:
            add(
                "OBJECT_ID_MISMATCH",
                "BLOCKING",
                f"{path}.after_object",
                f"after_object.{id_field} must equal object_id.",
                "Correct the object identifier before staging.",
            )
        if change.after_object.get("status") != change.target_status:
            add(
                "TARGET_STATUS_MISMATCH",
                "BLOCKING",
                f"{path}.target_status",
                "target_status does not match after_object.status.",
                "Use one explicit lifecycle status in both fields.",
            )

        if registry is not None:
            exists = change.object_id in registry.ids(change.registry)
            if change.operation == "ADD" and exists and record.state != PipelineState.APPLIED:
                add(
                    "ADD_OBJECT_EXISTS",
                    "BLOCKING",
                    path,
                    f"{change.object_id} already exists in {change.registry}.",
                    "Use UPDATE after completing duplicate/conflict review.",
                )
            if change.operation == "ADD" and exists and record.state == PipelineState.APPLIED:
                if canonical_sha256(registry.get(change.registry, change.object_id)) != canonical_sha256(change.after_object):
                    add(
                        "APPLIED_OBJECT_DRIFT",
                        "BLOCKING",
                        path,
                        f"Applied object {change.registry}/{change.object_id} no longer matches the approved changeset.",
                        "Open a new reviewed UPDATE changeset; never edit applied provenance in place.",
                    )
            if change.operation == "UPDATE" and record.state != PipelineState.APPLIED:
                if not exists:
                    add(
                        "UPDATE_OBJECT_MISSING",
                        "BLOCKING",
                        path,
                        f"{change.object_id} does not exist in {change.registry}.",
                        "Use ADD or correct the object ID.",
                    )
                elif change.expected_before_sha256 is None:
                    add(
                        "UPDATE_WITHOUT_PRECONDITION",
                        "BLOCKING",
                        f"{path}.expected_before_sha256",
                        "Updates require the exact hash of the reviewed prior object.",
                        "Record the canonical SHA-256 of the current object.",
                    )
                elif canonical_sha256(registry.get(change.registry, change.object_id)) != change.expected_before_sha256:
                    add(
                        "STALE_UPDATE_PRECONDITION",
                        "BLOCKING",
                        f"{path}.expected_before_sha256",
                        "The live object changed after review.",
                        "Rebase and re-review the proposed update.",
                    )
            if change.operation == "UPDATE" and record.state == PipelineState.APPLIED:
                if not exists or canonical_sha256(registry.get(change.registry, change.object_id)) != canonical_sha256(change.after_object):
                    add(
                        "APPLIED_OBJECT_DRIFT",
                        "BLOCKING",
                        path,
                        f"Applied object {change.registry}/{change.object_id} no longer matches the approved changeset.",
                        "Open a new reviewed UPDATE changeset; never edit applied provenance in place.",
                    )

        if change.operation == "ADD" and change.registry == "lanes":
            novelty = change.novelty_review
            if (
                novelty is None
                or novelty.decision != "DISTINCT"
                or not novelty.boundary_statement.strip()
                or len(novelty.independent_workflow_paths) < 2
            ):
                add(
                    "NEW_LANE_NOVELTY_UNPROVEN",
                    "BLOCKING",
                    f"{path}.novelty_review",
                    "A new lane needs a distinct boundary and at least two independent workflow paths.",
                    "Compare existing lanes, document overlap and show two reusable mechanism/workflow paths.",
                )

        if change.registry == "claims" and change.after_object.get("claim_type") == "FINAL_CLAIM":
            add(
                "DIRECT_REPORT_FINAL_CLAIM",
                "BLOCKING",
                path,
                "A single report record cannot directly create a final claim.",
                "Create intermediate claims and let a registered synthesis policy produce the final claim.",
            )

        if change.registry == "aggregations" and any(
            key in change.after_object for key in {"weights", "numeric_weights", "lane_weights"}
        ):
            add(
                "LLM_NUMERIC_WEIGHT_FORBIDDEN",
                "BLOCKING",
                path,
                "A report extraction record cannot supply numeric aggregation weights.",
                "Register a deterministic weight-estimation rule and estimate weights from training data.",
            )

        reviewed_approval = _has_authorized_review(record, "APPROVE_REVIEWED", change.change_id)
        active_approval = _has_authorized_review(record, "APPROVE_ACTIVE", change.change_id)
        if record.state in {PipelineState.APPROVED, PipelineState.CHANGESET_READY, PipelineState.APPLIED}:
            if change.target_status == "active" and not active_approval:
                add(
                    "ACTIVE_WITHOUT_AUTHORIZED_APPROVAL",
                    "BLOCKING",
                    path,
                    "An active registry object requires an explicit separate-pass Codex or human approval.",
                    "Add an APPROVE_ACTIVE CODEX/HUMAN review scoped to this change.",
                )
            elif change.target_status != "active" and not reviewed_approval:
                add(
                    "CHANGE_WITHOUT_AUTHORIZED_REVIEW",
                    "BLOCKING",
                    path,
                    "A staged registry change requires an explicit separate-pass Codex or human review.",
                    "Add an APPROVE_REVIEWED CODEX/HUMAN review scoped to this change.",
                )

        if change.target_status == "active" and change.registry in active_sensitive_registries:
            if record.reproduction.status != "PASSED":
                add(
                    "ACTIVE_WITHOUT_REPRODUCTION",
                    "BLOCKING",
                    path,
                    "This active object has not passed the reproduction gate.",
                    "Land code, synthetic tests and a real-data smoke test before activation.",
                )
            if not (
                record.reproduction.code_artifact
                and record.reproduction.synthetic_test_ids
                and record.reproduction.real_data_smoke_test_ids
                and record.reproduction.data_snapshot
                and record.reproduction.result_hash
            ):
                add(
                    "REPRODUCTION_EVIDENCE_INCOMPLETE",
                    "BLOCKING",
                    "reproduction",
                    "Reproduction passed status lacks code, tests, snapshot or result hash.",
                    "Attach all deterministic reproduction artifacts.",
                )
            linked_routes = [route for route in record.method_routes if route.method_route_id in change.method_route_ids]
            if change.registry in {"models", "model_specifications", "routes"} and not any(
                evidence.kind.value == "MODEL_SPECIFICATION"
                and evidence.statement_status == "EXPLICIT"
                for evidence in referenced_evidence
            ):
                add(
                    "ACTIVE_METHOD_WITHOUT_EXPLICIT_SPECIFICATION",
                    "BLOCKING",
                    path,
                    "An active method path lacks explicit source specification evidence.",
                    "Keep it reviewed/blocked or add the report pages that explicitly define the method.",
                )
            if any(route.free_data_feasibility != "AVAILABLE" for route in linked_routes):
                add(
                    "ACTIVE_WITHOUT_FREE_DATA",
                    "BLOCKING",
                    path,
                    "An active first-release path must be executable with available free data.",
                    "Keep the object reviewed/blocked or complete the free-data connector.",
                )
            if any(not route.diagnostic_requirements or not route.robustness_requirements for route in linked_routes):
                add(
                    "ACTIVE_METHOD_AUDIT_INCOMPLETE",
                    "BLOCKING",
                    path,
                    "An active method lacks method-specific diagnostics or robustness checks.",
                    "Complete the method audit and encode the checks in the recipe.",
                )

    unresolved_blockers = [item for item in record.blockers if item.severity == "BLOCKING" and not item.resolution]
    if unresolved_blockers:
        add(
            "UNRESOLVED_BLOCKERS",
            "BLOCKING",
            "blockers",
            f"Record has {len(unresolved_blockers)} unresolved blocking issue(s).",
            "Resolve the issues or move the record to BLOCKED.",
        )

    # Determine the highest lifecycle state the evidence can honestly support.
    blocking = any(issue.severity in {"ERROR", "BLOCKING"} for issue in issues)
    if record.state in {PipelineState.INGESTED, PipelineState.EXTRACTED}:
        max_state = record.state
    elif blocking:
        max_state = PipelineState.CANDIDATE
    elif not all(item.reviewer_verified for item in record.evidence):
        max_state = PipelineState.CANDIDATE
    elif record.reproduction.status == "PASSED":
        max_state = PipelineState.APPROVED if record.registry_changes else PipelineState.REPRODUCED
    else:
        max_state = PipelineState.APPROVED if record.registry_changes and all(
            change.registry == "reports" for change in record.registry_changes
        ) else PipelineState.REVIEWED

    can_build = (
        bool(record.registry_changes)
        and record.state in {PipelineState.APPROVED, PipelineState.CHANGESET_READY}
        and not blocking
    )
    active_changes = [change for change in record.registry_changes if change.target_status == "active"]
    can_activate = bool(active_changes) and can_build and all(
        _has_authorized_review(record, "APPROVE_ACTIVE", change.change_id)
        for change in active_changes
    )
    return ReportPolicyAudit(
        record_id=record.record_id,
        report_id=record.report_id,
        current_state=record.state,
        max_permitted_state=max_state,
        issues=issues,
        can_build_changeset=can_build,
        can_activate=can_activate,
    )
