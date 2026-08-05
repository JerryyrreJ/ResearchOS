# 跨角色接口矩阵

| ID | Producer | Consumer | Contract | Sync mode | Owner test |
|---|---|---|---|---|---|
| I-A1 | A | C | `DataObjectRef` | JSON/HTTP | A serialization + C parse |
| I-A2 | A | B | `DataResolveRequest/Response` | HTTP | A endpoint + B adapter |
| I-A3 | A | D | Object Summary / Ontology Graph | HTTP | A fixture + D rendering |
| I-A4 | A | C/D | `ContextPack` | JSON/HTTP | A build + C/D read |
| I-C1 | C | B | `ToolRequest` | HTTP | C request + B validate |
| I-B1 | B | C | `EvidenceBundle` | JSON/HTTP | B output + C compile |
| I-C2 | C | D | `ThesisBuild` | JSON/HTTP | C fixture + D form |
| I-C3 | C | D | `CompileResult` | JSON/HTTP | C output + D console |
| I-C4 | C | D | `JobEvent` | SSE | C stream + D progress |
| I-C5 | C | D | `VersionDiff` | JSON/HTTP | C diff + D view |

## 关键约束

- `DataObjectRef.version_id` 必须固定，不允许消费者自动取最新版本；
- `EvidenceBundle.evidence_type` 决定允许的语言上限；
- `CompileResult.conclusion_state` 只能由 C 产生；
- D 只展示后端状态；
- B 的 Research Graph 可以作为 Artifact 引用，不改变 C 的 Thesis Graph。
