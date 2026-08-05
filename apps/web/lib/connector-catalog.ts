export type ConnectorCategory = "market" | "macro" | "fundamentals" | "alternative";
export type ConnectorRuntime = "native" | "python-bridge" | "licensed";

export type DataConnectorDefinition = {
  id: string;
  mark: string;
  name: string;
  institution: string;
  category: ConnectorCategory;
  coverage: string;
  keyRequired: boolean;
  runtime: ConnectorRuntime;
  docsUrl: string;
  keyUrl: string;
  keyPlaceholder: string;
  sampleQuery: Record<string, string | number>;
  legalNote?: string;
};

export const DATA_CONNECTORS: DataConnectorDefinition[] = [
  { id: "fred", mark: "FR", name: "FRED / ALFRED", institution: "Federal Reserve Bank of St. Louis", category: "macro", coverage: "利率、CPI、GDP、就业与历史 vintage", keyRequired: true, runtime: "native", docsUrl: "https://fred.stlouisfed.org/docs/api/fred/series_observations.html", keyUrl: "https://fredaccount.stlouisfed.org/apikeys", keyPlaceholder: "32-character FRED API key", sampleQuery: { series_id: "GDP", limit: 5 }, legalNote: "Uses the FRED® API; not endorsed or certified by the Federal Reserve Bank of St. Louis." },
  { id: "tushare", mark: "TS", name: "Tushare Pro", institution: "Tushare", category: "market", coverage: "A股行情、基本面、资金流与国内宏观", keyRequired: true, runtime: "native", docsUrl: "https://tushare.pro/document/1?doc_id=40", keyUrl: "https://tushare.pro/register", keyPlaceholder: "Tushare token", sampleQuery: { api_name: "trade_cal", exchange: "SSE" } },
  { id: "alpha-vantage", mark: "AV", name: "Alpha Vantage", institution: "Alpha Vantage", category: "market", coverage: "全球股票、外汇、商品、宏观与新闻情绪", keyRequired: true, runtime: "native", docsUrl: "https://www.alphavantage.co/documentation/", keyUrl: "https://www.alphavantage.co/support/#api-key", keyPlaceholder: "Alpha Vantage API key", sampleQuery: { function: "TIME_SERIES_DAILY", symbol: "IBM" } },
  { id: "nasdaq-data-link", mark: "ND", name: "Nasdaq Data Link", institution: "Nasdaq", category: "alternative", coverage: "宏观、商品、利率与授权另类数据", keyRequired: true, runtime: "native", docsUrl: "https://docs.data.nasdaq.com/", keyUrl: "https://data.nasdaq.com/sign-up", keyPlaceholder: "Nasdaq Data Link API key", sampleQuery: { dataset: "FRED/GDP", limit: 5 } },
  { id: "world-bank", mark: "WB", name: "World Bank Open Data", institution: "World Bank", category: "macro", coverage: "全球 GDP、人口、贸易与发展指标", keyRequired: false, runtime: "native", docsUrl: "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392", keyUrl: "", keyPlaceholder: "", sampleQuery: { country: "US", indicator: "NY.GDP.MKTP.CD" } },
  { id: "treasury", mark: "UT", name: "U.S. Treasury Fiscal Data", institution: "U.S. Department of the Treasury", category: "macro", coverage: "联邦债务余额与财政数据", keyRequired: false, runtime: "native", docsUrl: "https://fiscaldata.treasury.gov/api-documentation/", keyUrl: "", keyPlaceholder: "", sampleQuery: { dataset: "debt_to_penny", limit: 5 } },
  { id: "nyfed", mark: "NY", name: "New York Fed Markets", institution: "Federal Reserve Bank of New York", category: "macro", coverage: "SOFR 与纽约联储参考利率", keyRequired: false, runtime: "native", docsUrl: "https://markets.newyorkfed.org/static/docs/markets-api.html", keyUrl: "", keyPlaceholder: "", sampleQuery: { series: "rates" } },
  { id: "yahoo-finance", mark: "YF", name: "Yahoo Finance", institution: "Yahoo", category: "market", coverage: "全球股票、ETF 与历史 OHLCV（演示适配器）", keyRequired: false, runtime: "native", docsUrl: "https://finance.yahoo.com/", keyUrl: "", keyPlaceholder: "", sampleQuery: { symbol: "NVDA", range: "1mo" }, legalNote: "Unofficial chart endpoint; use a licensed feed for production or redistribution." },
  { id: "akshare", mark: "AK", name: "AKShare", institution: "AKFamily", category: "market", coverage: "国内市场综合数据与公开信息聚合", keyRequired: false, runtime: "python-bridge", docsUrl: "https://akshare.akfamily.xyz/data/index.html", keyUrl: "", keyPlaceholder: "", sampleQuery: { function: "stock_zh_a_hist", symbol: "000001" }, legalNote: "Requires the ResearchOS Python connector service and source-specific usage review." },
  { id: "cninfo", mark: "CN", name: "巨潮资讯", institution: "深圳证券信息有限公司", category: "fundamentals", coverage: "上市公司公告、年报与监管披露文件", keyRequired: false, runtime: "python-bridge", docsUrl: "https://www.cninfo.com.cn/", keyUrl: "", keyPlaceholder: "", sampleQuery: { symbol: "000001", document_type: "annual-report" }, legalNote: "Public disclosure ingestion requires a reviewed connector and source terms compliance." },
  { id: "eastmoney-choice", mark: "EC", name: "东方财富 Choice", institution: "东方财富", category: "fundamentals", coverage: "行情、财务、行业、资金流、新闻与研报", keyRequired: true, runtime: "licensed", docsUrl: "https://choice.eastmoney.com/", keyUrl: "", keyPlaceholder: "Institution credential", sampleQuery: {} },
  { id: "wind", mark: "WD", name: "Wind", institution: "万得信息", category: "fundamentals", coverage: "国内外股票、债券、基金、宏观与另类数据", keyRequired: true, runtime: "licensed", docsUrl: "https://www.wind.com.cn/", keyUrl: "", keyPlaceholder: "Institution credential", sampleQuery: {} },
  { id: "bloomberg", mark: "BB", name: "Bloomberg", institution: "Bloomberg L.P.", category: "alternative", coverage: "全球多资产行情、基本面、新闻与企业级数据", keyRequired: true, runtime: "licensed", docsUrl: "https://www.bloomberg.com/professional/", keyUrl: "", keyPlaceholder: "Enterprise credential", sampleQuery: {} },
];

export const connectorById = (id: string) => DATA_CONNECTORS.find((item) => item.id === id);
