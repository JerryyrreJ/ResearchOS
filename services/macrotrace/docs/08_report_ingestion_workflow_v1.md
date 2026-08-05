# MacroTrace 研报规范化逆向与 Registry 治理工作流 v1

## 1. 目的与系统边界

这条工作流解决的不是“把一篇 PDF 总结成几段话”，而是把外部宏观研报安全地转化为 MacroTrace 可以复用、审计和执行的研究资产。标准输出必须能表达：原始问题、经济机制、泳道、研究节点、因子/变量、数据及变换、模型与识别、诊断与稳健性、聚合角色、页码证据、免费数据可行性、复现状态和 Registry 变更。

工作流属于内部构建平面，不属于公开网站的运行平面。原始 PDF、逐页文本、Codex 第一遍逆向草稿、第二遍独立 Codex 复核记录和未激活候选对象只保存在本地且被 Git 忽略的 batch workspace。公开产品只消费审核后、版本化、只读的 Registry；公开 API 不提供上传研报、修改 Registry 或执行任意代码的入口。

任何单次抽取或普通外部模型都没有直接修改 live Registry 的权限。Codex 是本工作流的研究员与审核主体：第一遍逐页做候选逆向，第二遍以不同 `review_run_id` 重新核对证据、经济边界、方法和冲突；Python 负责指纹、结构校验、引用校验、状态机、变更包、复现检查与事务。用户仍是最终授权人，但日常几百/几千篇逆向不要求额外人工逐篇复核。普通 `LLM`、词频程序或自动摘要器不能取得 `CODEX` 审核权限。

## 2. 标准对象链

每篇报告至少尝试复原以下链路：

```text
Source report
  → Research question / source claim
  → Lane
  → Economic mechanism
  → Research node
  → Variables / factors
  → Dataset / release / vintage / transform
  → Estimand / model / identification / sample
  → Diagnostics / robustness / failure conditions
  → Evidence object / lane signal
  → Aggregation role / intermediate claim
  → Registry change proposal
```

链路允许出现 `not stated`、`UNKNOWN`、`PARTIAL` 或 `UNAVAILABLE`，但不允许用推测填空。只展示描述统计或一张图、缺少变量与方法定义的内容，可以进入证据节点或 `evidence_only` 报告状态，却不能冒充可执行模型。研报中的最终观点也不能直接变成 MacroTrace 的 `FINAL_CLAIM`；它只能支持/反驳中间命题，再由注册的 Synthesis Policy 综合。

## 3. 十二步状态化流程

### Step 0 — Intake 与来源指纹

输入报告首先计算 SHA-256、字节大小、媒体类型和稳定 source ID。原文件不会复制进代码仓库。完全相同的 SHA-256 会被标记为 `DUPLICATE` 并停止后续抽取。标题相同但哈希不同不自动视为重复，因为可能是修订版、不同 vintage 或 OCR 版本。

输出：`manifest.json`、每篇报告的 `INGESTED` record、source pointer 和 fingerprint。

### Step 1 — 私有逐页文本地图

PDF 按文件页码逐页抽取，UTF-8 文本按 form-feed 分页；每页保存页号、文本哈希、字符数和文本。逐页文本只存在 `data/report_batches/<batch>/extracted/`，不进入 Registry、日志、截图或公开 artifact。抽取成功后状态变为 `EXTRACTED`。

页面证据默认使用 `PDF_FILE_PAGE`。若研报正文印刷页码与 PDF 页码不同，必须显式使用 `PRINTED_PAGE` 或记录 locator，不能混用。

### Step 2 — 问题、命题与机制抽取

先恢复报告真正回答的问题，而不是先看 MacroTrace 缺什么再反向改写报告。每个问题记录任务类型、自然语言 horizon、as-of、目标变量和页码证据。随后抽取机制、主张、限制和适用 regime，并把陈述标为：

- `EXPLICIT`：页面直接陈述或展示；
- `INFERRED`：由多个显式元素做出的保守重建；
- `NOT_STATED`：报告没有提供，只用于记录缺口。

长期保存以 paraphrase 为主。短引文仅用于定位并被 Schema 限制为 240 字符，避免把受版权保护的原文变成产品资产。

### Step 3 — 路径级逆向

每个 material method 必须形成独立 `MethodRoute`，而不是只记录“文章用了 VAR”或“文章看了就业”。路径要写清 lane、mechanism、node、上下游、变量角色、estimand、公式、样本、识别、诊断、稳健性、聚合角色和 evidence IDs。一个报告可以包含多条路径，一条路径也可以只作为背景或证据节点。

预测方法必须说明时间顺序、forecast origin、训练/测试切分和基准；因果方法必须说明 treatment、counterfactual、estimand 与识别假设；结构模型必须说明方程、校准/估计对象和闭合条件。缺少这些信息时，状态保持 candidate、blocked 或 evidence_only。

### Step 4 — 变量与数据字典

每个变量记录经济定义、实证角色、单位、频率、提供者、表/系列、发布时间、vintage 规则、变换和滞后，并尝试映射到现有 Factor Registry。相同名字不等于相同变量：headline CPI 与 core CPI、level 与 growth、revised GDP 与 real-time vintage 都必须分开。

数据可行性只允许四种结论：`AVAILABLE`、`PARTIAL`、`UNAVAILABLE`、`UNKNOWN`。第一版 active 路径必须能用免费、合法、实际可取得的数据执行。图表截图、付费终端名称或文章中的回归结果不是可执行数据源。

### Step 5 — 方法适配与学术完整性审核

审核不以复杂度为目标，而以问题—estimand—方法一致性为目标。每类方法按自己的完整性合同检查：

- 时间序列/nowcast：频率对齐、ragged edge、平稳性/稳定性、滚动样本外误差、基准和泄漏；
- Panel FE：面板单位、组内变异、固定效应、聚类层级、序列/截面相关和稳健协方差；
- DID/Event Study：处理定义、事件时间、对照组、pre-trend、placebo 和识别威胁；
- VAR/BVAR：变量顺序/识别、稳定根、IRF、FEVD、残差与样本外表现；
- Local Projection：冲击定义、HAC/聚类、前响应、horizon、多重推断与 placebo；
- Quantile/GaR：目标分位数、pinball loss、quantile crossing、时间切分与校准；
- ML：严格时间切分、泄漏检查、调参嵌套、校准、稳定性和可解释性。

“残差是否正态”可以展示，但不会被错误写成大样本 OLS 无偏的必要条件。方法名被提及、图表看起来像某模型，或者文章给出显著星号，都不足以激活配方。

### Step 6 — Registry 匹配、去重与冲突审核

匹配依次处理四层冲突：

1. 来源级：同一 SHA-256 直接重复；
2. 报告级：标题、机构、日期和版本接近但文件不同；
3. ID 级：拟议对象 ID 已存在；
4. 语义级：经济边界、变量定义或 estimand 实际相同/冲突。

完全相同的经济对象优先复用；已有对象发生有依据的扩展时使用带 `expected_before_sha256` 的 UPDATE；语义冲突不自动合并，必须由独立 Codex review pass 决定“复用、更新、并存、blocked 或 reject”。UPDATE 的 prior-object 哈希在 apply 前变化时，changeset 会被视为 stale，必须 rebase 并重新审核。

### Step 7 — 候选对象审核

Codex extraction pass 的输出只能停留在 candidate。页面证据的 `reviewer_verified` 只能由第二遍 Codex review pass（或用户本人）核对后改变；普通 LLM/自动程序不能伪装为 `CODEX` 或 `HUMAN` reviewer。进入 `REVIEWED` 需要每个变更都有 scoped `APPROVE_REVIEWED`，且 Codex 的 `review_run_id` 必须与 extraction 的 `producer_run_id` 不同。

新增对象的最低合同：

| 对象 | 必须证明的内容 |
|---|---|
| Report | 文件指纹、页码基础、机构/版本、用途与独立 Codex 证据审核 |
| Lane | 与所有已有泳道的边界差异、经济含义、至少两条独立可复用 workflow path |
| Mechanism | 传导逻辑、关键假设、输入输出、适用/失效 regime 和页码证据 |
| Research Node | 可复用子问题、上游/下游、factor pool、model pool 与输出命题 |
| Factor | 定义、单位、频率、来源、发布/vintage、变换、滞后和 regime |
| Dataset | 官方/合法来源、许可、connector、表/系列、修订和快照规则 |
| ModelRecipe / Specification | estimand、公式、变量角色、样本、参数白名单、诊断、失败条件、代码 artifact 和测试 |
| Route | 问题模式、lane/node/factor/model 路径、fallback、报告页码与 coverage |
| Aggregation | 可合并的证据对象、数学方法、训练窗/损失/约束、基准与稳定性；禁止 AI 数值权重 |
| Claim / Evidence Mapping | 中间命题、证据方向、支持/反驳、可证伪条件和 synthesis 关系 |

新增 lane 不允许因为一篇报告出现一个新图表就建立。它必须在经济机制上有清晰独立边界，并至少支持两条独立 workflow path；否则放到已有 lane 的 mechanism/node，或者保持 `UNRESOLVED`。

### Step 8 — 复现与激活审核

`reviewed` 表示研究路径被正确理解，不表示系统已经能执行。任何运行平面会使用的 `active` 对象还必须满足：

1. 注册代码 artifact 已存在，不是临时生成代码；
2. 已知 DGP 的 synthetic test 通过；
3. 免费真实数据 smoke test 通过；
4. 数据快照和结果 SHA-256 已记录；
5. 方法专属 diagnostics 和 robustness 已编码；
6. 参数、因子、数据和依赖通过 RegistryStore；
7. 独立 Codex review pass（或用户）`APPROVE_ACTIVE` 明确覆盖该 change；
8. 没有未解决 blocking issue。

报告本身可以在无模型复现时成为 reviewed/evidence-only source；但 lane、node、factor、route、model 或 aggregation 进入 active 会触发复现门。DID、RDD、深度学习或强化学习不因报告提到方法名而自动激活。

### Step 9 — 生成 staged changeset

通过审核的 batch 生成完整 staged Registry 副本、operation manifest、所有 registry 文件 SHA-256、content hash 和 `diff.md`。Builder 在 staged 目录运行完整 `RegistryStore` 引用校验。这个步骤不会修改 live Registry。多个报告修改同一对象时 builder 会拒绝，要求先合并为一个经过重新审核的 change。

### Step 10 — Codex/用户批准与事务式 apply

应用需要单独的 `ApplyApproval`：`changeset_id`、精确 `content_hash`、`CODEX` 或 `HUMAN` reviewer、时间和理由。任何哈希不一致都会拒绝。Codex 批准也必须来自 changeset 生成后的独立 review pass。apply 前重新校验 staged 文件哈希，随后备份全部 live Registry、逐文件原子替换并运行 RegistryStore；如任一步失败，系统自动恢复备份并再次验证。成功后生成 `application_receipt.json`，record 变为 `APPLIED`。

### Step 11 — 上线前验证与退役

应用 changeset 后还要运行全量统计测试、真实问题 smoke test、前端 Graph 回溯测试和 Factory substance audit。新增对象必须能从最终 claim 回到 report/page。后续发现定义错误时不能改写旧 record 或 receipt，而要创建新的 UPDATE changeset；旧对象可以被 deprecated/blocked，但 lineage 不删除。

## 4. 状态机

```text
INGESTED → EXTRACTED → CANDIDATE → REVIEWED
                                      ├→ APPROVED → CHANGESET_READY → APPLIED
                                      └→ REPRODUCTION_PENDING → REPRODUCED → APPROVED

INGESTED / EXTRACTED / CANDIDATE / REVIEWED / REPRODUCTION_PENDING / REPRODUCED
  └→ BLOCKED / EVIDENCE_ONLY / DUPLICATE / REJECTED（按允许的分支）
```

终态不会被原地重新打开。需要修正时创建新版本 record 或新 changeset。状态只能通过 CLI 追加 transition，手工只改 `state` 而不写 history 会被拒绝。

## 5. Evidence 等级

- E0 — Mention：报告只提及概念/方法，不能形成 Registry change。
- E1 — Page-grounded：有可核对页码和准确 paraphrase，可形成 evidence-only/candidate。
- E2 — Specification-complete：问题、机制、变量、estimand、样本、方法、诊断和局限完整，可 reviewed。
- E3 — Reproduced：代码、合成 DGP、真实数据、快照和结果哈希通过。
- E4 — Active：独立 Codex/用户审核、Registry 引用、全量测试、changeset 和 apply receipt 均通过。

一个对象的等级取决于它自己的证据链，不能因为报告整体质量高而继承。对于同一报告，某条 VAR 路径可以是 E3，而只在讨论部分出现的 DID 可以仍为 E0。

## 6. 批量规模化规则

每篇报告一个 record，每个批次一个 manifest；SHA-256 提供幂等性，record_id/report_id 提供 lineage。几百或几千篇报告可以分批抽取和独立审核，但 Registry 写入必须串行经过 changeset，从而避免并发覆盖。高吞吐来自并行的只读抽取和候选生成，而不是并行修改 Registry。

候选池可以很大，active Registry 必须保持策展式质量。未复现的方法仍然有价值：它可以进入 candidate/reviewed/blocked，形成未来数据连接器或模型开发 backlog；不得为了“吸收了很多研报”降低 active 门槛。

每批结束输出四张表：来源与重复表、路径覆盖表、候选对象/冲突表、激活与阻塞表。统计“处理了多少篇”不能替代“新增了多少可复用路径、多少已复现、哪些仍 blocked”。

## 7. 本地操作

```powershell
Set-Location <path-to-your-macrotrace-clone>

# 1. 建批次并记录来源指纹（原文件不会复制进仓库）
.\.venv\Scripts\python.exe scripts\report_pipeline.py init `
  --batch-id BATCH.20260715.001 `
  <path-to-report-a.pdf> <path-to-report-b.pdf>

# 2. 在 gitignored workspace 生成逐页文本地图
.\.venv\Scripts\python.exe scripts\report_pipeline.py extract `
  data\report_batches\BATCH.20260715.001

# 3. Codex/LLM 按 prompt contract 填充 records；仍保持 EXTRACTED
# 4. 通过政策校验后推进到 CANDIDATE
.\.venv\Scripts\python.exe scripts\report_pipeline.py transition `
  data\report_batches\BATCH.20260715.001\records\<report-id>.json CANDIDATE `
  --actor codex --reason "Structured route contract completed"

# 5. 第二遍 Codex review 核对页面、方法和冲突，写入 CODEX review 后再推进状态
# 6. 批次审计
.\.venv\Scripts\python.exe scripts\report_pipeline.py audit `
  data\report_batches\BATCH.20260715.001 --write

# 7. 只生成、不应用 Registry changeset
.\.venv\Scripts\python.exe scripts\report_pipeline.py build-changeset `
  data\report_batches\BATCH.20260715.001

# 8. 独立 Codex/用户查看 diff、staged Registry 和 content hash，创建 approval 后才可应用
.\.venv\Scripts\python.exe scripts\report_pipeline.py apply `
  data\report_batches\BATCH.20260715.001\changesets\<changeset-id> `
  --approval <private-approval-path>\<changeset-id>.approval.json
```

机器合同位于 `schemas/report_ingestion.schema.json`；LLM 合同位于 `report_pipeline/prompts/reverse_extraction_v1.md`；候选 record 与 apply approval 的可复制结构位于 `report_pipeline/examples/`。

## 8. 与产品封装的接口

部署时只把 canonical `registry/v2`、模型代码、测试过的数据同步/快照逻辑和公共 API 放入后端镜像。`data/report_batches`、原始 PDF、逐页文本、未审核 records、approval 文件和 rollback 备份不能进入 Docker build context、Cloud Storage 公共桶、Vercel 前端或 LLM trace。

未来使用 Cloud Run + 对象存储时，生产镜像仍是无状态消费者；Registry changeset 在受控 CI/build job 中产生和验证，而不是由公开 Cloud Run 请求写入。这样“持续逆向研报扩充能力”和“公开网站按请求缩容到零”可以同时成立，且不会把知识构建权限暴露给访问者。
