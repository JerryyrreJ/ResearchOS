# 首批 11 份研报的路径级逆向与激活边界

## 方法

本文件把早期的主题摘要进一步转换为可执行 Registry 证据。每条记录要求回答：原始问题是什么、机制假设是什么、路径经过哪些泳道/节点/因子、使用什么模型或图表、页码在哪里、对美国问题是否适用、免费数据能否复现，以及为什么是 active、reviewed、evidence-only 或 blocked。页码是定位线索，不代表原文授权 MacroTrace 复制整张表；实现只提取方法结构并重新用官方数据计算。

状态具有严格含义：`candidate` 只是第一遍 Codex 发现；`reviewed` 表示第二遍独立 Codex 已完成结构化语义核对但尚未进入自动执行；`active` 表示变量、数据、配方、诊断、复现和测试均已落地；`blocked` 表示缺少识别、免费数据或美国适用性；`evidence_only` 表示只能支持叙事或实时背景。任何研报结论都不能直接成为最终 claim，必须经过本地数据运行。

## R01 World Bank：Mainstreaming Nature into World Bank Macroeconomic Models

原始问题是自然资本、生态系统服务与宏观产出如何进入国家模型。机制路径从自然冲击进入生产率、部门投入产出、财政和长期增长，适合建立 `NATURE/CLIMATE → PRODUCTIVITY → ACTIVITY/FISCAL` 的未来泳道。报告提供结构模型思路而不是可直接移植到美国月度 nowcast 的统一估计式；关键因子包括土地、水资源、生态服务、部门产出和资本存量，通常需要空间或部门数据库。当前免费美国高频数据与模型校准不足，因此状态为 `reviewed/blocked`。它不会被 LLM-2 误路由到现有增长模型，也不会用通用 PCA 伪装成自然资本结构模型。

## R02 World Bank：Climate Change Impacts and Adaptation Options

该材料研究物理气候冲击、适应投资与宏观损失的情景差异，路径包含灾害暴露、资本损毁、生产率、迁移、财政支出和长期 GDP。它适合 Scenario 与结构化 counterfactual，而不适合用一条历史相关回归回答短期因果问题。需要的因子包括温度/降水异常、灾害暴露、适应资本、行业损失和财政成本；识别与参数高度依赖区域模型。当前文本来源被登记，但美国免费数据映射、情景校准和稳健性尚未完成，因此为 `reviewed/blocked`。该报告支持未来气候泳道的边界设计，不支持本轮激活 RDD、DID 或深度学习。

## R03 World Bank：Commodity Markets Outlook, October 2025

第 9–16 页围绕商品价格前景、供需冲击和宏观传导构建预测叙事，提供 `COMMODITY_ENERGY → INFLATION → MONETARY` 路径。逆向得到 WTI/能源价格、供给变化、需求状态、美元和价格传导等因子，以及时间序列预测、情景区间和贡献分解等图表合同。本轮使用 EIA WTI、BLS CPI/Core CPI 和 FRED 条件变量实现 `N.ENERGY.SHOCK → N.INFLATION.ENERGY_PASS`；Local Projection 用事件时间响应、HAC 区间、前响应和 placebo 展示动态关联。由于没有外生供给工具变量，不能把响应解释为油价的严格因果效应。报告整体为 `reviewed`，其中能源通胀路径进入 active Route，结构性商品均衡和全球供需情景仍未复现。

## R04 World Bank：Global Economic Prospects, June 2025

该报告的全球增长预测使用多指标、跨经济体、政策与贸易假设形成基线和风险情景。可迁移的研究结构是 `ACTIVITY + TRADE + FINANCIAL CONDITIONS → GROWTH FORECAST`，并强调历史回测和预测分歧。v0.2 从中审核 VAR/多变量系统的适用语境，并结合免费美国月度数据建立注册 VAR：CPI、工业生产、失业率、收益率或 NFCI 的变量顺序和滞后由 Registry 锁定，输出稳定性、IRF、FEVD 与 OOS RMSE。报告的跨国面板和全球贸易权重没有在本轮复现，所以状态为 `reviewed` 而非整份 active；只有经过本地 DGP 测试和真实数据 smoke test 的 VAR 配方是 active。

## R05 World Bank：Global Economic Prospects, January 2026

该报告强调增长下行风险、冲击传播和不同 horizon 的动态响应，可逆向为 `SHOCK → ACTIVITY/INFLATION RESPONSE → SCENARIO`。本轮从其动态响应语境审核 Local Projection/event-study 的形式：每个 horizon 独立估计响应，报告区间、样本、滞后、前响应和稳健性，而不是只展示一条平滑线。当前实现以 WTI 与美国 CPI 为免费数据验证载体，但将 evidence type 标记为 `DYNAMIC_ASSOCIATION`；真正因果 LP 需要预注册外生冲击或合格工具变量。报告为 `reviewed`，其一般风险情景与全球预测未声称复现。

## R06 World Bank：Indonesia Economic Prospects, June 2026

该国别报告把需求、贸易、价格、财政和结构改革组织成泳道，并展示如何从多部门指标聚合国家观点。对 MacroTrace 的价值主要是研究 DAG 结构：问题先分解为活动、消费、投资、贸易、财政和通胀，再在每条泳道建立中间 claim。由于研究对象是印度尼西亚，因子定义、季节性、政策制度和数据发布时间不能直接移植到美国；本轮只保留工作流设计证据，状态为 `reviewed`。任何美国结论都不会引用其中的数值，贸易泳道也因缺少完整美国免费高频 Route 而保持 PARTIAL。

## R07 BIS：Annual Economic Report 2026

第 67–68 页等部分讨论金融条件、利率、资产负债表和冲击传导，适合 `MONETARY/FINANCIAL CONDITIONS → ACTIVITY/INFLATION/ASSETS`。逆向记录收益率、金融条件、信贷、资产价格和政策变量，以及多变量系统、冲击响应和情景比较。本轮这些证据支持注册 VAR 和 Local Projection 的诊断合同，但不自动赋予结构识别。Cholesky 顺序必须来自 Registry，界面必须展示排序；LP 必须展示响应区间与识别限制。报告状态为 `reviewed`，尚未复现 BVAR、非线性金融加速器或完整资产负债表模型。

## R08 IMF：Global Financial Stability Report, April 2026

第 54–55、72–76 页提供金融条件与增长尾部风险的核心路径：`NFCI/FINANCIAL STRESS → FUTURE GDP DISTRIBUTION`。这是本轮最完整的 active 方法来源。实现使用 FRED 的季度实际 GDP 与 NFCI，估计未来 1/2/4 季度增长的条件分位数，要求至少 80 个季度，输出 5%、10%、50% 等分位数、crossing 检查、严格时间顺序 OOS pinball loss 和扇形图。结果是条件分布估计，不被转换成 LLM 生成的“衰退概率”。报告中跨国或机构级面板仅作为 Panel FE fixture 的研究提示；当前州房价—失业率样本没有该报告的直接 estimand，因此被降级并排除在综合之外。R08 状态为 `active`，只表示 GaR 路径 active，不代表整份报告全部复现。

## R09 Bank of England：Monetary Policy Report, November 2025

第 42、44–45 页展示通胀/活动预测与不确定区间，第 73、75 页展示政策和利率传导。其关键结构是 ragged-edge 数据进入 nowcast，再经过预测模型和判断形成扇形图，同时披露数据新闻和预测修订。v0.2 据此实现 Dynamic Factor/bridge nowcast 的因子载荷、解释比例、Kalman-like ragged-edge 提示和 OOS RMSE；当前具体实现使用 PCA 因子和 bridge 回归，并不冒充完整央行状态空间系统。VAR 路径也借鉴其多变量传导语境。报告为 `reviewed`，DFM 配方 active；news decomposition 仍是诊断合同中的后续项，尚未声称完整实现。

## R10 BNP Paribas：ScenarioEco Nowcasts, 2026-07-06

第 1–2 页是实时 nowcast 结果与方向性比较，清楚体现“多指标 → 当前季度活动判断”的产品输出，但方法披露不足。它支持用户界面的 nowcast 卡、更新时间、方向和历史比较，不足以独立决定因子载荷、窗口或模型参数。因此状态为 `evidence_only`。MacroTrace 不复制其预测数值，实际 DFM 使用官方美国数据和注册配方；报告只作为输出形态和 Route 合理性的第二来源。

## R11 Deutsche Bank：Tracking the Effects of AI on the US Labor Market

第 25–30、33、36 页把 AI 暴露、职业/行业结构、招聘、就业和工资连接起来，支持 `TECHNOLOGY EXPOSURE → LABOR MARKET` 的未来节点设计。要回答“AI 是否推高失业率”，需要职业或行业面板、暴露度定义、处理时点、控制变量、平行趋势或其他识别，而不能只看全国失业率。当前免费数据和研报披露不足以建立合格 DID，所以该路径为 `reviewed`，没有激活 DID、决策树或深度学习。用户问这一问题时系统应返回 PARTIAL/UNSUPPORTED，并明确缺少可注册的因果识别；州面板 fixture 不能替代 AI 暴露面板。

## 首轮方法审核结论

五类方法中，Dynamic Factor、VAR、Local Projection 和 Quantile Growth-at-Risk 已成为 active ModelRecipe；Panel FE 代码和真实数据能够执行，但由于缺少与州房价问题一致的研报 estimand，保持 fixture。BVAR 尚未与 VAR 分开实现，不能在界面声称已运行 BVAR。DID/RDD/ML/DL/RL 均未满足激活条件。每个 active 方法都有变量白名单、参数策略、失败条件、方法专属诊断、真实数据 snapshot、学术 artifact 和合成 DGP 测试。

逆向成果进入 `registry/v2/reports.json`、`routes.json`、`models.json` 及相关 Node/Factor/Dataset Registry。页码证据必须能够从最终模型节点 Provenance 反查；若某条 Route 只有主题相似而没有方法级证据，就只能是 candidate/reviewed，不能因为 LLM 判断“看起来相关”而转为 active。
