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
)

DOMAIN_TERMS = {
    "宏观经济": ("inflation", "employment", "gdp", "economy", "cpi", "pce", "通胀", "就业", "经济"),
    "股票市场": ("stock", "equity", "index", "earnings", "market", "股票", "指数", "盈利"),
    "债券与利率": ("yield", "treasury", "rate", "fomc", "bond", "收益率", "利率", "国债"),
    "行业与产业": ("industry", "sector", "manufacturing", "bank", "technology", "行业", "制造", "银行", "科技"),
    "能源与商品": ("oil", "gas", "energy", "commodity", "原油", "天然气", "能源", "商品"),
}


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

    def search(self, lookback_hours: int = 72) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
        items: list[dict[str, Any]] = []
        source_states: list[dict[str, str]] = []
        with ThreadPoolExecutor(max_workers=len(SOURCES), thread_name_prefix="daily-source") as pool:
            futures = {pool.submit(self._fetch_source, source, cutoff): source for source in SOURCES}
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

    def select(self, items: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
        domain_counts: dict[str, int] = {}
        selected: list[dict[str, Any]] = []
        ranked = sorted(items, key=lambda item: (float(item.get("recency_score") or 0), bool(item.get("source_summary"))), reverse=True)
        for item in ranked:
            domain = str(item.get("domain") or "综合市场")
            if domain_counts.get(domain, 0) >= 4:
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

    @property
    def cache_path(self) -> Path:
        return self.cache_dir / "latest_US.json"

    def _fallback(self, source_items: list[dict[str, Any]], source_states: list[dict[str, str]]) -> dict[str, Any]:
        questions = {
            "宏观经济": "围绕这项更新，系统评估美国经济所处状态、主要传导机制、影响幅度、持续时间与下行情景。",
            "股票市场": "围绕这项更新，系统评估其对美股方向、行业分化、盈利预期、风险偏好与未来定价的影响。",
            "债券与利率": "围绕这项更新，系统评估其对美债利率曲线、期限溢价、信用利差与流动性的影响。",
            "行业与产业": "围绕这项更新，系统评估相关美国行业的需求、供给、产能、利润率与相对收益影响。",
            "能源与商品": "围绕这项更新，系统评估供需、库存、期限结构与美元如何影响美国能源、金属或农产品期货。",
            "综合市场": "围绕这项更新，系统评估其对美国增长、政策、流动性以及股票、债券和期货的跨资产影响。",
        }
        cards = []
        for item in self.selection_agent.select(source_items):
            domain = str(item.get("domain") or "综合市场")
            cards.append(
                {
                    **item,
                    "headline": f"{item['source_name']}发布{domain}最新信息",
                    "summary": f"该官方来源发布了一项与{domain}相关的更新。自动中文译写未通过时，系统不会把未经核对的英文摘要伪装成中文结论；可打开原文查看完整口径。",
                    "significance": f"这项信息可能改变对{domain}最新状态的判断，适合进一步连接真实数据与注册模型进行检验。",
                    "empirical_question": questions[domain],
                    "generation_mode": "中文安全回退",
                }
            )
        return {
            "schema_version": "0.5.0",
            "market": "US",
            "market_label": "美国市场",
            "generated_at": datetime.now(UTC).isoformat(),
            "as_of_label": "最近可获取的市场信息",
            "headline": "美国市场每日研究简报",
            "summary": f"本轮从 {sum(state['status'] == '成功' for state in source_states)} 个可用官方来源整理出 {len(cards)} 条更新。中文日报编辑不可用时，仅展示来源约束的中文分类摘要，不生成未经核对的细节。",
            "source_states": source_states,
            "items": cards,
            "limitations": ["只收录本轮成功读取且保留原文链接的条目。", "来源发布时间缺失的条目可能不是当天发布。"],
        }

    def _llm_generate(self, fallback: dict[str, Any]) -> dict[str, Any]:
        if not self.llm.available or not fallback["items"]:
            return fallback
        payload_items = [
            {key: item.get(key) for key in ("item_id", "source_name", "title", "source_summary", "published_at", "domain")}
            for item in fallback["items"]
        ]
        market_label = "美国市场"
        system = f"""
你是服务买方研究员的日报编辑 Agent，本期市场为{market_label}。你只能依据给定来源写中文 A4 日报，禁止补充外部事实、价格、数字或因果关系。输出 JSON，必须包含 headline、summary、items。items 逐条使用输入 item_id，不得创造来源；每项包含 item_id、headline、summary、significance、empirical_question。headline 是事实约束下的中文短标题；summary 说明来源说了什么；significance 说明为什么值得跟踪。empirical_question 不是狭窄的两变量相关性问题，而是值得投入完整实证流程的研究问题：应围绕来源观点，要求评估其是否成立、经济或定价机制、影响方向与幅度、持续时间、异质性以及反证条件。不要使用“主命题”“Registry”“泳道”等工程词。
""".strip()
        output = self.llm.json_completion(system, json.dumps({"source_items": payload_items}, ensure_ascii=False), max_tokens=4200)
        if not {"headline", "summary", "items"}.issubset(output) or not isinstance(output["items"], list):
            raise ValueError("invalid daily brief contract")
        allowed_ids = {item["item_id"] for item in fallback["items"]}
        updates = {
            str(item.get("item_id")): item
            for item in output["items"]
            if isinstance(item, dict) and str(item.get("item_id")) in allowed_ids
        }
        if not updates:
            raise ValueError("daily brief contains no valid source item")
        required = {"item_id", "headline", "summary", "significance", "empirical_question"}
        merged = []
        for item in fallback["items"]:
            update = updates.get(item["item_id"])
            if not update or not required.issubset(update):
                merged.append(item)
                continue
            merged.append(
                {
                    **item,
                    "headline": str(update["headline"]).strip()[:180],
                    "summary": str(update["summary"]).strip()[:600],
                    "significance": str(update["significance"]).strip()[:500],
                    "empirical_question": str(update["empirical_question"]).strip()[:500],
                    "generation_mode": "来源约束的模型摘要",
                }
            )
        return {**fallback, "headline": str(output["headline"]).strip()[:220], "summary": str(output["summary"]).strip()[:1000], "items": merged}

    def generate(self, lookback_hours: int = 72) -> dict[str, Any]:
        source_items, source_states = self.search_agent.search(lookback_hours)
        fallback = self._fallback(source_items, source_states)
        try:
            result = self._llm_generate(fallback)
        except Exception:
            result = fallback
            result["limitations"].append("语言模型日报编辑未通过结构校验，本轮已回退到来源摘要。")
        temporary = self.cache_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.cache_path)
        return result

    def latest(self) -> dict[str, Any]:
        if self.cache_path.exists():
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        return self.generate()

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
