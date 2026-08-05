from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .models import EvidenceBundle, ThesisBuild
from .rules import evaluate, issue

EVIDENCE_RANK = {"DESCRIPTIVE": 0, "PREDICTIVE": 1, "ASSOCIATIONAL": 2,
                 "DYNAMIC_ASSOCIATION": 3, "STRUCTURAL_PROXY": 4, "CAUSAL_IDENTIFIED": 5}
CLAIM_REQUIREMENT = {"DESCRIPTIVE": 0, "PREDICTIVE": 1, "ASSOCIATIONAL": 2, "STRUCTURAL_PROXY": 4, "CAUSAL": 5}


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


class ThesisCompiler:
    def compile(self, thesis: ThesisBuild, evidence: EvidenceBundle | None = None, parent_build_id: str | None = None) -> dict[str, Any]:
        issues = evaluate(thesis, has_evidence=evidence is not None)
        evidence_refs: list[str] = []
        allowed = "DESCRIPTIVE"
        requested = thesis.language_level
        compiled_claim: str | None = None
        conclusion = "COMPILE_FAILED" if any(i.blocking for i in issues) else "EVIDENCE_INSUFFICIENT"

        if evidence:
            evidence_refs.append(evidence.bundle_id)
            allowed = evidence.evidence_type
            required_rank = CLAIM_REQUIREMENT[requested]
            allowed_rank = EVIDENCE_RANK[allowed]
            if allowed_rank < required_rank:
                issues.append(issue("CLAIM_LANG001", f"{allowed} 证据不能支持 {requested} 措辞。", thesis,
                                    actions=["将结论降级到证据允许的语言层级。", "提交更高识别等级的预注册证据。" ]))
                compiled_claim = f"现有 {allowed} 证据仅支持关联性解读，不能支持原论点中的因果措辞。"
            else:
                compiled_claim = evidence.engine_claim or thesis.normalized_claim

            triggered = any(str(f.get("status", "")).upper() in {"TRIGGERED", "FAIL"} for f in evidence.falsifiers)
            blocking_diag = any(bool(d.get("blocking")) and str(d.get("status", "")).upper() in {"FAIL", "FAILED"} for d in evidence.diagnostics)
            weakening = any(str(d.get("status", "")).upper() in {"FAIL", "FAILED", "WARNING"} for d in evidence.diagnostics)
            support = evidence.status == "COMPLETE" and evidence.coverage == "FULL"
            if blocking_diag:
                issues.append(issue("DIAG001", "阻断诊断失败，当前证据不可用于完成结论。", thesis,
                                    actions=["修复诊断失败或提交新的已注册模型运行。" ]))
                conclusion = "EVIDENCE_INSUFFICIENT"
            elif evidence.status != "COMPLETE" or evidence.coverage != "FULL": conclusion = "EVIDENCE_INSUFFICIENT"
            elif triggered and support: conclusion = "EVIDENCE_CONFLICT"
            elif triggered or weakening: conclusion = "WEAKENED"
            elif support: conclusion = "SUPPORTED"

        # Evidence-phase language/diagnostic failures have their own formal states;
        # only input/schema rules force COMPILE_FAILED here.
        blocking_non_language = any(i.blocking and i.code not in {"CLAIM_LANG001", "DIAG001"} for i in issues)
        if blocking_non_language:
            conclusion = "COMPILE_FAILED"
        build_status = "FAILED" if conclusion == "COMPILE_FAILED" else "SUCCESS"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        result: dict[str, Any] = {
            "contract_version": thesis.contract_version,
            "build_id": f"BUILD_{uuid4().hex[:12].upper()}", "thesis_id": thesis.thesis_id,
            "version_id": thesis.version_id, "parent_build_id": parent_build_id,
            "build_status": build_status, "conclusion_state": conclusion,
            "original_claim": thesis.raw_claim, "compiled_claim": compiled_claim,
            "issues": [i.model_dump() for i in issues],
            "validation_plan": self.validation_plan(thesis, issues),
            "evidence_bundle_refs": evidence_refs,
            "language_policy": {"requested_level": requested, "allowed_level": allowed,
                                "reason": "证据语言上限由当前最高等级 EvidenceBundle 决定。"},
            "affected_node_ids": [thesis.thesis_id, *evidence_refs],
            "reused_node_ids": [r.get("object_id") for r in thesis.input_object_refs if r.get("object_id")],
            "created_at": now, "result_hash": "", "metadata": {"compiler_version": "0.1.0"},
        }
        result["result_hash"] = _hash({k: v for k, v in result.items() if k != "result_hash"})
        return result

    @staticmethod
    def validation_plan(thesis: ThesisBuild, issues: list[Any]) -> list[dict[str, Any]]:
        issue_codes = {i.code for i in issues}
        return [
            {"step_id": "STEP_DEFINE", "label": "冻结关键概念和时间窗口", "status": "BLOCKED" if {"DEF001", "HORIZON001"} & issue_codes else "COMPLETE", "tool_request_id": None},
            {"step_id": "STEP_DATA", "label": "绑定版本化数据与变量", "status": "BLOCKED" if "VAR001" in issue_codes else "COMPLETE", "tool_request_id": None},
            {"step_id": "STEP_EMPIRICAL", "label": "执行注册的 MacroTrace 验证", "status": "PENDING", "tool_request_id": None},
            {"step_id": "STEP_RECOMPILE", "label": "摄取 EvidenceBundle 并重新编译", "status": "PENDING", "tool_request_id": None},
        ]

    @staticmethod
    def tool_request(thesis: ThesisBuild) -> dict[str, Any]:
        causal = thesis.language_level == "CAUSAL"
        return {"contract_version": thesis.contract_version, "request_id": f"TOOL_REQ_{uuid4().hex[:12].upper()}",
                "tool": "MACROTRACE", "thesis_id": thesis.thesis_id, "question": thesis.normalized_claim,
                "as_of_date": thesis.as_of_date, "requested_evidence_type": "CAUSAL_IDENTIFIED" if causal else "ASSOCIATIONAL",
                "workflow_hint": "THESIS_VALIDATION", "input_object_refs": thesis.input_object_refs,
                "falsifier_requirements": thesis.falsifier_requirements, "timeout_seconds": 180,
                "display_mode": "ACADEMIC", "metadata": {"generated_by": "thesis-compiler"}}
