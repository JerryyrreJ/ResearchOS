# 第一批免费数据 API 与本地数据仓库方案 v0.1

## 1. 结论

第一版不需要先买 Bloomberg、Haver、Macrobond、LSEG 或 FactSet。仅用美国官方免费数据，加上 FRED/ALFRED 的统一分发和 vintage 能力，就能搭出活动、劳动、通胀、货币、财政/Treasury、贸易、能源、住房和部分金融条件的 MVP。

必须从第一天就保存原始响应和抓取时间。否则系统日后只能用修订后的最终值回测，会产生 look-ahead bias，无法诚实回答“在当时的信息集下系统会怎么判断”。

## 2. P0：首发八个连接器

| ID | 官方来源 | 认证 | 第一版主要用途 | 点时能力 |
|---|---|---|---|---|
| `FRED_ALFRED` | [FRED API](https://fred.stlouisfed.org/docs/api/fred/overview.html) | 免费 API key | 跨来源统一时间序列、收益率、预期、金融条件、claims 等 | ALFRED 提供 revision/vintage；P0 核心 |
| `BLS_PUBLIC_DATA` | [BLS Public Data API](https://www.bls.gov/developers/) | v1 可无 key；免费 key 解锁 v2 配额 | CPI、PPI、就业、失业、工资、ECI、JOLTS、生产率 | API 不等于完整 vintage；每次发布保存快照 |
| `BEA_API` | [BEA API](https://apps.bea.gov/api/signup/) | 免费 key | NIPA、GDP by Industry、PCE/收入/储蓄、ITA、IIP、固定资产、投入产出 | 保存每次发布快照与参数 |
| `CENSUS_DATA_API` | [Census APIs](https://www.census.gov/data/developers/data-sets.html) | 免费 key，按当前官方要求配置 | 国际贸易、零售/批发、制造、住房、建设及企业调查 | 保存 release snapshot；部分历史表另行归档 |
| `EIA_API_V2` | [EIA Open Data](https://www.eia.gov/opendata/) | 免费 key | 油气煤、电力、库存、生产、进出口、价格、STEO | 保存 vintage；预测表尤其需要版本化 |
| `TREASURY_FISCAL_DATA` | [Fiscal Data API](https://fiscaldata.treasury.gov/api-documentation/) | 当前公开 API 无需 key | 债务、利息、收支、拍卖/债务结构等 | 原始响应按日保存 |
| `FED_DDP` | [Federal Reserve Data Download Program](https://www.federalreserve.gov/datadownload/) | 无 key | H.15、G.17、H.8、Z.1、DSR、H.10、H.6、G.19 | DDP 是当前发布值；自行保存快照，或优先用 ALFRED |
| `NYFED_MARKETS` | [New York Fed Markets API](https://markets.newyorkfed.org/static/docs/markets-api.html) | 无 key | SOFR、EFFR、OBFR、TGCR、BGCR、成交量与参考利率 | 按发布日期保存 |

### 2.1 为什么 FRED 不能代替所有原始连接器

FRED 适合统一读取和 ALFRED vintage，但仍应保留 BLS/BEA/Census/EIA 等原生连接器：

- 原生 API 有更多表维度、分类和 metadata；
- FRED series 可能晚于原始发布或只覆盖部分表；
- 原始表能保留更完整的行业/州/商品结构；
- 多来源交叉核验能发现口径、季调和单位错误；
- 上游 series 变更时，不把产品完全绑定给一个聚合平台。

## 3. P1/P2：扩展免费来源

| 来源 | 用途 | 阶段 | 备注 |
|---|---|---|---|
| [NOAA Climate Data Online](https://www.ncei.noaa.gov/cdo-web/webservices/v2) | 温度、降水、极端天气 | P2 | 免费 token；支持 Climate/Nature 泳道 |
| [USDA NASS Quick Stats](https://quickstats.nass.usda.gov/api) | 作物、产量、价格、农业投入 | P2 | 免费 key；支持农业与食品供给 |
| [OpenFEMA](https://www.fema.gov/about/openfema/api) | 灾害声明、援助和风险 | P2 | 用于物理冲击与财政损失 |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | 公司事实、申报、AI/data-center capex | P2 | 无 key；必须用合规 User-Agent 和速率 |
| [CFTC Public Reporting](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm) | 期货持仓、杠杆和集中度代理 | P2 | COT 可下载；实时微观结构覆盖有限 |
| [USAspending API](https://api.usaspending.gov/) | 联邦合同、补贴、地域/行业财政支出 | P1 | 财政冲击和产业政策 |
| [Treasury TIC](https://home.treasury.gov/data/treasury-international-capital-tic-system) | 跨境证券和银行流动 | P1 | 以官方文件/表格连接器接入，不假设统一 REST API |
| Census BTOS 下载/表格 | 企业 AI 采用率 | P1 | 先锁定稳定 series/table ID，再决定 API 或文件 adapter |
| 各州 WARN | 裁员通知 | P2 | 格式高度分散，需要州级 adapter 和口径 QA |

## 4. 泳道—数据源覆盖

| 泳道 | P0 主数据 | P1/P2 补充 |
|---|---|---|
| Activity | BEA NIPA/GDP by Industry、Fed G.17、Census 零售/制造/建设、FRED | 高频私营数据以后再买 |
| Labor | BLS CPS/CES/JOLTS/ECI/Productivity、FRED claims | Census BTOS、WARN、Indeed 许可数据 |
| Inflation | BLS CPI/PPI/工资、BEA PCE、EIA 能源、FRED breakeven/预期 | 商品微观价格以后补充 |
| Monetary | Fed H.15、NY Fed 参考利率、FRED/ALFRED、Fed 金融条件相关序列 | 市场隐含政策路径需要合规免费代理或后续付费 |
| Fiscal/Treasury | Fiscal Data、BEA、FRED | CBO/OMB 文件、USAspending、TIC |
| Trade | Census International Trade、BEA ITA/IIP | 港口/航运数据后续 |
| Commodity/Energy | EIA、FRED | USDA、NOAA、CFTC |
| Financial Stability | Fed H.8/Z.1/DSR/H.15、NY Fed、FRED | SEC、CFTC、OFR、付费 security-level holdings |
| AI/Productivity | BLS productivity、BEA fixed assets/GDP industry、Census BTOS | SEC filings、职位发布数据 |
| Climate/Nature | 首版只做情景接口 | NOAA、USDA、FEMA、地理数据 |
| Capital Flows/FX | BEA ITA/IIP、Fed H.10、FRED | Treasury TIC、基金流数据 |
| Housing/Consumption | Census housing/retail、BEA PCE/income/saving、Fed DSR/G.19、FRED | 贷款级数据后续 |

## 5. 第一批具体数据合同

数据注册表不能只写“用 FRED”。每个 factor 都要固定到 series/table 和语义。首个纵向切片至少需要：

### 5.1 通胀

- CPI headline/core、商品、服务、住房等分项；
- PPI 最终需求与关键中间品；
- PCE headline/core 与可获得的细分；
- 1/3/6 个月环比年化、同比、扩散和截尾/中位数代理；
- 5y/10y breakeven 与调查预期代理；
- 每个因子固定 seasonal adjustment、单位和 annualization。

### 5.2 劳动与工资

- nonfarm payroll、household employment、unemployment、participation；
- average hourly earnings、ECI、unit labor cost/productivity；
- JOLTS openings/quits/hires、initial/continuing claims；
- vacancy/unemployment、工资动量与行业扩散。

### 5.3 商品与能源

- WTI/Brent、汽油/柴油、天然气价格；
- 原油与成品油库存、生产、进口、出口和 refinery utilization；
- EIA STEO 的供需预测必须按 vintage 保存；
- 能源价格向 CPI/PPI 的已注册滞后变换。

### 5.4 Fed 与利率

- target range、EFFR、SOFR；
- Treasury 2y/5y/10y/30y 与 TIPS/breakeven；
- term spread、real yield、信用利差与免费 FCI；
- policy rule 所需 inflation gap、unemployment/output gap；
- 10 年期收益率结果不能只看一个回归，要分预期短率、实际利率、通胀补偿和期限溢价代理。

### 5.5 财政与 Treasury

- receipts、outlays、deficit、debt outstanding、interest expense；
- marketable debt 的 maturity/auction/issuance 结构；
- debt/GDP、interest/revenue、net issuance 和 weighted average maturity；
- 财政数据发布日期通常不同于经济所属月份，必须分别保存 `period_end` 与 `available_at`。

### 5.6 活动、消费与住房

- real/nominal GDP 与组成、GDI、PCE、disposable income、saving rate；
- industrial production/capacity utilization；
- retail sales、durable goods/shipments、construction spending；
- housing starts/permits/sales 与 mortgage/consumer credit/DSR。

### 5.7 贸易与资本流动

- export/import value、quantity proxy、price index；
- 按 partner、HS/end-use/NAICS 的结构；
- trade balance 与 real net exports；
- BEA ITA/IIP 的直接投资、证券投资与其他投资；
- 汇率和资产价格必须对齐交易日、月末或月均口径。

## 6. 本地仓库：三层数据而不是一个 CSV 文件夹

```text
data/
  raw/
    source=bls/ingest_date=2026-07-13/request_hash=.../response.json
    source=fred/ingest_date=2026-07-13/request_hash=.../response.json
  normalized/
    observations/source=bls/frequency=M/year=2026/*.parquet
    releases/source=bea/year=2026/*.parquet
  curated/
    factor_id=US_CPI_CORE_MOM3_SAAR/version=1/*.parquet
  snapshots/
    snapshot_id=.../manifest.json
```

三层含义：

- `raw`：原始响应不可修改，只追加；保留 URL、参数、headers、状态、hash 和抓取时间；
- `normalized`：把不同 API 统一成长表，但不加入研究判断；
- `curated`：按 Factor Registry 执行固定变换，供模型读取。

DuckDB 负责查询 Parquet；SQLite 保存 registry、job、release calendar 和 lineage。模型不得直接访问互联网，只能读取已经生成并冻结的 `snapshot_id`。

## 7. 标准观测表

建议统一字段：

```text
source_id
dataset_id
series_id
period_start
period_end
value
unit
frequency
seasonal_adjustment
geography
category_dimensions_json
release_id
available_at
vintage_start
vintage_end
ingested_at
raw_artifact_hash
quality_flags
```

`available_at` 和 `period_end` 不能合并。2026 年 7 月发布的 2026 年 6 月 CPI，观测期属于 6 月，但在发布日期之前不能被 as-of 查询看到。

## 8. 点时数据与 as-of 查询

### 8.1 真 vintage

FRED/ALFRED 支持 real-time/vintage 查询。对于这类来源，保存上游给出的 `vintage_start` / `vintage_end`，as-of 查询使用官方信息集。

### 8.2 自建 vintage

BLS、BEA、Census、EIA、Treasury 和 Fed DDP 需要每次发布后抓取快照：

1. release calendar 触发同步；
2. 原始响应不可变落盘；
3. 比较上一版，生成 revision event；
4. 旧值关闭 `vintage_end`，新值开始新的 vintage；
5. 运行任务绑定 snapshot manifest。

自建采集只能从项目开始后积累，不应假装拥有更早的完整实时 vintages。若用官方历史档案补录，要把来源和不确定性标出来。

### 8.3 as-of 规则

一个观测只有在以下条件同时满足时才可被任务读取：

```text
available_at <= job.as_of_date
vintage_start <= job.as_of_date
vintage_end is null OR job.as_of_date < vintage_end
```

当用户问未来 1—3 个月时，`as_of_date` 默认是提交时刻；回测时由测试显式指定。

## 9. 连接器接口

所有来源实现同一协议：

```text
discover()      列出 dataset/series/table metadata
fetch_raw()     拉原始响应，不做经济变换
normalize()     转标准观测表
detect_release()识别新发布或修订
validate()      检查行数、频率、单位、缺失和断点
checkpoint()    写入游标/etag/last-modified
```

连接器配置只能来自 Dataset Registry，不允许 LLM 生成 URL 或 API 参数。密钥只从环境变量/本地 secret store 读取，不能进入日志、trace 或模型上下文。

## 10. 数据质量门

每次入库至少做：

- schema/类型和主键唯一性；
- 频率、单位、季调状态是否与 registry 相符；
- 观测日期是否连续，是否意外大幅缩短历史；
- 与上一 vintage 的 revision 是否合理；
- 新值的量级、符号和跳变；
- 同义来源的交叉校验，例如 BLS CPI 与 FRED 转发；
- API 返回空结果、限流或错误 JSON 时不得覆盖旧数据；
- quality failure 时标记 connector degraded，并阻止依赖模型静默运行。

## 11. 免费 API 配额与同步策略

首版不要对每个用户问题实时打上游 API。采用集中同步：

- release-driven：CPI、就业、GDP 等按官方日历抓取；
- daily：市场利率、财政日度和能源高频；
- weekly：库存、claims、部分 Fed release；
- monthly/quarterly：NIPA、Z.1、ITA/IIP 等；
- metadata weekly diff：检测 series 说明、单位和季调变化。

官方当前文档显示，BLS v1 无注册配额较低，免费注册的 v2 配额更高；BEA、Census、EIA 和 FRED 也应申请各自免费 key。具体数字不写进业务代码，放入 Dataset Registry 的 rate-limit policy，并以官方文档为准。

## 12. 第一批不购买数据会缺什么

免费栈的边界必须展示给用户：

- 完整利率期货/期权隐含 Fed 路径；
- 实时 tick、dealer/repo、hedge fund 杠杆和 security-level 持仓；
- 高质量职位发布全文和 AI 技能标签；
- 公司级 consensus、精细 capex 项目和债券持有人；
- 部分商品航运、库存和高频价格；
- 历史完整 real-time vintage（项目开始前）。

首版处理方式是用公开代理、降低结论等级或明确 `DATA_BLOCKED`，不是从网页随意抓一个口径不明的数。

## 13. 数据接入实施顺序

1. 建 raw artifact、标准观测表、snapshot manifest 与 lineage；
2. 接 FRED/ALFRED，先验证 point-in-time 查询；
3. 接 BLS、BEA、EIA；
4. 接 Treasury、Fed DDP、NY Fed；
5. 接 Census 经济指标与国际贸易；
6. 建 release calendar 和 revision detector；
7. 固化首批 40—60 个 Factor IDs；
8. 跑通通胀→Fed→10 年期收益率的端到端数据快照；
9. 再接 AI、金融稳定、气候与州级数据。
