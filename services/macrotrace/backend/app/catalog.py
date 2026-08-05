from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeriesSpec:
    source_id: str
    series_id: str
    label: str
    frequency: str
    unit: str
    lane_id: str
    start: str = "2010-01-01"


FRED_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("FRED", "PCEPI", "美国整体PCE价格指数", "M", "index", "US.INFLATION"),
    SeriesSpec("FRED", "PCEPILFE", "美国核心PCE价格指数", "M", "index", "US.INFLATION"),
    SeriesSpec("FRED", "DGS10", "10年期美国国债收益率", "D", "percent", "US.MONETARY"),
    SeriesSpec("FRED", "DGS2", "2年期美国国债收益率", "D", "percent", "US.MONETARY"),
    SeriesSpec("FRED", "DGS5", "5年期美国国债收益率", "D", "percent", "US.MONETARY"),
    SeriesSpec("FRED", "DGS30", "30年期美国国债收益率", "D", "percent", "US.MONETARY"),
    SeriesSpec("FRED", "FEDFUNDS", "有效联邦基金利率", "M", "percent", "US.MONETARY", "1980-01-01"),
    SeriesSpec("FRED", "DFII10", "10年期美国实际国债收益率", "D", "percent", "US.MONETARY"),
    SeriesSpec("FRED", "T10YIE", "10年期盈亏平衡通胀率", "D", "percent", "US.INFLATION"),
    SeriesSpec("FRED", "THREEFYTP10", "10年期美国国债期限溢价", "D", "percent", "US.MONETARY", "1990-01-01"),
    SeriesSpec("FRED", "T5YIFR", "5年后5年期远期通胀预期", "D", "percent", "US.INFLATION", "2003-01-01"),
    SeriesSpec("FRED", "GFDEGDQ188S", "美国公共债务占GDP比重", "Q", "percent_of_gdp", "US.FISCAL_TREASURY", "1966-01-01"),
    SeriesSpec("FRED", "FGDEF", "美国联邦政府净储蓄", "Q", "billions_usd_saar", "US.FISCAL_TREASURY", "1980-01-01"),
    SeriesSpec("FRED", "NFCI", "芝加哥联储全国金融状况指数", "W", "index", "US.MONETARY", "1990-01-01"),
    SeriesSpec("FRED", "INDPRO", "美国工业生产指数", "M", "index", "US.ACTIVITY"),
    SeriesSpec("FRED", "RSAFS", "美国零售销售额", "M", "millions_usd", "US.ACTIVITY"),
    SeriesSpec("FRED", "GDPC1", "美国实际国内生产总值", "Q", "billions_chained_2017_usd", "US.ACTIVITY", "1980-01-01"),
    SeriesSpec("FRED", "CFNAI", "芝加哥联储全国活动指数", "M", "index", "US.ACTIVITY", "1980-01-01"),
    SeriesSpec("FRED", "PCEC96", "美国实际个人消费支出", "M", "billions_chained_2017_usd", "US.ACTIVITY", "1980-01-01"),
    SeriesSpec("FRED", "DSPIC96", "美国实际可支配个人收入", "M", "billions_chained_2017_usd", "US.ACTIVITY", "1980-01-01"),
    SeriesSpec("FRED", "PSAVERT", "美国个人储蓄率", "M", "percent", "US.HOUSING_CONSUMPTION", "1980-01-01"),
    SeriesSpec("FRED", "HOUST", "美国新屋开工", "M", "thousands_saar", "US.HOUSING_CONSUMPTION", "1980-01-01"),
    SeriesSpec("FRED", "PERMIT", "美国新屋建筑许可", "M", "thousands_saar", "US.HOUSING_CONSUMPTION", "1980-01-01"),
    SeriesSpec("FRED", "T10Y2Y", "美国10年期与2年期国债利差", "D", "percent", "US.MONETARY", "1980-01-01"),
    SeriesSpec("FRED", "BAA10Y", "美国Baa公司债与10年期国债利差", "D", "percent", "US.FIN_STABILITY", "1986-01-01"),
    SeriesSpec("FRED", "USREC", "NBER美国经济衰退指标", "M", "binary", "US.ACTIVITY", "1980-01-01"),
    SeriesSpec("FRED", "ICSA", "美国首次申请失业救济人数", "W", "count", "US.LABOR", "1980-01-01"),
    SeriesSpec("FRED", "CCSA", "美国持续领取失业救济人数", "W", "count", "US.LABOR", "1980-01-01"),
    SeriesSpec("FRED", "SP500", "标普500指数", "D", "index", "US.EQUITY_MARKET", "2016-01-01"),
    SeriesSpec("FRED", "NASDAQCOM", "纳斯达克综合指数", "D", "index", "US.EQUITY_MARKET", "1990-01-01"),
    SeriesSpec("FRED", "VIXCLS", "芝加哥期权交易所波动率指数", "D", "index", "US.EQUITY_MARKET", "1990-01-01"),
    SeriesSpec("FRED", "DTWEXBGS", "美国名义广义美元指数", "D", "index", "US.MONETARY", "2006-01-01"),
    SeriesSpec("FRED", "DCOILWTICO", "WTI原油现货价格", "D", "usd_per_barrel", "US.FUTURES_COMMODITY", "1990-01-01"),
    SeriesSpec("FRED", "DHHNGSP", "亨利港天然气现货价格", "D", "usd_per_mmbtu", "US.FUTURES_COMMODITY", "1997-01-01"),
    SeriesSpec("FRED", "PCOPPUSDM", "全球铜价", "M", "usd_per_metric_ton", "US.FUTURES_COMMODITY", "1990-01-01"),
    SeriesSpec("FRED", "PALLFNFINDEXM", "国际货币基金组织全球大宗商品价格指数", "M", "index", "US.FUTURES_COMMODITY", "1992-01-01"),
)


BLS_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("BLS", "CUSR0000SA0", "美国整体消费者价格指数（季调）", "M", "index", "US.INFLATION"),
    SeriesSpec("BLS", "CUSR0000SA0L1E", "美国核心消费者价格指数", "M", "index", "US.INFLATION"),
    SeriesSpec("BLS", "CES0000000001", "美国非农就业人数", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "LNS14000000", "美国失业率", "M", "percent", "US.LABOR"),
    SeriesSpec("BLS", "CES0500000003", "美国私营部门平均时薪", "M", "usd_per_hour", "US.LABOR"),
    SeriesSpec("BLS", "LNS14024887", "美国16至24岁人群失业率", "M", "percent", "US.LABOR"),
    SeriesSpec("BLS", "LNS12324887", "美国16至24岁人群就业人口比", "M", "percent", "US.LABOR"),
    SeriesSpec("BLS", "LNS14027662", "美国25岁以上本科及以上人群失业率", "M", "percent", "US.LABOR"),
    SeriesSpec("BLS", "LNS14027660", "美国25岁以上高中学历人群失业率", "M", "percent", "US.LABOR"),
    SeriesSpec("BLS", "JTS000000000000000JOL", "美国非农职位空缺人数", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS000000000000000HIL", "美国非农招聘人数", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS000000000000000QUL", "美国非农主动离职人数", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS000000000000000LDL", "美国非农裁员与解雇人数", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS510099000000000JOL", "美国信息业职位空缺人数", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS510099000000000LDL", "美国信息业裁员与解雇人数", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS540099000000000JOL", "美国专业及商业服务业职位空缺人数", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS540099000000000LDL", "美国专业及商业服务业裁员与解雇人数", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "CES5000000001", "美国信息业就业人数", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "CES5000000003", "美国信息业平均时薪", "M", "usd_per_hour", "US.LABOR"),
    SeriesSpec("BLS", "CES6000000001", "美国专业及商业服务业就业人数", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "CES6000000003", "美国专业及商业服务业平均时薪", "M", "usd_per_hour", "US.LABOR"),
)


EIA_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("EIA", "RWTC", "WTI原油现货价格", "W", "usd_per_barrel", "US.COMMODITY_ENERGY"),
    SeriesSpec("EIA", "WCESTUS1", "美国商业原油库存（不含战略储备）", "W", "thousand_barrels", "US.FUTURES_COMMODITY", "1990-01-01"),
)


TREASURY_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("TREASURY", "DEBT_TO_PENNY_TOTAL", "美国未偿公共债务总额", "D", "usd", "US.FISCAL_TREASURY", "2015-01-01"),
)


STATE_PANEL_STATES: tuple[tuple[str, str], ...] = (
    ("CA", "加利福尼亚州"),
    ("TX", "得克萨斯州"),
    ("FL", "佛罗里达州"),
    ("NY", "纽约州"),
    ("IL", "伊利诺伊州"),
    ("PA", "宾夕法尼亚州"),
    ("OH", "俄亥俄州"),
    ("GA", "佐治亚州"),
    ("NC", "北卡罗来纳州"),
    ("AZ", "亚利桑那州"),
)


def state_panel_specs() -> tuple[SeriesSpec, ...]:
    specs: list[SeriesSpec] = []
    for code, name in STATE_PANEL_STATES:
        specs.extend(
            (
                SeriesSpec("FRED", f"{code}UR", f"{name}失业率", "M", "percent", "US.LABOR", "2000-01-01"),
                SeriesSpec("FRED", f"{code}STHPI", f"{name}全口径房价指数", "Q", "index", "US.HOUSING_CONSUMPTION", "2000-01-01"),
            )
        )
    return tuple(specs)


ALL_SERIES: tuple[SeriesSpec, ...] = FRED_SERIES + BLS_SERIES + EIA_SERIES + TREASURY_SERIES + state_panel_specs()
SERIES_BY_ID = {spec.series_id: spec for spec in ALL_SERIES}

DATASET_LABELS_ZH = {
    "DS.BLS.CPI": "美国劳工统计局消费者价格数据", "DS.BLS.LABOR": "美国劳工统计局就业与工资数据",
    "DS.BLS.CPS_DEMOGRAPHICS": "美国人口分组劳动力数据", "DS.BLS.JOLTS": "美国职位空缺与劳动力流动数据",
    "DS.CENSUS.BTOS": "美国企业趋势与展望调查", "DS.ONET.OCCUPATIONS": "美国职业信息网络数据",
    "DS.FRED.ACTIVITY": "美国经济活动数据", "DS.FRED.PCE": "美国个人消费支出价格数据",
    "DS.FRED.RATES": "美国利率与金融条件数据", "DS.FRED.HOUSEHOLD": "美国家庭与住房数据",
    "DS.FRED.CLAIMS": "美国失业救济申请数据", "DS.EIA.WTI": "美国原油价格与库存数据",
    "DS.TREASURY.DEBT": "美国财政部债务数据", "DS.FRED.STATE_PANEL": "美国州级经济面板数据",
    "DS.FRED.FISCAL": "美国财政数据", "DS.FRED.MARKETS": "美国金融市场数据",
    "DS.FRED.COMMODITIES": "美国及全球大宗商品数据",
}

FACTOR_LABELS_ZH = {
    "F.CPI.HEADLINE": "美国整体消费者价格指数", "F.CPI.CORE": "美国核心消费者价格指数",
    "F.PCE.HEADLINE": "美国整体个人消费支出价格指数", "F.PCE.CORE": "美国核心个人消费支出价格指数",
    "F.LABOR.PAYROLL": "美国非农就业人数", "F.LABOR.UNEMPLOYMENT": "美国失业率", "F.LABOR.WAGES": "美国私营部门平均时薪",
    "F.ACTIVITY.INDPRO": "美国工业生产指数", "F.ACTIVITY.RETAIL": "美国零售销售额", "F.ACTIVITY.REAL_GDP": "美国实际国内生产总值",
    "F.MONETARY.NFCI": "美国全国金融状况指数", "F.RATES.UST10": "10年期美国国债收益率", "F.RATES.UST2": "2年期美国国债收益率",
    "F.RATES.UST5": "5年期美国国债收益率", "F.RATES.UST30": "30年期美国国债收益率", "F.RATES.REAL10": "10年期美国实际国债收益率",
    "F.RATES.POLICY": "有效联邦基金利率", "F.RATES.TERM_PREMIUM10": "10年期美国国债期限溢价",
    "F.INFLATION.BREAKEVEN10": "10年期盈亏平衡通胀率", "F.INFLATION.FORWARD_5Y5Y": "5年后5年期远期通胀预期",
    "F.ENERGY.WTI": "WTI原油现货价格", "F.FISCAL.DEBT": "美国未偿公共债务总额",
    "F.FISCAL.DEBT_GDP": "美国公共债务占国内生产总值比重", "F.FISCAL.NET_SAVING": "美国联邦政府净储蓄",
    "F.STATE.UNEMPLOYMENT": "美国州级失业率", "F.STATE.HPI": "美国州级房价指数",
    "F.ACTIVITY.CFNAI": "芝加哥联储全国活动指数", "F.ACTIVITY.REAL_PCE": "美国实际个人消费支出",
    "F.ACTIVITY.REAL_DPI": "美国实际可支配个人收入", "F.HOUSEHOLD.SAVING": "美国个人储蓄率",
    "F.HOUSING.STARTS": "美国新屋开工", "F.HOUSING.PERMITS": "美国新屋建筑许可",
    "F.MONETARY.CURVE_10Y2Y": "美国10年期与2年期国债利差", "F.FIN.CREDIT_SPREAD": "美国公司债信用利差",
    "F.ACTIVITY.RECESSION": "美国经济衰退指标", "F.LABOR.INITIAL_CLAIMS": "美国首次申请失业救济人数",
    "F.LABOR.CONTINUING_CLAIMS": "美国持续领取失业救济人数", "F.LABOR.YOUTH_UR": "美国青年失业率",
    "F.LABOR.YOUTH_EPOP": "美国青年就业人口比", "F.LABOR.BACHELOR_UR": "美国本科及以上人群失业率",
    "F.LABOR.HS_UR": "美国高中学历人群失业率", "F.LABOR.JOLTS_OPENINGS": "美国非农职位空缺人数",
    "F.LABOR.JOLTS_HIRES": "美国非农招聘人数", "F.LABOR.JOLTS_QUITS": "美国非农主动离职人数",
    "F.LABOR.JOLTS_LAYOFFS": "美国非农裁员与解雇人数", "F.LABOR.INFO_OPENINGS": "美国信息业职位空缺人数",
    "F.LABOR.INFO_LAYOFFS": "美国信息业裁员与解雇人数", "F.LABOR.PROF_OPENINGS": "美国专业及商业服务业职位空缺人数",
    "F.LABOR.PROF_LAYOFFS": "美国专业及商业服务业裁员与解雇人数", "F.LABOR.INFO_EMPLOYMENT": "美国信息业就业人数",
    "F.LABOR.INFO_WAGES": "美国信息业平均时薪", "F.LABOR.PROF_EMPLOYMENT": "美国专业及商业服务业就业人数",
    "F.LABOR.PROF_WAGES": "美国专业及商业服务业平均时薪", "F.AI.BTOS_ADOPTION": "美国企业人工智能使用比例",
    "F.AI.OCC_EXPOSURE": "美国职业人工智能暴露评分", "F.EQUITY.SP500": "标普500指数",
    "F.EQUITY.NASDAQ": "纳斯达克综合指数", "F.EQUITY.VIX": "芝加哥期权交易所波动率指数", "F.USD.BROAD": "美国广义美元指数",
    "F.COMMODITY.WTI_DAILY": "WTI原油现货价格（日频）", "F.COMMODITY.NATGAS": "亨利港天然气现货价格",
    "F.COMMODITY.COPPER": "全球铜价", "F.ENERGY.CRUDE_STOCKS": "美国商业原油库存",
    "F.COMMODITY.BROAD_INDEX": "全球大宗商品价格指数",
}


def series_label_zh(series_id: str) -> str:
    spec = SERIES_BY_ID.get(series_id)
    return spec.label if spec else "美国官方数据序列"


def dataset_label_zh(dataset_id: str) -> str:
    return DATASET_LABELS_ZH.get(dataset_id, "已登记研究数据集")


def factor_label_zh(factor_id: str) -> str:
    return FACTOR_LABELS_ZH.get(factor_id, "已登记实证因子")
