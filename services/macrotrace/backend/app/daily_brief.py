from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx

from .llm import DeepSeekClient


@dataclass(frozen=True)
class BriefSource:
    source_id: str
    name: str
    url: str
    home_url: str


SOURCES = (
    BriefSource("FED", "美联储", "https://www.federalreserve.gov/feeds/press_all.xml", "https://www.federalreserve.gov/newsevents.htm"),
    BriefSource("BLS", "美国劳工统计局", "https://www.bls.gov/feed/bls_latest.rss", "https://www.bls.gov/bls/newsrels.htm"),
    BriefSource("SEC", "美国证券交易委员会", "https://www.sec.gov/news/pressreleases.rss", "https://www.sec.gov/newsroom"),
    BriefSource("EIA", "美国能源信息署", "https://www.eia.gov/rss/todayinenergy.xml", "https://www.eia.gov/todayinenergy/"),
    BriefSource("NYFED", "纽约联储自由街经济学", "https://libertystreeteconomics.newyorkfed.org/feed/", "https://libertystreeteconomics.newyorkfed.org/"),
    BriefSource("STLFED", "圣路易斯联储经济研究", "https://www.stlouisfed.org/rss/page%20resources/publications/blog-entries", "https://www.stlouisfed.org/on-the-economy"),
    BriefSource("ATL_GDPNOW", "亚特兰大联储GDPNow", "https://www.atlantafed.org/rss/GDPNow", "https://www.atlantafed.org/cqer/research/gdpnow"),
    BriefSource("ATL_MACROBLOG", "亚特兰大联储宏观经济博客", "https://www.atlantafed.org/rss/macroblog", "https://www.atlantafed.org/blogs/macroblog"),
    BriefSource("CFTC", "美国商品期货交易委员会", "https://www.cftc.gov/RSS/RSSGP/rssgp.xml", "https://www.cftc.gov/PressRoom"),
    BriefSource("CENSUS", "美国人口普查局经济指标", "https://www.census.gov/economic-indicators/indicator.xml", "https://www.census.gov/economic-indicators/"),
)

REPORT_PRODUCTS: dict[str, dict[str, Any]] = {
    "daily": {
        "label": "美国市场日报",
        "description": "把最近 72 小时的来源事实综合成可验证的短线投资观点，适合每日晨会。",
        "lookback_hours": 72,
        "item_limit": 12,
        "report_object": "美国市场过去三个自然日的新信息及其跨资产含义",
        "editorial_focus": "跨来源形成有方向、有资产表达和退出条件的投资观点，事实只作为证据，不逐条复述新闻。",
        "preferred_domains": ["宏观经济", "债券与利率", "股票市场", "能源与商品", "行业与产业"],
        "preferred_source_ids": ["FED", "BLS", "NYFED", "SEC", "EIA"],
    },
    "weekly": {
        "label": "美国市场周报",
        "description": "把一周核心变化综合成跨资产投资观点、分歧与下周验证点。",
        "lookback_hours": 168,
        "item_limit": 18,
        "report_object": "美国市场最近七天的宏观、政策与跨资产变化",
        "editorial_focus": "形成周度投资主线，给出资产方向、催化剂与反证条件，而不是逐条新闻回顾。",
        "preferred_domains": ["宏观经济", "债券与利率", "股票市场", "能源与商品", "行业与产业"],
        "preferred_source_ids": ["FED", "NYFED", "BLS", "SEC", "EIA"],
    },
    "monthly": {
        "label": "美国市场月报",
        "description": "综合近一个月政策、增长与通胀证据，形成中期资产配置观点。",
        "lookback_hours": 744,
        "item_limit": 24,
        "report_object": "美国市场最近一个月的宏观状态、政策路径与资产定价变化",
        "editorial_focus": "突出月度投资判断而非逐条新闻，识别增长、通胀、流动性与风险资产之间可实证检验的中期命题。",
        "preferred_domains": ["宏观经济", "债券与利率", "股票市场", "行业与产业", "能源与商品"],
        "preferred_source_ids": ["BLS", "FED", "NYFED", "SEC", "EIA"],
    },
    "equity": {
        "label": "美股市场报告",
        "description": "形成美股指数、行业与风格的方向性观点，并明确催化剂和退出条件。",
        "lookback_hours": 336,
        "item_limit": 18,
        "report_object": "美国股票市场及其行业、盈利、估值、流动性和风险偏好驱动",
        "editorial_focus": "围绕美股方向与行业分化形成投资观点，说明政策、利率和宏观证据如何传导到盈利预期、估值和风险偏好。",
        "preferred_domains": ["股票市场", "行业与产业", "债券与利率", "宏观经济"],
        "preferred_source_ids": ["SEC", "FED", "NYFED", "BLS"],
    },
    "futures": {
        "label": "美国期货市场报告",
        "description": "形成能源、金属、农产品与金融期货的方向性观点和条件性交易表达。",
        "lookback_hours": 336,
        "item_limit": 18,
        "report_object": "美国相关期货市场的供需、库存、期限结构、美元与利率驱动",
        "editorial_focus": "优先形成能源与商品投资观点，并把供需、库存、美元、利率、增长和通胀证据连接到可实证检验的期货命题。",
        "preferred_domains": ["能源与商品", "宏观经济", "债券与利率", "行业与产业"],
        "preferred_source_ids": ["EIA", "FED", "BLS", "NYFED"],
    },
}

DOMAIN_TERMS = {
    "宏观经济": ("inflation", "employment", "gdp", "economy", "cpi", "pce", "通胀", "就业", "经济"),
    "股票市场": ("stock", "equity", "index", "earnings", "market", "股票", "指数", "盈利"),
    "债券与利率": ("yield", "treasury", "rate", "fomc", "bond", "收益率", "利率", "国债"),
    "行业与产业": ("industry", "sector", "manufacturing", "bank", "technology", "行业", "制造", "银行", "科技"),
    "能源与商品": ("oil", "gas", "energy", "commodity", "原油", "天然气", "能源", "商品"),
}

BRIEF_SCHEMA_VERSION = "0.6.0"
REPORT_HORIZONS = {
    "daily": "下一交易日至未来三个交易日",
    "weekly": "未来一至两周",
    "monthly": "未来一至三个月",
    "equity": "未来一至四周",
    "futures": "未来一至四周",
}
VIEWPOINT_REQUIRED_TEXT_FIELDS = (
    "headline",
    "summary",
    "significance",
    "stance",
    "asset_expression",
    "time_horizon",
    "core_thesis",
    "confidence",
    "confidence_basis",
    "support_level",
    "empirical_question",
)
VIEWPOINT_REQUIRED_LIST_FIELDS = (
    "catalysts",
    "falsifiers",
    "exit_conditions",
    "evidence_refs",
    "source_refs",
)

_MARKET_TERM_TRANSLATIONS = {
    "risk-on": "风险偏好上升",
    "risk on": "风险偏好上升",
    "risk-off": "风险偏好下降",
    "risk off": "风险偏好下降",
}
_UNSUPPORTED_TECHNICAL_PHRASES = ("突破上轨", "突破下轨", "上升通道", "下降通道", "金叉", "死叉")


def _chinese_market_language(value: str) -> str:
    text = value
    for term, translation in _MARKET_TERM_TRANSLATIONS.items():
        text = re.sub(re.escape(term), translation, text, flags=re.IGNORECASE)
    return _clean(text)


def _string_list(value: Any, *, limit: int = 6, item_limit: int = 300) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _chinese_market_language(str(item))[:item_limit]
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _has_viewpoint_contract(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    if any(not _clean(str(item.get(field) or "")) for field in VIEWPOINT_REQUIRED_TEXT_FIELDS):
        return False
    if any(not _string_list(item.get(field)) for field in VIEWPOINT_REQUIRED_LIST_FIELDS):
        return False
    return str(item.get("confidence")) in {"高", "中", "低"}


def _has_current_brief_contract(payload: Any, report_type: str) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("schema_version") != BRIEF_SCHEMA_VERSION or payload.get("report_mode") != "investment_views":
        return False
    if payload.get("report_type") != report_type or not isinstance(payload.get("items"), list):
        return False
    return all(_has_viewpoint_contract(item) for item in payload["items"])


def _contains_unsupported_market_claim(update: dict[str, Any], evidence_text: str) -> bool:
    output_text = json.dumps(update, ensure_ascii=False)
    for phrase in _UNSUPPORTED_TECHNICAL_PHRASES:
        if phrase in output_text and phrase not in evidence_text:
            return True
    precise_patterns = (
        r"[$￥¥]\s*\d+(?:\.\d+)?",
        r"\d+(?:\.\d+)?\s*%",
        r"(?:目标价|目标收益|预期收益)[^，。；]{0,18}\d",
    )
    for pattern in precise_patterns:
        for match in re.findall(pattern, output_text):
            if str(match) not in evidence_text:
                return True
    return False


def _clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()


def _published(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        return None


def _domain(text: str) -> str:
    lowered = text.lower()
    scores = {
        domain: sum(1 for term in terms if term in lowered)
        for domain, terms in DOMAIN_TERMS.items()
    }
    return max(scores, key=scores.get) if max(scores.values(), default=0) else "综合市场"


class OfficialSourceSearchAgent:
    """Small source-bound search agent: fetch official feeds, never invent an item."""

    def _fetch_source(self, source: BriefSource, cutoff: datetime) -> tuple[list[dict[str, Any]], dict[str, str]]:
        now = datetime.now(UTC)
        items: list[dict[str, Any]] = []
        headers = {"User-Agent": "MacroTrace-DailyBrief/0.5 research@example.invalid"}
        try:
            with httpx.Client(timeout=12, follow_redirects=True, headers=headers) as client:
                response = client.get(source.url)
                response.raise_for_status()
            root = ET.fromstring(response.content)
            entries = list(root.findall(".//item")) + list(root.findall(".//{*}entry"))
            for entry in entries[:30]:
                title = _clean(entry.findtext("title") or entry.findtext("{*}title") or "")
                summary = _clean(entry.findtext("description") or entry.findtext("summary") or entry.findtext("{*}summary") or "")
                link = _clean(entry.findtext("link") or "")
                if not link:
                    link_node = entry.find("{*}link")
                    if link_node is not None:
                        link = str(link_node.attrib.get("href") or "")
                published = _published(entry.findtext("pubDate") or entry.findtext("published") or entry.findtext("updated") or entry.findtext("{*}published") or entry.findtext("{*}updated") or "")
                if not title or not link or (published and published < cutoff):
                    continue
                item_id = hashlib.sha256(f"{source.source_id}|{link}".encode("utf-8")).hexdigest()[:16]
                recency = max(0.0, 1.0 - ((now - published).total_seconds() / 3600 / 168)) if published else 0.25
                items.append({
                    "item_id": item_id, "source_id": source.source_id, "source_name": source.name,
                    "source_home": source.home_url, "title": title[:300], "source_summary": summary[:900],
                    "url": link, "published_at": published.isoformat() if published else None,
                    "domain": _domain(f"{title} {summary}"), "recency_score": round(recency, 4),
                })
            return items, {"source_id": source.source_id, "name": source.name, "status": "成功", "items": str(len(items))}
        except Exception:
            return [], {"source_id": source.source_id, "name": source.name, "status": "暂不可用", "items": "0"}

    def search(
        self,
        lookback_hours: int = 72,
        source_ids: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
        items: list[dict[str, Any]] = []
        source_states: list[dict[str, str]] = []
        allowed = set(source_ids or [source.source_id for source in SOURCES])
        selected_sources = [source for source in SOURCES if source.source_id in allowed]
        if not selected_sources:
            return [], []
        with ThreadPoolExecutor(max_workers=len(selected_sources), thread_name_prefix="daily-source") as pool:
            futures = {pool.submit(self._fetch_source, source, cutoff): source for source in selected_sources}
            for future in as_completed(futures):
                rows, state = future.result()
                items.extend(rows)
                source_states.append(state)
        source_states.sort(key=lambda state: state["source_id"])
        unique = {item["url"]: item for item in items}
        ordered = sorted(
            unique.values(),
            key=lambda item: item.get("published_at") or "",
            reverse=True,
        )
        return ordered[:36], source_states


class DailyBriefSelectionAgent:
    """Deterministically ranks coverage before the language model sees it."""

    def select(
        self,
        items: list[dict[str, Any]],
        limit: int = 12,
        preferred_domains: list[str] | None = None,
        preferred_source_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        domain_counts: dict[str, int] = {}
        selected: list[dict[str, Any]] = []
        domain_rank = {value: index for index, value in enumerate(preferred_domains or [])}
        source_rank = {value: index for index, value in enumerate(preferred_source_ids or [])}

        def ranking(item: dict[str, Any]) -> tuple[float, int, int, int]:
            domain = str(item.get("domain") or "综合市场")
            source_id = str(item.get("source_id") or "")
            domain_bonus = max(0.0, 0.22 - domain_rank.get(domain, 99) * 0.035) if domain in domain_rank else 0.0
            source_bonus = max(0.0, 0.12 - source_rank.get(source_id, 99) * 0.02) if source_id in source_rank else 0.0
            return (
                float(item.get("recency_score") or 0) + domain_bonus + source_bonus,
                int(bool(item.get("source_summary"))),
                -domain_rank.get(domain, 99),
                -source_rank.get(source_id, 99),
            )

        ranked = sorted(items, key=ranking, reverse=True)
        per_domain_limit = max(4, (limit + 2) // 3)
        for item in ranked:
            domain = str(item.get("domain") or "综合市场")
            if domain_counts.get(domain, 0) >= per_domain_limit:
                continue
            selected.append(item)
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            if len(selected) >= limit:
                break
        return selected


class DailyBriefService:
    def __init__(self, cache_dir: Path, llm: DeepSeekClient) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.llm = llm
        self.search_agent = OfficialSourceSearchAgent()
        self.selection_agent = DailyBriefSelectionAgent()

    def cache_path(self, report_type: str = "daily") -> Path:
        safe_type = report_type if report_type in REPORT_PRODUCTS else "daily"
        return self.cache_dir / f"latest_US_{safe_type}.json"

    def catalog(self) -> dict[str, Any]:
        return {
            "market": "US",
            "sources": [
                {
                    "source_id": source.source_id,
                    "name": source.name,
                    "home_url": source.home_url,
                    "kind": "官方动态与研究",
                    "description": {
                        "FED": "货币政策、监管与美联储公告",
                        "BLS": "就业、工资、通胀与生产率",
                        "SEC": "资本市场监管与公司披露动态",
                        "EIA": "原油、天然气、电力与能源市场",
                        "NYFED": "金融条件、市场运行与联储研究",
                        "STLFED": "美国经济、通胀、就业与金融市场研究",
                        "ATL_GDPNOW": "美国实际国内生产总值即时预测更新",
                        "ATL_MACROBLOG": "宏观经济、支付体系与金融研究",
                        "CFTC": "期货、掉期、衍生品监管与市场动态",
                        "CENSUS": "零售、住房、制造业、贸易与企业活动指标",
                    }.get(source.source_id, "美国官方公开信息"),
                    "default_selected": True,
                }
                for source in SOURCES
            ],
            "report_products": [
                {"report_type": report_type, **spec}
                for report_type, spec in REPORT_PRODUCTS.items()
            ],
        }

    @staticmethod
    def _fallback_profile(report_type: str, domain: str) -> dict[str, Any]:
        horizon = REPORT_HORIZONS.get(report_type, REPORT_HORIZONS["daily"])
        if domain in {"宏观经济", "债券与利率"}:
            stance = "条件性偏多"
            asset_expression = "美国中长期国债ETF或等方向的利率多头工具"
            confirmation = "增长、通胀或政策证据共同支持利率下行方向"
        elif domain in {"股票市场", "行业与产业"}:
            stance = "防守性低配"
            asset_expression = "降低高波动美国股票指数或行业ETF敞口，增配现金类及美国短期国债工具"
            confirmation = "盈利、流动性和风险偏好证据至少有两项转为同向改善"
        elif domain == "能源与商品":
            stance = "防守性减仓"
            asset_expression = "降低原油及能源商品期货的单边方向敞口，增配现金类工具"
            confirmation = "供需、库存和宏观定价证据形成同向确认"
        else:
            stance = "防守性偏多现金"
            asset_expression = "现金类及美国短期国债工具，同时降低高波动风险资产敞口"
            confirmation = "跨来源证据对增长、流动性和风险偏好形成一致方向"
        return {
            "stance": stance,
            "asset_expression": asset_expression,
            "time_horizon": horizon,
            "confirmation": confirmation,
        }

    def _fallback(
        self,
        source_items: list[dict[str, Any]],
        source_states: list[dict[str, str]],
        report_type: str = "daily",
    ) -> dict[str, Any]:
        product = REPORT_PRODUCTS.get(report_type, REPORT_PRODUCTS["daily"])
        selected_evidence = self.selection_agent.select(
            source_items,
            int(product["item_limit"]),
            preferred_domains=list(product["preferred_domains"]),
            preferred_source_ids=list(product["preferred_source_ids"]),
        )
        grouped: dict[str, list[dict[str, Any]]] = {}
        for evidence in selected_evidence:
            grouped.setdefault(str(evidence.get("domain") or "综合市场"), []).append(evidence)
        ordered_domains = list(product["preferred_domains"])
        ordered_domains.extend(domain for domain in grouped if domain not in ordered_domains)

        views: list[dict[str, Any]] = []
        for domain in ordered_domains:
            evidence_rows = grouped.get(domain) or []
            if not evidence_rows:
                continue
            profile = self._fallback_profile(report_type, domain)
            evidence_refs = [str(row["item_id"]) for row in evidence_rows]
            source_refs = list(dict.fromkeys(str(row.get("source_id") or "") for row in evidence_rows if row.get("source_id")))
            primary = evidence_rows[0]
            view_id = hashlib.sha256(
                f"{report_type}|{domain}|{'|'.join(evidence_refs)}".encode("utf-8")
            ).hexdigest()[:16]
            core_thesis = (
                f"现有{domain}来源事实尚未经过可靠的方向语义综合，因此先采取{profile['stance']}而不是追逐单条消息；"
                f"只有当{profile['confirmation']}时，才把该筛选观点升级为执行级观点。"
            )
            catalysts = [
                f"后续{domain}官方更新与当前条件形成方向一致的确认",
                "至少两个独立来源给出同方向证据",
            ]
            falsifiers = [
                "同一来源的后续数据或表述与当前条件相反",
                "跨来源信号持续分歧，无法支持同一传导方向",
            ]
            exit_conditions = [
                "任一反证条件触发时退出该条件性表达",
                "在证据没有形成一致方向前不把筛选观点升级为执行级仓位",
            ]
            views.append(
                {
                    "item_id": view_id,
                    "view_type": "investment_view",
                    "domain": domain,
                    "headline": f"{profile['stance']}：{profile['asset_expression']}",
                    "summary": core_thesis,
                    "significance": (
                        f"投资表达为{profile['asset_expression']}，观察期限为{profile['time_horizon']}；"
                        f"证据转向或持续分歧时退出。"
                    ),
                    "stance": profile["stance"],
                    "asset_expression": profile["asset_expression"],
                    "time_horizon": profile["time_horizon"],
                    "core_thesis": core_thesis,
                    "catalysts": catalysts,
                    "falsifiers": falsifiers,
                    "exit_conditions": exit_conditions,
                    "confidence": "低",
                    "confidence_basis": "仅完成来源级聚合，未完成可靠的中文语义和方向交叉验证。",
                    "support_level": "筛选级观点",
                    "evidence_refs": evidence_refs,
                    "source_refs": source_refs,
                    "empirical_question": (
                        f"检验“{profile['stance']}、通过{profile['asset_expression']}表达”的观点在{profile['time_horizon']}是否成立："
                        "评估所列证据的方向、传导机制、表现幅度、持续性、异质性以及触发退出的反证条件。"
                    ),
                    "source_id": str(primary.get("source_id") or ""),
                    "source_name": str(primary.get("source_name") or "来源未标注"),
                    "source_home": str(primary.get("source_home") or ""),
                    "title": str(primary.get("title") or ""),
                    "source_summary": str(primary.get("source_summary") or ""),
                    "url": str(primary.get("url") or ""),
                    "published_at": primary.get("published_at"),
                    "generation_mode": "跨来源条件性观点回退",
                    "evidence": [
                        {
                            key: row.get(key)
                            for key in ("item_id", "source_id", "source_name", "title", "url", "published_at")
                        }
                        for row in evidence_rows
                    ],
                }
            )
        available_sources = sum(state["status"] == "成功" for state in source_states)
        if views:
            report_summary = (
                f"本期从 {available_sources} 个可用来源的 {len(selected_evidence)} 条事实证据中，按领域综合出 {len(views)} 条投资观点。"
                "当前为低置信度筛选级结果：保持明确的防守倾向，并以催化剂和反证条件决定是否升级。"
            )
        else:
            report_summary = "本期没有取得可引用的来源事实，因此不生成无证据的投资观点，当前行动倾向为不交易并等待来源恢复。"
        return {
            "schema_version": BRIEF_SCHEMA_VERSION,
            "report_mode": "investment_views",
            "market": "US",
            "market_label": "美国市场",
            "report_type": report_type,
            "report_label": product["label"],
            "report_object": product["report_object"],
            "lookback_hours": int(product["lookback_hours"]),
            "item_limit": int(product["item_limit"]),
            "preferred_domains": list(product["preferred_domains"]),
            "preferred_source_ids": list(product["preferred_source_ids"]),
            "generated_at": datetime.now(UTC).isoformat(),
            "as_of_label": "最近可获取的市场信息",
            "headline": f"{product['label']}｜投资观点",
            "summary": report_summary,
            "action_posture": "筛选级防守" if views else "不交易",
            "source_states": source_states,
            "evidence_catalog": selected_evidence,
            "items": views,
            "limitations": [
                "事实只作为观点证据，不把逐条来源摘要当作投资结论。",
                "语言模型不可用时仅给出低置信度、条件性的筛选观点，不生成未经来源支持的价格、技术突破或精确收益判断。",
                "来源发布时间缺失的证据可能不是当天发布。",
            ],
        }

    def _llm_generate(self, fallback: dict[str, Any]) -> dict[str, Any]:
        if not self.llm.available or not fallback["items"]:
            return fallback
        payload_items = [
            {
                key: item.get(key)
                for key in ("item_id", "source_id", "source_name", "title", "source_summary", "url", "published_at", "domain")
            }
            for item in fallback["evidence_catalog"]
        ]
        view_slots = [
            {
                key: item.get(key)
                for key in ("item_id", "domain", "time_horizon", "evidence_refs", "source_refs")
            }
            for item in fallback["items"]
        ]
        market_label = "美国市场"
        report_label = str(fallback.get("report_label") or "美国市场日报")
        report_object = str(fallback.get("report_object") or "美国市场最近变化")
        editorial_focus = str(
            REPORT_PRODUCTS.get(str(fallback.get("report_type") or "daily"), REPORT_PRODUCTS["daily"])["editorial_focus"]
        )
        system = f"""
你是服务买方研究员的投资观点综合 Agent。本期生成“{report_label}”，研究对象是“{report_object}”，市场范围仅限{market_label}。编辑重点是：{editorial_focus}

这不是新闻汇总。source_items 中的事实只能作为 evidence，报告正文必须跨条目、尽可能跨来源综合成可交易、可证伪的投资观点。全文强制使用中文：risk-on 必须写成“风险偏好上升”，risk-off 必须写成“风险偏好下降”，其他英文市场黑话也应翻译为中文。

每条观点必须有明确倾向，禁止只写“关注”“中性”或重复事实。必须给出：stance（例如偏多、偏空、减仓、增配）、asset_expression（资产类别、指数/行业ETF或期货等工具表达）、time_horizon、core_thesis、catalysts、falsifiers、exit_conditions、confidence（只能为高/中/低）、confidence_basis、support_level、evidence_refs、source_refs、empirical_question。empirical_question 必须检验观点方向、传导机制、幅度、期限、异质性和反证条件，而不是检验新闻真假。

只能引用输入中的 view slot、evidence item_id 和 source_id，不得创造来源。证据不足或只有单一来源时仍要给出明确的条件性倾向，但 support_level 必须写“筛选级观点”或“条件性观点”，confidence 必须为低。禁止添加来源没有出现的价格点位、技术突破、通道、精确收益率、目标价或确定性因果；可以提出明确标注为条件性的传导假设。不能把美股报告写成泛宏观日报，也不能把期货报告写成股票评论。

只输出 JSON，包含 headline、summary、items。items 使用 view_slots 的 item_id，每项完整包含上述字段，另保留 headline、summary、significance。headline 直接写投资判断；summary 写核心论点；significance 写资产表达、期限、催化剂和退出逻辑。不要使用“主命题”“Registry”“泳道”等工程词。
""".strip()
        output = self.llm.json_completion(
            system,
            json.dumps(
                {
                    "report_type": fallback.get("report_type"),
                    "report_label": report_label,
                    "report_object": report_object,
                    "view_slots": view_slots,
                    "source_items": payload_items,
                },
                ensure_ascii=False,
            ),
            max_tokens=4200,
        )
        if not {"headline", "summary", "items"}.issubset(output) or not isinstance(output["items"], list):
            raise ValueError("invalid daily brief contract")
        allowed_ids = {item["item_id"] for item in fallback["items"]}
        updates = {
            str(item.get("item_id")): item
            for item in output["items"]
            if isinstance(item, dict) and str(item.get("item_id")) in allowed_ids
        }
        if not updates:
            raise ValueError("daily brief contains no valid investment view")
        evidence_by_id = {str(item["item_id"]): item for item in fallback["evidence_catalog"]}
        required = {"item_id", *VIEWPOINT_REQUIRED_TEXT_FIELDS, *VIEWPOINT_REQUIRED_LIST_FIELDS}
        merged: list[dict[str, Any]] = []
        for base_view in fallback["items"]:
            update = updates.get(base_view["item_id"])
            if not update or not required.issubset(update):
                merged.append(base_view)
                continue
            candidate_refs = set(base_view["evidence_refs"])
            evidence_refs = [ref for ref in _string_list(update.get("evidence_refs"), limit=12, item_limit=80) if ref in candidate_refs]
            if not evidence_refs:
                merged.append(base_view)
                continue
            evidence_text = " ".join(
                f"{evidence_by_id[ref].get('title', '')} {evidence_by_id[ref].get('source_summary', '')}"
                for ref in evidence_refs
                if ref in evidence_by_id
            )
            if _contains_unsupported_market_claim(update, evidence_text):
                merged.append(base_view)
                continue
            catalysts = _string_list(update.get("catalysts"))
            falsifiers = _string_list(update.get("falsifiers"))
            exit_conditions = _string_list(update.get("exit_conditions"))
            if not catalysts or not falsifiers or not exit_conditions:
                merged.append(base_view)
                continue
            source_refs = list(
                dict.fromkeys(
                    str(evidence_by_id[ref].get("source_id") or "")
                    for ref in evidence_refs
                    if ref in evidence_by_id and evidence_by_id[ref].get("source_id")
                )
            )
            confidence = _chinese_market_language(str(update.get("confidence") or ""))
            support_level = _chinese_market_language(str(update.get("support_level") or ""))
            if confidence not in {"高", "中", "低"} or not source_refs:
                merged.append(base_view)
                continue
            if len(source_refs) < 2:
                confidence = "低"
                support_level = "筛选级观点"
            primary = evidence_by_id[evidence_refs[0]]
            model_view = {
                **base_view,
                "headline": _chinese_market_language(str(update["headline"]))[:180],
                "summary": _chinese_market_language(str(update["summary"]))[:700],
                "significance": _chinese_market_language(str(update["significance"]))[:600],
                "stance": _chinese_market_language(str(update["stance"]))[:80],
                "asset_expression": _chinese_market_language(str(update["asset_expression"]))[:240],
                "time_horizon": _chinese_market_language(str(update["time_horizon"]))[:100],
                "core_thesis": _chinese_market_language(str(update["core_thesis"]))[:800],
                "catalysts": catalysts,
                "falsifiers": falsifiers,
                "exit_conditions": exit_conditions,
                "confidence": confidence,
                "confidence_basis": _chinese_market_language(str(update["confidence_basis"]))[:360],
                "support_level": support_level[:80],
                "evidence_refs": evidence_refs,
                "source_refs": source_refs,
                "empirical_question": _chinese_market_language(str(update["empirical_question"]))[:700],
                "source_id": str(primary.get("source_id") or ""),
                "source_name": str(primary.get("source_name") or "来源未标注"),
                "source_home": str(primary.get("source_home") or ""),
                "title": str(primary.get("title") or ""),
                "source_summary": str(primary.get("source_summary") or ""),
                "url": str(primary.get("url") or ""),
                "published_at": primary.get("published_at"),
                "generation_mode": "跨来源投资观点综合",
            }
            merged.append(model_view if _has_viewpoint_contract(model_view) else base_view)
        if not any(item.get("generation_mode") == "跨来源投资观点综合" for item in merged):
            raise ValueError("daily brief contains no complete investment view")
        return {
            **fallback,
            "headline": _chinese_market_language(str(output["headline"]))[:220],
            "summary": _chinese_market_language(str(output["summary"]))[:1200],
            "action_posture": "观点已生成，按催化剂和退出条件执行",
            "items": merged,
        }

    def generate(
        self,
        lookback_hours: int | None = None,
        source_ids: list[str] | None = None,
        report_type: str = "daily",
    ) -> dict[str, Any]:
        product = REPORT_PRODUCTS.get(report_type, REPORT_PRODUCTS["daily"])
        effective_hours = int(lookback_hours or product["lookback_hours"])
        if source_ids is None:
            source_items, source_states = self.search_agent.search(effective_hours)
        else:
            source_items, source_states = self.search_agent.search(effective_hours, source_ids)
        fallback = self._fallback(source_items, source_states, report_type)
        try:
            result = self._llm_generate(fallback)
        except Exception:
            result = fallback
            result["limitations"].append("语言模型投资观点未通过结构校验，本轮已回退到按领域聚合的条件性观点。")
        cache_path = self.cache_path(report_type)
        temporary = cache_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(cache_path)
        return result

    def latest(self, report_type: str = "daily") -> dict[str, Any]:
        cache_path = self.cache_path(report_type)
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                cached = None
            if _has_current_brief_contract(cached, report_type):
                return cached
        return self.generate(report_type=report_type)

    def research_question(self, excerpt: str) -> dict[str, str]:
        excerpt = _clean(excerpt)[:1800]
        if len(excerpt) < 8:
            raise ValueError("selected excerpt is too short")
        market_label = "美国市场"
        fallback = (
            f"围绕以下{market_label}观点，系统检验它是否成立，并评估主要传导机制、影响方向与幅度、"
            f"持续时间、不同情景下的异质性以及可能推翻该观点的证据：{excerpt}"
        )
        if not self.llm.available:
            return {"question": fallback, "mode": "结构化回退"}
        system = f"""
你是实证研究问题编辑器。把用户从{market_label}日报或研报中选中的文字，改写成一条值得投入完整实证流程的大问题。问题必须直接保留原观点的对象与方向，并要求检验：观点是否成立、传导机制、影响幅度、持续时间或预测期限、异质性和反证条件。禁止把它缩窄成两个变量的普通相关系数问题。不要虚构原文没有的数字。只输出 JSON：{{"question":"..."}}。
""".strip()
        try:
            output = self.llm.json_completion(system, json.dumps({"excerpt": excerpt}, ensure_ascii=False), max_tokens=700)
            question = _clean(str(output.get("question") or ""))
            if len(question) < 20:
                raise ValueError("question too short")
            return {"question": question[:1800], "mode": "模型编译"}
        except Exception:
            return {"question": fallback, "mode": "结构化回退"}
