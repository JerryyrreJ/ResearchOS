# RACI 与跨角色握手

## 1. RACI

| 事项 | A | B | C | D |
|---|---|---|---|---|
| Object identity and version | A/R | C | C | I |
| Canonicalization | A/R | I | I | I |
| Ontology relations | A/R | I | C | I |
| Context Pack | A/R | C | C | I |
| Data Resolve | A/R | C | I | I |
| MacroTrace upstream | I | A/R | C | I |
| Model and diagnostic semantics | I | A/R | C | I |
| EvidenceBundle | C | A/R | C/R | I |
| Thesis rules | I | C | A/R | I |
| Final conclusion state | I | C | A/R | I |
| Contracts process | C | C | A/R | C |
| UI and deployment | I | C | C | A/R |
| E2E release | C | C | C | A/R |

A = Accountable，R = Responsible，C = Consulted，I = Informed。

## 2. A 到 B：Data Resolve 握手

A 提供：

- DataResolve Endpoint；
- DataObjectRef Fixture；
- Schema、权限和固定 version_id；
- 至少一个成功和两个失败用例。

B 验收：

- 只消费明确版本；
- 内容哈希一致；
- 缺字段和权限错误可映射；
- 不读取 A 数据库。

## 3. C 到 B：ToolRequest 握手

C 提供有效、Unsupported 和 Timeout Fixture。B 验证合同并返回异步任务 ID 或 EvidenceBundle。

## 4. B 到 C：EvidenceBundle 握手

B 提供：

- COMPLETE Fixture；
- PARTIAL Fixture；
- FAILED Fixture；
- evidence_type 低于请求等级的 Fixture；
- 阻断诊断 Fixture。

C 验收语言政策和结论状态。

## 5. C 到 D：UI 握手

C 提供 OpenAPI、CompileResult、JobEvent 和 VersionDiff Fixtures。D 对未知状态必须 fail visibly。

## 6. A 到 D：Ontology UI 握手

A 提供 Object Summary、Relation、Conflict 和 Context Pack Fixtures。D 只负责布局和交互。

## 7. 合并门

任一握手完成需要：

1. Producer Test；
2. Consumer Test；
3. Fixture Snapshot；
4. 错误路径；
5. Contract Hash；
6. 两方在 PR 中确认。
