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
    SeriesSpec("FRED", "PCEPI", "PCE price index", "M", "index", "US.INFLATION"),
    SeriesSpec("FRED", "PCEPILFE", "Core PCE price index", "M", "index", "US.INFLATION"),
    SeriesSpec("FRED", "DGS10", "10-year Treasury yield", "D", "percent", "US.MONETARY"),
    SeriesSpec("FRED", "DGS2", "2-year Treasury yield", "D", "percent", "US.MONETARY"),
    SeriesSpec("FRED", "DGS5", "5-year Treasury yield", "D", "percent", "US.MONETARY"),
    SeriesSpec("FRED", "DGS30", "30-year Treasury yield", "D", "percent", "US.MONETARY"),
    SeriesSpec("FRED", "FEDFUNDS", "Effective federal funds rate", "M", "percent", "US.MONETARY", "1980-01-01"),
    SeriesSpec("FRED", "DFII10", "10-year real Treasury yield", "D", "percent", "US.MONETARY"),
    SeriesSpec("FRED", "T10YIE", "10-year breakeven inflation", "D", "percent", "US.INFLATION"),
    SeriesSpec("FRED", "THREEFYTP10", "10-year zero-coupon Treasury term premium", "D", "percent", "US.MONETARY", "1990-01-01"),
    SeriesSpec("FRED", "T5YIFR", "5-year, 5-year forward inflation expectation rate", "D", "percent", "US.INFLATION", "2003-01-01"),
    SeriesSpec("FRED", "GFDEGDQ188S", "Total public debt as a percent of GDP", "Q", "percent_of_gdp", "US.FISCAL_TREASURY", "1966-01-01"),
    SeriesSpec("FRED", "FGDEF", "Net federal government saving", "Q", "billions_usd_saar", "US.FISCAL_TREASURY", "1980-01-01"),
    SeriesSpec("FRED", "NFCI", "Chicago Fed National Financial Conditions Index", "W", "index", "US.MONETARY", "1990-01-01"),
    SeriesSpec("FRED", "INDPRO", "Industrial production index", "M", "index", "US.ACTIVITY"),
    SeriesSpec("FRED", "RSAFS", "Advance retail sales", "M", "millions_usd", "US.ACTIVITY"),
    SeriesSpec("FRED", "GDPC1", "Real gross domestic product", "Q", "billions_chained_2017_usd", "US.ACTIVITY", "1980-01-01"),
    SeriesSpec("FRED", "CFNAI", "Chicago Fed National Activity Index", "M", "index", "US.ACTIVITY", "1980-01-01"),
    SeriesSpec("FRED", "PCEC96", "Real personal consumption expenditures", "M", "billions_chained_2017_usd", "US.ACTIVITY", "1980-01-01"),
    SeriesSpec("FRED", "DSPIC96", "Real disposable personal income", "M", "billions_chained_2017_usd", "US.ACTIVITY", "1980-01-01"),
    SeriesSpec("FRED", "PSAVERT", "Personal saving rate", "M", "percent", "US.HOUSING_CONSUMPTION", "1980-01-01"),
    SeriesSpec("FRED", "HOUST", "Housing starts", "M", "thousands_saar", "US.HOUSING_CONSUMPTION", "1980-01-01"),
    SeriesSpec("FRED", "PERMIT", "New private housing units authorized by permits", "M", "thousands_saar", "US.HOUSING_CONSUMPTION", "1980-01-01"),
    SeriesSpec("FRED", "T10Y2Y", "10-year minus 2-year Treasury spread", "D", "percent", "US.MONETARY", "1980-01-01"),
    SeriesSpec("FRED", "BAA10Y", "Moody's Baa corporate bond spread over 10-year Treasury", "D", "percent", "US.FIN_STABILITY", "1986-01-01"),
    SeriesSpec("FRED", "USREC", "NBER based recession indicator", "M", "binary", "US.ACTIVITY", "1980-01-01"),
    SeriesSpec("FRED", "ICSA", "Initial unemployment insurance claims", "W", "count", "US.LABOR", "1980-01-01"),
    SeriesSpec("FRED", "CCSA", "Continued unemployment insurance claims", "W", "count", "US.LABOR", "1980-01-01"),
    SeriesSpec("FRED", "SP500", "S&P 500 index", "D", "index", "US.EQUITY_MARKET", "2016-01-01"),
    SeriesSpec("FRED", "NASDAQCOM", "Nasdaq Composite index", "D", "index", "US.EQUITY_MARKET", "1990-01-01"),
    SeriesSpec("FRED", "VIXCLS", "CBOE VIX index", "D", "index", "US.EQUITY_MARKET", "1990-01-01"),
    SeriesSpec("FRED", "DTWEXBGS", "Nominal broad US dollar index", "D", "index", "US.MONETARY", "2006-01-01"),
    SeriesSpec("FRED", "DCOILWTICO", "WTI spot price", "D", "usd_per_barrel", "US.COMMODITY_ENERGY", "1990-01-01"),
    SeriesSpec("FRED", "DHHNGSP", "Henry Hub natural gas spot price", "D", "usd_per_mmbtu", "US.COMMODITY_ENERGY", "1997-01-01"),
    SeriesSpec("FRED", "PCOPPUSDM", "Global copper price", "M", "usd_per_metric_ton", "US.COMMODITY_ENERGY", "1990-01-01"),
    SeriesSpec("FRED", "WCESTUS1", "US crude oil stocks excluding SPR", "W", "thousand_barrels", "US.COMMODITY_ENERGY", "1990-01-01"),
    SeriesSpec("FRED", "PALLFNFINDEXM", "IMF all-commodity price index", "M", "index", "US.COMMODITY_ENERGY", "1992-01-01"),
)


BLS_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("BLS", "CUSR0000SA0", "CPI-U all items, seasonally adjusted", "M", "index", "US.INFLATION"),
    SeriesSpec("BLS", "CUSR0000SA0L1E", "CPI-U all items less food and energy", "M", "index", "US.INFLATION"),
    SeriesSpec("BLS", "CES0000000001", "Total nonfarm payrolls", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "LNS14000000", "Civilian unemployment rate", "M", "percent", "US.LABOR"),
    SeriesSpec("BLS", "CES0500000003", "Average hourly earnings, total private", "M", "usd_per_hour", "US.LABOR"),
    SeriesSpec("BLS", "LNS14024887", "Unemployment rate, age 16 to 24", "M", "percent", "US.LABOR"),
    SeriesSpec("BLS", "LNS12324887", "Employment-population ratio, age 16 to 24", "M", "percent", "US.LABOR"),
    SeriesSpec("BLS", "LNS14027662", "Unemployment rate, bachelor's degree and higher, age 25+", "M", "percent", "US.LABOR"),
    SeriesSpec("BLS", "LNS14027660", "Unemployment rate, high-school graduates no college, age 25+", "M", "percent", "US.LABOR"),
    SeriesSpec("BLS", "JTS000000000000000JOL", "JOLTS total nonfarm job openings", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS000000000000000HIL", "JOLTS total nonfarm hires", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS000000000000000QUL", "JOLTS total nonfarm quits", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS000000000000000LDL", "JOLTS total nonfarm layoffs and discharges", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS510099000000000JOL", "JOLTS information job openings", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS510099000000000LDL", "JOLTS information layoffs and discharges", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS540099000000000JOL", "JOLTS professional and business services job openings", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "JTS540099000000000LDL", "JOLTS professional and business services layoffs and discharges", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "CES5000000001", "Information employment", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "CES5000000003", "Information average hourly earnings", "M", "usd_per_hour", "US.LABOR"),
    SeriesSpec("BLS", "CES6000000001", "Professional and business services employment", "M", "thousands", "US.LABOR"),
    SeriesSpec("BLS", "CES6000000003", "Professional and business services average hourly earnings", "M", "usd_per_hour", "US.LABOR"),
)


EIA_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("EIA", "RWTC", "WTI spot price", "W", "usd_per_barrel", "US.COMMODITY_ENERGY"),
)


TREASURY_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("TREASURY", "DEBT_TO_PENNY_TOTAL", "Total public debt outstanding", "D", "usd", "US.FISCAL_TREASURY", "2015-01-01"),
)


STATE_PANEL_STATES: tuple[tuple[str, str], ...] = (
    ("CA", "California"),
    ("TX", "Texas"),
    ("FL", "Florida"),
    ("NY", "New York"),
    ("IL", "Illinois"),
    ("PA", "Pennsylvania"),
    ("OH", "Ohio"),
    ("GA", "Georgia"),
    ("NC", "North Carolina"),
    ("AZ", "Arizona"),
)


def state_panel_specs() -> tuple[SeriesSpec, ...]:
    specs: list[SeriesSpec] = []
    for code, name in STATE_PANEL_STATES:
        specs.extend(
            (
                SeriesSpec("FRED", f"{code}UR", f"Unemployment rate: {name}", "M", "percent", "US.LABOR", "2000-01-01"),
                SeriesSpec("FRED", f"{code}STHPI", f"All-transactions house price index: {name}", "Q", "index", "US.HOUSING_CONSUMPTION", "2000-01-01"),
            )
        )
    return tuple(specs)


ALL_SERIES: tuple[SeriesSpec, ...] = FRED_SERIES + BLS_SERIES + EIA_SERIES + TREASURY_SERIES + state_panel_specs()
SERIES_BY_ID = {spec.series_id: spec for spec in ALL_SERIES}
