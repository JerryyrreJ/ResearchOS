# MacroTrace CORPUS30 语义逆向结果

## 1. 本批结论

`CORPUS30.20260715` 已完成 30/30 份来源的 Codex 语义逆向与第二遍独立 Codex 复核。批次由 10 份机构宏观报告 PDF、10 个官方方法网页和 10 份基础方法论文 PDF 组成。20 份 PDF 共 1,051 个文件页，另有 10 份带 form-feed 页码映射的网页快照。

治理产物包含：

- 30 份 `ReportReverseRecord`；
- 120 条页码证据；
- 139 个有角色、定义、单位、频率和来源的变量；
- 31 条完整 Method Route；
- 129 个待去重、复现或实现的 Registry candidate object；
- 30 个第一遍 `producer_run_id` 和 30 个不同的第二遍 `review_run_id`；
- 30/30 Schema、页码、引用、状态机和 changeset 审计通过；
- 0 个候选方法被直接激活。

来源字节、逐页正文和审计工作区留在 Git 忽略的本地 `data/report_*` 目录。仓库只保存来源目录、Codex 撰写的语义档案、去原文的结构化记录和执行脚本。原文没有复制进 Registry，也没有在公开 artifact 中保留长引文。

## 2. 逆向深度合同

这一批不使用词频、主题词聚类或自动摘要替代阅读。每份材料至少恢复以下对象：

1. 原作者真正回答的研究问题，以及结论不能越过的边界；
2. 冲击或状态通过什么经济机制传到中间命题和结果；
3. 因变量、自变量、处理、控制、状态、权重等变量角色；
4. estimand、样本、频率、变换、公式、识别与关键假设；
5. 方法专属 diagnostics、robustness、vintage 和样本外要求；
6. 对应的 Lane、Mechanism、Research Node、Factor、Model 与 Aggregation 位置；
7. 与现有 Registry 的重叠、可合并部分和必须保持为候选的部分。

抓取脚本的权限只到“保存原文、最终 URL、抓取时间、字节数和 SHA-256”。它不生成研究理解。第一遍 Codex 阅读生成候选记录；第二遍不同 run identity 的 Codex 阅读核对页码、变量含义、方法边界、局限和变更范围。Python 只负责可重复的合同校验和状态门。

## 3. 三十份来源分别带来了什么

### 3.1 机构宏观报告

| ID | 来源 | 逆向进入的核心研究资产 |
|---|---|---|
| CR01 | Federal Reserve Monetary Policy Report | 双重使命状态评估；通胀组件、劳动力平衡、活动、金融条件和政策立场必须保留为并行证据，叙事判断不冒充因果估计。 |
| CR02 | Federal Reserve Financial Stability Report | 资产估值、非金融借款、金融部门杠杆、融资挤兑风险四域框架，以及冲击如何被资产负债表放大的机制图。 |
| CR03 | Federal Reserve Supervision and Regulation Report | 银行资本、流动性、资产质量、盈利和放贷条件到信用供给与宏观活动的传导节点。 |
| CR04 | BLS Employment Situation | CES 与 CPS 双调查、行业工资、失业、参与率、修订和调查口径差异的正式 reconciliation workflow。 |
| CR05 | IMF United States 2026 Article IV | 基准增长/通胀/财政路径、债务动态和政策情景的条件式综合；风险情景不被伪造为无条件概率。 |
| CR06 | U.S. Treasury FX Report | 经常账户、双边贸易、汇率干预、实际汇率和政策透明度的规则化筛选路径。 |
| CR07 | EIA Annual Energy Outlook 2026 | 产量、消费、发电、燃料结构和价格在长期情景中的物理与结构约束；情景不是统计置信区间。 |
| CR08 | EIA Short-Term Energy Outlook | 供给、需求、库存、贸易和价格的短期物理平衡预测，以及实际/预测边界和月度更新 lineage。 |
| CR09 | New York Fed Household Debt and Credit | 债务余额、拖欠迁移、信用评分、年龄和贷款类型的 cohort/transition 研究节点。 |
| CR10 | Philadelphia Fed Manufacturing Survey | 扩散指数、当前/预期活动、订单、就业和价格指标到区域制造状态与全国活动 bridge 的路径。 |

### 3.2 官方方法网页

| ID | 来源 | 逆向进入的核心研究资产 |
|---|---|---|
| CW01 | SF Fed Monetary Policy and Financial Conditions | 窄窗口政策/CPI surprise、事件研究、后续日 FCI 响应、事件污染和 placebo 合同。 |
| CW02 | NY Fed Trend Wage Inflation | 工人层工资到持久趋势、共同成分、行业成分和噪声的层级 latent-state 分解与不确定区间。 |
| CW03 | NY Fed Outlook-at-Risk | 条件分位数到完整增长密度的展示和校准合同；尾部分位数不得冒充衰退概率。 |
| CW04 | SF Fed Tariffs and Inflation Components | 十六国历史面板、组件通胀、本国效应、控制变量和 horizon-specific local projection。 |
| CW05 | Atlanta Fed GDPNow | ragged-edge DFM、十三个 GDP 子项 bridge/BVAR、release news 和 NIPA 恒等式聚合 DAG。 |
| CW06 | Cleveland Fed Inflation Nowcasting | 日度油价、周度汽油、月度 CPI/PCE 到月度与季度通胀的混频 bridge。 |
| CW07 | NY Fed GSCPI | 运输成本与 PMI 的需求调整因子、标准化、loading 稳定性和全球供应成本冲击节点。 |
| CW08 | Dallas Fed Trimmed Mean PCE | PCE 组件排序、支出权重、非对称截尾、边界 prorating、权重 add-up 和调参稳定性。 |
| CW09 | Chicago Fed NFCI | 105 个金融变量的共同因子、风险/信用/杠杆子指数，以及活动和通胀调整后的 ANFCI。 |
| CW10 | Philadelphia Fed ADS | 六个周/月/季指标的混频状态空间、ragged edge、Kalman 更新、实时 vintage 和 revision tentacle。 |

### 3.3 基础方法论文

| ID | 来源 | 逆向进入的核心研究资产 |
|---|---|---|
| CF01 | Stock–Watson large-panel forecasting | 大面板 PCA/DFM、目标预测回归、factor count、loading 漂移和严格样本外基准。 |
| CF02 | Giannone–Reichlin–Small nowcasting | 不平衡数据集、Kalman nowcast、release news decomposition 和实时信息集重建。 |
| CF03 | Jordà–Taylor local projections | LP estimand、shock 定义、horizon 回归、协方差、多重推断、pre-response 和 VAR 对照。 |
| CF04 | Adrian–Boyarchenko–Giannone vulnerable growth | 金融条件到增长条件分位数、密度拟合、PIT/coverage 和 tail-loss 校准。 |
| CF05 | Bańbura–Giannone–Reichlin large BVAR | 大系统 Minnesota-style shrinkage、先验紧度随维度调整、预测/IRF 和基准比较。 |
| CF06 | Bernanke–Boivin–Eliasz FAVAR | 可观测政策变量与不可观测信息因子共同进入 VAR，解决小 VAR 信息遗漏问题。 |
| CF07 | Clarida–Galí–Gertler monetary-policy framework | 前瞻 IS、New Keynesian Phillips Curve、政策规则和 determinacy 的结构机制，不直接当作实证回归。 |
| CF08 | Galí–Gertler inflation dynamics | real marginal cost 驱动的混合 NKPC、GMM 工具、弱工具与 moment diagnostics。 |
| CF09 | Bernanke–Gertler–Gilchrist financial accelerator | 外部融资溢价、借款人净值、资产价格和投资/产出的资产负债表放大机制。 |
| CF10 | Blanchard–Quah demand/supply SVAR | 长期约束识别需求与供给冲击、累计长期响应、结构 IRF 和识别敏感性。 |

## 4. 去重与冲突结论

本批没有因为文献里出现一个新名称就直接新增 Lane。多数来源扩展的是既有泳道内部的 mechanism、node、factor 或 model recipe：

- CF01、CF02、CW05 和 CW10 共同补强 DFM/nowcast 家族，但分别对应大面板压缩、实时 news、GDP 会计子项和高频活动状态，不能粗暴合并成一个节点；
- CF03 与 CW04 共享 local-projection 计算骨架，但 shock、面板结构、协方差和 transportability 合同不同；
- CF04 与 CW03 属于同一 Outlook-at-Risk 方法族，前者提供估计与校准，后者提供用户解释边界；
- CR02、CR03、CR09、CW09 和 CF09 都涉及金融传导，但监测域、银行信用、家庭 cohort、共同金融因子和结构放大机制是不同 estimand；
- CR07、CR08、CW06 和 CW07 都涉及供给/能源/价格，但长期能源情景、短期物理平衡、通胀 bridge 和全球供应因子不能互相替代；
- CW08 是确定性变换，不是回归模型；CR04 是官方数据 reconciliation，不是因果劳动模型；CR01 是政策证据综合，不是识别出的政策冲击。

因此 changeset 只登记 30 个 reviewed source provenance 和每份来源的 candidate inventory。它没有复制已有 active recipe，也没有用文献权威绕过复现门。

## 5. 当前能激活与不能激活的边界

这一批的 `can_build_changeset=true` 表示“来源记录足够完整，可以安全进入 staged Registry”，不表示候选模型已经可以回答用户问题。

仍需代码、合成 DGP、免费真实数据、vintage 和方法专属诊断后才能激活的重点包括：

- FAVAR、Blanchard–Quah SVAR、NKPC GMM 和结构性货币政策模块；
- GDPNow-style 十三子项 nowcast 和 ADS-style 完整实时状态空间；
- 高频政策 surprise 事件研究；
- 国际关税面板 local projection；
- GSCPI、NFCI/ANFCI 和 Trend Wage Inflation 的完整可复现构建；
- IMF 财政/债务情景与 EIA 能源物理平衡的正式 scenario engine。

含有商业运输数据、调查微观数据或未完全公开监管拆分的来源保持 `PARTIAL`。这些材料仍可定义机制和需要的数据，但不能把图中结果当作本地真实运行。

## 6. 产物位置与状态

- 来源目录：[`report_pipeline/corpus30/source_catalog.json`](../report_pipeline/corpus30/source_catalog.json)
- Codex 精读协议：[`docs/09_reverse_corpus_30_source_catalog.md`](09_reverse_corpus_30_source_catalog.md)
- 三类语义档案：`report_pipeline/corpus30/reverse_*.jsonl`
- 版权安全的结构化记录：`report_pipeline/corpus30/reverse_records/*.json`
- 确定性下载器：[`scripts/fetch_reverse_corpus.py`](../scripts/fetch_reverse_corpus.py)
- 记录构建器：[`scripts/build_corpus30_reverse_records.py`](../scripts/build_corpus30_reverse_records.py)
- 批次合同测试：[`tests/test_corpus30_reverse.py`](../tests/test_corpus30_reverse.py)
- 本地 staged changeset：`data/report_batches/BATCH.CORPUS30.20260715/changesets/CS.BATCH.CORPUS30.20260715.729BDF18BB66`

staged changeset 尚未写入 live `registry/v2`。这是当前交付的有意停止点：先把 30 份阅读结果、diff 和 candidate inventory 冻结，再在模型实现/封装阶段决定哪些对象合并、哪些进入 reproduction backlog，以及哪些 source provenance 一次性应用。
