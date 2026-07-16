# MacroTrace v0.2 技术与研究架构

## 1. 设计目标

v0.2 的核心不是扩大聊天提示词，而是把“任意美国宏观问题”变成一种可验证的编译过程。自然语言具有开放性，但执行面必须封闭：AI 可以选择注册对象，却不能改变公式、变量定义、依赖图、模型代码或数值聚合权重。系统无法覆盖的问题被保留为 unsupported claim，最终 coverage 随之下降。这一约束使较弱模型也只能输出有限枚举和局部参数，不会以错误代码污染研究内核。

## 2. 分层编译器

`backend/app/compiler.py` 实现职责分离的编译链。LLM-0 提取目标、问题形式、as-of、自然语言期限、条件事件和输出要求；LLM-1 在 forecast、nowcast、driver、causal、scenario、asset transmission 等工作流中分类；LLM-2 选择核心、辅助、低优先级和排除泳道；LLM-3 为每条泳道选择节点及依赖；LLM-4 只能从节点 Factor Pool 选择因子；LLM-5 只能从兼容 Model Pool 选择模型；LLM-6 在单个模型的局部上下文选择窗口、滞后、固定效应、协方差等白名单参数；LLM-7 只解释最终结构化证据。

每层输出都记录 provider、model、schema 状态、是否修复、Registry 版本与决策理由。验证失败允许一次结构化修复，第二次失败直接使用 Registry fallback 或删除节点。编译器不会把 LLM 返回的 Python、SQL、公式或额外字段传入执行器。明确期限来源标为 `USER_EXPLICIT`；问题没有期限时使用 Workflow Registry 的默认值，并标为 `POLICY_DEFAULT`。

## 3. Registry 和合同

`registry/v2` 是执行权威，版本均为 0.2.0。Lane 定义经济机制与边界；Workflow 定义问题类型、默认期限、节点 DAG 与 fallback；Node 限定上下游、Factor Pool 与 Model Pool；Factor 保存经济定义、单位、频率、来源、发布时间、变换和 regime 限制；Dataset 保存 API、许可、修订和 vintage 属性；ModelRecipe 固定公式语义、变量白名单、参数空间、诊断套件、失败条件与 Python artifact；ParameterPolicy 约束局部选择；AggregationRecipe 规定同目标预测、潜在状态、可比效应量或异质证据如何合并；Report/Route 保存研报页码及问题到方法的路径；Claim 保存支持、反驳与证伪关系。

`RegistryStore` 在启动时验证所有 ID、版本和跨表引用。参数验证要求键集合精确相等，枚举必须命中，数值必须处在边界内；模型因子和数据依赖也必须兼容。Research Graph 的节点类型固定为 QUESTION、QUERY、CLAIM、LANE、RESEARCH_NODE、FACTOR、DATASET、TRANSFORM、MODEL_RUN、DIAGNOSTIC、EVIDENCE、LANE_SIGNAL、AGGREGATION、FINAL_CLAIM 与 FALSIFIER。

## 4. 数据与执行

`SyncService` 从官方连接器抓取数据，保存原始元数据、标准化观测和 snapshot。当前 active 方法使用 FRED、BLS、EIA、Treasury 和 New York Fed 的真实数据。查询严格截断于任务 as-of date；但只有来源本身提供 vintage 或系统保存过历史快照时，才能声称 point-in-time。没有 vintage 的修订序列会在 provenance 中标注限制，不得用于宣称无前视偏差的历史回测。

研究任务由线程池异步执行，状态包括 QUEUED、PARSING_QUERY、CLASSIFYING_WORKFLOW、ROUTING_LANES、ROUTING_NODES、SELECTING_FACTORS、PLANNING_MODELS、SELECTING_PARAMETERS、VALIDATING、EXECUTING、AGGREGATING_LANES、SYNTHESIZING、COMPLETE、PARTIAL、FAILED 与 CANCELLED。每个状态、节点结果和图快照写入 DuckDB；SSE 以单调 sequence 推送，客户端用 Last-Event-ID 恢复。终态只由 JobManager 在 result、graph 与 trace 同一轮持久化之后发布，避免前端先看到 COMPLETE 再得到 409。

## 5. 模型与诊断

Dynamic Factor 配方标准化月度指标，以 PCA 提取注册数量的因子并使用 bridge 回归预测目标；输出载荷、解释比例、样本外 RMSE、残差 Ljung–Box 与 ragged-edge 状态。VAR 使用固定变量池、固定滞后候选和注册 Cholesky 顺序，输出稳定根、Portmanteau、正态性、滚动 OOS、IRF 与 FEVD。Local Projection 通过一组 horizon-specific 回归生成事件时间响应和 HAC 区间，输出前响应联合检查和 placebo；当前数据语境不足以识别外生冲击，所以证据类型是动态关联。Growth-at-Risk 用 NFCI 条件化未来实际 GDP 增长分位数，输出 pinball loss、crossing 和扇形图。州面板 FE 只作为 fixture，明确排除在一般综合之外。

诊断不是通用打勾清单。每个 ModelRecipe 声明适用检查、统计量、p 值、阈值、判断和对结论可信度的影响。残差正态性可展示，但不会被错误称为大样本 OLS 无偏的必要条件。失败条件触发时节点保留在图中并标红，coverage 下降，系统不把失败模型悄悄替换成描述统计。

## 6. 聚合与不确定性

相同 target/horizon 的预测可使用训练期 inverse-loss 权重，施加非负、和为一约束，并以 50% 向等权收缩；同时报告等权结果和敏感性。异质证据先映射到中间 claim，再按注册的 ordinal quality tier 综合，保留方向冲突。只有每个 contributing model 都达到 HIGH 时，总体 confidence 才可能为 HIGH；完整 coverage 不等于高可信度。不同 estimand 禁止 inverse-variance 硬合并，无法校准时只给条件结论和 LOW/MEDIUM/HIGH 离散置信度，不输出 LLM 生成的数值概率。

## 7. 白盒界面

前端主画布是可缩放、平移、折叠和筛选的泳道图。默认显示问题、泳道、主要节点、模型、聚合和最终命题，把 Factor、Dataset、Transform 与 Diagnostic 折叠起来。任务执行时节点随 SSE 状态点亮；刷新后从 localStorage 中的 job id 恢复。

模型详情抽屉包含 Overview、Specification、Data & Variables、Results、Diagnostics、Robustness 与 Provenance。公式由 KaTeX 渲染；学术三线表显示系数、括号内标准误、精确 p、CI、星号、N、R² 类型、检验统计、固定效应、聚类、样本期和版本。artifact store 同时生成 JSON、CSV、HTML、LaTeX 和图表 JSON，并记录 SHA-256。图表与方法一致：DFM 显示载荷/预测，VAR 显示 IRF，LP 显示 event-study，GaR 显示扇形图；不存在的方法不显示装饰性伪图表。

## 8. 已知边界

当前 Registry 只覆盖增长/衰退、通胀、利率传导和面板 fixture 等首轮路径。财政、贸易、住房/消费和更细资产传导已有 Lane/Factor 基础，但尚没有足够 active Workflow 或免费数据，因此开放问题可能是 PARTIAL/UNSUPPORTED。DID、RDD、BVAR、random-effects meta-analysis、MCS、DMA/BPS 和真正实时 vintage 尚未达到 active 条件。这些是下一轮研究工程任务，不应在本轮本地原型中被描述为已经完成。
