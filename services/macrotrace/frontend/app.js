const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const API_BASE_URL = String(window.MACROTRACE_CONFIG?.apiBaseUrl || "").replace(/\/$/, "");

function apiUrl(path) {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
const TERMINAL = new Set(["COMPLETE", "PARTIAL", "FAILED", "CANCELLED"]);
const TECHNICAL_TYPES = new Set(["FACTOR", "DATASET", "TRANSFORM", "DIAGNOSTIC"]);
const COLORS = ["#1769d2", "#087b6c", "#b42318", "#9a6100", "#6555a6", "#66707d"];
const STAGE_ORDER = ["PARSING_QUERY", "CLASSIFYING_WORKFLOW", "ROUTING_LANES", "ROUTING_NODES", "SELECTING_FACTORS", "PLANNING_MODELS", "SELECTING_PARAMETERS", "VALIDATING_PLAN", "EXECUTING_MODELS", "AGGREGATING_LANES", "SYNTHESIZING"];
const COLUMN_BY_TYPE = {
  QUESTION: 0, QUERY: 1, RESEARCH_DEPTH_GATE: 2, LANE: 2,
  MECHANISM: 3, RESEARCH_NODE: 4, FACTOR: 5, DATASET: 5,
  TRANSFORM: 6, MODEL_SPECIFICATION: 7, MODEL_RUN: 8,
  DIAGNOSTIC: 9, EVIDENCE: 9, CLAIM: 10, LANE_SIGNAL: 11,
  AGGREGATION: 12, FINAL_CLAIM: 13, FALSIFIER: 14,
};
const DISPLAY_LABELS = {
  COMPLETE:"完成", PARTIAL:"部分完成", FAILED:"失败", CANCELLED:"已取消", QUEUED:"排队中",
  PARSING_QUERY:"解析问题", CLASSIFYING_WORKFLOW:"识别任务", ROUTING_LANES:"选择通道",
  ROUTING_NODES:"选择节点", SELECTING_FACTORS:"选择因子", PLANNING_MODELS:"规划模型",
  SELECTING_PARAMETERS:"选择参数", VALIDATING_PLAN:"验证计划", EXECUTING_MODELS:"执行模型",
  AGGREGATING_LANES:"聚合通道", SYNTHESIZING:"生成结论", SUCCESS:"成功", WARNING:"警告",
  RUNNING:"运行中", BLOCKED:"受阻", NOT_ROUTED:"未路由", PLANNED:"已规划", PENDING:"等待中",
  FULL:"完整", UNSUPPORTED:"暂不支持", ANSWERABLE:"可回答", CONDITIONAL:"有条件可回答",
  POLICY_DEFAULT:"工作流默认", USER_EXPLICIT:"用户明确指定", DAYS:"天", WEEKS:"周", MONTHS:"个月",
  QUARTERS:"季度", YEARS:"年", HIGH:"高", MEDIUM:"中", LOW:"低", GLOBAL:"全局",
  QUESTION:"原始问题", QUERY:"结构化问题", RESEARCH_DEPTH_GATE:"研究深度闸门", LANE:"研究通道",
  MECHANISM:"作用机制", RESEARCH_NODE:"研究节点", CLAIM:"中间判断", FACTOR:"实证因子",
  DATASET:"数据集", TRANSFORM:"数据变换", MODEL_SPECIFICATION:"模型设定", MODEL_RUN:"模型运行",
  DIAGNOSTIC:"模型诊断", EVIDENCE:"证据", LANE_SIGNAL:"通道信号", AGGREGATION:"证据聚合",
  FINAL_CLAIM:"最终结论", FALSIFIER:"证伪条件",
};

const ZH_LANES = {
  "US.ACTIVITY":"美国经济活动与商业周期", "US.LABOR":"美国劳动力市场与工资", "US.INFLATION":"美国通胀与价格",
  "US.MONETARY":"美国货币政策与金融条件", "US.FISCAL_TREASURY":"美国财政与国债供给", "US.COMMODITY_ENERGY":"大宗商品与能源冲击",
  "US.HOUSING_CONSUMPTION":"美国住房与居民需求", "US.TRADE":"美国贸易与外部需求", "US.FIN_STABILITY":"美国金融稳定",
  "US.AI_PRODUCTIVITY":"AI 应用、岗位暴露与生产率", "US.EQUITY_MARKET":"美国股票市场、波动率与风险偏好",
  "US.FUTURES_COMMODITY":"美国期货与大宗商品市场", "US.EQUITY_SECTOR":"美国股票行业与轮动", GLOBAL:"全局研究链",
};

const ZH_FACTORS = {
  "F.CPI.HEADLINE":"整体 CPI（季调）", "F.CPI.CORE":"核心 CPI", "F.PCE.HEADLINE":"整体 PCE 价格指数", "F.PCE.CORE":"核心 PCE 价格指数",
  "F.LABOR.PAYROLL":"非农就业人数", "F.LABOR.UNEMPLOYMENT":"失业率", "F.LABOR.WAGES":"私营部门平均时薪",
  "F.ACTIVITY.INDPRO":"工业生产指数", "F.ACTIVITY.RETAIL":"名义零售销售", "F.ACTIVITY.REAL_GDP":"实际 GDP",
  "F.MONETARY.NFCI":"芝加哥联储全国金融状况指数", "F.RATES.UST10":"10 年期美国国债收益率", "F.RATES.UST2":"2 年期美国国债收益率",
  "F.RATES.UST5":"5 年期美国国债收益率", "F.RATES.UST30":"30 年期美国国债收益率", "F.RATES.REAL10":"10 年期美国实际国债收益率",
  "F.RATES.POLICY":"有效联邦基金利率", "F.RATES.TERM_PREMIUM10":"10 年期国债期限溢价", "F.INFLATION.BREAKEVEN10":"10 年期盈亏平衡通胀率",
  "F.INFLATION.FORWARD_5Y5Y":"5 年后 5 年期远期通胀预期", "F.ENERGY.WTI":"WTI 现货价格", "F.FISCAL.DEBT":"美国未偿公共债务总额",
  "F.FISCAL.DEBT_GDP":"美国公共债务占 GDP 比重", "F.FISCAL.NET_SAVING":"美国联邦政府净储蓄 / 净借款",
  "F.STATE.UNEMPLOYMENT":"州级失业率（测试样本）", "F.STATE.HPI":"州级 FHFA 房价指数（测试样本）", "F.ACTIVITY.CFNAI":"芝加哥联储全国活动指数",
  "F.ACTIVITY.REAL_PCE":"实际个人消费支出", "F.ACTIVITY.REAL_DPI":"实际可支配个人收入", "F.HOUSEHOLD.SAVING":"个人储蓄率",
  "F.HOUSING.STARTS":"新屋开工", "F.HOUSING.PERMITS":"新屋建筑许可", "F.MONETARY.CURVE_10Y2Y":"10 年期—2 年期国债期限利差",
  "F.FIN.CREDIT_SPREAD":"Baa 公司债—10 年期国债信用利差", "F.ACTIVITY.RECESSION":"NBER 美国衰退指示变量",
  "F.LABOR.INITIAL_CLAIMS":"首次申请失业救济人数", "F.LABOR.CONTINUING_CLAIMS":"持续领取失业救济人数",
  "F.LABOR.YOUTH_UR":"16—24 岁失业率", "F.LABOR.YOUTH_EPOP":"16—24 岁就业人口比", "F.LABOR.BACHELOR_UR":"25 岁以上本科及以上人群失业率",
  "F.LABOR.HS_UR":"25 岁以上高中学历人群失业率", "F.LABOR.JOLTS_OPENINGS":"JOLTS 非农职位空缺", "F.LABOR.JOLTS_HIRES":"JOLTS 非农招聘人数",
  "F.LABOR.JOLTS_QUITS":"JOLTS 非农主动离职人数", "F.LABOR.JOLTS_LAYOFFS":"JOLTS 非农裁员与解雇人数",
  "F.LABOR.INFO_OPENINGS":"信息业职位空缺", "F.LABOR.INFO_LAYOFFS":"信息业裁员与解雇", "F.LABOR.PROF_OPENINGS":"专业及商业服务业职位空缺",
  "F.LABOR.PROF_LAYOFFS":"专业及商业服务业裁员与解雇", "F.LABOR.INFO_EMPLOYMENT":"信息业就业人数", "F.LABOR.INFO_WAGES":"信息业平均时薪",
  "F.LABOR.PROF_EMPLOYMENT":"专业及商业服务业就业人数", "F.LABOR.PROF_WAGES":"专业及商业服务业平均时薪",
  "F.AI.BTOS_ADOPTION":"美国企业 AI 使用比例（BTOS）", "F.AI.OCC_EXPOSURE":"职业层面 AI 暴露评分",
  "F.EQUITY.SP500":"标普 500 指数", "F.EQUITY.NASDAQ":"纳斯达克综合指数", "F.EQUITY.VIX":"CBOE VIX 波动率指数", "F.USD.BROAD":"美元广义指数",
  "F.COMMODITY.WTI_DAILY":"WTI 原油现货价格（日频）", "F.COMMODITY.NATGAS":"Henry Hub 天然气现货价格", "F.COMMODITY.COPPER":"全球铜价",
  "F.ENERGY.CRUDE_STOCKS":"美国商业原油库存（不含战略储备）", "F.COMMODITY.BROAD_INDEX":"IMF 全球大宗商品价格指数",
};

const ZH_NODES = {
  "N.ACTIVITY.NOWCAST":"经济活动即时预测", "N.ACTIVITY.TAIL_RISK":"增长下行与衰退尾部风险", "N.INFLATION.DYNAMICS":"通胀持续性与短期方向",
  "N.INFLATION.ENERGY_PASS":"能源价格向通胀传导", "N.ENERGY.SHOCK":"WTI 能源价格冲击", "N.LABOR.STATE":"劳动力市场综合状态",
  "N.MONETARY.CONDITIONS":"利率曲线与金融条件", "N.FISCAL.SUPPLY":"国债供给与利率共变", "N.HOUSING.STATE_PANEL_FIXTURE":"州级住房—就业面板测试",
  "N.ACTIVITY.PRODUCTION":"生产与产出动量", "N.ACTIVITY.HOUSEHOLD_DEMAND":"居民需求与实际收入", "N.HOUSING.CYCLE":"利率敏感型住房周期",
  "N.LABOR.VACANCIES":"职位空缺与招聘需求", "N.LABOR.DISPLACEMENT":"裁员与劳动者置换压力", "N.LABOR.WAGE_ADJUSTMENT":"工资调整压力",
  "N.LABOR.COHORT_INCIDENCE":"青年与教育群体分化", "N.LABOR.AI_SECTORS":"AI 敏感行业劳动力表现", "N.AI.ADOPTION":"美国企业 AI 应用程度",
  "N.AI.COMPLEMENTARITY":"AI 应用与就业互补 / 替代关联", "N.AI.CAUSAL_PANEL":"AI 应用因果识别面板", "N.FIN.CREDIT":"信用利差与金融条件放大",
  "N.MONETARY.POLICY_EXPECTATIONS":"政策利率预期", "N.MONETARY.REAL_RATE":"实际利率与名义收益率分解", "N.MONETARY.LIQUIDITY":"流动性与金融条件",
  "N.INFLATION.EXPECTATIONS":"市场隐含通胀预期", "N.INFLATION.COMPENSATION":"通胀补偿分解", "N.INFLATION.DEMAND_PRESSURE":"需求敏感型通胀压力",
  "N.FISCAL.DEBT_TRAJECTORY":"联邦债务路径", "N.FISCAL.BALANCE":"联邦收支与融资流", "N.FISCAL.TERM_PREMIUM":"久期吸收与期限溢价",
  "N.EQUITY.PRICE_DIRECTION":"美国大盘股指短期方向", "N.EQUITY.VOLATILITY":"波动率与风险偏好", "N.EQUITY.DISCOUNT_RATE":"贴现率与美元传导",
  "N.COMMODITY.PRICE_DIRECTION":"美国能源与商品价格短期方向", "N.COMMODITY.SUPPLY_BALANCE":"美国能源实物供需平衡", "N.COMMODITY.MACRO_TRANSMISSION":"美元、利率与需求向商品价格传导",
  "N.FUTURES.TS_MOMENTUM":"期货时间序列动量", "N.COMMODITY.STORAGE_EQUILIBRIUM":"库存、储存与便利收益均衡", "N.COMMODITY.INVENTORY_BASIS":"库存、基差与风险溢价",
  "N.COMMODITY.OIL_TERM_STRUCTURE":"原油期货期限结构", "N.EQUITY.FOMC_EVENT":"FOMC 公告股票事件研究", "N.EQUITY.SECTOR_FORECAST":"美国行业收益预测",
};

const ZH_MECHANISMS = {
  "MECH.ACTIVITY.PRODUCTION":"生产与产出", "MECH.ACTIVITY.HOUSEHOLD_DEMAND":"居民需求与实际收入", "MECH.ACTIVITY.BROAD_STATE":"经济活动同步状态", "MECH.ACTIVITY.TAIL_RISK":"增长下行与衰退尾部",
  "MECH.LABOR.PAYROLL_STATE":"就业与失业状态", "MECH.LABOR.VACANCIES":"职位空缺与招聘需求", "MECH.LABOR.DISPLACEMENT":"裁员与劳动者置换", "MECH.LABOR.WAGES":"工资调整",
  "MECH.LABOR.COHORT":"青年与教育群体差异", "MECH.LABOR.AI_SENSITIVE_SECTORS":"AI 敏感行业表现", "MECH.AI.ADOPTION":"企业 AI 应用", "MECH.AI.OCCUPATIONAL_EXPOSURE":"职业任务 AI 暴露",
  "MECH.AI.SUBSTITUTION":"任务替代", "MECH.AI.COMPLEMENTARITY":"任务互补与岗位扩张", "MECH.AI.CAUSAL_IDENTIFICATION":"AI 应用到结果的因果识别",
  "MECH.INFLATION.PERSISTENCE":"通胀持续性", "MECH.INFLATION.EXPECTATIONS":"通胀预期", "MECH.MONETARY.CURVE":"收益率曲线与政策传导", "MECH.FINANCIAL.CREDIT":"信用条件放大",
  "MECH.HOUSING.CONSTRUCTION":"住房建设周期", "MECH.ENERGY.PRICE_SHOCK":"能源价格冲击", "MECH.FISCAL.SUPPLY":"国债供给与期限溢价", "MECH.TRADE.EXTERNAL_DEMAND":"外部需求与贸易价格",
  "MECH.MONETARY.POLICY_EXPECTATIONS":"政策利率预期", "MECH.MONETARY.REAL_RATE":"实际利率分解", "MECH.MONETARY.LIQUIDITY":"流动性与金融条件",
  "MECH.INFLATION.COMPENSATION":"通胀补偿分解", "MECH.INFLATION.DEMAND_PRESSURE":"需求敏感型价格压力", "MECH.FISCAL.DEBT_TRAJECTORY":"债务路径",
  "MECH.FISCAL.BALANCE":"联邦收支与融资流", "MECH.FISCAL.DURATION_ABSORPTION":"久期吸收与期限溢价", "MECH.EQUITY.PRICE_MOMENTUM":"美国大盘股指方向",
  "MECH.EQUITY.VOLATILITY_RISK":"波动率与风险偏好", "MECH.EQUITY.DISCOUNT_RATE":"贴现率与美元传导", "MECH.COMMODITY.SUPPLY_BALANCE":"能源实物供需平衡",
  "MECH.COMMODITY.DOLLAR_DEMAND":"美元、利率与实际需求传导", "MECH.FUTURES.PRICE_DIRECTION":"期货标的价格方向", "MECH.FUTURES.TREND_PREMIA":"波动率调整后的期货趋势溢价",
  "MECH.COMMODITY.STORAGE_CONVENIENCE_YIELD":"储存均衡与便利收益", "MECH.COMMODITY.INVENTORY_RISK_PREMIUM":"库存、基差与期货风险溢价", "MECH.COMMODITY.TERM_STRUCTURE":"原油期货期限结构",
  "MECH.EQUITY.MONETARY_ANNOUNCEMENT":"FOMC 意外信息传导", "MECH.EQUITY.RETURN_PREDICTABILITY":"行业收益递归预测",
};

const ZH_DATASETS = {
  "DS.BLS.CPI":"BLS 消费价格数据", "DS.BLS.LABOR":"BLS 就业与工资数据", "DS.BLS.CPS_DEMOGRAPHICS":"BLS 人口分组劳动力数据", "DS.BLS.JOLTS":"BLS JOLTS 职位流动数据",
  "DS.CENSUS.BTOS":"美国人口普查局企业趋势与展望调查", "DS.ONET.OCCUPATIONS":"美国劳工部 O*NET 职业数据", "DS.FRED.ACTIVITY":"FRED 经济活动数据",
  "DS.FRED.PCE":"FRED PCE 价格数据", "DS.FRED.RATES":"FRED 利率与金融条件数据", "DS.FRED.HOUSEHOLD":"FRED 居民与住房数据", "DS.FRED.CLAIMS":"FRED 失业救济申请数据",
  "DS.EIA.WTI":"EIA 原油价格与库存数据", "DS.TREASURY.DEBT":"美国财政部债务数据", "DS.FRED.STATE_PANEL":"FRED 州级面板数据", "DS.FRED.FISCAL":"FRED / OMB / BEA 财政数据",
  "DS.FRED.MARKETS":"FRED 美国金融市场数据", "DS.FRED.COMMODITIES":"FRED / EIA / IMF 大宗商品数据",
};

const ZH_MODELS = {
  "M.DFM_NOWCAST.V1":"动态因子 / 桥接即时预测", "M.PANEL_FE_FIXTURE.V1":"面板固定效应（真实数据测试）", "M.VAR_SYSTEM.V1":"VAR 系统与滚动样本外检验",
  "M.LOCAL_PROJECTION.V1":"Local Projection 事件研究（HAC 推断）", "M.GROWTH_AT_RISK.V1":"分位数增长风险模型", "M.UNIVARIATE_AR.V1":"单变量自回归基准",
  "M.BRIDGE_OLS.V1":"桥接 OLS 预测（HAC 推断）", "M.DAILY_MARKET_AR.V1":"日频市场自回归与滚动验证", "M.DAILY_MARKET_BRIDGE.V1":"日频市场桥接预测（HAC 推断）",
  "M.DAILY_MARKET_VAR.V1":"日频市场 VAR、滚动验证与脉冲响应",
  "Dynamic factor / bridge nowcast":"动态因子 / 桥接即时预测", "Panel fixed effects (real-data fixture)":"面板固定效应（真实数据测试）",
  "Registered VAR with rolling out-of-sample evaluation":"VAR 系统与滚动样本外检验", "Local projection event-study with HAC inference":"Local Projection 事件研究（HAC 推断）",
  "Quantile Growth-at-Risk":"分位数增长风险模型", "Registered univariate autoregressive benchmark":"单变量自回归基准",
  "Registered bridge OLS forecast with HAC inference":"桥接 OLS 预测（HAC 推断）", "Daily market autoregressive benchmark with rolling-origin validation":"日频市场自回归与滚动验证",
  "Daily market bridge forecast with registered drivers and HAC inference":"日频市场桥接预测（HAC 推断）", "Daily market VAR with rolling validation and ordering-based impulse responses":"日频市场 VAR、滚动验证与脉冲响应",
};

const ZH_TERMS = {
  CORE:"核心", SUPPORTING:"辅助", BACKGROUND:"背景", EXCLUDED:"排除", PRIMARY:"主要", SECONDARY:"辅助",
  PREDICTIVE:"预测证据", PREDICTIVE_BENCHMARK:"预测基准", PREDICTIVE_ASSOCIATION:"预测关联", PREDICTIVE_STRUCTURAL_PROXY:"预测性结构代理",
  DYNAMIC_ASSOCIATION:"动态关联", ASSOCIATIONAL:"关联性证据", ASSOCIATIONAL_FIXTURE:"关联性测试证据", TAIL_RISK_PREDICTIVE:"尾部风险预测",
  "Registered stationary transform":"已登记平稳化变换", "Registered factor not selected for this question.":"该因子已登记，但本次问题未选择。",
  "Identification design not yet activated":"识别设计尚未激活", "Pre-registered core specification.":"预先登记的核心模型设定。", "Pre-registered supporting specification.":"预先登记的辅助模型设定。",
  factor_variance:"因子解释方差", loadings:"因子载荷", residual_ljung_box:"残差 Ljung–Box 检验", rolling_oos_rmse:"滚动样本外 RMSE", ragged_edge:"非同步发布数据处理",
  within_r_squared:"组内 R²", cluster_count:"聚类数量", serial_correlation:"序列相关检验", cross_section_dependence:"截面相关检验", robust_covariance:"稳健协方差",
  stability_roots:"VAR 稳定根", portmanteau:"Portmanteau 残差检验", normality:"残差分布检验", irf:"脉冲响应", fevd:"预测误差方差分解",
  joint_pretrend:"联合前趋势检验", residual_autocorrelation:"残差自相关", placebo:"安慰剂检验", response_confidence_interval:"响应置信区间", effective_sample:"有效样本",
  quantile_crossing:"分位数交叉检验", pinball_loss:"Pinball 损失", rolling_oos_backtest:"滚动样本外回测", coverage:"区间覆盖率", density_integrity:"分布完整性",
  heteroskedasticity:"异方差检验", residual_distribution:"残差分布", reset:"RESET 设定检验", horizon_embargo:"预测期限隔离检查",
  forecast_fan:"预测扇形图", factor_loadings:"因子载荷图", actual:"实际值", fitted:"拟合值", forecast:"预测值", history:"历史值", lower95:"95% 下限", upper95:"95% 上限",
};

const ZH_SERIES = {
  UNRATE:"美国失业率", PAYEMS:"美国非农就业人数", CPIAUCSL:"美国整体 CPI", CPILFESL:"美国核心 CPI", PCEPI:"美国整体 PCE 价格指数", PCEPILFE:"美国核心 PCE 价格指数",
  GDPC1:"美国实际 GDP", INDPRO:"美国工业生产指数", DGS10:"10 年期美国国债收益率", DFF:"有效联邦基金利率", T10Y2Y:"10 年期—2 年期美国国债利差", BAMLH0A0HYM2:"美国高收益债期权调整利差",
};

const FALLBACK_DAILY_SOURCES = [
  { source_id: "FED", name: "美联储", kind: "政策与研究", description: "货币政策、监管公告与美联储研究", home_url: "https://www.federalreserve.gov/newsevents.htm", default_selected: true },
  { source_id: "BLS", name: "美国劳工统计局", kind: "宏观数据", description: "就业、工资、通胀与生产率", home_url: "https://www.bls.gov/bls/newsrels.htm", default_selected: true },
  { source_id: "SEC", name: "美国证券交易委员会", kind: "公司与市场", description: "资本市场监管与公司披露动态", home_url: "https://www.sec.gov/newsroom", default_selected: true },
  { source_id: "EIA", name: "美国能源信息署", kind: "能源与商品", description: "原油、天然气、电力与能源市场", home_url: "https://www.eia.gov/todayinenergy/", default_selected: true },
  { source_id: "NYFED", name: "纽约联储自由街经济学", kind: "金融市场", description: "金融条件、市场运行与联储研究", home_url: "https://libertystreeteconomics.newyorkfed.org/", default_selected: true },
  { source_id: "STLFED", name: "圣路易斯联储经济研究", kind: "机构研究", description: "美国经济、通胀、就业与金融市场研究", home_url: "https://www.stlouisfed.org/on-the-economy", default_selected: true },
  { source_id: "ATL_GDPNOW", name: "亚特兰大联储GDPNow", kind: "即时预测", description: "美国实际国内生产总值即时预测更新", home_url: "https://www.atlantafed.org/cqer/research/gdpnow", default_selected: true },
  { source_id: "ATL_MACROBLOG", name: "亚特兰大联储宏观经济博客", kind: "机构研究", description: "宏观经济、支付体系与金融研究", home_url: "https://www.atlantafed.org/blogs/macroblog", default_selected: true },
  { source_id: "CFTC", name: "美国商品期货交易委员会", kind: "期货监管", description: "期货、掉期、衍生品监管与市场动态", home_url: "https://www.cftc.gov/PressRoom", default_selected: true },
  { source_id: "CENSUS", name: "美国人口普查局经济指标", kind: "宏观数据", description: "零售、住房、制造业、贸易与企业活动指标", home_url: "https://www.census.gov/economic-indicators/", default_selected: true },
];

const FALLBACK_DAILY_PRODUCTS = [
  { report_type: "daily", label: "美国市场日报", short_label: "日报", description: "聚焦最近 72 小时的政策、数据与市场线索。", lookback_hours: 72 },
  { report_type: "weekly", label: "美国市场周报", short_label: "周报", description: "复盘一周核心变化与下周验证点。", lookback_hours: 168 },
  { report_type: "monthly", label: "美国市场月报", short_label: "月报", description: "汇总近一个月的政策、增长、通胀与资产定价变化。", lookback_hours: 744 },
  { report_type: "equity", label: "美国股票市场报告", short_label: "美股", description: "聚焦指数、行业、盈利预期与风险偏好。", lookback_hours: 168 },
  { report_type: "futures", label: "美国期货市场报告", short_label: "期货", description: "聚焦能源、金属、农产品与金融期货。", lookback_hours: 168 },
];

const DAILY_PRODUCT_SHORT_LABELS = {
  daily: "日报",
  weekly: "周报",
  monthly: "月报",
  equity: "美股",
  stocks: "美股",
  futures: "期货",
  commodity: "期货",
  policy: "政策专题",
};

const state = {
  dailyBrief: null,
  dailySources: [],
  dailyProducts: [],
  selectedDailySources: new Set(),
  selectedDailyProduct: "daily",
  dailyCatalogReady: false,
  dailyDomain: "全部",
  dailyView: "brief",
  selectedExcerpt: "",
  pdfDocument: null,
  health: null,
  dataStatus: null,
  examples: [],
  currentJob: null,
  graph: null,
  result: null,
  eventSource: null,
  refreshTimer: null,
  showDetail: false,
  zoom: 1,
  panX: 20,
  panY: 20,
  graphInitialized: false,
  layout: null,
  selectedNode: null,
  expandedNodes: new Set(),
  nodeDetail: null,
  activeTab: "overview",
  lastQuestion: "",
  drawerReturnFocus: null,
  historyReturnFocus: null,
  settingsCatalog: null,
  settingsStatus: null,
  assetGraph: null,
  dataPlugins: [],
  pluginCatalog: { akshare: [], fred: [] },
  dataZoom: .78,
  dataPanX: 18,
  dataPanY: 18,
  dataLayout: null,
  dataInitialized: false,
  dataFocusOnly: false,
  dataItems: new Map(),
  selectedProvider: "deepseek",
  settingsReturnFocus: null,
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function pretty(value) {
  const raw = String(value ?? "—");
  return DISPLAY_LABELS[raw] || raw.replaceAll("_", " ");
}

function knownRegistryKey(value, dictionary) {
  const raw = String(value ?? "");
  if (dictionary[raw]) return raw;
  return Object.keys(dictionary).find((key) => raw.includes(key)) || null;
}

function zhLane(value) {
  const key = knownRegistryKey(value, ZH_LANES);
  return key ? ZH_LANES[key] : pretty(value);
}

function zhFactor(value) {
  const key = knownRegistryKey(value, ZH_FACTORS);
  return key ? ZH_FACTORS[key] : null;
}

function zhDataset(value) {
  const key = knownRegistryKey(value, ZH_DATASETS);
  return key ? ZH_DATASETS[key] : null;
}

function zhModel(value) {
  const key = knownRegistryKey(value, ZH_MODELS);
  return key ? ZH_MODELS[key] : null;
}

function zhText(value, fallback = null) {
  if (value == null || value === "") return fallback ?? "—";
  const raw = String(value);
  if (ZH_TERMS[raw]) return ZH_TERMS[raw];
  return zhFactor(raw) || zhDataset(raw) || zhModel(raw) || (ZH_MECHANISMS[knownRegistryKey(raw, ZH_MECHANISMS)] || null) || (ZH_NODES[knownRegistryKey(raw, ZH_NODES)] || null) || (ZH_LANES[knownRegistryKey(raw, ZH_LANES)] || null) || DISPLAY_LABELS[raw] || fallback || raw;
}

function chineseOr(value, fallback) {
  if (value == null || value === "") return fallback;
  const raw = String(value);
  const translated = zhText(raw);
  if (translated !== raw || /[\u3400-\u9fff]/.test(raw)) return translated;
  return fallback;
}

function graphNodeLabel(node) {
  const nodeId = node?.node_id || "";
  const metadata = node?.metadata || {};
  const factor = zhFactor(metadata.factor_id || nodeId);
  const dataset = zhDataset(metadata.dataset_id || nodeId);
  const researchKey = knownRegistryKey(metadata.node_id || metadata.research_node_id || nodeId, ZH_NODES);
  const mechanismKey = knownRegistryKey(metadata.mechanism_id || nodeId, ZH_MECHANISMS);
  const model = zhModel(metadata.model_recipe_id || metadata.recipe_id || node.label || nodeId);
  if (node.node_type === "QUESTION") return "原始研究问题";
  if (node.node_type === "QUERY") return "结构化研究问题与期限";
  if (node.node_type === "RESEARCH_DEPTH_GATE") return "研究深度与证据覆盖检查";
  if (node.node_type === "LANE") return zhLane(node.lane_id || nodeId);
  if (node.node_type === "MECHANISM") return mechanismKey ? ZH_MECHANISMS[mechanismKey] : "经济传导机制";
  if (node.node_type === "RESEARCH_NODE") return researchKey ? ZH_NODES[researchKey] : "中间研究任务";
  if (node.node_type === "FACTOR") return factor || "已登记实证因子";
  if (node.node_type === "DATASET") return dataset || zhText(node.label, "已登记数据集");
  if (node.node_type === "TRANSFORM") return `${factor || "数据序列"}：平稳化与频率变换`;
  if (node.node_type === "MODEL_SPECIFICATION") return `${researchKey ? ZH_NODES[researchKey] : "研究节点"}：${model || "已登记模型设定"}`;
  if (node.node_type === "MODEL_RUN") return model || `${researchKey ? ZH_NODES[researchKey] : "研究节点"}：模型运行`;
  if (node.node_type === "DIAGNOSTIC") return `${model || "模型"}：方法专属诊断`;
  if (node.node_type === "EVIDENCE") return `${researchKey ? ZH_NODES[researchKey] : "模型"}：结构化证据`;
  if (node.node_type === "CLAIM") return `${researchKey ? ZH_NODES[researchKey] : "研究节点"}：中间判断`;
  if (node.node_type === "LANE_SIGNAL") return `${zhLane(node.lane_id)}：通道结论`;
  if (node.node_type === "AGGREGATION") return "跨通道证据综合";
  if (node.node_type === "FINAL_CLAIM") return "最终研究结论";
  if (node.node_type === "FALSIFIER") return "证伪条件";
  return zhText(node.label, pretty(node.node_type));
}

function zhUnit(value) {
  const map = { index:"指数", percent:"%", thousands:"千人", count:"人数", binary:"0/1 指示变量", usd:"美元", usd_per_hour:"美元 / 小时", usd_per_barrel:"美元 / 桶", billions_chained_2017_usd:"十亿美元（2017 年不变价）", millions_usd:"百万美元", thousands_saar:"千套（季调年率）" };
  return map[value] || value || "—";
}

function zhFrequency(value) {
  return ({ D:"日频", W:"周频", M:"月频", Q:"季频", A:"年频", BIWEEKLY:"双周频", RELEASE:"随版本发布", daily:"日频", weekly:"周频", monthly:"月频", quarterly:"季频" })[value] || value || "—";
}

function zhReleaseLag(value) {
  const raw = String(value || "");
  if (!raw) return "—";
  if (/BLS JOLTS/i.test(raw)) return "按 BLS JOLTS 发布日历";
  if (/BLS/i.test(raw)) return "按 BLS 发布日历";
  if (/BEA/i.test(raw)) return "按 BEA 发布日历";
  if (/Census/i.test(raw)) return "按美国人口普查局发布日历";
  if (/Federal Reserve|Chicago Fed/i.test(raw)) return "按美联储发布日历";
  if (/NBER/i.test(raw)) return "由 NBER 事后认定";
  if (/daily/i.test(raw)) return "每日发布";
  if (/weekly/i.test(raw)) return "每周发布";
  if (/quarterly/i.test(raw)) return "每季度发布";
  if (/varies/i.test(raw)) return "随数据来源变化";
  return chineseOr(raw, "按数据源发布日历");
}

const ZH_JSON_KEYS = {
  status:"状态", note:"说明", method:"方法", result:"结果", results:"结果", sample:"样本", start:"开始日期", end:"结束日期", observations:"观测数", frequency:"频率",
  parameters:"参数", values:"参数值", source:"来源", factor_ids:"因子", factor_pool:"候选因子", dataset_id:"数据集", dataset_dependencies:"依赖数据集", model_recipe_id:"模型配方",
  diagnostics:"诊断", robustness:"稳健性", warnings:"警告", limitations:"限制", report_ids:"来源研报", report_evidence:"研报页码证据", data_lineage:"数据沿革",
  code_artifact:"代码制品", registry_version:"注册表版本", statistic:"统计量", p_value:"p-value", interpretation:"解释", credibility_impact:"对可信度的影响",
  rolling_oos:"滚动样本外检验", rmse:"RMSE", mae:"MAE", horizon:"预测期限", lags:"滞后阶数", covariance:"协方差估计", fixed_effects:"固定效应",
};

function localizedStructured(value) {
  if (Array.isArray(value)) return value.map(localizedStructured);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [ZH_JSON_KEYS[key] || key, localizedStructured(item)]));
  if (typeof value === "string") return zhText(value);
  return value;
}

function formatNumber(value, digits = 4) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  if (Math.abs(number) >= 1000) return number.toLocaleString(undefined, { maximumFractionDigits: 1 });
  return number.toLocaleString(undefined, { maximumFractionDigits: digits });
}

async function api(url, options = {}) {
  const response = await fetch(apiUrl(url), options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `HTTP ${response.status}`);
  }
  return response.json();
}

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove("show"), 2600);
}

function readHistory() {
  try { return JSON.parse(localStorage.getItem("macrotrace.history") || "[]"); }
  catch { return []; }
}

function rememberJob(job, question = state.lastQuestion) {
  const items = readHistory().filter((item) => item.job_id !== job.job_id);
  items.unshift({ job_id: job.job_id, question: question || job.question || "实证研究", status: job.status, created_at: job.created_at || new Date().toISOString() });
  localStorage.setItem("macrotrace.history", JSON.stringify(items.slice(0, 20)));
  localStorage.setItem("macrotrace.currentJob", job.job_id);
  const url = new URL(window.location.href);
  url.searchParams.set("job", job.job_id);
  window.history.replaceState(null, "", url);
  renderHistory();
}

function renderHistory() {
  const items = readHistory();
  $("#historyList").innerHTML = items.length ? items.map((item) => `
    <button class="history-item" type="button" data-job-id="${escapeHtml(item.job_id)}">
      <span><i>${escapeHtml(pretty(item.status))}</i><time>${escapeHtml(String(item.created_at).slice(0, 16).replace("T", " "))}</time></span>
      <strong>${escapeHtml(item.question)}</strong>
    </button>`).join("") : `<div class="history-item"><strong>还没有本地研究任务。</strong></div>`;
}

async function boot() {
  document.body.dataset.workspaceMode = "empty";
  renderHistory();
  loadDailyBriefCatalog()
    .then(() => loadDailyBrief())
    .catch((error) => renderDailyBriefError(error.message));
  try {
    const [health, dataStatus, examples] = await Promise.all([api("/v1/health"), api("/v1/data/status"), api("/v1/examples")]);
    state.health = health;
    state.dataStatus = dataStatus;
    state.examples = examples.questions;
    $("#healthPulse").classList.add("live");
    $("#healthText").textContent = health.database_ready ? "系统就绪" : "需要同步数据";
    $("#seriesCount").textContent = `${dataStatus.series_count} 条序列`;
    const latest = dataStatus.series.map((item) => item.last_period).filter(Boolean).sort().at(-1);
    $("#dataFreshness").textContent = dataStatus.ready ? `${dataStatus.series_count} 条真实序列 / 最近更新 ${String(latest || "—").slice(0, 10)}` : "真实数据仓库为空";
    renderExamples();
    await loadConnectionSettings().catch((error) => {
      $("#providerSetupLabel").textContent = "API 配置中心暂不可用";
      console.warn("Local provider settings unavailable:", error.message);
    });
    await loadDataEvidenceCatalog().catch((error) => {
      console.warn("ResearchOS data layer unavailable:", error.message);
    });
  } catch (error) {
    $("#healthPulse").classList.add("fail");
    $("#healthText").textContent = "离线";
    $("#dataFreshness").textContent = error.message;
  }
  const saved = new URLSearchParams(window.location.search).get("job") || localStorage.getItem("macrotrace.currentJob");
  if (saved) {
    try { await loadJob(saved, true); }
    catch { localStorage.removeItem("macrotrace.currentJob"); }
  }
}

function dailyProductSpec(reportType = state.selectedDailyProduct) {
  return state.dailyProducts.find((product) => product.report_type === reportType)
    || FALLBACK_DAILY_PRODUCTS.find((product) => product.report_type === reportType)
    || FALLBACK_DAILY_PRODUCTS[0];
}

function dailyProductShortLabel(product) {
  return product.short_label || DAILY_PRODUCT_SHORT_LABELS[product.report_type] || product.label || "研究报告";
}

function readSavedDailySources() {
  try {
    const raw = localStorage.getItem("macrotrace.dailySources.v2");
    if (raw === null) return null;
    const saved = JSON.parse(raw);
    return Array.isArray(saved) ? saved.map(String) : null;
  } catch {
    return null;
  }
}

function renderDailySourcePicker() {
  const container = $("#dailySourcePickerList");
  if (!container) return;
  const selected = state.selectedDailySources;
  container.innerHTML = state.dailySources.length
    ? state.dailySources.map((source) => {
        const checked = selected.has(source.source_id);
        const registryId = source.source_id.split("::").slice(1).join("::");
        const localDisplayName = source.source_id.startsWith("FACTOR::")
          ? zhFactor(registryId)
          : source.source_id.startsWith("DATASET::")
            ? zhDataset(registryId)
            : source.source_id.startsWith("SERIES::")
              ? (ZH_SERIES[registryId] || registryId)
              : source.name;
        const displayName = source.name_zh || source.display_name || source.name || localDisplayName;
        return `<label class="daily-source-option ${checked ? "selected" : ""}">
          <input type="checkbox" data-daily-source="${escapeHtml(source.source_id)}" ${checked ? "checked" : ""}>
          <span class="daily-source-check" aria-hidden="true"></span>
          <span class="daily-source-copy">
            <span><strong>${escapeHtml(displayName)}</strong><small>${escapeHtml(source.kind || "公开研究来源")}</small></span>
            <p>${escapeHtml(source.description || "美国公开信息与研究更新")}</p>
          </span>
          ${source.home_url ? `<a href="${escapeHtml(source.home_url)}" target="_blank" rel="noopener noreferrer" aria-label="打开${escapeHtml(displayName)}官方网站">官网 ↗</a>` : ""}
        </label>`;
      }).join("")
    : `<p class="daily-source-loading">暂时没有可选来源。</p>`;
  const count = $("#dailySelectedSourceCount");
  if (count) count.textContent = String(selected.size);
  const total = $("#dailySourceTotal");
  if (total) total.textContent = `${state.dailySources.length} 个已登记来源`;
}

function renderDailyProductList() {
  const container = $("#dailyProductList");
  if (!container) return;
  container.innerHTML = state.dailyProducts.map((product) => {
    const selected = product.report_type === state.selectedDailyProduct;
    const lookbackDays = Math.max(1, Math.round(Number(product.lookback_hours || 24) / 24));
    return `<button type="button" class="daily-product-option ${selected ? "selected" : ""}" data-daily-product="${escapeHtml(product.report_type)}" role="radio" aria-checked="${selected}">
      <span>${escapeHtml(dailyProductShortLabel(product))}</span>
      <strong>${escapeHtml(product.label || dailyProductShortLabel(product))}</strong>
      <p>${escapeHtml(product.description || "按已勾选来源生成可追溯研究报告。")}</p>
      <small>回看 ${lookbackDays} 天</small>
    </button>`;
  }).join("");
  const button = $("#refreshDailyBrief span");
  if (button) button.textContent = `生成${dailyProductShortLabel(dailyProductSpec())}`;
}

async function loadDailyBriefCatalog() {
  let catalog;
  try {
    catalog = await api("/v1/daily-brief/sources");
  } catch (error) {
    console.warn("研究来源目录暂不可用，使用本地登记目录：", error.message);
    catalog = { sources: FALLBACK_DAILY_SOURCES, report_products: FALLBACK_DAILY_PRODUCTS };
  }
  state.dailySources = Array.isArray(catalog.sources) && catalog.sources.length ? catalog.sources : FALLBACK_DAILY_SOURCES;
  const remoteProducts = Array.isArray(catalog.report_products) ? catalog.report_products : [];
  const byType = new Map(FALLBACK_DAILY_PRODUCTS.map((product) => [product.report_type, product]));
  remoteProducts.forEach((product) => byType.set(product.report_type, { ...byType.get(product.report_type), ...product }));
  state.dailyProducts = [...byType.values()];

  const availableSourceIds = new Set(state.dailySources.map((source) => source.source_id));
  const storedSources = readSavedDailySources();
  const savedSources = storedSources?.filter((sourceId) => availableSourceIds.has(sourceId)) || [];
  const defaultSources = state.dailySources.filter((source) => source.default_selected !== false).map((source) => source.source_id);
  state.selectedDailySources = new Set(storedSources === null ? defaultSources : savedSources);

  const savedProduct = localStorage.getItem("macrotrace.dailyProduct") || "daily";
  state.selectedDailyProduct = state.dailyProducts.some((product) => product.report_type === savedProduct) ? savedProduct : "daily";
  state.dailyCatalogReady = true;
  renderDailySourcePicker();
  renderDailyProductList();
}

function renderDailyBriefError(message) {
  $("#dailyBriefHeadline").textContent = "日报暂时无法读取";
  $("#dailyBriefSummary").textContent = message || "请确认本地服务已启动。";
  $("#dailyBriefCards").innerHTML = `<article class="daily-empty"><strong>日报不会使用虚构内容</strong><p>来源恢复后再刷新；研究工作台仍可独立使用。</p></article>`;
}

async function loadDailyBrief(refresh = false) {
  const button = $("#refreshDailyBrief");
  if (refresh && state.selectedDailySources.size === 0) {
    throw new Error("请至少勾选一个研究来源。 ");
  }
  const product = dailyProductSpec();
  button.disabled = true;
  button.querySelector("span").textContent = refresh ? `正在生成${dailyProductShortLabel(product)}…` : "正在读取最近报告…";
  try {
    state.dailyBrief = await api(
      refresh ? "/v1/daily-brief/refresh" : "/v1/daily-brief",
      refresh ? {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report_type: state.selectedDailyProduct,
          source_ids: [...state.selectedDailySources],
        }),
      } : {},
    );
    renderDailyBrief();
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = `生成${dailyProductShortLabel(dailyProductSpec())}`;
  }
}

function dailyItems() {
  const items = state.dailyBrief?.items || [];
  return state.dailyDomain === "全部" ? items : items.filter((item) => item.domain === state.dailyDomain);
}

function hasDailyValue(value) {
  if (Array.isArray(value)) return value.some(hasDailyValue);
  if (value && typeof value === "object") return Object.values(value).some(hasDailyValue);
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function dailyText(value) {
  if (!hasDailyValue(value)) return "";
  if (Array.isArray(value)) return value.map(dailyText).filter(Boolean).join("；");
  if (value && typeof value === "object") {
    const preferred = [
      value.text, value.label, value.name, value.title, value.description,
      value.expression, value.instrument, value.asset, value.ticker, value.value,
    ].map(dailyText).filter(Boolean);
    if (preferred.length) return [...new Set(preferred)].join(" · ");
    return Object.values(value).map(dailyText).filter(Boolean).join(" · ");
  }
  return String(value).replace(/\s+/g, " ").trim();
}

function dailyList(value) {
  if (!hasDailyValue(value)) return [];
  const values = Array.isArray(value) ? value : [value];
  return values.flatMap((entry) => {
    if (entry && typeof entry === "object") {
      const text = dailyText(entry);
      return text ? [text] : [];
    }
    return String(entry)
      .split(/\r?\n|\s*[;；]\s*/)
      .map((text) => text.replace(/^[-•·\d.)、\s]+/, "").trim())
      .filter(Boolean);
  });
}

function dailyStance(value) {
  const raw = dailyText(value);
  const normalized = raw.toLowerCase().replaceAll("_", " ");
  if (/减持|卖出|做空|看空|降低仓位|underweight|\bsell\b|\bshort\b|bearish|risk\s*off/.test(normalized)) {
    return { label: "减持", tone: "decrease", raw };
  }
  if (/增持|买入|做多|看多|提高仓位|overweight|\bbuy\b|\blong\b|bullish|risk\s*on/.test(normalized)) {
    return { label: "增持", tone: "increase", raw };
  }
  return { label: "观望", tone: "watch", raw };
}

function dailyEvidenceRefs(item) {
  const values = [
    ...(Array.isArray(item.source_refs) ? item.source_refs : hasDailyValue(item.source_refs) ? [item.source_refs] : []),
    ...(Array.isArray(item.evidence_refs) ? item.evidence_refs : hasDailyValue(item.evidence_refs) ? [item.evidence_refs] : []),
  ];
  if (hasDailyValue(item.source_name) || hasDailyValue(item.url)) {
    values.push({
      source_name: item.source_name,
      title: item.source_title || item.headline || item.title,
      url: item.url,
      published_at: item.published_at,
      source_id: item.source_id,
    });
  }
  const seen = new Set();
  return values.map((entry) => {
    if (entry && typeof entry === "object") {
      const label = dailyText(entry.source_name || entry.institution || entry.name || entry.label || entry.source_id || entry.ref_id || "证据来源");
      const title = dailyText(entry.title || entry.headline || entry.description || entry.note || entry.text);
      const url = dailyText(entry.url || entry.href || entry.source_url);
      const publishedAt = dailyText(entry.published_at || entry.date || entry.as_of);
      return { label, title: title === label ? "" : title, url, publishedAt };
    }
    const text = dailyText(entry);
    return /^https?:\/\//i.test(text)
      ? { label: "证据来源", title: "", url: text, publishedAt: "" }
      : { label: text || "证据来源", title: "", url: "", publishedAt: "" };
  }).filter((ref) => {
    const key = ref.url || `${ref.label}|${ref.title}`;
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function dailyOpinionModel(item) {
  const hasOpinionContract = [
    item.stance, item.action, item.asset_expression, item.horizon, item.thesis,
    item.catalysts, item.invalidation, item.kill_criteria, item.confidence,
    item.source_refs, item.evidence_refs,
  ].some(hasDailyValue);
  const stance = dailyStance(item.stance || item.action);
  const legacyHeadline = dailyText(item.headline || item.title);
  const thesis = dailyText(item.thesis || item.investment_thesis || item.viewpoint || item.recommendation || (hasOpinionContract ? legacyHeadline : ""));
  const legacyMeaning = dailyText(item.significance || item.market_implication);
  let title = thesis || (legacyMeaning ? `待验证观点｜${legacyMeaning}` : "待验证观点｜当前材料是否足以改变组合仓位？");
  if (hasOpinionContract && stance.label !== "观望" && !/增持|减持|买入|卖出|做多|做空|看多|看空|观望/.test(title)) {
    title = `${stance.label}｜${title}`;
  }
  const rawAction = stance.raw && stance.raw !== stance.label ? stance.raw : "";
  const assetExpression = dailyText(
    item.asset_expression || item.trade_expression || item.instrument || item.asset || item.ticker || (rawAction.length > 4 ? rawAction : ""),
  ) || "未指定具体表达工具";
  const horizon = dailyText(item.horizon || item.time_horizon || item.holding_period) || "期限待确认";
  const logic = dailyText(item.rationale || item.logic || item.thesis_summary || (hasOpinionContract ? item.summary : legacyMeaning))
    || "当前材料尚未形成完整投资逻辑，需先验证事实与资产价格之间的传导。";
  const catalysts = dailyList(item.catalysts || item.triggers || item.watch_points);
  const invalidation = dailyList(item.invalidation || item.kill_criteria || item.falsifiers || item.risks);
  const evidenceSummary = dailyText(item.evidence_summary || item.fact_summary || item.source_summary || (!hasOpinionContract ? item.summary : ""));
  const confidence = dailyText(item.confidence || item.conviction);
  return {
    hasOpinionContract,
    stance,
    title,
    assetExpression,
    horizon,
    logic,
    catalysts,
    invalidation,
    confidence,
    evidenceSummary,
    legacyHeadline,
    empiricalQuestion: dailyText(item.empirical_question || item.research_question),
    evidenceRefs: dailyEvidenceRefs(item),
  };
}

function renderDailyList(items, emptyText) {
  return items.length
    ? `<ul>${items.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul>`
    : `<p class="daily-viewpoint-empty">${escapeHtml(emptyText)}</p>`;
}

function renderDailyEvidence(model) {
  const context = [model.legacyHeadline, model.evidenceSummary].filter(Boolean);
  const contextHtml = context.length
    ? `<div class="daily-fact-context"><span>事实背景</span>${context.map((text) => `<p>${escapeHtml(text)}</p>`).join("")}</div>`
    : "";
  const refs = model.evidenceRefs.length
    ? model.evidenceRefs
    : [{ label: "本期来源状态", title: "当前条目没有提供可点击的独立引用。", url: "", publishedAt: "" }];
  return `${contextHtml}<div class="daily-evidence-block"><span>证据来源</span><ol>${refs.map((ref, index) => `
    <li><sup>[${index + 1}]</sup><div>
      ${ref.url ? `<a href="${escapeHtml(ref.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(ref.label)} ↗</a>` : `<strong>${escapeHtml(ref.label)}</strong>`}
      ${ref.title ? `<p>${escapeHtml(ref.title)}</p>` : ""}
      ${ref.publishedAt ? `<time>${escapeHtml(ref.publishedAt.slice(0, 16).replace("T", " "))}</time>` : ""}
    </div></li>`).join("")}</ol></div>`;
}

function renderDailyBrief() {
  const brief = state.dailyBrief;
  if (!brief) return;
  if (state.dailyView === "pdf" && state.pdfDocument) {
    renderPdfDocument();
    return;
  }
  const reportLabel = brief.report_label || dailyProductSpec(brief.report_type).label || "美国市场研究报告";
  if ($("#dailyReaderModeLabel")) $("#dailyReaderModeLabel").textContent = reportLabel;
  $("#dailyPaperMarket").textContent = reportLabel;
  $("#backToDailyBrief").classList.add("hidden");
  $("#dailyBriefDate").textContent = brief.as_of_label || "最近可获取信息";
  $("#dailyBriefHeadline").textContent = brief.investment_outlook || brief.headline || "本期投资观点";
  $("#dailyBriefSummary").textContent = brief.summary || "";
  const domains = ["全部", ...new Set((brief.items || []).map((item) => item.domain || "综合市场"))];
  if (!domains.includes(state.dailyDomain)) state.dailyDomain = "全部";
  $("#dailyDomainFilters").innerHTML = domains.map((domain) => `<button type="button" data-daily-domain="${escapeHtml(domain)}" class="${domain === state.dailyDomain ? "active" : ""}">${escapeHtml(domain)}</button>`).join("");
  const items = dailyItems();
  const sourceKeys = new Set(items.flatMap((item) => dailyEvidenceRefs(item).map((ref) => ref.url || ref.label)).filter(Boolean));
  $("#dailyBriefMeta").textContent = `${items.length} 条投资观点 · ${sourceKeys.size} 个引用来源`;
  const groups = [...new Set(items.map((item) => item.domain || "综合市场"))];
  $("#dailyBriefCards").innerHTML = items.length ? groups.map((domain, groupIndex) => {
    const rows = items.filter((item) => (item.domain || "综合市场") === domain);
    return `<section class="daily-report-section" data-domain="${escapeHtml(domain)}">
      <header><span>${String(groupIndex + 1).padStart(2, "0")}</span><h3>${escapeHtml(domain)}</h3></header>
      ${rows.map((item, index) => {
        const model = dailyOpinionModel(item);
        const confidence = model.confidence ? `<span class="daily-confidence">置信度 ${escapeHtml(model.confidence)}</span>` : "";
        return `<article class="daily-report-item daily-viewpoint" data-index="${String(index + 1).padStart(2, "0")}" data-daily-item="${escapeHtml(item.item_id || `${groupIndex}-${index}`)}">
          <div class="daily-viewpoint-meta">
            <span class="daily-stance" data-stance="${model.stance.tone}">${escapeHtml(model.stance.label)}</span>
            <span class="daily-horizon">期限 · ${escapeHtml(model.horizon)}</span>
            ${confidence}
          </div>
          <h4>${escapeHtml(model.title)}</h4>
          <div class="daily-expression"><span>表达工具</span><strong>${escapeHtml(model.assetExpression)}</strong></div>
          <div class="daily-viewpoint-grid">
            <section class="daily-logic"><span>投资逻辑</span><p>${escapeHtml(model.logic)}</p></section>
            <section><span>关键催化剂</span>${renderDailyList(model.catalysts, "当前材料未单列催化剂。")}</section>
            <section class="daily-kill"><span>反证 / 失效条件</span>${renderDailyList(model.invalidation, "当前材料未单列反证条件；进入实证前需补充。")}</section>
          </div>
          ${model.empiricalQuestion ? `<aside class="daily-empirical-question"><span>可进入实证研究</span><p>${escapeHtml(model.empiricalQuestion)}</p></aside>` : ""}
          ${renderDailyEvidence(model)}
        </article>`;
      }).join("")}
    </section>`;
  }).join("") : `<article class="daily-empty"><strong>这个分类暂时没有投资观点</strong><p>切换分类或重新生成报告。</p></article>`;
  $("#dailyBriefLimitations").innerHTML = normalizeTextList(brief.limitations).map((item) => `<span>${escapeHtml(item)}</span>`).join("");
}

function placeResearchQuestion(question) {
  $("#questionInput").value = question;
  $("#charCount").textContent = `${question.length} / 4000`;
  state.lastQuestion = question;
  $("#researchForm").scrollIntoView({ behavior: "smooth", block: "center" });
  $("#questionInput").focus({ preventScroll: true });
}

async function compileSelectedExcerpt() {
  const excerpt = state.selectedExcerpt.trim();
  if (excerpt.length < 8) return;
  const button = $("#selectionResearchButton");
  button.disabled = true;
  button.textContent = "正在编译研究问题…";
  try {
    const result = await api("/v1/daily-brief/research-question", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ excerpt }),
    });
    placeResearchQuestion(result.question);
    window.getSelection()?.removeAllRanges();
    $("#selectionToolbar").classList.add("hidden");
    toast("选中的观点已编译为完整研究问题，可直接开始实证。 ");
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "进入实证研究 →";
  }
}

function showSelectionAction() {
  const selection = window.getSelection();
  const paper = $("#dailyBriefDocument");
  const excerpt = String(selection || "").replace(/\s+/g, " ").trim().slice(0, 1800);
  const anchor = selection?.anchorNode;
  const focus = selection?.focusNode;
  const toolbar = $("#selectionToolbar");
  if (excerpt.length < 8 || !anchor || !focus || !paper.contains(anchor) || !paper.contains(focus) || !selection.rangeCount) {
    toolbar.classList.add("hidden");
    return;
  }
  state.selectedExcerpt = excerpt;
  const rect = selection.getRangeAt(0).getBoundingClientRect();
  toolbar.style.left = `${Math.min(window.innerWidth - 115, Math.max(115, rect.left + rect.width / 2))}px`;
  toolbar.style.top = `${Math.max(80, rect.top - 9)}px`;
  toolbar.classList.remove("hidden");
}

function renderPdfDocument() {
  const documentData = state.pdfDocument;
  if ($("#dailyReaderModeLabel")) $("#dailyReaderModeLabel").textContent = "本地研报阅读器";
  $("#dailyPaperMarket").textContent = "本地文件 · 只在内存中读取";
  $("#dailyBriefDate").textContent = `${documentData.page_count} 页 PDF`;
  $("#dailyBriefHeadline").textContent = documentData.filename;
  $("#dailyBriefSummary").textContent = `已提取 ${documentData.pages.length} 页可选择文字。拖动选中一句或几段，即可编译为美国市场实证研究问题；原文件不会保存到本地数据仓库。`;
  $("#dailyDomainFilters").innerHTML = "";
  $("#dailyBriefMeta").textContent = `${documentData.pages.length} 页可选文字`;
  $("#backToDailyBrief").classList.remove("hidden");
  $("#dailyBriefCards").innerHTML = documentData.pages.map((page) => `<section class="pdf-page"><span>第 ${page.page} 页</span><p>${escapeHtml(page.text)}</p></section>`).join("");
  $("#dailyBriefLimitations").innerHTML = `<span>扫描图片型 PDF 暂不进行 OCR；当前只显示成功提取的文字页。</span>`;
}

async function readPdfFile(file) {
  if (!file) return;
  if (file.size > 20 * 1024 * 1024) {
    toast("PDF 不能超过 20 MB。 ");
    return;
  }
  $("#dailyBriefCards").innerHTML = `<div class="daily-uploading">正在读取 ${escapeHtml(file.name)}…</div>`;
  const form = new FormData();
  form.append("file", file);
  try {
    state.pdfDocument = await api("/v1/documents/read-pdf", { method: "POST", body: form });
    state.dailyView = "pdf";
    renderPdfDocument();
  } catch (error) {
    renderDailyBrief();
    toast(error.message);
  } finally {
    $("#dailyPdfInput").value = "";
  }
}

async function loadDataEvidenceCatalog() {
  const safe = async (path, fallback) => {
    try { return await api(path); }
    catch { return fallback; }
  };
  const [plugins, workspaces, fred] = await Promise.all([
    safe("/api/v1/data-plugins", []),
    safe("/api/v1/workspaces", []),
    safe("/api/v1/data-plugins/fred/datasets?limit=100", []),
  ]);
  // MacroTrace's public product boundary is now United States only. Keep the
  // AKShare adapter available to other ResearchOS roles, but never mix its
  // China catalogue into the US evidence universe rendered here.
  state.dataPlugins = plugins.filter((plugin) => plugin.plugin_id !== "akshare");
  state.pluginCatalog = { akshare: [], fred };
  state.assetGraph = workspaces.length
    ? await safe(`/api/v1/workspaces/${encodeURIComponent(workspaces[0].id)}/ontology/graph`, null)
    : null;
  renderDataEvidenceLayer();
}

function renderExamples() {
  $("#exampleQuestions").innerHTML = state.examples.map((question, index) => `<button type="button" data-example="${index}" title="${escapeHtml(question)}">${String(index + 1).padStart(2, "0")} · ${escapeHtml(question.slice(0, 22))}${question.length > 22 ? "…" : ""}</button>`).join("");
}

function setWorkspaceMode(mode) {
  document.body.dataset.workspaceMode = mode;
  $("#emptyState").classList.toggle("hidden", mode !== "empty");
  $("#errorState").classList.toggle("hidden", mode !== "error");
  $("#workspace").classList.toggle("hidden", mode === "empty" || mode === "error");
  $("#jobStrip").classList.toggle("hidden", mode === "empty");
}

async function submitResearch(event) {
  event?.preventDefault();
  const question = $("#questionInput").value.trim();
  if (!question) return;
  state.lastQuestion = question;
  closeEventSource();
  state.graph = null;
  state.result = null;
  state.expandedNodes = new Set();
  state.graphInitialized = false;
  state.dataZoom = .78;
  state.dataPanX = 18;
  state.dataPanY = 18;
  state.dataInitialized = false;
  $("#runButton").disabled = true;
  setWorkspaceMode("running");
  $("#conclusionCard").classList.add("hidden");
  $("#researchReport").classList.add("hidden");
  try {
    const job = await api("/v1/research-jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, display_mode: "ACADEMIC" }),
    });
    state.currentJob = job;
    rememberJob(job, question);
    updateJobStrip(job);
    connectEvents(job.job_id);
    await refreshJob(job.job_id);
  } catch (error) {
    showError("无法创建研究任务", error.message);
  } finally {
    $("#runButton").disabled = false;
  }
}

async function loadJob(jobId, resumed = false) {
  closeEventSource();
  const job = await api(`/v1/research-jobs/${encodeURIComponent(jobId)}`);
  state.currentJob = job;
  state.lastQuestion = job.question;
  $("#questionInput").value = job.question;
  $("#charCount").textContent = `${job.question.length} / 4000`;
  rememberJob(job, job.question);
  setWorkspaceMode("running");
  updateJobStrip(job);
  await refreshJob(jobId);
  if (!TERMINAL.has(job.status)) connectEvents(jobId);
  if (resumed) toast(`已恢复任务 ${jobId}`);
}

function connectEvents(jobId) {
  closeEventSource();
  const source = new EventSource(apiUrl(`/v1/research-jobs/${encodeURIComponent(jobId)}/events`));
  state.eventSource = source;
  const handler = () => scheduleRefresh(jobId);
  source.addEventListener("job_progress", handler);
  source.addEventListener("job_terminal", handler);
  source.addEventListener("stream_complete", () => { scheduleRefresh(jobId); closeEventSource(); });
  source.onerror = () => {
    if (!state.currentJob || TERMINAL.has(state.currentJob.status)) return;
    scheduleRefresh(jobId, 900);
  };
}

function closeEventSource() {
  if (state.eventSource) state.eventSource.close();
  state.eventSource = null;
}

function scheduleRefresh(jobId, delay = 120) {
  clearTimeout(state.refreshTimer);
  state.refreshTimer = setTimeout(() => refreshJob(jobId).catch((error) => toast(error.message)), delay);
}

async function refreshJob(jobId) {
  const [job, graph] = await Promise.all([
    api(`/v1/research-jobs/${encodeURIComponent(jobId)}`),
    api(`/v1/research-jobs/${encodeURIComponent(jobId)}/graph`),
  ]);
  if (state.currentJob?.job_id !== jobId) return;
  state.currentJob = job;
  state.graph = graph;
  rememberJob(job, job.question);
  updateJobStrip(job);
  renderGraph();
  if (TERMINAL.has(job.status)) {
    closeEventSource();
    if (job.status === "CANCELLED") {
      showError("研究任务已取消", "任务保留了取消前的图谱与审计事件。你可以修改问题后重新执行。");
      return;
    }
    if (job.status === "FAILED" && !job.coverage_score) {
      showError("研究任务未产生合法证据", job.error?.message || "查看 trace 以定位失败阶段。");
      return;
    }
    try {
      state.result = await api(`/v1/research-jobs/${encodeURIComponent(jobId)}/result`);
      renderConclusion(state.result);
      setWorkspaceMode("result");
    } catch (error) {
      if (job.status === "FAILED") showError("研究任务失败", error.message);
    }
  }
}

function updateJobStrip(job) {
  $("#jobStatus").textContent = pretty(job.status);
  $("#jobId").textContent = job.job_id;
  $("#progressBar").style.width = `${Math.max(1, Number(job.progress || 0) * 100)}%`;
  const current = STAGE_ORDER.indexOf(job.status);
  $$("#stageRail li").forEach((item, index) => {
    item.classList.toggle("done", current > index || TERMINAL.has(job.status));
    item.classList.toggle("active", current === index);
  });
  $("#cancelButton").disabled = TERMINAL.has(job.status);
}

function showError(title, detail) {
  setWorkspaceMode("error");
  $("#errorTitle").textContent = title;
  $("#errorDetail").textContent = detail;
}

function compactConclusionFinding(item) {
  return String(item?.finding_zh || "")
    .split("（", 1)[0]
    .replace("方向：", "")
    .replaceAll("：", "")
    .replace(/[。；\s]+$/g, "")
    .trim();
}

function isLimitationHeadline(value) {
  const text = String(value || "");
  return ["当前只能", "尚不能", "无法回答", "无法覆盖", "没有足以识别", "只描述相关性", "不能支持", "Registry 无法覆盖"]
    .some((marker) => text.includes(marker));
}

function displayConclusionHeadline(synthesis) {
  const findings = (synthesis.primary_findings?.length ? synthesis.primary_findings : synthesis.claim_summaries) || [];
  const parts = findings.map(compactConclusionFinding).filter(Boolean).slice(0, 2);
  if (parts.length) return parts.join("；");
  if (synthesis.answerability === "UNSUPPORTED") return "本轮未形成可验证的研究结论";
  return isLimitationHeadline(synthesis.headline) ? "本轮未形成可验证的研究结论" : synthesis.headline;
}

function displayConclusionQualifier(synthesis, gaps) {
  const originalHeadline = String(synthesis.headline || "").trim();
  if (isLimitationHeadline(originalHeadline)) {
    return { label: "研究边界", text: originalHeadline };
  }
  if (synthesis.evidence_state === "CONDITIONAL_SCENARIO") {
    return { label: "方法说明", text: "条件响应依赖已注册冲击、代理映射与识别假设，不自动等同于因果效应。" };
  }
  if (synthesis.evidence_state === "BASELINE_ONLY") {
    return { label: "研究边界", text: "以下为基线状态，不代表情景冲击的条件效应。" };
  }
  if (synthesis.evidence_state === "ASSOCIATIONAL_ONLY") {
    return { label: "IDENTIFICATION LIMIT", text: "现有模型提供关联性与预测性证据，不能据此识别因果效应。" };
  }
  if (synthesis.answerability === "UNSUPPORTED" && gaps.length) {
    return { label: "覆盖边界", text: gaps[0] };
  }
  return null;
}

function renderConclusion(result) {
  const synthesis = result.synthesis;
  const report = result.report || synthesis.report || null;
  const unsupported = normalizeTextList(synthesis.unsupported_aspects);
  const limitations = normalizeTextList(synthesis.limitations);
  const gaps = [...new Set([...unsupported, ...limitations])];
  const displayHeadline = report?.direct_answer?.headline || displayConclusionHeadline(synthesis);
  const directAnswer = report?.direct_answer?.text || synthesis.answer;
  $("#conclusionCard").classList.remove("hidden");
  $("#coverageLabel").textContent = `${pretty(synthesis.coverage)}覆盖 / ${pretty(synthesis.answerability || "历史版本")} / ${pretty(synthesis.evidence_state || synthesis.stance)}`;
  $("#answerAsOf").textContent = `截至 ${result.as_of_date} · ${result.horizon.minimum}–${result.horizon.maximum} ${pretty(result.horizon.unit)} · ${pretty(result.horizon.source)}`;
  $("#answerHeadline").textContent = displayHeadline;
  const qualifier = displayConclusionQualifier(synthesis, gaps);
  $("#answerQualifier").classList.toggle("hidden", !qualifier);
  $("#answerQualifier").textContent = qualifier?.text || "";
  $("#answerQualifier").dataset.label = qualifier?.label || "研究边界";
  $("#answerNarrative").textContent = directAnswer;
  $("#confidenceValue").textContent = synthesis.confidence;
  $("#coverageMeter").style.width = `${Math.max(0, Math.min(100, synthesis.coverage_score * 100))}%`;
  $("#coverageValue").textContent = `${Math.round(synthesis.coverage_score * 100)}% 覆盖度`;
  const falsifiers = normalizeTextList(synthesis.falsifiers);
  $("#falsifierList").innerHTML = falsifiers.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  $("#limitationList").innerHTML = gaps.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>没有已记录的覆盖缺口。</li>";
  renderResearchReport(report);
  const finalClaim = state.graph?.nodes?.find((node) => node.node_type === "FINAL_CLAIM");
  if (finalClaim && finalClaim.label !== displayHeadline) {
    finalClaim.label = displayHeadline;
    finalClaim.summary = directAnswer;
    renderGraph();
  }
}

function renderResearchReport(report) {
  const container = $("#researchReport");
  if (!report?.abstract || !report?.conclusion) {
    container.classList.add("hidden");
    return;
  }

  container.classList.remove("hidden");
  $("#reportQuestion").textContent = report.question ? `研究问题：${report.question}` : "";
  $("#reportAbstract").textContent = report.abstract.text || "";
  $("#reportKeyPoints").innerHTML = normalizeTextList(report.abstract.key_points)
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");

  const mechanisms = Array.isArray(report.economic_mechanisms) ? report.economic_mechanisms : [];
  $("#mechanismList").innerHTML = mechanisms.length
    ? mechanisms.map((item, index) => {
        const sourceNode = normalizeTextList(item.source_node_ids)[0];
        const role = item.role === "CORE" ? "核心机制" : "辅助机制";
        return `<article class="mechanism-card">
          <header><span>${String(index + 1).padStart(2, "0")}</span><h4>${escapeHtml(item.title || "经济传导机制")}</h4><i>${role}</i></header>
          <p>${escapeHtml(item.explanation || "该机制的解释记录在研究图中。")}</p>
          <div class="transmission-note"><span>传导路径</span><p>${escapeHtml(item.transmission_chain || "")}</p></div>
          ${sourceNode ? `<button type="button" data-report-node="${escapeHtml(sourceNode)}">查看关联实证证据 →</button>` : ""}
        </article>`;
      }).join("")
    : `<p class="report-empty-note">本轮没有形成可展示的经济机制链，相关缺口已列入限制条件。</p>`;

  const evidence = Array.isArray(report.empirical_evidence) ? report.empirical_evidence : [];
  const summary = report.method_summary || {};
  const total = Number(summary.successful_runs || evidence.length);
  const highlighted = Number(summary.highlighted_runs || evidence.length);
  const additional = Number(summary.additional_runs || Math.max(0, total - highlighted));
  $("#empiricalIntro").textContent = additional > 0
    ? `本轮共有 ${total} 项数据或计量规格完成运行。下方重点解释对结论影响最大的 ${highlighted} 项；其余 ${additional} 项基准、稳健性或反证规格可在 Research Graph 中逐项展开。`
    : `本轮共有 ${total} 项数据或计量规格完成运行，下方解释其中对结论影响最大的分析。`;
  $("#empiricalList").innerHTML = evidence.length
    ? evidence.map((item, index) => {
        const sourceNode = normalizeTextList(item.source_node_ids)[0] || item.node_id;
        const variables = normalizeTextList(item.variables);
        return `<article class="empirical-card">
          <header>
            <span>实证分析 ${String(index + 1).padStart(2, "0")}</span>
            <h4>${escapeHtml(item.title || item.method || "实证分析")}</h4>
            <div><i>${escapeHtml(item.method || "已注册模型")}</i><i>${escapeHtml(item.role || "主要分析")}</i></div>
          </header>
          <div class="empirical-question"><span>这项分析回答什么</span><p>${escapeHtml(item.question_addressed || "")}</p></div>
          <dl class="empirical-meta">
            <div><dt>数据与样本</dt><dd>${escapeHtml(item.data_and_sample || "详见节点数据页签")}</dd></div>
            <div><dt>主要变量</dt><dd>${escapeHtml(variables.join("；") || "详见节点变量表")}</dd></div>
            <div class="wide"><dt>模型规格</dt><dd>${escapeHtml(item.specification || "详见节点规格页签")}</dd></div>
          </dl>
          <div class="empirical-result"><span>结果</span><p>${escapeHtml(item.finding || "")}</p></div>
          <div class="empirical-implication"><span>经济含义</span><p>${escapeHtml(item.implication || "")}</p></div>
          <footer><p>${escapeHtml(item.diagnostics || "")}</p>${sourceNode ? `<button type="button" data-report-node="${escapeHtml(sourceNode)}">打开模型、回归表与诊断 →</button>` : ""}</footer>
        </article>`;
      }).join("")
    : `<p class="report-empty-note">没有足够的成功模型可形成实证摘要；请结合上方限制条件解释本轮结果。</p>`;

  $("#reportConclusion").textContent = report.conclusion.text || "";
}

function normalizeTextList(value) {
  if (value == null || value === "") return [];
  const items = (Array.isArray(value) ? value : [value])
    .filter((item) => item != null)
    .map((item) => String(item));
  // v0.1 persisted some LLM strings as arrays of Unicode characters. Treat that
  // unmistakable legacy shape as one sentence while keeping normal lists intact.
  if (items.length >= 4 && items.every((item) => [...item].length <= 1)) {
    return [items.join("").trim()].filter(Boolean);
  }
  return items.map((item) => item.trim()).filter(Boolean);
}

function dataNodeStatus(node) {
  return !node || node.status === "NOT_ROUTED" ? "available" : node.status === "BLOCKED" ? "blocked" : "used";
}

function stableHash(value) {
  let hash = 2166136261;
  for (const char of String(value)) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  return hash >>> 0;
}

const DATA_CLUSTER_META = {
  catalog: { index: "01", label: "源数据目录", note: "美国官方序列与市场数据" },
  evidence: { index: "02", label: "版本化证据", note: "数据集、文档与冻结快照" },
  factor: { index: "03", label: "实证因子", note: "进入模型前的可检验变量" },
};

function dataStatusLabel(status) {
  return ({ used: "本次使用", available: "可用未路由", blocked: "暂不可执行", asset: "版本化资产" })[status] || pretty(status);
}

function dataTypeLabel(type) {
  return ({ "FRED SERIES": "FRED 序列", AKSHARE: "AKShare 序列", ASSET: "版本化资产", DATASET: "数据集", FACTOR: "实证因子" })[type] || pretty(type);
}

function inferDataDomain(item) {
  const haystack = `${item.node_id} ${item.label} ${item.detail}`.toLowerCase();
  if (/cpi|pce|inflation|price|通胀|价格/.test(haystack)) return "inflation";
  if (/unrate|payems|labor|wage|employment|job|失业|就业|工资/.test(haystack)) return "labor";
  if (/treasury|yield|dgs|fed fund|rate|t10y|利率|收益率/.test(haystack)) return "rates";
  if (/oil|energy|wti|commodity|inventory|crude|能源|原油|商品/.test(haystack)) return "energy";
  if (/equity|stock|s&p|spread|vix|market|股票|信用|市场/.test(haystack)) return "market";
  if (/housing|home|rent|房价|住房|租金/.test(haystack)) return "housing";
  if (/trade|export|import|dollar|fx|贸易|美元|汇率/.test(haystack)) return "trade";
  return "growth";
}

function computeClusteredDataLayout(items) {
  const frameWidth = 560, frameGap = 62, left = 66, top = 116;
  const cardWidth = 166, cardHeight = 54, cardGapX = 12, cardGapY = 14;
  const dotSize = 24, dotGapX = 45, dotGapY = 43, dotColumns = 11;
  const frames = {};
  const positions = new Map();
  let requiredHeight = 720;
  Object.keys(DATA_CLUSTER_META).forEach((cluster, clusterIndex) => {
    const x = left + clusterIndex * (frameWidth + frameGap);
    const group = items.filter((item) => item.cluster === cluster)
      .sort((a, b) => {
        const rank = { used: 0, asset: 1, blocked: 2, available: 3 };
        return (rank[a.status] ?? 9) - (rank[b.status] ?? 9) || a.label.localeCompare(b.label);
      });
    const prominent = group.filter((item) => item.status !== "available");
    const ambient = group.filter((item) => item.status === "available");
    prominent.forEach((item, index) => {
      const column = index % 3, row = Math.floor(index / 3);
      positions.set(item.node_id, {
        x: x + 20 + column * (cardWidth + cardGapX),
        y: top + 42 + row * (cardHeight + cardGapY),
        width: cardWidth,
        height: cardHeight,
        cluster,
        prominent: true,
      });
    });
    const prominentRows = Math.ceil(prominent.length / 3);
    const ambientTop = top + Math.max(156, 54 + prominentRows * (cardHeight + cardGapY));
    ambient.forEach((item, index) => {
      const column = index % dotColumns, row = Math.floor(index / dotColumns);
      const jitter = (stableHash(item.node_id) % 7) - 3;
      positions.set(item.node_id, {
        x: x + 29 + column * dotGapX + jitter,
        y: ambientTop + row * dotGapY + ((stableHash(`${item.node_id}:y`) % 5) - 2),
        width: dotSize,
        height: dotSize,
        cluster,
        prominent: false,
      });
    });
    const ambientRows = Math.ceil(ambient.length / dotColumns);
    const groupBottom = ambientTop + Math.max(1, ambientRows) * dotGapY + 48;
    requiredHeight = Math.max(requiredHeight, groupBottom);
    frames[cluster] = { x, y: top, width: frameWidth, height: groupBottom - top, count: group.length, active: prominent.length };
  });
  const width = left * 2 + frameWidth * 3 + frameGap * 2;
  const height = Math.max(720, requiredHeight + 36);
  Object.values(frames).forEach((frame) => { frame.height = height - top - 42; });
  return { positions, frames, width, height };
}

function renderDataEvidenceLayer() {
  const container = $("#dataEvidenceNodes");
  if (!container) return;
  const graphNodes = state.graph?.nodes || [];
  const graphEdges = state.graph?.edges || [];
  const datasets = graphNodes.filter((node) => node.node_type === "DATASET")
    .sort((a, b) => dataNodeStatus(b).localeCompare(dataNodeStatus(a)) || a.label.localeCompare(b.label));
  const factors = graphNodes.filter((node) => node.node_type === "FACTOR")
    .sort((a, b) => dataNodeStatus(b).localeCompare(dataNodeStatus(a)) || a.label.localeCompare(b.label));
  const selectedSeries = new Set(datasets
    .filter((node) => dataNodeStatus(node) === "used")
    .flatMap((node) => node.metadata?.series_ids || []));
  const fredCatalog = (state.pluginCatalog.fred || []).map((item) => ({
    node_id: `CATALOG::FRED::${item.dataset_id}`,
    label: item.dataset_id,
    detail: ZH_SERIES[item.dataset_id] || "FRED 美国经济时间序列",
    node_type: "FRED SERIES",
    status: selectedSeries.has(item.dataset_id) ? "used" : "available",
    cluster: "catalog",
  }));
  const assets = (state.assetGraph?.nodes || []).map((item) => ({
    node_id: `ASSET::${item.node_id}`,
    label: item.label,
    detail: `${item.ref?.representation || "ASSET"} · ${String(item.ref?.content_hash || "").slice(0, 10)}`,
    node_type: item.ref?.representation || "ASSET",
    status: "asset",
    cluster: "evidence",
  }));

  const visibleDatasets = datasets.map((item) => ({
    ...item,
    label: zhDataset(item.metadata?.dataset_id || item.node_id) || item.summary || "已登记数据集",
    detail: `${zhDataset(item.metadata?.dataset_id || item.node_id) || "美国官方数据"} · ${zhFrequency(item.metadata?.frequency)}`,
    status: dataNodeStatus(item),
    cluster: "evidence",
  }));
  const visibleFactors = factors.map((item) => ({
    ...item,
    label: zhFactor(item.metadata?.factor_id || item.node_id) || "已登记实证因子",
    detail: `${zhFactor(item.metadata?.factor_id || item.node_id) || "实证因子"} · ${item.metadata?.series_id || "登记序列"}`,
    status: dataNodeStatus(item),
    cluster: "factor",
  }));
  const all = [...fredCatalog, ...visibleDatasets, ...assets, ...visibleFactors].map((item) => ({ ...item, domain: inferDataDomain(item) }));
  state.dataItems = new Map(all.map((item) => [item.node_id, item]));
  const edgeRows = [];
  datasets.forEach((dataset) => {
    (dataset.metadata?.series_ids || []).forEach((seriesId) => {
      const source = `CATALOG::FRED::${seriesId}`;
      edgeRows.push({ source, target: dataset.node_id, relation: "提供数据" });
    });
  });
  graphEdges.forEach((edge) => edgeRows.push(edge));
  (state.assetGraph?.edges || []).forEach((edge) => {
    const source = `ASSET::${edge.source_ref}`;
    const target = `ASSET::${edge.target_ref}`;
    edgeRows.push({ source, target, relation: edge.relation_type });
  });
  const layout = computeClusteredDataLayout(all);
  const { positions, width, height, frames } = layout;
  state.dataLayout = layout;
  const canvas = $("#dataEvidenceCanvas");
  const edgeSvg = $("#dataEvidenceEdges");
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  edgeSvg.setAttribute("width", width);
  edgeSvg.setAttribute("height", height);
  edgeSvg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  edgeSvg.innerHTML = `<defs><marker id="dataArrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,1 L7,4 L0,7 Z"></path></marker></defs>` + edgeRows.map((edge) => {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) return "";
    const sourceItem = state.dataItems.get(edge.source), targetItem = state.dataItems.get(edge.target);
    const sourceActive = sourceItem?.status === "used" || sourceItem?.status === "asset";
    const targetActive = targetItem?.status === "used" || targetItem?.status === "asset";
    const active = sourceActive && targetActive;
    const contextual = !active && (sourceActive || targetActive);
    let sx = source.x + source.width / 2, sy = source.y + source.height / 2;
    let tx = target.x + target.width / 2, ty = target.y + target.height / 2;
    if (source.cluster !== target.cluster) {
      if (source.x < target.x) { sx = source.x + source.width; tx = target.x; }
      else { sx = source.x; tx = target.x + target.width; }
    }
    const bend = source.cluster === target.cluster ? 46 : Math.max(58, Math.abs(tx - sx) * .42);
    const direction = tx >= sx ? 1 : -1;
    return `<path data-source="${escapeHtml(edge.source)}" data-target="${escapeHtml(edge.target)}" class="data-evidence-edge ${active ? "used" : contextual ? "contextual" : ""}" ${active ? 'marker-end="url(#dataArrow)"' : ""} d="M${sx},${sy} C${sx + bend * direction},${sy} ${tx - bend * direction},${ty} ${tx},${ty}"></path>`;
  }).join("");
  container.innerHTML = [
    ...Object.entries(frames).map(([cluster, frame]) => {
      const meta = DATA_CLUSTER_META[cluster];
      return `<section class="data-cluster-frame" data-cluster="${cluster}" style="left:${frame.x}px;top:${frame.y}px;width:${frame.width}px;height:${frame.height}px"><header><i>${meta.index}</i><div><b>${meta.label}</b><small>${meta.note}</small></div><em>${frame.active} / ${frame.count}</em></header></section>`;
    }),
    ...all.map((item) => {
      const point = positions.get(item.node_id);
      const density = point.prominent ? "prominent" : "ambient";
      return `<button class="data-evidence-node ${density}" type="button" data-node-id="${escapeHtml(item.node_id)}" data-cluster="${escapeHtml(item.cluster)}" data-status="${escapeHtml(item.status)}" data-domain="${escapeHtml(item.domain)}" data-type="${escapeHtml(item.node_type)}" aria-label="${escapeHtml(`${item.label}，${dataStatusLabel(item.status)}`)}" title="${escapeHtml(item.detail || item.label)}" style="left:${point.x}px;top:${point.y}px;width:${point.width}px;height:${point.height}px"><i></i><span><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(dataTypeLabel(item.node_type))}</small></span></button>`;
    }),
  ].join("");
  const routedDatasets = datasets.filter((node) => dataNodeStatus(node) === "used").length;
  const routedFactors = factors.filter((node) => dataNodeStatus(node) === "used").length;
  $("#dataUniverseCount").textContent = String(all.length);
  $("#dataRoutedCount").textContent = String(routedDatasets);
  $("#dataFactorCount").textContent = String(routedFactors);
  $("#dataPluginBadges").innerHTML = state.dataPlugins.length
    ? state.dataPlugins.map((plugin) => `<button type="button" data-plugin-toggle="${escapeHtml(plugin.plugin_id)}" data-enabled="${String(plugin.enabled)}" data-state="${plugin.enabled ? "on" : "off"}" ${plugin.configured ? "" : "disabled"} title="${plugin.configured ? "点击切换数据插件" : "需要先在本机配置该来源"}"><b>${escapeHtml(plugin.name)}</b>${plugin.enabled ? "已启用 ✓" : plugin.configured ? "点击启用" : "待配置"}</button>`).join("")
    : `<span><b>注册表</b>${datasets.length} 组官方数据 · ${assets.length} 个 A 类资产</span>`;
  applyDataFocusMode();
  showDataInspector();
  if (!state.dataInitialized && all.length) {
    requestAnimationFrame(resetDataView);
    state.dataInitialized = true;
  } else {
    applyDataTransform();
  }
}

function applyDataFocusMode() {
  const panel = $("#dataEvidencePanel");
  const button = $("#dataFocusToggle");
  panel.classList.toggle("focus-path", state.dataFocusOnly);
  button.setAttribute("aria-pressed", String(state.dataFocusOnly));
  $("span", button).textContent = state.dataFocusOnly ? "显示完整数据宇宙" : "只看本次路径";
}

function showDataInspector(item = null) {
  const inspector = $("#dataEvidenceInspector");
  if (!inspector) return;
  if (!item) {
    inspector.innerHTML = `<span>节点检查器</span><strong>悬停查看数据沿革</strong><p>灰色小点构成完整美国数据宇宙；高亮卡片组成这次研究真正读取的证据路径。</p>`;
    inspector.dataset.status = "idle";
    return;
  }
  inspector.dataset.status = item.status;
  inspector.innerHTML = `<span>${escapeHtml(DATA_CLUSTER_META[item.cluster]?.label || "数据节点")} · ${escapeHtml(dataStatusLabel(item.status))}</span><strong>${escapeHtml(item.label)}</strong><p>${escapeHtml(item.detail || dataTypeLabel(item.node_type))}</p><small>${escapeHtml(dataTypeLabel(item.node_type))} · ${escapeHtml(item.node_id)}</small>`;
}

function applyDataTransform() {
  $("#dataEvidenceCanvas").style.transform = `translate(${state.dataPanX}px, ${state.dataPanY}px) scale(${state.dataZoom})`;
  $("#dataZoomReset").textContent = `${Math.round(state.dataZoom * 100)}%`;
}

function adjustDataZoom(delta) {
  state.dataZoom = Math.max(.35, Math.min(1.5, state.dataZoom + delta));
  applyDataTransform();
}

function resetDataView() {
  const viewport = $("#dataEvidenceViewport");
  state.dataZoom = Math.max(.42, Math.min(.9, (viewport.clientWidth - 34) / (state.dataLayout?.width || 1880)));
  state.dataPanX = 16;
  state.dataPanY = 16;
  applyDataTransform();
}

function visibleGraphNodes() {
  if (!state.graph?.nodes) return [];
  const lane = $("#laneFilter").value;
  const status = $("#statusFilter").value;
  const evidence = $("#evidenceFilter").value;
  const locallyVisible = new Set();
  if (!state.showDetail && state.expandedNodes.size) {
    (state.graph.edges || []).forEach((edge) => {
      if (state.expandedNodes.has(edge.source)) locallyVisible.add(edge.target);
      if (state.expandedNodes.has(edge.target)) locallyVisible.add(edge.source);
    });
  }
  return state.graph.nodes.filter((node) => {
    if (!state.showDetail && TECHNICAL_TYPES.has(node.node_type) && !state.expandedNodes.has(node.node_id) && !locallyVisible.has(node.node_id)) return false;
    if (lane !== "ALL" && node.lane_id && node.lane_id !== lane) return false;
    if (status !== "ALL" && node.status !== status && !["QUESTION", "QUERY", "AGGREGATION", "FINAL_CLAIM"].includes(node.node_type)) return false;
    if (evidence !== "ALL" && ["MODEL_RUN", "EVIDENCE"].includes(node.node_type)) {
      const nodeEvidence = node.metadata?.evidence_type || node.role;
      if (nodeEvidence !== evidence) return false;
    }
    return true;
  });
}

function updateLaneFilter() {
  const select = $("#laneFilter");
  const current = select.value;
  const lanes = [...new Set((state.graph?.nodes || []).map((node) => node.lane_id).filter(Boolean))];
  select.innerHTML = `<option value="ALL">全部泳道</option>${lanes.map((lane) => `<option value="${escapeHtml(lane)}">${escapeHtml(zhLane(lane))}</option>`).join("")}`;
  select.value = lanes.includes(current) ? current : "ALL";
}

function computeLayout(nodes) {
  const lanes = ["__GLOBAL__", ...[...new Set(nodes.map((node) => node.lane_id).filter(Boolean))]];
  const groups = new Map();
  lanes.forEach((lane) => groups.set(lane, []));
  nodes.forEach((node) => groups.get(node.lane_id || "__GLOBAL__")?.push(node));
  const positions = new Map();
  const bands = [];
  let yCursor = 0;
  lanes.forEach((lane) => {
    const group = groups.get(lane) || [];
    if (!group.length) return;
    const byColumn = new Map();
    group.forEach((node) => {
      const column = COLUMN_BY_TYPE[node.node_type] ?? 5;
      if (!byColumn.has(column)) byColumn.set(column, []);
      byColumn.get(column).push(node);
    });
    const maxCount = Math.max(1, ...[...byColumn.values()].map((items) => items.length));
    const height = Math.max(lane === "__GLOBAL__" ? 174 : 198, maxCount * 116 + 68);
    bands.push({ lane, y: yCursor, height });
    byColumn.forEach((items, column) => {
      items.forEach((node, index) => positions.set(node.node_id, { x: 78 + column * 282, y: yCursor + 42 + index * 116, width: 246, height: 94 }));
    });
    yCursor += height;
  });
  return { positions, bands, width: 78 + 15 * 282 + 274, height: Math.max(560, yCursor + 36) };
}

function renderGraph() {
  if (!state.graph) return;
  renderDataEvidenceLayer();
  updateLaneFilter();
  const nodes = visibleGraphNodes();
  const visibleIds = new Set(nodes.map((node) => node.node_id));
  const edges = (state.graph.edges || []).filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
  const layout = computeLayout(nodes);
  state.layout = layout;
  const canvas = $("#graphCanvas");
  const edgeSvg = $("#graphEdges");
  canvas.style.width = `${layout.width}px`;
  canvas.style.height = `${layout.height}px`;
  edgeSvg.setAttribute("width", layout.width);
  edgeSvg.setAttribute("height", layout.height);
  edgeSvg.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
  const hiddenCounts = new Map();
  if (!state.showDetail) {
    (state.graph.edges || []).forEach((edge) => {
      const source = state.graph.nodes.find((node) => node.node_id === edge.source);
      const target = state.graph.nodes.find((node) => node.node_id === edge.target);
      if (target && TECHNICAL_TYPES.has(target.node_type) && visibleIds.has(edge.source)) hiddenCounts.set(edge.source, (hiddenCounts.get(edge.source) || 0) + 1);
      if (source && TECHNICAL_TYPES.has(source.node_type) && visibleIds.has(edge.target)) hiddenCounts.set(edge.target, (hiddenCounts.get(edge.target) || 0) + 1);
    });
  }
  $("#graphNodes").innerHTML = [
    ...layout.bands.map((band) => `<div class="lane-band" style="left:0;top:${band.y}px;width:${layout.width}px;height:${band.height}px"><span class="lane-label">${escapeHtml(band.lane === "__GLOBAL__" ? "全局研究链" : zhLane(band.lane))}</span></div>`),
    ...nodes.map((node) => {
      const position = layout.positions.get(node.node_id);
      const collapsed = hiddenCounts.get(node.node_id) || 0;
      const counts = node.metadata?.universe_counts;
      const countLabel = counts ? `${counts.mechanisms || 0} 机制 · ${counts.factors || 0} 因子 · ${counts.model_specifications || 0} 规格` : "";
      return `<button class="graph-node" type="button" data-node-id="${escapeHtml(node.node_id)}" data-type="${escapeHtml(node.node_type)}" data-status="${escapeHtml(node.status)}" data-role="${escapeHtml(node.role || "")}" style="left:${position.x}px;top:${position.y}px">
        <span class="node-top"><i>${escapeHtml(pretty(node.node_type))}</i><b class="node-status"></b></span>
        <strong class="node-label">${escapeHtml(graphNodeLabel(node))}</strong>
        ${countLabel ? `<span class="node-density">${escapeHtml(countLabel)}</span>` : ""}
        <span class="node-foot"><i>${escapeHtml(node.lane_id ? zhLane(node.lane_id) : pretty(node.status))}</i>${collapsed ? `<b class="collapsed-count" title="点击展开相连的数据节点">+${collapsed}</b>` : `<i>${escapeHtml(pretty(node.status))}</i>`}</span>
      </button>`;
    }),
  ].join("");
  edgeSvg.innerHTML = edges.map((edge) => {
    const source = layout.positions.get(edge.source);
    const target = layout.positions.get(edge.target);
    const sx = source.x + source.width, sy = source.y + source.height / 2;
    const tx = target.x, ty = target.y + target.height / 2;
    const dx = Math.max(35, (tx - sx) * .48);
    const targetNode = nodes.find((node) => node.node_id === edge.target);
    const classes = ["graph-edge", targetNode?.status === "FAILED" ? "failed" : ""].filter(Boolean).join(" ");
    return `<path class="${classes}" data-source="${escapeHtml(edge.source)}" data-target="${escapeHtml(edge.target)}" d="M${sx},${sy} C${sx + dx},${sy} ${tx - dx},${ty} ${tx},${ty}"></path>`;
  }).join("");
  const allNodes = state.graph.nodes || [];
  const planned = allNodes.filter((node) => ["PLANNED", "PENDING", "RUNNING", "SUCCESS", "WARNING", "FAILED"].includes(node.status)).length;
  const blocked = allNodes.filter((node) => node.status === "BLOCKED").length;
  const notRouted = allNodes.filter((node) => node.status === "NOT_ROUTED").length;
  $("#graphStats").textContent = `${nodes.length} 个可见 / 共 ${allNodes.length} 个 · ${planned} 个已路由 · ${blocked} 个受阻 · ${notRouted} 个未路由`;
  if (!state.graphInitialized && nodes.length) {
    resetGraphView();
    state.graphInitialized = true;
  } else {
    applyGraphTransform();
  }
}

function applyGraphTransform() {
  $("#graphCanvas").style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom})`;
  $("#zoomReset").textContent = `${Math.round(state.zoom * 100)}%`;
}

function resetGraphView() {
  const viewport = $("#graphViewport");
  const width = state.layout?.width || 2400;
  // On phones, preserve readable node typography and let the user pan through
  // the graph instead of shrinking the entire DAG into illegible thumbnails.
  state.zoom = window.innerWidth <= 640
    ? .68
    : Math.max(.38, Math.min(.85, (viewport.clientWidth - 40) / width));
  state.panX = 20;
  state.panY = 15;
  applyGraphTransform();
}

function adjustZoom(delta) {
  state.zoom = Math.max(.3, Math.min(1.45, state.zoom + delta));
  applyGraphTransform();
}

async function openNode(nodeId) {
  const node = state.graph?.nodes?.find((item) => item.node_id === nodeId);
  if (!node) return;
  if (!state.showDetail) {
    state.expandedNodes.add(nodeId);
    renderGraph();
  }
  state.selectedNode = node;
  state.nodeDetail = null;
  state.activeTab = "overview";
  state.drawerReturnFocus = document.activeElement;
  $("#drawerType").textContent = pretty(node.node_type);
  $("#drawerTitle").textContent = graphNodeLabel(node);
  $("#drawerSubtitle").textContent = `${node.node_id} · ${pretty(node.status)}`;
  $("#detailDrawer").classList.add("open");
  $("#detailDrawer").setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  $(".drawer-close", $("#detailDrawer"))?.focus({ preventScroll: true });
  updateDrawerTabs();
  $("#drawerBody").innerHTML = `<div class="detail-section"><h3>正在读取节点详情…</h3></div>`;
  try {
    state.nodeDetail = await api(`/v1/research-jobs/${encodeURIComponent(state.currentJob.job_id)}/nodes/${encodeURIComponent(node.node_id)}`);
  } catch (error) {
    state.nodeDetail = { error: error.message, status: node.status, metadata: node.metadata, node_type: node.node_type, lane_id: node.lane_id, role: node.role };
  }
  renderDrawer();
}

function closeDrawer() {
  if (!$("#detailDrawer").classList.contains("open")) return;
  $("#detailDrawer").classList.remove("open");
  $("#detailDrawer").setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
  state.drawerReturnFocus?.focus?.();
  state.drawerReturnFocus = null;
}

function focusable(container) {
  return $$("button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])", container)
    .filter((element) => element.offsetParent !== null);
}

function trapFocus(event, container) {
  if (event.key !== "Tab") return;
  const items = focusable(container);
  if (!items.length) return;
  const first = items[0], last = items.at(-1);
  if (!container.contains(document.activeElement)) { event.preventDefault(); first.focus(); }
  else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}

function openHistory() {
  state.historyReturnFocus = document.activeElement;
  $("#historyPanel").classList.add("open");
  $("#historyPanel").setAttribute("aria-hidden", "false");
  // Focus after the visibility transition has entered the rendering pipeline;
  // otherwise the activating button can reclaim focus at the end of its click.
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if ($("#historyPanel").classList.contains("open")) {
      $("#historyClose").focus({ preventScroll: true });
    }
  }));
}

function closeHistory() {
  if (!$("#historyPanel").classList.contains("open")) return;
  $("#historyPanel").classList.remove("open");
  $("#historyPanel").setAttribute("aria-hidden", "true");
  state.historyReturnFocus?.focus?.();
  state.historyReturnFocus = null;
}

function updateDrawerTabs() {
  $$("#drawerTabs button").forEach((button) => button.classList.toggle("active", button.dataset.tab === state.activeTab));
}

function renderDrawer() {
  updateDrawerTabs();
  const detail = state.nodeDetail || {};
  const renderers = { overview: renderOverview, specification: renderSpecification, data: renderDataVariables, results: renderResults, diagnostics: renderDiagnostics, robustness: renderRobustness, provenance: renderProvenance };
  $("#drawerBody").innerHTML = (renderers[state.activeTab] || renderOverview)(detail);
  if (state.activeTab === "specification") renderFormula(detail.specification?.formula);
}

function fallbackNodeExplanation(detail) {
  const node = state.selectedNode || {};
  const type = detail.node_type || node.node_type || (String(detail.node_id || node.node_id || "").startsWith("MR::") ? "MODEL_RUN" : "RESEARCH_OBJECT");
  const title = graphNodeLabel(node) || detail.node_id || node.node_id || "该研究对象";
  const summaries = {
    QUESTION: ["保存用户的原始研究问题，作为整张图的起点。", "防止后续路由和模型偏离用户真正提出的问题。"],
    QUERY: ["把自然语言问题编译成结构化任务、期限和输出要求。", "通道选择和模型执行前，Python 必须先获得经过验证的问题合同。"],
    RESEARCH_DEPTH_GATE: ["检查计划中的证据深度是否与问题复杂度相匹配。", "避免一个重大结论只建立在少量浅层统计上。"],
    LANE: ["拆出一个独立研究通道并汇集其中的证据。", "复杂问题需要先按机制并行研究，再进行跨通道综合。"],
    MECHANISM: ["提出通道内可被数据检验的作用机制。", "把宽泛叙事连接到可观测因子和已登记模型。"],
    RESEARCH_NODE: ["生成一个边界清晰的中间研究判断。", "证据必须先在中间判断层闭合，才能进入总论。"],
    CLAIM: ["保存一条可被证据支持或反驳的中间判断。", "避免把不可比较的估计结果直接相加。"],
    FACTOR: ["定义机制所使用的可观测变量。", "变量必须先固定定义、来源、单位和频率，才能进入模型。"],
    DATASET: ["定义数据来源和历史版本合同。", "保证结果可复现，并防止历史任务读取未来修订值。"],
    TRANSFORM: ["把原始序列转换成模型允许使用的形式。", "估计前必须控制尺度、频率和趋势处理。"],
    MODEL_SPECIFICATION: ["冻结实证设计、变量、参数和诊断要求。", "AI 可以选择已登记积木，但不能改写模型代码。"],
    MODEL_RUN: ["执行已登记的 Python 统计模型并产生定量证据。", "机制在这里接受真实观测检验，而不是由大语言模型描述。"],
    DIAGNOSTIC: ["检验上游模型是否足够可信。", "系数或预测只有通过方法专属诊断后才能进入结论。"],
    EVIDENCE: ["把模型结果标准化为可追溯证据对象。", "不同方法共享证据边界，同时保留各自解释限制。"],
    LANE_SIGNAL: ["综合同一研究通道内已诊断的证据。", "跨通道综合前，需要透明记录每条通道的方向和贡献。"],
    AGGREGATION: ["把异质通道证据综合成总答案。", "复杂问题不能由单个模型独立回答。"],
    FINAL_CLAIM: ["给出面向用户的主要结论。", "结论闭合研究链，同时保留到底层模型和数据快照的链接。"],
    FALSIFIER: ["记录可能推翻当前结论的可观测条件。", "研究结论必须说明在什么情况下需要修订。"],
  };
  const [purpose, why] = summaries[type] || [`把“${title}”作为可追溯研究步骤保存并执行。`, "让这部分研究过程可以在图谱中展开检查。"];
  const variables = detail.variables || [];
  const sample = detail.sample;
  const data = variables.length
    ? `使用 ${variables.length} 个已登记变量${sample ? `，样本期为 ${sample.start} 至 ${sample.end}，共 ${sample.observations || "—"} 个观测` : ""}。`
    : "使用结构化上游输入；这个节点本身不额外运行新的数据序列。";
  return {
    purpose,
    why_it_exists: why,
    mechanism: ZH_MECHANISMS[knownRegistryKey(detail.metadata?.mechanism_id || node.metadata?.mechanism_id || node.node_id, ZH_MECHANISMS)] || `${title}沿已登记的经济机制，把上游数据转换为可进入下一层聚合的结构化判断。`,
    data_summary: data,
    output_summary: "结构化结果会传给相连的下游研究节点。",
    plain_summary: `${purpose} ${why}`,
  };
}

function renderNodeBrief(detail) {
  const fixed = fallbackNodeExplanation(detail);
  const raw = detail.explanation || {};
  const llm = raw.llm || {};
  const facts = {
    purpose: chineseOr(raw.purpose, fixed.purpose),
    why_it_exists: chineseOr(raw.why_it_exists, fixed.why_it_exists),
    mechanism: chineseOr(raw.mechanism, fixed.mechanism),
    data_summary: chineseOr(raw.data_summary, fixed.data_summary),
    output_summary: chineseOr(raw.output_summary, fixed.output_summary),
    plain_summary: chineseOr(raw.plain_summary, fixed.plain_summary),
  };
  const usesLlm = llm.status === "SUCCESS" && /[\u3400-\u9fff]/.test(`${llm.narrative_summary || ""}${llm.mechanism_walkthrough || ""}`);
  const narrative = usesLlm ? (llm.narrative_summary || facts.plain_summary) : facts.plain_summary;
  const mechanism = usesLlm ? (llm.mechanism_walkthrough || facts.mechanism) : facts.mechanism;
  return `<article class="node-brief">
    <header class="node-brief-head">
      <div><span>节点摘要</span><strong>这一步在研究链中做什么</strong></div>
      <em class="explanation-source ${usesLlm ? "llm" : "fixed"}">${usesLlm ? "证据约束的模型解释" : "注册表固定说明"}</em>
    </header>
    <p class="node-brief-lead">${escapeHtml(narrative)}</p>
    <div class="node-brief-grid">
      <section><span>具体作用</span><p>${escapeHtml(facts.purpose)}</p></section>
      <section><span>存在原因</span><p>${escapeHtml(facts.why_it_exists)}</p></section>
      <section><span>机制</span><p>${escapeHtml(mechanism)}</p></section>
      <section><span>数据 / 输入</span><p>${escapeHtml(facts.data_summary)}</p></section>
    </div>
    <footer><span>输出</span><p>${escapeHtml(facts.output_summary)}</p></footer>
  </article>`;
}

function renderOverview(detail) {
  if (detail.error) return `<div class="detail-section"><h3>节点暂不可用</h3><div class="detail-card wide"><p>${escapeHtml(detail.error)}</p></div></div>`;
  const overview = detail.overview || {};
  const methodRaw = detail.method || detail.specification?.method || detail.metadata?.model_recipe_id || state.selectedNode?.node_type;
  const method = zhModel(methodRaw) || pretty(methodRaw);
  const lane = detail.lane_id || overview.lane_id || state.selectedNode?.lane_id || "GLOBAL";
  const role = detail.role || overview.role || state.selectedNode?.role || "—";
  const fallback = fallbackNodeExplanation(detail);
  return `<div class="detail-section"><h3>研究目的与结论贡献</h3>${renderNodeBrief(detail)}<div class="detail-grid execution-detail-grid">
    ${detailCard("状态", pretty(detail.status || detail.node_status), chineseOr(detail.summary || state.selectedNode?.summary, fallback.plain_summary))}
    ${detailCard("方法 / 对象", method, detail.evidence_type ? `证据类型：${zhText(detail.evidence_type)}` : `泳道：${zhLane(lane)} · 角色：${zhText(role)}`)}
    ${detailCard("方向", pretty(detail.direction || "—"), `置信度：${pretty(detail.confidence || "—")} · 信号：${formatNumber(detail.signal)}`)}
    ${detailCard("样本", detail.sample ? `${detail.sample.start} → ${detail.sample.end}` : "不适用", detail.sample ? `${detail.sample.observations || "—"} 个观测 · ${detail.sample.frequency || "—"}` : "即使尚未执行数值估计，这个对象也可以被检查。")}
    ${detail.specification ? detailCard("估计对象 / 假设", chineseOr(detail.specification.estimand || detail.specification.hypothesis || detail.specification.intermediate_claim, `${graphNodeLabel(state.selectedNode)}的方向、幅度与不确定性`), detail.specification.dependent_variable ? `因变量：${zhText(detail.specification.dependent_variable)}` : chineseOr(detail.specification.estimand_boundary, "详见模型设定与来源追溯页签。"), "wide") : ""}
    ${overview.upstream ? detailCard("数据沿革", `${overview.upstream.length} 个上游 · ${overview.downstream?.length || 0} 个下游`, "每个相连对象都可在这份不可变任务图中追溯。", "wide") : ""}
  </div>${renderCharts(detail.charts || [])}</div>`;
}

function detailCard(kicker, title, text, className = "") {
  return `<article class="detail-card ${className}"><span>${escapeHtml(kicker)}</span><h4>${escapeHtml(title)}</h4><p>${escapeHtml(text)}</p></article>`;
}

function renderSpecification(detail) {
  const spec = detail.specification;
  if (!spec) return emptyDetail("模型设定", "这个节点没有已登记的模型设定合同。 ");
  return `<div class="detail-section"><h3>已登记模型设定</h3>${spec.formula ? `<div id="formulaBox" class="formula-box">${escapeHtml(spec.formula)}</div>` : ""}<dl class="definition-list">
    <div><dt>方法</dt><dd>${escapeHtml(zhModel(spec.method || detail.method) || "非模型研究对象")}</dd></div>
    <div><dt>研究假设</dt><dd>${escapeHtml(chineseOr(spec.hypothesis || spec.intermediate_claim, `${graphNodeLabel(state.selectedNode)}存在可被数据支持或反驳的方向性判断。`))}</dd></div>
    <div><dt>估计对象</dt><dd>${escapeHtml(chineseOr(spec.estimand || spec.estimand_boundary, "估计目标变量的方向、幅度与不确定性。"))}</dd></div>
    <div><dt>因变量</dt><dd>${escapeHtml(zhText(spec.dependent_variable || "—"))}</dd></div>
    <div><dt>自变量</dt><dd>${escapeHtml((spec.independent_variables || spec.factor_ids || []).map((item) => zhText(item)).join(" · ") || "—")}</dd></div>
    <div><dt>控制变量</dt><dd>${escapeHtml((spec.controls || []).map((item) => zhText(item)).join(" · ") || "无")}</dd></div>
    ${spec.fixed_effects ? `<div><dt>固定效应</dt><dd>${escapeHtml(zhText(spec.fixed_effects))}</dd></div>` : ""}
    <div><dt>参数</dt><dd>${escapeHtml(JSON.stringify(localizedStructured(spec.parameters || detail.parameters?.values || {}), null, 0))}</dd></div>
    <div><dt>参数来源</dt><dd>${escapeHtml(chineseOr(detail.parameters?.source, "注册表参数政策 / 不可变设定"))}</dd></div>
  </dl></div>`;
}

function renderFormula(formula) {
  const target = $("#formulaBox");
  if (!target || !formula || !window.katex) return;
  try { window.katex.render(formula, target, { displayMode: true, throwOnError: false }); }
  catch { target.textContent = formula; }
}

function renderDataVariables(detail) {
  const variables = detail.variables || [];
  if (!variables.length) {
    const factorIds = detail.specification?.factor_ids || detail.provenance?.registry_metadata?.factor_pool || [];
    return factorIds.length
      ? `<div class="detail-section"><h3>已登记因子依赖</h3><ul class="localized-factor-list">${factorIds.map((factorId) => `<li><strong>${escapeHtml(zhFactor(factorId) || "已登记因子")}</strong><span>${escapeHtml(factorId)}</span></li>`).join("")}</ul></div>`
      : emptyDetail("数据与变量", "这个对象没有变量层数据合同；请查看相连的因子或模型节点。 ");
  }
  return `<div class="detail-section"><h3>数据、变量与历史版本</h3><div class="table-scroll"><table class="variable-table"><thead><tr><th>因子</th><th>定义</th><th>序列</th><th>单位</th><th>频率</th><th>数据集</th><th>发布时间</th></tr></thead><tbody>${variables.map((variable) => `<tr><td><strong>${escapeHtml(zhFactor(variable.factor_id) || "已登记因子")}</strong><small>${escapeHtml(variable.factor_id)}</small></td><td>${escapeHtml(zhFactor(variable.factor_id) || chineseOr(variable.definition, "定义见注册表"))}</td><td>${escapeHtml(variable.series_id)}</td><td>${escapeHtml(zhUnit(variable.unit))}</td><td>${escapeHtml(zhFrequency(variable.frequency))}</td><td>${escapeHtml(zhDataset(variable.dataset_id) || variable.dataset_id)}</td><td>${escapeHtml(zhReleaseLag(variable.release_lag))}</td></tr>`).join("")}</tbody></table></div>
    <h3 style="margin-top:28px">样本合同</h3><pre class="json-block">${escapeHtml(JSON.stringify(localizedStructured(detail.sample || {}), null, 2))}</pre></div>`;
}

function renderResults(detail) {
  const table = detail.table;
  if (!table) {
    if (detail.status === "FAILED") return emptyDetail("结果", `模型失败：${detail.error_type || "未知错误"}`);
    return `<div class="detail-section"><h3>结构化结果状态</h3><pre class="json-block">${escapeHtml(JSON.stringify(localizedStructured(detail.results || { status: detail.status, note: "只有实际执行的模型运行才会产生数值结果。" }), null, 2))}</pre></div>`;
  }
  const columns = table.columns || [];
  const variables = [];
  const matrix = new Map();
  const labels = new Map();
  Object.entries(table.coefficients || {}).forEach(([column, coefficients]) => coefficients.forEach((item) => {
    if (!variables.includes(item.variable_id)) variables.push(item.variable_id);
    labels.set(item.variable_id, item.label);
    matrix.set(`${item.variable_id}::${column}`, item);
  }));
  const variableRows = variables.map((variable) => {
    const estimates = columns.map((column) => {
      const item = matrix.get(`${variable}::${column}`);
      return `<td>${item ? `${formatNumber(item.coefficient)}${escapeHtml(item.stars || "")}` : ""}</td>`;
    }).join("");
    const errors = columns.map((column) => {
      const item = matrix.get(`${variable}::${column}`);
      return `<td>${item ? `(${formatNumber(item.standard_error)})` : ""}</td>`;
    }).join("");
    const details = columns.map((column) => {
      const item = matrix.get(`${variable}::${column}`);
      return `<td>${item ? `p=${formatNumber(item.p_value, 6)}<br>CI [${formatNumber(item.ci_low)}, ${formatNumber(item.ci_high)}]` : ""}</td>`;
    }).join("");
    return `<tr><th>${escapeHtml(zhText(labels.get(variable) || variable))}</th>${estimates}</tr><tr class="se-row"><th></th>${errors}</tr><tr class="detail-row"><th></th>${details}</tr>`;
  }).join("");
  const statisticRows = Object.entries(table.statistics || {}).map(([label, values], index) => `<tr class="${index === 0 ? "stat-start" : ""}"><th>${escapeHtml(label)}</th>${columns.map((_, columnIndex) => `<td>${escapeHtml(values[columnIndex] ?? "")}</td>`).join("")}</tr>`).join("");
  return `<div class="detail-section"><h3>学术结果</h3><p class="table-title">${escapeHtml(chineseOr(table.title, `${graphNodeLabel(state.selectedNode)}：模型估计结果`))}</p>${artifactLinks(detail.artifacts)}<div class="table-scroll"><table class="academic-table"><thead><tr><th>变量</th>${columns.map((column) => `<th>${escapeHtml(zhText(column))}</th>`).join("")}</tr></thead><tbody>${variableRows}${statisticRows}</tbody></table></div><p class="table-notes">${escapeHtml(chineseOr((table.notes || []).join(" "), "系数显著性、标准误、p-value 与置信区间按模型配方完整报告。"))}</p>${renderCharts(detail.charts || [])}</div>`;
}

function artifactLinks(artifacts = []) {
  const tableArtifacts = artifacts.filter((item) => ["CSV", "JSON", "HTML", "LATEX"].includes(item.artifact_type));
  if (!tableArtifacts.length) return "";
  return `<div class="artifact-row">${tableArtifacts.map((item) => `<a href="${escapeHtml(apiUrl(`/v1/artifacts/${encodeURIComponent(item.artifact_id)}`))}" target="_blank" rel="noopener">${escapeHtml(item.artifact_type)} ↗</a>`).join("")}</div>`;
}

function renderDiagnostics(detail) {
  const diagnostics = detail.diagnostics || [];
  if (!diagnostics.length) return emptyDetail("诊断", detail.status === "FAILED" ? `执行失败：${detail.error_type || "未知错误"}` : "该节点没有方法专属诊断。");
  const normalized = diagnostics.map((item) => typeof item === "string"
    ? { status: "PLANNED", name: item, interpretation: "已登记模型配方要求执行这项诊断。", credibility_impact: "只有报告这项诊断后，该证据才能进入可信结论。", statistic: null, p_value: null }
    : item);
  return `<div class="detail-section"><h3>方法专属诊断</h3><div class="diagnostic-list">${normalized.map((item) => `<article class="diagnostic-card ${String(item.status).toLowerCase()}"><div class="diagnostic-status">${escapeHtml(pretty(item.status))}</div><div class="diagnostic-main"><h4>${escapeHtml(zhText(item.name))}</h4><p>${escapeHtml(chineseOr(item.interpretation, "按模型配方检验该统计条件是否满足。"))}</p><p><strong>可信度影响：</strong> ${escapeHtml(chineseOr(item.credibility_impact, "诊断警告会降低该证据进入最终结论时的权重。"))}</p></div><div class="diagnostic-stat">统计量 ${escapeHtml(formatNumber(item.statistic, 6))}<br>p-value ${escapeHtml(formatNumber(item.p_value, 6))}</div></article>`).join("")}</div>${renderCharts(detail.charts || [])}</div>`;
}

function renderRobustness(detail) {
  if (!detail.robustness) return emptyDetail("稳健性", "该节点没有稳健性或样本外结果。");
  return `<div class="detail-section"><h3>稳健性与样本外检验</h3><pre class="json-block">${escapeHtml(JSON.stringify(localizedStructured(detail.robustness), null, 2))}</pre>${renderCharts(detail.charts || [])}</div>`;
}

function renderProvenance(detail) {
  const provenance = detail.provenance || detail.metadata || {};
  const registryMetadata = provenance.registry_metadata || {};
  const factors = registryMetadata.factor_pool || detail.specification?.factor_ids || [];
  const datasets = registryMetadata.dataset_dependencies || [];
  const researchNode = knownRegistryKey(registryMetadata.node_id || state.selectedNode?.node_id, ZH_NODES);
  return `<div class="detail-section"><h3>不可变来源追溯</h3>${artifactLinks(detail.artifacts)}<dl class="definition-list">
    <div><dt>研究节点</dt><dd>${escapeHtml(researchNode ? ZH_NODES[researchNode] : graphNodeLabel(state.selectedNode))}</dd></div>
    <div><dt>模型配方</dt><dd>${escapeHtml(zhModel(provenance.model_recipe_id || registryMetadata.model_recipe_id || detail.model_recipe_id) || "非模型图节点")}</dd></div>
    <div><dt>代码制品</dt><dd>${escapeHtml(provenance.code_artifact || registryMetadata.code_artifact || "注册表图对象")}</dd></div>
    <div><dt>注册表版本</dt><dd>${escapeHtml(provenance.registry_version || "0.2.0 + 深度扩展")}</dd></div>
    <div><dt>参数决策</dt><dd>${escapeHtml(JSON.stringify(localizedStructured(detail.parameters || {}), null, 0))}</dd></div>
    <div><dt>登记因子</dt><dd>${escapeHtml(factors.map((item) => zhFactor(item) || item).join(" · ") || "不适用")}</dd></div>
    <div><dt>依赖数据</dt><dd>${escapeHtml(datasets.map((item) => zhDataset(item) || item).join(" · ") || "见数据沿革")}</dd></div>
  </dl><h3 style="margin-top:28px">研报页码证据</h3><pre class="json-block">${escapeHtml(JSON.stringify(localizedStructured((provenance.report_evidence || []).map((item) => ({ 报告编号: item.report_id || item.id || "—", 页码: item.pages || item.page || "—", 证据用途: chineseOr(item.use || item.role, "方法与机制来源") }))), null, 2))}</pre><h3 style="margin-top:28px">数据快照</h3><pre class="json-block">${escapeHtml(JSON.stringify(localizedStructured(provenance.data_lineage || []), null, 2))}</pre></div>`;
}

function emptyDetail(title, message) {
  return `<div class="detail-section"><h3>${escapeHtml(title)}</h3><div class="detail-card wide"><p>${escapeHtml(message)}</p></div></div>`;
}

function renderCharts(charts) {
  if (!charts.length) return "";
  return charts.map((chart) => `<article class="chart-card"><h4>${escapeHtml(chineseOr(chart.title, "模型结果与诊断图"))}</h4><span>${escapeHtml(zhText(chart.kind))}</span>${chartSvg(chart)}<div class="chart-legend">${(chart.series || []).map((series, index) => `<span><i style="background:${COLORS[index % COLORS.length]}"></i>${escapeHtml(zhText(series.label))}</span>`).join("")}</div></article>`).join("");
}

function chartSvg(chart) {
  const series = chart.series || [];
  const points = series.flatMap((item) => item.points || []).filter((point) => Number.isFinite(Number(point.value)));
  if (!points.length) return `<p>没有可绘制的图表数据。</p>`;
  const categories = [...new Set(points.map((point) => String(point.date)))];
  const values = points.map((point) => Number(point.value));
  let min = Math.min(...values), max = Math.max(...values);
  if (min === max) { min -= 1; max += 1; }
  const pad = Math.max((max - min) * .12, .05);
  min -= pad; max += pad;
  const width = 820, height = 300, left = 52, right = 16, top = 16, bottom = 34;
  const x = (category) => left + categories.indexOf(String(category)) / Math.max(1, categories.length - 1) * (width - left - right);
  const y = (value) => top + (max - Number(value)) / (max - min) * (height - top - bottom);
  const grid = [0, .5, 1].map((ratio) => {
    const yy = top + ratio * (height - top - bottom);
    return `<line class="chart-gridline" x1="${left}" y1="${yy}" x2="${width - right}" y2="${yy}"></line><text class="chart-axis" x="2" y="${yy + 3}">${formatNumber(max - ratio * (max - min), 2)}</text>`;
  }).join("");
  const zero = min < 0 && max > 0 ? `<line class="chart-zero" x1="${left}" y1="${y(0)}" x2="${width - right}" y2="${y(0)}"></line>` : "";
  let marks;
  if (chart.kind === "factor_loadings") {
    const barWidth = Math.max(4, (width - left - right) / Math.max(1, categories.length) * .55);
    marks = points.map((point, index) => {
      const xx = x(point.date) - barWidth / 2, yy = y(Math.max(0, Number(point.value))), y0 = y(0);
      return `<rect x="${xx}" y="${Math.min(yy, y0)}" width="${barWidth}" height="${Math.max(1, Math.abs(y0 - yy))}" fill="${COLORS[index % COLORS.length]}"></rect>`;
    }).join("");
  } else {
    marks = series.map((item, index) => {
      const valid = (item.points || []).filter((point) => Number.isFinite(Number(point.value)));
      const d = valid.map((point, pointIndex) => `${pointIndex ? "L" : "M"}${x(point.date).toFixed(1)},${y(point.value).toFixed(1)}`).join(" ");
      return `<path class="chart-line" d="${d}" stroke="${COLORS[index % COLORS.length]}"></path>`;
    }).join("");
  }
  const first = categories[0], last = categories.at(-1);
  return `<div class="table-scroll"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(chart.title)}">${grid}${zero}${marks}<text class="chart-axis" x="${left}" y="${height - 5}">${escapeHtml(first)}</text><text class="chart-axis" text-anchor="end" x="${width - right}" y="${height - 5}">${escapeHtml(last)}</text></svg></div>`;
}

async function cancelCurrentJob() {
  if (!state.currentJob || TERMINAL.has(state.currentJob.status)) return;
  try {
    await api(`/v1/research-jobs/${encodeURIComponent(state.currentJob.job_id)}/cancel`, { method: "POST" });
    toast("已发送取消请求");
  } catch (error) { toast(error.message); }
}

async function loadConnectionSettings() {
  const [catalog, status] = await Promise.all([
    api("/v1/settings/catalog"),
    api("/v1/settings/status"),
  ]);
  state.settingsCatalog = catalog;
  state.settingsStatus = status;
  state.selectedProvider = status.llm.provider || "deepseek";
  renderConnectionSummary();
  renderLlmSettings(true);
  renderDataSources();
}

function renderConnectionSummary() {
  const status = state.settingsStatus;
  if (!status) return;
  const llm = status.llm;
  const required = status.data_sources.filter((item) => item.key_required);
  const ready = required.filter((item) => item.configured).length;
  $("#providerSetupDot").classList.toggle("ready", llm.configured && ready > 0);
  $("#providerSetupLabel").textContent = llm.configured
    ? `${llm.provider_label} / ${llm.model} · 数据 Key ${ready}/${required.length}`
    : `配置你自己的模型与数据 API · 数据 Key ${ready}/${required.length}`;
}

function openSettings(tab = "model") {
  state.settingsReturnFocus = document.activeElement;
  $("#settingsPanel").setAttribute("aria-hidden", "false");
  document.body.classList.add("settings-open");
  selectSettingsTab(tab);
  $(".settings-close", $("#settingsPanel")).focus();
}

function closeSettings() {
  $("#settingsPanel").setAttribute("aria-hidden", "true");
  document.body.classList.remove("settings-open");
  state.settingsReturnFocus?.focus?.();
}

function selectSettingsTab(tab) {
  $$("#settingsTabs button").forEach((button) => button.classList.toggle("active", button.dataset.settingsTab === tab));
  $$(".settings-tab").forEach((panel) => panel.classList.toggle("active", panel.dataset.settingsPanel === tab));
  $(".settings-body", $("#settingsPanel")).scrollTop = 0;
}

function providerConfig(providerId = state.selectedProvider) {
  return state.settingsCatalog?.llm_providers.find((item) => item.provider_id === providerId);
}

function selectLlmProvider(providerId, preserveCurrent = false) {
  const config = providerConfig(providerId);
  if (!config) return;
  state.selectedProvider = providerId;
  $$("#llmProviderPills button").forEach((button) => button.classList.toggle("active", button.dataset.provider === providerId));
  const select = $("#llmModelSelect");
  select.innerHTML = config.models.map((model) => `<option value="${escapeHtml(model.id)}">${escapeHtml(model.label)} · ${escapeHtml(model.tier)}</option>`).join("")
    + `<option value="__custom__">自定义模型 ID…</option>`;
  const current = preserveCurrent && state.settingsStatus?.llm.provider === providerId ? state.settingsStatus.llm : null;
  const selectedModel = current?.model || config.default_model;
  const exists = config.models.some((model) => model.id === selectedModel);
  select.value = exists ? selectedModel : "__custom__";
  $("#llmCustomModelField").classList.toggle("hidden", exists);
  $("#llmCustomModel").value = exists ? "" : selectedModel;
  $("#llmBaseUrl").value = current?.base_url || config.default_base_url || "";
  $("#llmApiKey").placeholder = current?.api_key_masked
    ? `${current.api_key_masked} 已配置；留空则保留`
    : config.key_placeholder || "输入 API Key";
  $("#llmKeyHint").textContent = current?.configured
    ? `当前密钥：${current.api_key_masked || "已配置"}；存储方式：${pretty(current.storage)}。`
    : "默认只保留到本次 Python 服务器关闭。";
  renderLlmGuide(config);
}

function renderLlmSettings(preserveCurrent = false) {
  if (!state.settingsCatalog || !state.settingsStatus) return;
  $("#llmProviderPills").innerHTML = state.settingsCatalog.llm_providers
    .map((item) => `<button type="button" role="radio" aria-checked="${item.provider_id === state.selectedProvider}" data-provider="${escapeHtml(item.provider_id)}">${escapeHtml(item.label)}</button>`)
    .join("");
  const status = state.settingsStatus.llm;
  $("#llmConfigStatus").textContent = status.configured ? `${status.provider_label} / 已就绪` : "尚未配置";
  $("#llmConfigStatus").classList.toggle("ready", status.configured);
  $("#llmPersist").checked = status.storage === "persistent";
  selectLlmProvider(state.selectedProvider, preserveCurrent);
}

function renderLlmGuide(config) {
  const links = [
    config.key_url ? `<a href="${escapeHtml(config.key_url)}" target="_blank" rel="noopener">打开 API Key 申请页 ↗</a>` : "",
    config.docs_url ? `<a href="${escapeHtml(config.docs_url)}" target="_blank" rel="noopener">查看官方模型 / API 文档 ↗</a>` : "",
  ].filter(Boolean).join(" · ");
  $("#llmGuideBody").innerHTML = `<ol>${config.guide_steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol><p>${links}</p>`;
}

function selectedLlmModel() {
  return $("#llmModelSelect").value === "__custom__"
    ? $("#llmCustomModel").value.trim()
    : $("#llmModelSelect").value;
}

async function saveLlmSettings() {
  const button = $("#saveLlmSettings");
  button.disabled = true;
  setTestResult($("#llmTestResult"), "正在保存…");
  try {
    const key = $("#llmApiKey").value.trim();
    const payload = {
      provider: state.selectedProvider,
      model: selectedLlmModel(),
      base_url: $("#llmBaseUrl").value.trim(),
      persist: $("#llmPersist").checked,
    };
    if (key) payload.api_key = key;
    await api("/v1/settings/llm", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    $("#llmApiKey").value = "";
    await refreshSettingsStatus();
    setTestResult($("#llmTestResult"), "配置已保存；尚未发送模型请求。", true);
  } catch (error) {
    setTestResult($("#llmTestResult"), error.message, false);
  } finally {
    button.disabled = false;
  }
}

async function testLlmSettings() {
  const button = $("#testLlmSettings");
  button.disabled = true;
  setTestResult($("#llmTestResult"), "正在发送最小结构化输出测试…");
  try {
    const result = await api("/v1/settings/llm/test", { method: "POST" });
    setTestResult($("#llmTestResult"), `${result.model} · ${result.latency_ms} ms · ${result.detail}`, true);
  } catch (error) {
    setTestResult($("#llmTestResult"), error.message, false);
  } finally {
    button.disabled = false;
  }
}

async function clearLlmSettings() {
  try {
    const cleared = await api("/v1/settings/llm", { method: "DELETE" });
    $("#llmApiKey").value = "";
    await refreshSettingsStatus();
    setTestResult(
      $("#llmTestResult"),
      cleared.storage === "environment"
        ? "当前密钥来自 .env.local；请删除对应环境变量并重启服务器。"
        : "本地设置文件中的模型密钥已清除。",
      cleared.storage === "environment" ? null : true,
    );
  } catch (error) {
    setTestResult($("#llmTestResult"), error.message, false);
  }
}

function setTestResult(element, message, success = null) {
  element.textContent = message;
  element.classList.toggle("success", success === true);
  element.classList.toggle("failure", success === false);
}

async function refreshSettingsStatus() {
  state.settingsStatus = await api("/v1/settings/status");
  state.selectedProvider = state.settingsStatus.llm.provider || state.selectedProvider;
  renderConnectionSummary();
  renderLlmSettings(true);
  renderDataSources();
  if (state.health) {
    state.health.llm_configured = state.settingsStatus.llm.configured;
    state.health.llm_provider = state.settingsStatus.llm.provider;
    state.health.llm_model = state.settingsStatus.llm.model;
  }
}

function dataStatus(sourceId) {
  return state.settingsStatus?.data_sources.find((item) => item.source_id === sourceId);
}

function renderDataSources() {
  if (!state.settingsCatalog || !state.settingsStatus) return;
  $("#dataSourceList").innerHTML = state.settingsCatalog.data_sources.map((source) => {
    const status = dataStatus(source.source_id);
    const statusText = status?.configured ? (source.key_required ? "KEY READY" : "NO KEY REQUIRED") : "KEY REQUIRED";
    const guide = `<details class="data-source-guide"><summary>申请步骤与官方文档</summary><ol>${source.guide_steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol><div class="data-source-links">${source.key_url ? `<a href="${escapeHtml(source.key_url)}" target="_blank" rel="noopener">申请 / 管理 API Key ↗</a>` : ""}<a href="${escapeHtml(source.docs_url)}" target="_blank" rel="noopener">官方 API 文档 ↗</a></div></details>`;
    const controls = source.key_required ? `
      <div class="data-source-controls">
        <div class="data-secret-row">
          <input type="password" autocomplete="off" spellcheck="false" data-source-key="${escapeHtml(source.source_id)}" placeholder="${status?.api_key_masked ? `${escapeHtml(status.api_key_masked)} 已配置；输入新 Key 可替换` : escapeHtml(source.key_placeholder)}">
          <button class="primary" type="button" data-source-action="save" data-source-id="${escapeHtml(source.source_id)}">保存</button>
          <button type="button" data-source-action="test" data-source-id="${escapeHtml(source.source_id)}">测试</button>
          <button type="button" data-source-action="clear" data-source-id="${escapeHtml(source.source_id)}">清除</button>
        </div>
        <div class="data-source-options">
          <label><input type="checkbox" data-source-persist="${escapeHtml(source.source_id)}" ${status?.storage === "persistent" ? "checked" : ""}> 保存到这台电脑</label>
          <span data-source-result="${escapeHtml(source.source_id)}">${status?.configured ? `${escapeHtml(pretty(status.storage))} STORAGE` : "NOT CONFIGURED"}</span>
        </div>
      </div>` : `
      <div class="source-no-key"><span>这个官方连接器不需要用户密钥，可以直接测试。</span><button type="button" data-source-action="test" data-source-id="${escapeHtml(source.source_id)}">测试公开接口</button></div>`;
    return `<article class="data-source-card" data-source-card="${escapeHtml(source.source_id)}">
      <div class="data-source-head"><div><span>${escapeHtml(source.source_id)} / ${escapeHtml(source.institution)}</span><h4>${escapeHtml(source.label)}</h4><p>${escapeHtml(source.coverage)}</p></div><b class="source-state ${status?.configured ? "ready" : ""}">${statusText}</b></div>
      ${controls}${guide}
    </article>`;
  }).join("");
}

async function saveDataSource(sourceId) {
  const input = $(`[data-source-key="${CSS.escape(sourceId)}"]`);
  const result = $(`[data-source-result="${CSS.escape(sourceId)}"]`);
  if (!input?.value.trim()) {
    setTestResult(result, "请先填写 API Key。", false);
    return;
  }
  setTestResult(result, "正在保存…");
  try {
    await api(`/v1/settings/data-sources/${encodeURIComponent(sourceId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: input.value.trim(),
        persist: Boolean($(`[data-source-persist="${CSS.escape(sourceId)}"]`)?.checked),
      }),
    });
    input.value = "";
    await refreshSettingsStatus();
    setTestResult($(`[data-source-result="${CSS.escape(sourceId)}"]`), "已保存；建议继续测试连接。", true);
  } catch (error) {
    setTestResult(result, error.message, false);
  }
}

async function testDataSource(sourceId) {
  const result = $(`[data-source-result="${CSS.escape(sourceId)}"]`) || $(".source-no-key span", $(`[data-source-card="${CSS.escape(sourceId)}"]`));
  setTestResult(result, "正在连接官方接口…");
  try {
    const response = await api(`/v1/settings/data-sources/${encodeURIComponent(sourceId)}/test`, { method: "POST" });
    setTestResult(result, `${response.latency_ms} ms · ${response.detail}`, true);
  } catch (error) {
    setTestResult(result, error.message, false);
  }
}

async function clearDataSource(sourceId) {
  const result = $(`[data-source-result="${CSS.escape(sourceId)}"]`);
  try {
    const cleared = await api(`/v1/settings/data-sources/${encodeURIComponent(sourceId)}`, { method: "DELETE" });
    await refreshSettingsStatus();
    setTestResult(
      $(`[data-source-result="${CSS.escape(sourceId)}"]`),
      cleared.storage === "environment"
        ? "该密钥来自 .env.local；请删除环境变量并重启服务器。"
        : "本地设置文件中的密钥已清除。",
      cleared.storage === "environment" ? null : true,
    );
  } catch (error) {
    setTestResult(result, error.message, false);
  }
}

async function syncConfiguredSources() {
  const button = $("#syncConfiguredSources");
  button.disabled = true;
  button.textContent = "正在同步…";
  try {
    const result = await api("/v1/data/sync", { method: "POST" });
    toast(`数据同步 ${pretty(result.status)} · ${Object.values(result.rows_by_source || {}).reduce((sum, value) => sum + Number(value || 0), 0)} 行`);
    state.dataStatus = await api("/v1/data/status");
    $("#seriesCount").textContent = `${state.dataStatus.series_count} 条序列`;
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "同步已配置来源";
  }
}

// Event wiring
$("#dailySourcePickerList").addEventListener("change", (event) => {
  const input = event.target.closest("input[data-daily-source]");
  if (!input) return;
  if (input.checked) state.selectedDailySources.add(input.dataset.dailySource);
  else state.selectedDailySources.delete(input.dataset.dailySource);
  localStorage.setItem("macrotrace.dailySources.v2", JSON.stringify([...state.selectedDailySources]));
  renderDailySourcePicker();
});
$("#dailySourcePickerList").addEventListener("click", (event) => {
  if (event.target.closest("a")) event.stopPropagation();
});
$("#selectAllDailySources").addEventListener("click", () => {
  state.selectedDailySources = new Set(state.dailySources.map((source) => source.source_id));
  localStorage.setItem("macrotrace.dailySources.v2", JSON.stringify([...state.selectedDailySources]));
  renderDailySourcePicker();
});
$("#clearDailySources").addEventListener("click", () => {
  state.selectedDailySources = new Set();
  localStorage.setItem("macrotrace.dailySources.v2", "[]");
  renderDailySourcePicker();
});
$("#dailyProductList").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-daily-product]");
  if (!button) return;
  state.selectedDailyProduct = button.dataset.dailyProduct;
  localStorage.setItem("macrotrace.dailyProduct", state.selectedDailyProduct);
  renderDailyProductList();
});
$("#refreshDailyBrief").addEventListener("click", () => {
  state.dailyView = "brief";
  loadDailyBrief(true).catch((error) => {
    if (!state.dailyBrief) renderDailyBriefError(error.message);
    toast(error.message);
  });
});
$("#dailyDomainFilters").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-daily-domain]");
  if (!button) return;
  state.dailyDomain = button.dataset.dailyDomain;
  renderDailyBrief();
});
$("#dailyBriefDocument").addEventListener("mouseup", () => window.setTimeout(showSelectionAction, 0));
$("#selectionToolbar").addEventListener("mousedown", (event) => event.preventDefault());
$("#selectionResearchButton").addEventListener("click", () => compileSelectedExcerpt());
$("#dailyPdfInput").addEventListener("change", (event) => readPdfFile(event.target.files?.[0]));
$("#backToDailyBrief").addEventListener("click", () => {
  state.dailyView = "brief";
  state.pdfDocument = null;
  renderDailyBrief();
});
document.addEventListener("mousedown", (event) => {
  if (!event.target.closest("#selectionToolbar") && !event.target.closest("#dailyBriefDocument")) {
    $("#selectionToolbar").classList.add("hidden");
  }
});
$("#researchForm").addEventListener("submit", submitResearch);
$("#questionInput").addEventListener("input", (event) => $("#charCount").textContent = `${event.target.value.length} / 4000`);
$("#exampleQuestions").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-example]");
  if (!button) return;
  $("#questionInput").value = state.examples[Number(button.dataset.example)];
  $("#charCount").textContent = `${$("#questionInput").value.length} / 4000`;
  $("#questionInput").focus();
});
$("#retryButton").addEventListener("click", submitResearch);
$("#cancelButton").addEventListener("click", cancelCurrentJob);
$("#detailToggle").addEventListener("click", () => {
  state.showDetail = !state.showDetail;
  $("#detailToggle").setAttribute("aria-pressed", String(state.showDetail));
  $("#detailToggle").lastChild.textContent = state.showDetail ? " 隐藏数据层" : " 显示数据层";
  renderGraph();
});
["#dataZoomIn", "#dataZoomOut", "#dataZoomReset"].forEach((selector) => {
  const button = $(selector);
  if (!button) return;
  button.addEventListener("click", () => {
    if (selector === "#dataZoomIn") adjustDataZoom(.1);
    else if (selector === "#dataZoomOut") adjustDataZoom(-.1);
    else resetDataView();
  });
});
$("#dataFocusToggle").addEventListener("click", () => {
  state.dataFocusOnly = !state.dataFocusOnly;
  applyDataFocusMode();
});
$("#dataEvidenceNodes").addEventListener("click", (event) => {
  const node = event.target.closest("[data-node-id]");
  if (!node) return;
  const nodeId = node.dataset.nodeId;
  showDataInspector(state.dataItems.get(nodeId));
  if ((state.graph?.nodes || []).some((item) => item.node_id === nodeId)) {
    openNode(nodeId).catch((error) => toast(error.message));
  } else {
    toast(node.title || "该节点来自 Part A 的可用数据空间");
  }
});
$("#dataEvidenceNodes").addEventListener("mouseover", (event) => {
  const node = event.target.closest("[data-node-id]");
  if (!node) return;
  const nodeId = node.dataset.nodeId;
  showDataInspector(state.dataItems.get(nodeId));
  const neighbors = new Set([nodeId]);
  $$(".data-evidence-edge").forEach((edge) => {
    const adjacent = edge.dataset.source === nodeId || edge.dataset.target === nodeId;
    edge.classList.toggle("focused", adjacent);
    edge.classList.toggle("dimmed", !adjacent);
    if (adjacent) {
      neighbors.add(edge.dataset.source);
      neighbors.add(edge.dataset.target);
    }
  });
  $$(".data-evidence-node").forEach((item) => item.classList.toggle("dimmed", !neighbors.has(item.dataset.nodeId)));
});
$("#dataEvidenceNodes").addEventListener("mouseout", (event) => {
  if (event.relatedTarget?.closest?.(".data-evidence-node")) return;
  $$(".data-evidence-edge").forEach((edge) => edge.classList.remove("focused", "dimmed"));
  $$(".data-evidence-node").forEach((item) => item.classList.remove("dimmed"));
  showDataInspector();
});
$("#dataEvidenceNodes").addEventListener("focusin", (event) => {
  const node = event.target.closest("[data-node-id]");
  if (node) showDataInspector(state.dataItems.get(node.dataset.nodeId));
});
$("#dataEvidenceNodes").addEventListener("focusout", () => showDataInspector());
$("#dataPluginBadges").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-plugin-toggle]");
  if (!button || button.disabled) return;
  button.disabled = true;
  try {
    await api(`/api/v1/data-plugins/${encodeURIComponent(button.dataset.pluginToggle)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: button.dataset.enabled !== "true", actor_id: "local-product-user" }),
    });
    await loadDataEvidenceCatalog();
  } catch (error) {
    toast(error.message);
    button.disabled = false;
  }
});
["#laneFilter", "#statusFilter", "#evidenceFilter"].forEach((selector) => $(selector).addEventListener("change", renderGraph));
$("#zoomIn").addEventListener("click", () => adjustZoom(.1));
$("#zoomOut").addEventListener("click", () => adjustZoom(-.1));
$("#zoomReset").addEventListener("click", resetGraphView);
$("#graphNodes").addEventListener("click", (event) => {
  const node = event.target.closest("[data-node-id]");
  if (node) openNode(node.dataset.nodeId);
});
$("#graphNodes").addEventListener("mouseover", (event) => {
  const node = event.target.closest("[data-node-id]");
  if (!node) return;
  $$(".graph-edge").forEach((edge) => edge.classList.toggle("active", edge.dataset.source === node.dataset.nodeId || edge.dataset.target === node.dataset.nodeId));
});
$("#graphNodes").addEventListener("mouseout", () => $$(".graph-edge").forEach((edge) => edge.classList.remove("active")));
let dataDrag = null;
$("#dataEvidenceViewport").addEventListener("pointerdown", (event) => {
  if (event.target.closest(".data-evidence-node")) return;
  dataDrag = { x: event.clientX, y: event.clientY, panX: state.dataPanX, panY: state.dataPanY };
  $("#dataEvidenceViewport").setPointerCapture?.(event.pointerId);
  $("#dataEvidenceViewport").classList.add("dragging");
});
$("#dataEvidenceViewport").addEventListener("pointermove", (event) => {
  if (!dataDrag) return;
  state.dataPanX = dataDrag.panX + event.clientX - dataDrag.x;
  state.dataPanY = dataDrag.panY + event.clientY - dataDrag.y;
  applyDataTransform();
});
const endDataDrag = () => { dataDrag = null; $("#dataEvidenceViewport").classList.remove("dragging"); };
$("#dataEvidenceViewport").addEventListener("pointerup", endDataDrag);
$("#dataEvidenceViewport").addEventListener("pointercancel", endDataDrag);
$("#dataEvidenceViewport").addEventListener("wheel", (event) => {
  if (!event.ctrlKey && Math.abs(event.deltaY) < Math.abs(event.deltaX)) return;
  event.preventDefault();
  adjustDataZoom(event.deltaY > 0 ? -.06 : .06);
}, { passive: false });
$("#researchReport").addEventListener("click", (event) => {
  const button = event.target.closest("[data-report-node]");
  if (!button) return;
  openNode(button.dataset.reportNode).catch((error) => toast(error.message));
});
$$('[data-close-drawer]').forEach((element) => element.addEventListener("click", closeDrawer));
$("#drawerTabs").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-tab]");
  if (!button) return;
  state.activeTab = button.dataset.tab;
  renderDrawer();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if ($("#settingsPanel").getAttribute("aria-hidden") === "false") closeSettings();
    else if ($("#detailDrawer").classList.contains("open")) closeDrawer();
    else closeHistory();
    return;
  }
  if ($("#settingsPanel").getAttribute("aria-hidden") === "false") trapFocus(event, $(".settings-sheet", $("#settingsPanel")));
  else if ($("#detailDrawer").classList.contains("open")) trapFocus(event, $(".drawer-sheet", $("#detailDrawer")));
  else if ($("#historyPanel").classList.contains("open")) trapFocus(event, $("#historyPanel"));
});
$("#historyButton").addEventListener("click", openHistory);
$("#historyClose").addEventListener("click", closeHistory);
$("#historyList").addEventListener("click", (event) => {
  const item = event.target.closest("[data-job-id]");
  if (!item) return;
  closeHistory();
  loadJob(item.dataset.jobId, true).catch((error) => toast(error.message));
});
$("#settingsButton").addEventListener("click", () => openSettings("model"));
$("#mobileSettingsButton").addEventListener("click", () => openSettings("model"));
$("#heroSettingsButton").addEventListener("click", () => openSettings("model"));
$$("[data-close-settings]").forEach((element) => element.addEventListener("click", closeSettings));
$("#settingsTabs").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-settings-tab]");
  if (button) selectSettingsTab(button.dataset.settingsTab);
});
$("#llmProviderPills").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-provider]");
  if (!button) return;
  selectLlmProvider(button.dataset.provider, false);
  $$("#llmProviderPills button").forEach((item) => item.setAttribute("aria-checked", String(item === button)));
});
$("#llmModelSelect").addEventListener("change", () => {
  const custom = $("#llmModelSelect").value === "__custom__";
  $("#llmCustomModelField").classList.toggle("hidden", !custom);
  if (custom) $("#llmCustomModel").focus();
});
$("#llmKeyVisibility").addEventListener("click", () => {
  const input = $("#llmApiKey");
  const visible = input.type === "text";
  input.type = visible ? "password" : "text";
  $("#llmKeyVisibility").textContent = visible ? "显示" : "隐藏";
});
$("#saveLlmSettings").addEventListener("click", saveLlmSettings);
$("#testLlmSettings").addEventListener("click", testLlmSettings);
$("#clearLlmSettings").addEventListener("click", clearLlmSettings);
$("#syncConfiguredSources").addEventListener("click", syncConfiguredSources);
$("#dataSourceList").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-source-action]");
  if (!button) return;
  const sourceId = button.dataset.sourceId;
  if (button.dataset.sourceAction === "save") saveDataSource(sourceId);
  else if (button.dataset.sourceAction === "test") testDataSource(sourceId);
  else if (button.dataset.sourceAction === "clear") clearDataSource(sourceId);
});
$("#copyConnectorPrompt").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("#connectorPrompt").textContent);
    $("#copyConnectorPrompt").textContent = "已复制";
    setTimeout(() => { $("#copyConnectorPrompt").textContent = "复制给 Codex"; }, 1800);
  } catch {
    toast("浏览器未允许剪贴板访问，请手动复制。");
  }
});

// Pan and wheel zoom for the research graph.
let drag = null;
$("#graphViewport").addEventListener("pointerdown", (event) => {
  if (event.target.closest(".graph-node")) return;
  drag = { x: event.clientX, y: event.clientY, panX: state.panX, panY: state.panY };
  $("#graphViewport").classList.add("dragging");
  event.currentTarget.setPointerCapture(event.pointerId);
});
$("#graphViewport").addEventListener("pointermove", (event) => {
  if (!drag) return;
  state.panX = drag.panX + event.clientX - drag.x;
  state.panY = drag.panY + event.clientY - drag.y;
  applyGraphTransform();
});
$("#graphViewport").addEventListener("pointerup", () => { drag = null; $("#graphViewport").classList.remove("dragging"); });
$("#graphViewport").addEventListener("wheel", (event) => {
  if (!event.ctrlKey) return;
  event.preventDefault();
  adjustZoom(event.deltaY > 0 ? -.06 : .06);
}, { passive: false });

boot();
