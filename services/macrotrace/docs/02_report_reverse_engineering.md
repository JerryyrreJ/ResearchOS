# 首批研报逆向与美国宏观泳道 v0.1

## 1. 本轮逆向口径

本轮处理了用户提供的 9 份 PDF 和 2 份分页文本，共 11 个报告单元。逆向的目标不是摘要报告观点，而是回答六个问题：

1. 作者在研究什么经济机制？
2. 每条机制用了什么数据、因子、变换和方法？
3. 方法披露到什么程度，能否做成固定可执行模块？
4. 它对美国宏观是直接适用，还是只能迁移方法？
5. 免费数据能否支持第一版复现？
6. 它应该进入 Workflow/Model Registry，还是只进入 Evidence/Scenario Registry？

页码均指文件页码；两个 `.txt` 文件按换页符分割后的页码计数。报告中的描述性相关不能被提升为因果结果，报告未披露的模型也不会被“脑补”为可执行模型。

## 2. 逆向状态枚举

| 状态 | 含义 |
|---|---|
| `EXECUTABLE_CANDIDATE` | 披露足以形成固定配方，但仍需编码、测试与复现 |
| `ADAPTABLE_RECIPE` | 原研究不是美国样本，方法可以迁移到美国数据 |
| `EVIDENCE_ONLY` | 观点、制度知识、风险情景或预测有价值，但方法不足以执行 |
| `DATA_BLOCKED` | 方法可行，但首版免费数据无法忠实复现 |
| `OUT_OF_SCOPE_COMPONENT` | 与美国宏观第一版没有直接关系，只保留来源记录 |

美国适用性：

- `US_DIRECT`：对象或主要数据是美国；
- `US_ADAPTABLE`：机制/方法可迁移，但不能把原报告系数直接当作美国结论；
- `OUT_OF_SCOPE`：不进入首版运行时。

## 3. 从 11 份材料反推出的种子泳道

泳道不是固定为五条，也不是每次由 AI 临时发明。首批材料归一后得到 12 条种子泳道：

| ID | 泳道 | 典型问题 | 首批来源 |
|---|---|---|---|
| `US.ACTIVITY` | 实体活动与商业周期 | GDP、需求、产出缺口、衰退/复苏 | GEP、BNP、BoE、Indonesia |
| `US.LABOR` | 劳动力市场与工资 | 就业、失业、工资、岗位、裁员 | Deutsche Bank、BoE |
| `US.INFLATION` | 通胀、价格与预期 | 商品/服务通胀、黏性、预期、拐点 | BoE、CMO、BIS |
| `US.MONETARY` | 货币政策与金融条件 | Fed 反应、实际利率、FCI、收益率传导 | IMF、BIS、BoE |
| `US.FISCAL_TREASURY` | 财政、主权债务与 Treasury | 赤字、债务、供给、期限溢价、财政风险 | GEP Jan、BIS、IMF |
| `US.TRADE` | 贸易、关税与全球溢出 | 进出口、关税、FDI、全球需求 | GEP June、Indonesia、CMO |
| `US.COMMODITY_ENERGY` | 商品、能源与供给冲击 | 油气、金属、农产品、库存与成本传导 | CMO、BIS、BoE |
| `US.FIN_STABILITY` | 金融稳定与市场结构 | 杠杆、NBFI、流动性、市场放大器 | IMF、BIS |
| `US.AI_PRODUCTIVITY` | AI、生产率与投资 | AI 采用、资本开支、生产率、r-star | Deutsche Bank、BIS、IMF |
| `US.CLIMATE_NATURE` | 气候、自然资本与物理风险 | 产量、基础设施、适应投资、自然服务 | Nature、Climate Adaptation |
| `US.CAPITAL_FLOWS_FX` | 资本流动与美元 | VIX、跨境流动、美元、FX/repo | IMF、BIS、GEP |
| `US.HOUSING_CONSUMPTION` | 住房、消费与家庭资产负债表 | 储蓄、财富、房贷、消费反应 | BoE HANK、GEP/BNP outlook |

这是 `v0.1` 分类，不是永远不变的本体。后续报告可以提出新的泳道候选，但必须给出与现有泳道的边界、至少两个独立工作流以及迁移方案，经独立 Codex 语义复核和 Registry 迁移审计后才新增。

## 4. 报告总览

| 报告 | 主要泳道 | 适用性 | 逆向结论 |
|---|---|---|---|
| Mainstreaming Nature into World Bank Macroeconomic Models | Climate/Nature、Activity、Fiscal | `US_ADAPTABLE` | 三模型循环架构可迁移；高颗粒度生态数据是主要阻塞 |
| Climate Change Impacts and Adaptation Options | Climate/Nature、Activity、Fiscal | `US_ADAPTABLE` | 冲击→生物物理→宏观→适应情景工作流可迁移 |
| Commodity Markets Outlook Oct 2025 | Commodity/Energy、Inflation、Trade | `US_ADAPTABLE` | 因子与情景结构有价值；报告本身未披露可复制预测器 |
| GEP June 2025 | Trade、Capital Flows、Activity | `US_ADAPTABLE` | FDI 异质 PVAR 是配方候选；多数预测为证据层 |
| GEP January 2026 | Fiscal/Treasury、Capital Flows | `US_ADAPTABLE` | 财政规则 LP-AIPW 是强方法候选，但不是美国政策模块 |
| Indonesia Economic Prospects June 2026 | Activity、Fiscal、Trade | `US_ADAPTABLE` | 研究框架可迁移；国别结论不进入美国运行时 |
| BIS Annual Economic Report 2026 | Fiscal、Financial Stability、AI、FX | 混合 | 财政风险重定价识别可执行；其他多为机制/情景 |
| IMF GFSR April 2026 | Financial Stability、Monetary、Capital Flows | 混合 | GaR、flighty-investor 面板等为候选；大量付费数据需代理 |
| BoE MPR November 2025 | Inflation、Monetary、Consumption | `US_ADAPTABLE` | SET-BVAR/HANK/规则结构可迁移，UK 校准不可直接使用 |
| BNP ScénarioÉco Nowcasts 2026-07-06 | Activity、Inflation、Monetary | 混合 | 只有预测/叙事；方法未披露，不能登记为 nowcast 模型 |
| Tracking AI Effects on US Labor Market | Labor、AI/Productivity | `US_DIRECT` | 美国描述性监测工作流可立即搭建；不能宣称因果 |

## 5. 逐份逆向

### R01. Mainstreaming Nature into World Bank Macroeconomic Models

**文件：** `P180275-13b364e3-f045-47f2-97de-f9218682df98.pdf`，92 页。

**核心机制。** 自然资本不是外生背景，而是经由土地覆盖与生态系统服务改变部门生产率、产量、收入和宏观结果；经济活动和政策又反过来改变土地利用，形成反馈环。

**反向出的工作流：**

1. 建立无政策基准和政策/自然冲击反事实；
2. 宏观模型产生经济活动和土地需求；
3. LULC 模型把经济/政策输入映射为土地覆盖变化；
4. ES 模型把覆盖变化映射为侵蚀、授粉、水、作物产量、旅游或海岸保护等生态服务；
5. 把生态服务变化转为宏观模型中的生产率、生产、资本损失或成本冲击；
6. 迭代至收敛，比较 GDP、消费、投资、部门产出和财政成本；
7. 对干预成本、避免损失和收益做 NPV/成本收益分析。

**模型/数据。** 报告描述 MANAGE-WB CGE、MFMod、LULC 与 ES 连接和自动化软件（文件页 12、16、20 起）；试点涵盖森林与红树林等场景。

**产品落点。**

- `CLIMATE_NATURE_THREE_MODEL_LOOP_V1`：`ADAPTABLE_RECIPE`；
- `CLIMATE_POLICY_COST_BENEFIT_V1`：`ADAPTABLE_RECIPE`；
- 精细生态服务模块：首版 `DATA_BLOCKED`；
- 原报告国别参数与结果：不作为美国系数。

**美国第一版最小化。** 不立即做完整 CGE-LULC-ES 联立系统；先注册“物理冲击→资本/劳动/农业生产率→美国行业产出”的情景接口，等 NOAA/USDA/FEMA 等免费数据补齐后扩展。

### R02. The Macroeconomic Implications of Climate Change Impacts and Adaptation Options

**文件：** `content.txt`，45 个分页单元。

**核心机制。** 气候情景通过高温劳动生产率、农业作物产量、洪水/气旋等基础设施损害、健康和旅游等通道进入宏观模型；适应投资同时产生前期成本和未来避免损失。

**反向出的工作流：**

1. 选择气候/温升/灾害情景与时间窗；
2. 调用生物物理或损失函数得到各通道冲击；
3. 把通道冲击映射到 MFMod 的劳动、资本、生产率和财政变量；
4. 比较无气候冲击、无适应、有适应三组路径；
5. 分解毛损失、适应成本、避免损失和净 GDP 收益；
6. 对冲击、模型和参数不确定性做敏感性/Monte Carlo。

**证据位置。** MFMod 与通道描述集中在分页 14—23；适应与不确定性贯穿正文，Monte Carlo 在分页 42。

**产品落点。** `CLIMATE_IMPACT_ADAPTATION_SCENARIO_V1` 为 `ADAPTABLE_RECIPE`。它是情景模型，不应输出为短期精确预测。

### R03. Commodity Markets Outlook, October 2025

**文件：** `CMO-October-2025.pdf`，66 页。

**核心机制与泳道：**

- 能源：全球需求、OPEC+供给、美国页岩、库存、地缘冲突与航运；
- 农产品：天气、收成、库存、投入成本和贸易限制；
- 肥料：天然气成本、产能、贸易和农业需求；
- 金属与贵金属：全球工业需求、中国周期、AI/电网投资、矿山供给、美元和避险需求；
- 向美国传导：进口成本→PPI/CPI，能源→实际收入/消费，金属→投资成本。

**报告结构。** 执行摘要和分品种预测/风险位于文件页 9—16 起；特别专题讨论商品协议的历史与政策工具。

**重要判定。** 这份报告给了 forecast table、驱动叙事和上下行风险，但没有在文件中充分披露一个可按原样编码的统一预测算法。因此：

- 分品种因子树进入 `COMMODITY_MONITOR_V1`；
- 供需/库存/美元/天气规则进入 Workflow Registry；
- 报告预测进入 Evidence/Scenario Registry；
- 不创建名为“World Bank Commodity Forecast Model”的伪模型。

### R04. Global Economic Prospects, June 2025

**文件：** `GEP-June-2025.pdf`，254 页。

**可执行核心：FDI 对增长的异质 PVAR。**

- 强平衡年度面板，74 个 EMDE，1995—2019；
- 主要变量包括实际净 FDI、实际 GDP、实际固定资本形成；
- 扩展条件变量包括私人信贷、贸易开放、教育、TFP、就业、制度和非正规经济；
- 用 heterogeneous PVAR 处理动态、内生性和国家异质性；
- 通过变量排序/Cholesky 识别冲击，输出 impulse response；
- 报告示例是 FDI 冲击后数年 GDP 响应，不可直接当作美国效应。

方法和数据集中在文件页 143—145、161 起。

**产品落点。**

- `HETEROGENEOUS_PVAR_V1`：`ADAPTABLE_RECIPE`；
- 美国可以改用州/行业面板研究投资、资本开支与产出，但变量集合必须另经审核；
- 全球增长、关税和政策不确定性预测流程包含模型与 judgment，文件页 245 描述其组合，但不足以形成单一确定性配方，故进入 Evidence/Scenario Registry。

### R05. Global Economic Prospects, January 2026

**文件：** `Global Economic Prospects, January 2026.pdf`，244 页。

**可执行核心：财政规则采用的动态效果。**

- 结果变量是 cyclically adjusted primary balance 等财政指标；
- local projections 估计采用前后的累计变化；
- 包含国家和时间固定效应、CAPB 滞后、处理变量 leads/lags；
- 以 LP-AIPW 做双重稳健估计，用 propensity 模型平衡采用财政规则的选择；
- 控制债务/GDP、增长、通胀、经常账户、选举、制度、通胀目标制、汇率制度、资本账户开放、财政委员会和金融发展等；
- 报告约有 58 个规则采用事件，并检查制度环境和规则设计的异质性。

方法与附录集中在文件页 134—155，LP-AIPW 见 135、137、139、154。

**产品落点。**

- `LOCAL_PROJECTION_FE_V1`：通用 `ADAPTABLE_RECIPE`；
- `LP_AIPW_TREATMENT_V1`：高级 `ADAPTABLE_RECIPE`；
- 原报告回答跨国财政规则，不直接回答美国短期赤字或 Treasury；
- 美国运行时可用同一技术研究州级财政制度或已审核的政策事件，但不能让 AI 自行定义 treatment。

### R06. Indonesia Economic Prospects, June 2026

**文件：** `content2.txt`，44 个分页单元。

**逆向出的研究框架：**

- activity nowcast/outlook：消费、投资、净出口和高频活动；
- fiscal/debt：收入、支出、赤字、债务可持续性与公共投资；
- trade/FDI：贸易协议、关税、出口结构、进口和外资；
- productivity：物流、数字基础设施、营商环境、人力资本；
- public investment：项目效率、挤入/挤出和乘数。

相关主题在分页 4—13、18—31、41 等。

**产品落点。** 国别事实为 `OUT_OF_SCOPE_COMPONENT`；“国别宏观监测→预测→政策优先级”的报告组织方式进入 Workflow Registry。若报告没有完整估计式，就不登记公共投资乘数模型。

### R07. BIS Annual Economic Report 2026

**文件：** `ar2026e.pdf`，133 页。

**模块 A：AI 投资、生产率与 r-star。**

- AI capex 短期支撑增长，但同时带来估值、融资和过度建设风险；
- 长期通过生产率、资本需求、储蓄/投资平衡影响自然利率；
- 报告文件页 21、30—32 给出机制和情景。

产品状态：`EVIDENCE_ONLY` + `AI_CAPEX_PRODUCTIVITY_SCENARIO_V1`；不能把长期情景当成计量预测。

**模块 B：财政风险重定价。**

- 识别思想：政府债券收益率上升、而可比期限高等级公司债收益率下降的负共动，更可能是财政风险重估，而不是共同的通胀/货币冲击；
- 使用 2010 年以来广泛 AE/EME 面板；
- 冲击后考察 10 年期国债收益率、NEER、CPI 与工业生产；
- 比较主动和被动货币政策反应。

文件页 67—68 明确说明识别、样本和 Graph 9 输出。产品状态：`FISCAL_RISK_REPRICING_V1` 为 `EXECUTABLE_CANDIDATE`。美国版可使用 Treasury 与投资级公司债曲线，但必须先验证期限和信用构成可比性。

**模块 C：财政—金融放大器。** repo、FX swap、杠杆基金、dealer balance sheet、margin spiral 与央行 backstop 构成一条市场放大泳道；美国 March 2020 dash-for-cash 被作为案例（文件页 64—65）。状态：规则/事件型 workflow，完整复现可能需要微观或付费数据。

**模块 D：stablecoin。** 储备资产需求、银行存款替代、跨境资本流动、美元化、货币传导与金融诚信是多条情景链，主要在文件页 101—116。首版进入 Evidence/Scenario Registry，不直接成为美国短期预测模型。

### R08. IMF Global Financial Stability Report, April 2026

**文件：** `text.pdf`，86 页。

**模块 A：Financial Conditions → Growth-at-Risk。**

- 把金融条件指数或特定市场冲击作为条件变量；
- 估计未来 GDP 增长的条件分布；
- 关注左尾分位数，而不仅是均值；
- 可把战争/商品价格/市场放大情景映射到一年期增长风险。

方法/结果见文件页 54—55、75。产品状态：`GROWTH_AT_RISK_V1` 为 `EXECUTABLE_CANDIDATE`，美国可用免费 FCI 和 GDP 数据搭一个透明简化版。

**模块 B：flighty investors 与压力期发行。**

- 构造投资者稳定性/易逃逸持有占比；
- 在压力事件中研究该占比与主权/企业发行、利差、资本开支的关系；
- 使用面板、国家固定效应和控制变量；
- 文件页 72—76 披露主要定义、回归和结果。

状态：`PANEL_FE_V1` 可复用，但原始 security-level holdings、LSEG/Bloomberg/FactSet/Haver 等依赖使忠实复现 `DATA_BLOCKED`。美国版可先用公开基金流、发行和 Treasury 数据做较窄代理。

**模块 C：AI 数据中心融资压力。** 资本开支、债务融资、寿命/技术淘汰、集中度和估值冲击形成压力测试，见文件页 42—43、56—59。状态：情景 workflow；公司级融资数据部分付费。

**模块 D：资本流动与市场放大。** VIX、基金类型、非居民/居民流动、杠杆、ETF/衍生品和银行—NBFI 关联形成跨境流动与金融稳定泳道。可登记因子树，不能把图表相关性自动写成因果。

### R09. Bank of England Monetary Policy Report, November 2025

**文件：** `monetary-policy-report-november-2025.pdf`，79 页。

**模块 A：通胀机制树。** 商品/食品/能源、工资、服务价格、企业成本与利润率、通胀预期和工资—价格设定组合为核心通胀判断。

**模块 B：SET-BVAR。** 用平滑转移/状态依赖 BVAR 比较低通胀与高通胀 regime 下全球冲击对通胀、预期和活动的不同反应，见文件页 42—45。状态：`SET_BVAR_REGIME_V1` 为 `ADAPTABLE_RECIPE`，需重新选择并审核美国变量和先验。

**模块 C：COMPASS 情景。** 报告用宏观模型调整通胀持续性，见文件页 71。因完整模型未在该报告中披露，状态为 `EVIDENCE_ONLY`，不能创建 COMPASS 复刻。

**模块 D：HANK 家庭储蓄情景。** 校准 UK HANK，模拟风险厌恶上升→储蓄→消费→需求与通胀，见文件页 72—73。状态：`HANK_SAVING_SCENARIO_V1` 为长期 `ADAPTABLE_RECIPE`；首版先实现透明的情景映射，不声称复现 BoE 模型。

**模块 E：Taylor-type policy rules。** 用同期和前瞻型规则产生政策路径比较，见文件页 73—75。状态：`POLICY_RULE_PATH_V1` 可快速实现，但只能作为反事实规则，不等于央行预测。

### R10. BNP Paribas ScénarioÉco Nowcasts, 2026-07-06

**文件：** `ScénarioÉcoNowcasts_06.07.2026_ENG.pdf`，2 页。

第一页是欧元区/法国/比利时 nowcast 图表，第二页是美国增长、通胀、Fed、10 年期、美元、油价等预测与叙事。

**重要判定。** 该文件没有披露 nowcast 的训练样本、特征、估计器、权重或回测，因此：

- 预测值和风险叙事进入 Evidence/Scenario Registry；
- 宏观→政策→收益率/汇率的输出模板可作为产品呈现参考；
- 不登记 `BNP_NOWCAST_MODEL`；
- 第一页欧洲 nowcast 为 `OUT_OF_SCOPE_COMPONENT`。

### R11. Tracking the Effects of AI on the US Labor Market

**文件：** `Tracking_the_effects_of_AI_on_the_US_labor_market.pdf`，37 页。

这是首批材料中最直接的美国专题。反向出四组监测 workflow：

1. **AI adoption monitor**：按行业、州和企业规模跟踪 Census 企业 AI 使用/预期；文件页 2—5。
2. **Job postings monitor**：总岗位、AI 高暴露职业、岗位中 AI 关键词占比；文件页 7—14。
3. **Layoff/claims monitor**：WARN、初请/续请与采用率的横截面对照；文件页 17—20。
4. **Wage/youth monitor**：行业采用率与工资增速、年轻/高学历人群失业与就业不足；文件页 25—36。

**证据等级。** 图表主要是时间序列监测、横截面散点和简单拟合；工资与采用等关系很弱，不能写成“AI 导致工资/就业变化”。

**产品落点。**

- `AI_ADOPTION_MONITOR_V1`：`EXECUTABLE_CANDIDATE`；
- `AI_JOB_POSTINGS_MONITOR_V1`：Indeed 数据可能受访问/许可限制，首版部分 `DATA_BLOCKED`；
- `AI_WARN_CLAIMS_MONITOR_V1`：WARN 需要各州清洗，claims 可用官方免费数据；
- `AI_WAGE_CROSS_SECTION_V1`：descriptive only；
- `AI_LABOR_PANEL_DID_V1`：只能作为未来研究提案，不能声称来自报告已有因果识别。treatment、event time、parallel-trend 检验和因变量都必须由研究者预注册。

## 6. 首批工作流地图

下面是从报告反向得到、经过美国宏观归一后的核心候选。详细字段在 `registry/seed/workflows.json`。

| Workflow ID | 泳道 | 输出 | 第一版优先级 |
|---|---|---|---|
| `US_ACTIVITY_NOWCAST_MONITOR_V1` | Activity | 活动方向/拐点 | P0 |
| `US_LABOR_TIGHTNESS_V1` | Labor | 就业与工资压力 | P0 |
| `US_AI_ADOPTION_MONITOR_V1` | Labor/AI | 行业州企业采用扩散 | P1 |
| `US_INFLATION_MOMENTUM_V1` | Inflation | 1/3/6 月动量和广度 | P0 |
| `US_INFLATION_REGIME_V1` | Inflation | 高/低通胀状态依赖 | P1 |
| `US_COMMODITY_SUPPLY_DEMAND_V1` | Commodity | 供需/库存/价格冲击 | P0 |
| `US_COMMODITY_INFLATION_PASS_V1` | Commodity/Inflation | 能源商品→PPI/CPI | P0 |
| `US_FED_REACTION_PATH_V1` | Monetary | 规则路径与市场定价差 | P0 |
| `US_FCI_GROWTH_AT_RISK_V1` | Monetary/Activity | 条件增长左尾 | P1 |
| `US_TREASURY_YIELD_DECOMP_V1` | Fiscal/Monetary | 预期短率/通胀/期限溢价 | P0 |
| `US_FISCAL_RISK_REPRICING_V1` | Fiscal/Fin Stability | 财政风险冲击响应 | P1 |
| `US_TREASURY_SUPPLY_V1` | Fiscal/Treasury | 发行/期限结构/收益率压力 | P0 |
| `US_TRADE_FLOW_V1` | Trade | 进出口量价结构 | P1 |
| `US_TARIFF_PASS_THROUGH_V1` | Trade/Inflation | 关税→进口价→通胀 | P1 |
| `US_CAPITAL_FLOW_RISK_V1` | Capital Flows | VIX/美元/流动方向 | P1 |
| `US_NBFI_AMPLIFICATION_V1` | Fin Stability | 杠杆/流动性压力 | P2 |
| `US_HOUSEHOLD_SAVING_CONSUMPTION_V1` | Consumption | 储蓄冲击与消费 | P1 |
| `US_AI_CAPEX_PRODUCTIVITY_V1` | AI/Productivity | capex/生产率情景 | P2 |
| `US_CLIMATE_PHYSICAL_SCENARIO_V1` | Climate | 物理冲击宏观路径 | P2 |

## 7. 哪些内容可以真正进入第一版执行器

### 7.1 立即可做

- 高频/低频描述性监测、同比/环比/年化、广度、扩散和 z-score；
- 预先定义的阈值与 regime 规则；
- 固定变量集合的 OLS、panel FE、VAR/BVAR 与 local projection；
- 基于免费 FCI/GDP 的简化 Growth-at-Risk；
- Fed 规则路径和 Treasury 收益率分解；
- 美国通胀、劳动、商品、财政与贸易核心因子树。

### 7.2 需要第二阶段

- SET-BVAR 的稳健 regime 估计与实时回测；
- LP-AIPW 的完整 treatment 研究；
- security-level 投资者结构与 NBFI 杠杆；
- 公司级 AI 数据中心融资压力测试；
- 州级 WARN 全量统一清洗；
- 生态服务/LULC 与 HANK/CGE 结构模型。

### 7.3 明确不能伪造

- BNP 未披露的 nowcast 模型；
- World Bank/BoE 由内部模型和 judgment 共同形成的完整预测系统；
- 报告没有给出的公式、权重、先验和变量映射；
- 付费数据库缺失后却声称是“原样复现”；
- 将跨国或英国估计系数直接套在美国；
- 将 AI adoption 散点图提升为因果结论。

## 8. 本轮逆向的产品结论

首批报告证明，MacroTrace 的 C 层不应以“固定五条叙事泳道”组织，也不应以“模型类型”组织。更稳定的结构是：

- 泳道负责经济机制；
- 工作流负责可回答的研究子问题；
- 因子负责统一数据口径；
- 模型配方负责固定计算方法和有限自由度；
- 报告只提供这些对象的来源证据，不拥有运行时结构。

因此一份报告可以贡献多个泳道；多个报告也可以共同完善同一个 workflow。这个结构才能让新研报批量进入系统，又不让底层代码随着 prompt 失控。
