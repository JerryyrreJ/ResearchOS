from __future__ import annotations

from .models import CompileIssue, ThesisBuild


def issue(code: str, message: str, thesis: ThesisBuild, *, blocking: bool = True, severity: str = "ERROR", actions: list[str] | None = None) -> CompileIssue:
    return CompileIssue(code=code, severity=severity, blocking=blocking, message=message,
                        related_refs=[thesis.thesis_id], suggested_actions=actions or [])


def evaluate(thesis: ThesisBuild, *, has_evidence: bool = False) -> list[CompileIssue]:
    issues: list[CompileIssue] = []
    missing_defs = [d.term for d in thesis.definitions if not d.definition or d.status in {"MISSING", "AMBIGUOUS"}]
    if missing_defs:
        issues.append(issue("DEF001", f"关键术语尚未冻结定义：{', '.join(missing_defs)}。", thesis,
                            actions=["补充可操作定义、单位与来源。" ]))
    horizon = str(thesis.scope.get("horizon_text") or "")
    if not horizon or any(x in horizon for x in ("尚未定义", "持续", "长期", "短期")):
        issues.append(issue("HORIZON001", "预测/影响期限不可计算。", thesis,
                            actions=["提供明确起止日期或可计算窗口。" ]))
    late_refs = [r.get("object_id", "UNKNOWN") for r in thesis.input_object_refs
                 if r.get("as_of_date") and r["as_of_date"] > thesis.as_of_date]
    if late_refs:
        issues.append(issue("TIME001", f"输入对象晚于 as-of date：{', '.join(late_refs)}。", thesis))
    if not thesis.input_object_refs:
        issues.append(issue("VAR001", "没有绑定输入数据对象。", thesis,
                            actions=["从 Research Ontology 选择带版本的数据对象。" ]))
    elif not any((r.get("data_schema") or {}).get("value_fields") for r in thesis.input_object_refs):
        issues.append(issue("VAR001", "输入对象没有可验证的变量字段。", thesis))
    else:
        fields = {f for r in thesis.input_object_refs for f in (r.get("data_schema") or {}).get("value_fields", [])}
        controls = thesis.metadata.get("competition_controls", [])
        if len(fields) < 2 and not controls:
            issues.append(issue("VAR001", "缺少竞争性解释或控制变量。", thesis,
                                actions=["绑定至少一个竞争机制变量并冻结版本。" ]))
    if not thesis.falsifier_requirements or not thesis.metadata.get("falsifiers_registered", False):
        issues.append(issue("FALS001", "证伪条件尚未完成预注册。", thesis,
                            actions=["冻结判定方向、阈值、窗口和对应输入。" ]))
    if not thesis.required_evidence_types:
        issues.append(issue("EVIDENCE001", "没有声明所需证据类型。", thesis))
    if thesis.language_level == "CAUSAL" and ("CAUSAL_IDENTIFIED" not in thesis.required_evidence_types or not has_evidence):
        issues.append(issue("CLAIM_LANG001", "因果措辞尚未获得 CAUSAL_IDENTIFIED 证据。", thesis,
                            actions=["降级为关联措辞，或注册因果识别设计。" ]))
    if not any((r.get("access_scope") for r in thesis.input_object_refs)):
        issues.append(issue("PERM001", "输入对象缺少访问范围。", thesis))
    route = thesis.metadata.get("tool_route_status")
    if route == "UNSUPPORTED":
        issues.append(issue("TOOL001", "所需注册工具路线不存在。", thesis,
                            actions=["选择已注册路线或提交 Registry 审核。" ]))
    elif route not in {"READY", "OFFLINE_REPLAY"}:
        issues.append(issue("TOOL001", "注册工具路线尚未确认。", thesis,
                            blocking=False, severity="WARNING", actions=["确认 MacroTrace route 与 registry version。" ]))
    if not thesis.normalized_claim.strip():
        issues.append(issue("DIAG001", "规范化论点为空。", thesis))
    return issues
