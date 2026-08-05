from __future__ import annotations

import json
import re
from contextvars import ContextVar
from datetime import date
from typing import Any, Callable

from pydantic import ValidationError

from .llm import DeepSeekClient
from .registry import RegistryError, RegistryStore
from .schemas import (
    Coverage,
    FactorDecision,
    HorizonSpec,
    LaneDecision,
    MechanismDecision,
    ModelDecision,
    ModelSpecificationDecision,
    NodeDecision,
    ParameterSelection,
    ResearchPlan,
    StructuredQuery,
)


Emit = Callable[[str, dict[str, Any]], None]


CHINESE_NUMBERS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十二": 12,
    "十八": 18,
    "二十四": 24,
}


def _number(value: str) -> int | None:
    value = value.strip()
    if value.isdigit():
        return int(value)
    if value in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[value]
    if value.startswith("十") and len(value) == 2:
        return 10 + CHINESE_NUMBERS.get(value[1], 0)
    if len(value) == 2 and value[1] == "十":
        return CHINESE_NUMBERS.get(value[0], 0) * 10
    return None


def extract_horizon(question: str, default: dict[str, Any]) -> HorizonSpec:
    patterns = [
        (r"明天|下一个交易日|tomorrow|next trading day", "NEXT_DAY"),
        (r"(?:未来|接下来)\s*([0-9一二两三四五六七八九十十二十八二十四]+)\s*(?:到|至|[-–—])\s*([0-9一二两三四五六七八九十十二十八二十四]+)\s*个?月", "MONTHS"),
        (r"([0-9一二两三四五六七八九十十二十八二十四]+)\s*(?:到|至|[-–—])\s*([0-9一二两三四五六七八九十十二十八二十四]+)\s*个月", "MONTHS"),
        (r"(?:未来|接下来)\s*([0-9一二两三四五六七八九十十二十八二十四]+)\s*个?月", "MONTHS"),
        (r"下(?:一)?个?月", "NEXT_MONTH"),
        (r"([0-9一二两三四五六七八九十十二十八二十四]+)\s*个月", "MONTHS"),
        (r"(?:next|over the next)\s+(\d+)\s*(?:to|-)\s*(\d+)\s*months?", "MONTHS"),
        (r"(?:next|over the next)\s+(\d+)\s*months?", "MONTHS"),
        (r"(?:未来|接下来)?\s*([0-9一二两三四五六七八九十]+)\s*个?季度", "QUARTERS"),
        (r"(?:未来|接下来)?\s*([0-9一二两三四五六七八九十]+)\s*年", "YEARS"),
    ]
    for pattern, unit in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if not match:
            continue
        if unit == "NEXT_MONTH":
            return HorizonSpec(
                minimum=1,
                maximum=1,
                unit="MONTHS",
                source="USER_EXPLICIT",
                raw_text=match.group(0),
            )
        if unit == "NEXT_DAY":
            return HorizonSpec(
                minimum=1,
                maximum=1,
                unit="DAYS",
                source="USER_EXPLICIT",
                raw_text=match.group(0),
            )
        values = [_number(value) for value in match.groups() if value is not None]
        if values and all(value is not None for value in values):
            low = int(values[0])
            high = int(values[-1])
            return HorizonSpec(
                minimum=min(low, high),
                maximum=max(low, high),
                unit=unit,
                source="USER_EXPLICIT",
                raw_text=match.group(0),
            )
    return HorizonSpec(
        minimum=default["minimum"],
        maximum=default["maximum"],
        unit=default["unit"],
        source="POLICY_DEFAULT",
        raw_text=None,
    )


def _concepts(question: str) -> list[str]:
    text = question.lower()
    groups = {
        "inflation": ("inflation", "cpi", "pce", "通胀", "物价"),
        "activity": ("growth", "gdp", "activity", "经济", "增长", "走弱", "加速"),
        "recession": ("recession", "衰退"),
        "labor": ("labor", "employment", "unemployment", "wage", "就业", "失业", "工资"),
        "rates": ("yield", "rate", "treasury", "fed", "收益率", "利率", "美债", "美联储"),
        "energy": ("oil", "wti", "brent", "natural gas", "energy", "crude", "油价", "原油", "天然气", "能源"),
        "fiscal": ("fiscal", "debt", "deficit", "issuance", "财政", "债务", "赤字", "发行"),
        "housing": ("housing", "house price", "房价", "住房"),
        "panel": ("panel", "fixed effect", "面板", "固定效应"),
        "trade": ("trade", "tariff", "import", "export", "贸易", "关税", "进口", "出口"),
        "ai": ("artificial intelligence", "ai", "人工智能"),
        "equity": ("stock", "equity", "s&p", "s&p 500", "sp500", "nasdaq", "dow", "vix", "标普", "纳斯达克", "指数", "股票", "个股", "美股"),
        "bond": ("bond", "credit spread", "duration", "债券", "信用利差", "久期"),
        "industry": ("industry", "sector", "景气度", "行业", "板块"),
        "commodity": ("commodity", "futures", "gold", "copper", "silver", "corn", "wheat", "商品", "期货", "黄金", "白银", "铜价", "农产品"),
    }
    def contains(term: str) -> bool:
        # Short ASCII symbols such as AI, CPI, PCE and Fed must match tokens,
        # not substrings. Without this guard, for example, "Shanghai" was
        # incorrectly classified as an AI question.
        if term.isascii() and re.fullmatch(r"[a-z0-9]+", term):
            return re.search(rf"\b{re.escape(term)}\b", text) is not None
        return term in text

    return [name for name, terms in groups.items() if any(contains(term) for term in terms)]


def _question_form(question: str, concepts: list[str]) -> str:
    text = question.lower()
    if any(term in text for term in ("cause", "causal", "impact of", "因果", "导致")):
        return "CAUSAL"
    if any(term in text for term in ("scenario", "if ", "如果", "情景")):
        return "SCENARIO"
    if "rates" in concepts and ("inflation" in concepts or "fiscal" in concepts):
        return "ASSET_TRANSMISSION"
    if any(term in text for term in ("forecast", "predict", "未来", "下个月", "接下来", "明天", "下一个交易日", "会涨", "会跌")):
        return "FORECAST"
    if any(term in text for term in ("nowcast", "current", "当前", "现在")):
        return "NOWCAST"
    if any(term in text for term in ("why", "driver", "什么推动", "原因")):
        return "DRIVER"
    return "STATE_ASSESSMENT"


def _research_context(question: str, concepts: list[str]) -> tuple[str, str]:
    text = question.lower()
    non_us_terms = (
        "china", "chinese market", "shanghai", "shenzhen", "hong kong",
        "csi 300", "a-share", "a share", "中国", "上证", "深证", "沪深",
        "A股", "人民币", "中债", "恒生", "港股",
    )
    jurisdiction = "OTHER" if any(term.lower() in text for term in non_us_terms) else "US"
    asset_concepts = {"equity", "bond", "commodity", "energy"}.intersection(concepts)
    if len(asset_concepts) >= 2:
        domain = "CROSS_ASSET"
    elif "industry" in concepts:
        domain = "INDUSTRY"
    elif "equity" in concepts:
        domain = "SINGLE_EQUITY" if any(term in text for term in ("个股", "公司", "股票代码")) else "EQUITY_INDEX"
    elif "commodity" in concepts or "energy" in concepts:
        domain = "COMMODITY"
    elif "bond" in concepts or "rates" in concepts:
        domain = "BOND"
    else:
        domain = "MACRO"
    return jurisdiction, domain


def _scenario_magnitude(question: str) -> dict[str, Any] | None:
    patterns = [
        (r"([+-]?\d+(?:\.\d+)?)\s*%", "PERCENT"),
        (r"([+-]?\d+(?:\.\d+)?)\s*(?:bp|bps|basis points?|个基点|基点)", "BASIS_POINTS"),
    ]
    for pattern, unit in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if not match:
            continue
        value = float(match.group(1))
        local_context = question[max(0, match.start() - 12): min(len(question), match.end() + 12)].lower()
        if value >= 0 and any(
            term in local_context
            for term in ("下降", "下跌", "降低", "减少", "下调", "降息", "fall", "drop", "decline", "cut")
        ):
            value *= -1
        return {
            "value": value,
            "unit": unit,
            "raw_text": match.group(0),
            "source": "USER_EXPLICIT",
        }
    return None


def _reject_extra(value: dict[str, Any], allowed: set[str]) -> None:
    extras = set(value) - allowed
    if extras:
        raise ValueError(f"unregistered output fields: {sorted(extras)}")


class ResearchCompiler:
    """Closed execution compiler: LLMs choose IDs/parameters; Python validates every edge."""

    def __init__(self, registry: RegistryStore, llm: DeepSeekClient) -> None:
        self.registry = registry
        self.llm = llm
        self._trace_context: ContextVar[list[dict[str, Any]]] = ContextVar(
            f"macrotrace_compiler_trace_{id(self)}", default=[]
        )

    @property
    def trace(self) -> list[dict[str, Any]]:
        """Return a copy of the current compile's job-local trace."""
        return list(self._trace_context.get())

    def _record(self, role: str, status: str, detail: dict[str, Any]) -> None:
        self._trace_context.get().append({"role": role, "status": status, "detail": detail})

    def _llm_json(
        self,
        role: str,
        instruction: str,
        payload: dict[str, Any],
        validator: Callable[[dict[str, Any]], dict[str, Any]],
        fallback: dict[str, Any],
        failure_fallback: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.llm.available:
            self._record(role, "FALLBACK_NO_KEY", {"selection": fallback})
            return fallback
        system = (
            "You are a constrained stage in MacroTrace's US macro compiler. "
            "Return JSON only. Never create code, SQL, formulas, URLs, IDs, variables, or numeric weights. "
            + instruction
        )
        user = json.dumps(payload, ensure_ascii=False)
        errors: list[str] = []
        for attempt in range(2):
            try:
                candidate = self.llm.json_completion(system, user, max_tokens=1200)
                validated = validator(candidate)
                self._record(role, "SUCCESS" if attempt == 0 else "REPAIRED", {"selection": validated})
                return validated
            except Exception as exc:  # the exact provider payload must never escape into the trace
                errors.append(type(exc).__name__)
                user = json.dumps({**payload, "repair": "Previous output failed validation. Use only the supplied IDs and allowed values."}, ensure_ascii=False)
        degraded = fallback if failure_fallback is None else failure_fallback
        self._record(role, "FALLBACK_AFTER_REPAIR", {"errors": errors, "selection": degraded, "nodes_removed": failure_fallback is not None})
        return degraded

    def _workflow_for(self, concepts: list[str]) -> str:
        if "ai" in concepts and "labor" in concepts:
            return "WF.US.AI_LABOR_CAUSAL.V1"
        if "panel" in concepts:
            return "WF.US.PANEL_FIXTURE.V1"
        if "inflation" in concepts:
            return "WF.US.INFLATION_OUTLOOK.V1"
        if "commodity" in concepts or "energy" in concepts:
            return "WF.US.COMMODITY_MARKET.V1"
        if "equity" in concepts or "industry" in concepts:
            return "WF.US.EQUITY_MARKET.V1"
        if "rates" in concepts or "fiscal" in concepts:
            return "WF.US.RATES_TRANSMISSION.V1"
        if "activity" in concepts or "recession" in concepts or "labor" in concepts:
            return "WF.US.ACTIVITY_RISK.V1"
        return "WF.US.GENERAL_MACRO.V1"

    def compile(self, question: str, as_of_date: date, emit: Emit | None = None) -> ResearchPlan:
        emit = emit or (lambda _status, _detail: None)
        # A ContextVar keeps traces isolated when the shared compiler is used by
        # multiple ThreadPoolExecutor workers.
        self._trace_context.set([])
        concepts = _concepts(question)
        jurisdiction, domain = _research_context(question, concepts)
        workflow_id = self._workflow_for(concepts)
        workflow = self.registry.get("workflows", workflow_id)

        emit("PARSING_QUERY", {"role": "LLM-0"})
        deterministic_form = _question_form(question, concepts)
        fallback_query = {
            "target_concepts": concepts or ["general macro"],
            "question_form": deterministic_form,
            "domain": domain,
            "research_target": question[:160],
            "conditional_events": [question[:160]] if deterministic_form == "SCENARIO" else [],
            "output_requirements": ["white-box evidence graph", "academic diagnostics"],
        }

        def validate_query(value: dict[str, Any]) -> dict[str, Any]:
            _reject_extra(value, {"target_concepts", "question_form", "domain", "research_target", "conditional_events", "output_requirements"})
            form = value.get("question_form")
            if form not in {"FORECAST", "NOWCAST", "DRIVER", "CAUSAL", "SCENARIO", "ASSET_TRANSMISSION", "STATE_ASSESSMENT"}:
                raise ValueError("invalid question form")
            selected_domain = value.get("domain")
            if selected_domain not in {"MACRO", "EQUITY_INDEX", "SINGLE_EQUITY", "BOND", "INDUSTRY", "COMMODITY", "CROSS_ASSET", "OTHER"}:
                raise ValueError("invalid US research domain")
            targets = [str(item)[:80] for item in value.get("target_concepts", [])][:12]
            if not targets:
                raise ValueError("missing target concepts")
            return {
                "target_concepts": targets,
                "question_form": form,
                "domain": selected_domain,
                "research_target": str(value.get("research_target", ""))[:160],
                "conditional_events": [str(item)[:160] for item in value.get("conditional_events", [])][:8],
                "output_requirements": [str(item)[:160] for item in value.get("output_requirements", [])][:8],
            }

        query_parts = self._llm_json(
            "LLM-0 Query Parser",
            "Classify this US-market research question before any empirical routing. Return exactly one object with keys target_concepts (string array), question_form (one supplied enum), domain (one supplied enum), research_target (short string), conditional_events (string array), and output_requirements (string array). Distinguish macro, equity index, single equity, bond, industry, commodity/futures, and cross-asset questions from their economic meaning rather than keyword matching. No other keys. Horizon is parsed separately from the user's exact language.",
            {
                "question": question,
                "market_scope": "United States only",
                "allowed_domains": ["MACRO", "EQUITY_INDEX", "SINGLE_EQUITY", "BOND", "INDUSTRY", "COMMODITY", "CROSS_ASSET", "OTHER"],
                "allowed_question_forms": ["FORECAST", "NOWCAST", "DRIVER", "CAUSAL", "SCENARIO", "ASSET_TRANSMISSION", "STATE_ASSESSMENT"],
            },
            validate_query,
            fallback_query,
        )
        # Explicit conditional language is a hard semantic guard. An LLM may
        # refine the event text, but it may not silently turn an "if" question
        # into a baseline forecast and thereby bypass scenario execution.
        if deterministic_form == "SCENARIO":
            query_parts["question_form"] = "SCENARIO"
            if not query_parts["conditional_events"]:
                query_parts["conditional_events"] = [question[:160]]
        query = StructuredQuery(
            jurisdiction=jurisdiction,
            domain=query_parts["domain"],
            question=question,
            as_of_date=as_of_date,
            target_concepts=query_parts["target_concepts"],
            question_form=query_parts["question_form"],
            horizon=extract_horizon(question, workflow["default_horizon"]),
            conditional_events=query_parts["conditional_events"],
            output_requirements=query_parts["output_requirements"],
            policy_defaults=["horizon"] if extract_horizon(question, workflow["default_horizon"]).source == "POLICY_DEFAULT" else [],
        )

        emit("CLASSIFYING_WORKFLOW", {"role": "LLM-1"})
        domain_workflows = {
            "EQUITY_INDEX": ["WF.US.EQUITY_MARKET.V1"],
            "SINGLE_EQUITY": ["WF.US.EQUITY_MARKET.V1"],
            "INDUSTRY": ["WF.US.EQUITY_MARKET.V1"],
            "COMMODITY": ["WF.US.COMMODITY_MARKET.V1"],
            "BOND": ["WF.US.RATES_TRANSMISSION.V1"],
            "CROSS_ASSET": ["WF.US.EQUITY_MARKET.V1", "WF.US.COMMODITY_MARKET.V1", "WF.US.RATES_TRANSMISSION.V1"],
            "MACRO": ["WF.US.ACTIVITY_RISK.V1", "WF.US.INFLATION_OUTLOOK.V1", "WF.US.RATES_TRANSMISSION.V1", "WF.US.AI_LABOR_CAUSAL.V1", "WF.US.GENERAL_MACRO.V1"],
            "OTHER": [workflow_id],
        }
        allowed_workflows = [
            item for item in domain_workflows.get(query.domain, [workflow_id])
            if item in self.registry.ids("workflows")
        ]
        if not allowed_workflows:
            allowed_workflows = [workflow_id]
        fallback_workflow_id = workflow_id if workflow_id in allowed_workflows else allowed_workflows[0]
        workflow_options = [
            {
                "workflow_id": item,
                "target_concepts": self.registry.get("workflows", item).get("target_concepts", []),
                "lane_pool": self.registry.get("workflows", item).get("lane_pool", []),
            }
            for item in allowed_workflows
        ]

        def validate_workflow(value: dict[str, Any]) -> dict[str, Any]:
            _reject_extra(value, {"workflow_id", "reason"})
            selected = value.get("workflow_id")
            if selected not in allowed_workflows:
                raise RegistryError("unknown workflow")
            return {"workflow_id": selected, "reason": str(value.get("reason", ""))[:240]}

        selected_workflow = self._llm_json(
            "LLM-1 Workflow Classifier",
            "Reason over the structured US asset domain, research target, requested horizon and available lane pools, then select exactly one supplied workflow_id. Return exactly {\"workflow_id\":\"one supplied ID\",\"reason\":\"short reason\"}. No other keys.",
            {"query": query.model_dump(mode="json"), "research_target": query_parts["research_target"], "workflow_options": workflow_options},
            validate_workflow,
            {"workflow_id": fallback_workflow_id, "reason": "Deterministic concept-to-workflow fallback constrained by the structured asset domain."},
        )
        workflow_id = selected_workflow["workflow_id"]
        workflow = self.registry.get("workflows", workflow_id)
        if workflow_id == "WF.US.AI_LABOR_CAUSAL.V1" or query.question_form == "CAUSAL":
            complexity_class = "CAUSAL_ATTRIBUTION"
        elif query.question_form == "SCENARIO":
            complexity_class = "STRUCTURAL_SCENARIO"
        elif workflow_id in {"WF.US.ACTIVITY_RISK.V1", "WF.US.GENERAL_MACRO.V1"}:
            complexity_class = "SYSTEM_FORECAST"
        else:
            complexity_class = "STANDARD_FORECAST"
        if (
            workflow_id == "WF.US.RATES_TRANSMISSION.V1"
            and query.question_form != "SCENARIO"
            and workflow.get("evidence_budget_id")
        ):
            complexity_class = self.registry.get(
                "evidence_budgets", workflow["evidence_budget_id"]
            )["complexity_class"]

        emit("ROUTING_LANES", {"role": "LLM-2"})
        lane_pool = workflow["lane_pool"]
        fallback_lanes = [
            {"lane_id": lane_id, "priority": "CORE" if index < 2 else "SUPPORTING", "reason": "Registered workflow lane."}
            for index, lane_id in enumerate(lane_pool)
        ]

        def validate_lanes(value: dict[str, Any]) -> dict[str, Any]:
            _reject_extra(value, {"lanes"})
            rows = value.get("lanes", [])
            output = []
            seen = set()
            for row in rows:
                lane_id = row.get("lane_id")
                if lane_id not in lane_pool or lane_id in seen:
                    continue
                priority = row.get("priority")
                if priority not in {"CORE", "SUPPORTING", "LOW"}:
                    raise ValueError("invalid lane priority")
                seen.add(lane_id)
                output.append({"lane_id": lane_id, "priority": priority, "reason": str(row.get("reason", ""))[:240]})
            if not output:
                raise ValueError("no legal lanes")
            return {"lanes": output, "excluded": [lane for lane in lane_pool if lane not in seen]}

        lane_selection = self._llm_json(
            "LLM-2 Lane Router",
            "Return exactly {\"lanes\":[{\"lane_id\":\"one supplied ID\",\"priority\":\"CORE|SUPPORTING|LOW\",\"reason\":\"short reason\"}]}. No other keys. Select only supplied lane IDs; do not estimate weights.",
            {"query": query.model_dump(mode="json"), "workflow_id": workflow_id, "allowed_lane_ids": lane_pool},
            validate_lanes,
            {"lanes": fallback_lanes, "excluded": []},
            {"lanes": [], "excluded": lane_pool},
        )
        lanes = [LaneDecision(**row) for row in lane_selection["lanes"]]
        if workflow.get("evidence_budget_id") or workflow.get("force_all_lanes"):
            selected_lane_ids_now = {lane.lane_id for lane in lanes}
            for index, lane_id in enumerate(workflow["lane_pool"]):
                if lane_id not in selected_lane_ids_now:
                    lanes.append(
                        LaneDecision(
                            lane_id=lane_id,
                            priority="CORE" if index < 2 else "SUPPORTING",
                            reason="Added by the registered workflow completeness policy so a complex question cannot silently drop a required lane.",
                        )
                    )
        if workflow.get("required_lane_ids"):
            required_lane_ids = list(workflow["required_lane_ids"])
            lane_by_id = {lane.lane_id: lane for lane in lanes}
            for lane_id in required_lane_ids:
                lane_by_id.setdefault(
                    lane_id,
                    LaneDecision(
                        lane_id=lane_id,
                        priority="CORE",
                        reason="Mandatory core lane retained by the registered hybrid-routing policy.",
                    ),
                )
            ordered_lane_ids = [lane_id for lane_id in workflow["lane_pool"] if lane_id in lane_by_id]
            minimum_lanes = int(workflow.get("minimum_selected_lanes", len(required_lane_ids)))
            for lane_id in workflow["lane_pool"]:
                if len(ordered_lane_ids) >= minimum_lanes:
                    break
                if lane_id not in ordered_lane_ids:
                    lane_by_id[lane_id] = LaneDecision(
                        lane_id=lane_id,
                        priority="SUPPORTING",
                        reason="Added by the registered minimum-lane fallback after API routing.",
                    )
                    ordered_lane_ids.append(lane_id)
            maximum_lanes = int(workflow.get("maximum_selected_lanes", len(workflow["lane_pool"])))
            retained_lane_ids = required_lane_ids + [
                lane_id for lane_id in ordered_lane_ids if lane_id not in required_lane_ids
            ][: max(0, maximum_lanes - len(required_lane_ids))]
            lanes = [lane_by_id[lane_id] for lane_id in retained_lane_ids]
            self._record(
                "Hybrid Lane Guard",
                "SUCCESS",
                {"required": required_lane_ids, "retained": retained_lane_ids, "minimum": minimum_lanes, "maximum": maximum_lanes},
            )
        selected_lane_ids = {lane.lane_id for lane in lanes}

        emit("ROUTING_NODES", {"role": "LLM-3"})
        workflow_nodes = [self.registry.get("nodes", node_id) for node_id in workflow["node_pool"]]
        candidate_nodes = [node for node in workflow_nodes if node["status"] in {"active", "reviewed", "blocked", "fixture"}]
        selected_node_ids: list[str] = []
        for lane in lanes:
            lane_pool = [node["node_id"] for node in candidate_nodes if node["lane_id"] == lane.lane_id]
            if not lane_pool:
                continue

            def validate_nodes(value: dict[str, Any], allowed: list[str] = lane_pool) -> dict[str, Any]:
                _reject_extra(value, {"node_ids", "reason"})
                node_ids = list(dict.fromkeys(value.get("node_ids", [])))
                if not node_ids or not set(node_ids).issubset(set(allowed)):
                    raise RegistryError("illegal or empty node selection")
                return {"node_ids": node_ids, "reason": str(value.get("reason", ""))[:240]}

            selection = self._llm_json(
                "LLM-3 Node Router",
                "For this one lane return exactly {\"node_ids\":[\"supplied ID\"],\"reason\":\"short reason\"}. No other keys. The backend derives dependencies from the Registry.",
                {"query": query.model_dump(mode="json"), "lane_id": lane.lane_id, "allowed_node_ids": lane_pool},
                validate_nodes,
                {"node_ids": lane_pool, "reason": "Registered lane fallback."},
                {"node_ids": [], "reason": "Removed after two invalid LLM-3 outputs."},
            )
            selected_node_ids.extend(selection["node_ids"])
        if workflow.get("evidence_budget_id") or workflow.get("force_all_nodes"):
            selected_node_ids = [node["node_id"] for node in candidate_nodes if node["lane_id"] in selected_lane_ids]
        elif workflow.get("required_node_ids"):
            required_node_ids = [
                node_id for node_id in workflow["required_node_ids"]
                if self.registry.get("nodes", node_id)["lane_id"] in selected_lane_ids
            ]
            api_selected = list(dict.fromkeys(selected_node_ids))
            optional_candidates = [
                node["node_id"] for node in candidate_nodes
                if node["lane_id"] in selected_lane_ids and node["node_id"] not in required_node_ids
            ]
            optional_selected = [node_id for node_id in api_selected if node_id in optional_candidates]
            minimum_optional = int(workflow.get("minimum_optional_nodes", 0))
            for node_id in optional_candidates:
                if len(optional_selected) >= minimum_optional:
                    break
                if node_id not in optional_selected:
                    optional_selected.append(node_id)
            maximum_optional = int(workflow.get("maximum_optional_nodes", len(optional_candidates)))
            selected_node_ids = required_node_ids + optional_selected[:maximum_optional]
            self._record(
                "Hybrid Node Guard",
                "SUCCESS",
                {"required": required_node_ids, "api_optional": api_selected, "retained_optional": optional_selected[:maximum_optional], "minimum_optional": minimum_optional, "maximum_optional": maximum_optional},
            )
        selected_nodes = [node for node in candidate_nodes if node["node_id"] in set(selected_node_ids)]
        node_decisions = [
            NodeDecision(
                node_id=node["node_id"],
                lane_id=node["lane_id"],
                depends_on=[upstream for upstream in node.get("allowed_upstream", []) if upstream in {item["node_id"] for item in selected_nodes}],
                reason=node["purpose"],
            )
            for node in selected_nodes
        ]

        emit("SELECTING_FACTORS", {"role": "LLM-4"})
        factors: list[FactorDecision] = []
        for node in selected_nodes:
            factor_pool = node["factor_pool"]

            def validate_factors(value: dict[str, Any], allowed: list[str] = factor_pool) -> dict[str, Any]:
                _reject_extra(value, {"factors"})
                output = []
                seen = set()
                for row in value.get("factors", []):
                    _reject_extra(row, {"factor_id", "role", "reason"})
                    factor_id = row.get("factor_id")
                    role = row.get("role")
                    if factor_id not in allowed or factor_id in seen or role not in {"CORE", "SUPPORTING", "BACKGROUND"}:
                        raise RegistryError("illegal factor selection")
                    seen.add(factor_id)
                    output.append({"factor_id": factor_id, "role": role, "reason": str(row.get("reason", ""))[:240]})
                if not output:
                    raise ValueError("empty factor selection")
                return {"factors": output}

            fallback_factors = [
                {"factor_id": factor_id, "role": "CORE" if index < 2 else "SUPPORTING", "reason": "Registered node factor fallback."}
                for index, factor_id in enumerate(factor_pool)
            ]
            selection = self._llm_json(
                "LLM-4 Factor Selector",
                "Return exactly {\"factors\":[{\"factor_id\":\"supplied ID\",\"role\":\"CORE|SUPPORTING|BACKGROUND\",\"reason\":\"short reason\"}]}. No other keys.",
                {"question": question, "lane_id": node["lane_id"], "node_id": node["node_id"], "purpose": node["purpose"], "allowed_factor_ids": factor_pool},
                validate_factors,
                {"factors": fallback_factors},
                {"factors": []},
            )
            for row in selection["factors"]:
                factors.append(
                    FactorDecision(
                        factor_id=row["factor_id"],
                        node_id=node["node_id"],
                        role=row["role"],
                        reason=row["reason"],
                    )
                )

        emit("PLANNING_MODELS", {"role": "LLM-5"})
        models: list[ModelDecision] = []
        for node in selected_nodes:
            compatible: list[dict[str, Any]] = []
            selected_factor_ids = [factor.factor_id for factor in factors if factor.node_id == node["node_id"]]
            for recipe_id in node["model_pool"]:
                recipe = self.registry.get("models", recipe_id)
                if recipe["status"] not in {"active", "fixture"}:
                    continue
                factor_ids = [factor_id for factor_id in selected_factor_ids if factor_id in recipe["factor_pool"]]
                if len(factor_ids) < recipe.get("minimum_factor_count", 1):
                    continue
                compatible.append({"model_recipe_id": recipe_id, "factor_ids": factor_ids, "method": recipe["method"]})
            if not compatible:
                self._record("LLM-5 Model Planner", "NO_COMPATIBLE_MODEL", {"node_id": node["node_id"]})
                continue
            allowed_recipe_ids = [item["model_recipe_id"] for item in compatible]

            def validate_models(value: dict[str, Any], allowed: list[str] = allowed_recipe_ids) -> dict[str, Any]:
                _reject_extra(value, {"model_recipe_ids", "reason"})
                recipe_ids = list(dict.fromkeys(value.get("model_recipe_ids", [])))
                if not recipe_ids or not set(recipe_ids).issubset(set(allowed)):
                    raise RegistryError("illegal or empty model selection")
                return {"model_recipe_ids": recipe_ids, "reason": str(value.get("reason", ""))[:240]}

            model_selection = self._llm_json(
                "LLM-5 Model Planner",
                "Return exactly {\"model_recipe_ids\":[\"supplied ID\"],\"reason\":\"short reason\"}. No other keys. Do not add formulas or weights.",
                {"question": question, "node_id": node["node_id"], "factor_ids": selected_factor_ids, "compatible_models": compatible},
                validate_models,
                {"model_recipe_ids": allowed_recipe_ids, "reason": "All registered compatible model fallbacks."},
                {"model_recipe_ids": [], "reason": "Removed after two invalid LLM-5 outputs."},
            )
            for recipe_id in model_selection["model_recipe_ids"]:
                item = next(candidate for candidate in compatible if candidate["model_recipe_id"] == recipe_id)
                values = self._default_parameters(recipe_id, query)
                models.append(
                    ModelDecision(
                        model_recipe_id=recipe_id,
                        node_id=node["node_id"],
                        factor_ids=item["factor_ids"],
                        parameters=ParameterSelection(model_recipe_id=recipe_id, values=values, source="POLICY_DEFAULT"),
                        reason=model_selection["reason"] or f"Registered in {node['node_id']} and compatible with the selected factor set.",
                    )
                )

        emit("SELECTING_PARAMETERS", {"role": "LLM-6"})
        retained_models: list[ModelDecision] = []
        for model in models:
            recipe = self.registry.get("models", model.model_recipe_id)
            fallback = {"values": model.parameters.values}

            def parameter_validator(value: dict[str, Any], recipe_id: str = model.model_recipe_id) -> dict[str, Any]:
                _reject_extra(value, {"values"})
                values = value.get("values", {})
                self.registry.validate_parameters(recipe_id, values)
                return {"values": values}

            selected = self._llm_json(
                "LLM-6 Parameter Agent",
                "Return exactly {\"values\":{...}} where values contains every and only registered parameter key, using supplied allowed values. No other top-level keys. Do not add variables or a formula.",
                {
                    "question": question,
                    "workflow_id": workflow_id,
                    "node_id": model.node_id,
                    "model_recipe_id": model.model_recipe_id,
                    "factor_ids": model.factor_ids,
                    "allowed_parameters": recipe["allowed_parameters"],
                    "policy_default": model.parameters.values,
                },
                parameter_validator,
                fallback,
                {"drop_model": True},
            )
            if selected.get("drop_model"):
                continue
            model.parameters = ParameterSelection(
                model_recipe_id=model.model_recipe_id,
                values=selected["values"],
                source="LLM_ALLOWLIST" if self.llm.available and selected != fallback else "POLICY_DEFAULT",
            )
            retained_models.append(model)
        models = retained_models

        # v0.3 research-depth extension: executable work is taken from immutable
        # pre-registered specifications. The LLM may route and prioritise, but it
        # cannot invent or silently delete the empirical programme for a complex
        # workflow.
        specification_rows = [
            item
            for item in self.registry.all("model_specifications")
            if workflow_id in item.get("workflow_ids", []) and item["lane_id"] in selected_lane_ids
        ]
        model_specifications = [
            ModelSpecificationDecision(
                specification_id=item["specification_id"],
                lane_id=item["lane_id"],
                mechanism_id=item["mechanism_id"],
                node_id=item["node_id"],
                model_recipe_id=item.get("model_recipe_id"),
                factor_ids=item.get("factor_ids", []),
                parameters=item.get("parameters", {}),
                role=item["role"],
                execution_status=item["execution_status"],
                blocked_reason=item.get("blocked_reason"),
            )
            for item in specification_rows
        ]
        selected_node_id_set = {item["node_id"] for item in selected_nodes}
        if specification_rows:
            models = []
            factor_keys = {(factor.node_id, factor.factor_id) for factor in factors}
            for item in specification_rows:
                if item["node_id"] not in selected_node_id_set:
                    continue
                for index, factor_id in enumerate(item.get("factor_ids", [])):
                    key = (item["node_id"], factor_id)
                    if key not in factor_keys:
                        factors.append(
                            FactorDecision(
                                factor_id=factor_id,
                                node_id=item["node_id"],
                                role="CORE" if index == 0 else "SUPPORTING",
                                reason=f"Required by pre-registered specification {item['specification_id']}.",
                            )
                        )
                        factor_keys.add(key)
                if item["execution_status"] != "ACTIVE" or item.get("model_recipe_id") is None:
                    continue
                self.registry.validate_parameters(item["model_recipe_id"], item["parameters"])
                models.append(
                    ModelDecision(
                        specification_id=item["specification_id"],
                        model_recipe_id=item["model_recipe_id"],
                        node_id=item["node_id"],
                        factor_ids=item["factor_ids"],
                        parameters=ParameterSelection(
                            model_recipe_id=item["model_recipe_id"],
                            values=item["parameters"],
                            source="POLICY_DEFAULT",
                        ),
                        reason=f"Pre-registered {item['role'].lower()} specification.",
                        role=item["role"],
                    )
                )
            self._record(
                "ModelSpecification Registry",
                "SUCCESS",
                {
                    "planned": len(specification_rows),
                    "executable": len(models),
                    "blocked": sum(item["execution_status"] == "BLOCKED" for item in specification_rows),
                },
            )

        lane_priority = {lane.lane_id: lane.priority for lane in lanes}
        selected_mechanism_rows = [
            item for item in self.registry.all("mechanisms") if item["lane_id"] in selected_lane_ids
        ]
        mechanisms = [
            MechanismDecision(
                mechanism_id=item["mechanism_id"],
                lane_id=item["lane_id"],
                role=lane_priority.get(item["lane_id"], "LOW"),
                reason=item["hypothesis"],
            )
            for item in selected_mechanism_rows
        ]

        unsupported = []
        if jurisdiction != "US":
            unsupported.append("MacroTrace 当前版本只覆盖美国市场；非美国市场问题不会被美国数据代理替代。")
        repair_failures = [entry["role"] for entry in self.trace if entry["status"] == "FALLBACK_AFTER_REPAIR"]
        if repair_failures:
            unsupported.append(f"Compiler stages removed invalid selections after one repair attempt: {', '.join(sorted(set(repair_failures)))}.")
        selected_node_lanes = {node["lane_id"] for node in selected_nodes}
        for lane in lanes:
            if lane.lane_id not in selected_node_lanes:
                unsupported.append(f"{lane.lane_id} has no active reviewed research node in this Registry version.")
        modeled_node_ids = {model.node_id for model in models}
        for node in selected_nodes:
            if node["model_pool"] and node["node_id"] not in modeled_node_ids:
                node_specifications = [item for item in specification_rows if item["node_id"] == node["node_id"]]
                if node_specifications and all(item["execution_status"] == "BLOCKED" for item in node_specifications):
                    continue
                unsupported.append(f"{node['node_id']} has no compatible registered model after factor and model selection.")
        if "trade" in concepts:
            unsupported.append("The US trade workflow is registry-blocked pending a reviewed Census international-trade implementation.")
        if "ai" in concepts:
            unsupported.append("Census BTOS adoption and a reviewed occupation-exposure crosswalk are not yet executable; AI-specific causal specifications remain visible as BLOCKED.")
        if complexity_class == "CAUSAL_ATTRIBUTION" and workflow_id != "WF.US.PANEL_FIXTURE.V1":
            unsupported.append("No registered identification design covers the requested causal claim; available results are predictive or associational.")
        scenario_execution: dict[str, Any] = {"status": "NOT_APPLICABLE"}
        if query.question_form == "SCENARIO":
            scenario_execution = self._compile_scenario_execution(question, query, models)
            if scenario_execution["status"] == "REGISTERED_DYNAMIC_RESPONSE":
                unsupported.append(
                    "The registered dynamic response is model-conditional and is not labeled as an externally identified causal effect."
                )
            elif scenario_execution["status"] == "MODEL_CONDITIONAL":
                unsupported.append(
                    "The event is translated through registered proxy shocks; estimates are conditional transmission sensitivities rather than event-specific causal effects."
                )
            else:
                unsupported.append(
                    "The event-to-macro translation is an explicit registered sensitivity envelope; the result remains answerable but assumption-dependent."
                )
        research_depth: dict[str, Any] = {"status": "NOT_APPLICABLE"}
        budget_id = workflow.get("evidence_budget_id")
        if budget_id:
            budget = self.registry.get("evidence_budgets", budget_id)
            core_lanes = [lane.lane_id for lane in lanes if lane.priority == "CORE"]
            lane_metrics = {}
            for lane_id in [lane.lane_id for lane in lanes]:
                lane_specs = [item for item in specification_rows if item["lane_id"] == lane_id]
                lane_metrics[lane_id] = {
                    "mechanisms": len({item["mechanism_id"] for item in selected_mechanism_rows if item["lane_id"] == lane_id}),
                    "factors": len({factor_id for item in lane_specs for factor_id in item.get("factor_ids", [])}),
                    "model_specifications": len(lane_specs),
                    "executable_model_specifications": sum(item["execution_status"] == "ACTIVE" for item in lane_specs),
                    "blocked_model_specifications": sum(item["execution_status"] == "BLOCKED" for item in lane_specs),
                }
            method_families = len({item.get("model_recipe_id") for item in specification_rows if item.get("model_recipe_id")})
            benchmark_count = sum(item.get("role") == "BENCHMARK" for item in specification_rows)
            checks = {
                "routed_lanes": len(lanes) >= budget["minimum_routed_lanes"],
                "mechanisms_per_core_lane": all(lane_metrics[lane_id]["mechanisms"] >= budget["minimum_mechanisms_per_core_lane"] for lane_id in core_lanes),
                "factors_per_core_lane": all(lane_metrics[lane_id]["factors"] >= budget["minimum_factors_per_core_lane"] for lane_id in core_lanes),
                "model_specifications_per_core_lane": all(lane_metrics[lane_id]["model_specifications"] >= budget["minimum_model_specifications_per_core_lane"] for lane_id in core_lanes),
                "method_families": method_families >= budget["minimum_method_families"],
                "benchmarks": benchmark_count >= budget["minimum_benchmarks"],
            }
            identification_active = any(
                item["mechanism_id"] == "MECH.AI.CAUSAL_IDENTIFICATION" and item["execution_status"] == "ACTIVE"
                for item in specification_rows
            )
            if budget.get("requires_identification"):
                checks["identification"] = identification_active
            research_depth = {
                "status": "PASS" if all(checks.values()) else "FAIL",
                "budget_id": budget_id,
                "complexity_class": complexity_class,
                "identification_required": bool(budget.get("requires_identification")),
                "identification_active": identification_active,
                "checks": checks,
                "lane_metrics": lane_metrics,
                "method_families": method_families,
                "benchmark_count": benchmark_count,
                "planned_specifications": len(specification_rows),
                "executable_specifications": len(models),
                "blocked_specifications": sum(item["execution_status"] == "BLOCKED" for item in specification_rows),
            }
            if research_depth["status"] == "FAIL":
                unsupported.append("The registered empirical completeness budget is not met; FULL coverage is prohibited.")

        if jurisdiction != "US":
            # Fail closed: retain the registered universe for a grey graph, but
            # do not execute a US workflow as a proxy for another jurisdiction.
            lanes = []
            mechanisms = []
            node_decisions = []
            factors = []
            model_specifications = []
            models = []

        coverage_score = 1.0 if not unsupported else max(0.35, 1 - 0.15 * len(unsupported))
        coverage = Coverage.FULL if not unsupported else Coverage.PARTIAL
        if jurisdiction != "US":
            coverage = Coverage.UNSUPPORTED
            coverage_score = 0
        if (
            complexity_class == "CAUSAL_ATTRIBUTION"
            and research_depth.get("identification_required")
            and not research_depth.get("identification_active")
        ):
            coverage = Coverage.UNSUPPORTED
        if not models:
            coverage = Coverage.UNSUPPORTED
            coverage_score = 0
            unsupported.append("No active registered model is compatible with the selected factors.")

        plan = ResearchPlan(
            workflow_id=workflow_id,
            complexity_class=complexity_class,
            evidence_budget_id=workflow.get("evidence_budget_id"),
            query=query,
            lanes=lanes,
            excluded_lanes=[{"lane_id": lane_id, "reason": "Not selected for this query."} for lane_id in lane_selection.get("excluded", [])],
            mechanisms=mechanisms,
            nodes=node_decisions,
            factors=factors,
            model_specifications=model_specifications,
            models=models,
            coverage=coverage,
            coverage_score=coverage_score,
            unsupported_aspects=unsupported,
            validation={"status": "PASS", "registry_version": "0.2.0+v0.3-depth-extension", "arbitrary_code_allowed": False, "research_depth": research_depth, "scenario_execution": scenario_execution},
        )
        self.validate_plan(plan)
        return plan

    def _compile_scenario_execution(
        self,
        question: str,
        query: StructuredQuery,
        models: list[ModelDecision],
    ) -> dict[str, Any]:
        text = question.lower()
        catalog = [
            item
            for item in self.registry.all("scenario_mappings")
            if item.get("status") in {"active", "reviewed"}
        ]
        matched = [
            item
            for item in catalog
            if not item.get("is_fallback")
            and any(keyword.lower() in text for keyword in item.get("keywords", []))
        ]
        if not matched:
            matched = [next(item for item in catalog if item.get("is_fallback"))]
        matched = matched[:3]
        planned_recipe_ids = {model.model_recipe_id for model in models}
        mapping_recipe_ids = {
            recipe_id for item in matched for recipe_id in item.get("model_recipe_ids", [])
        }
        dynamic_models = [
            model
            for model in models
            if model.model_recipe_id in mapping_recipe_ids
            and model.model_recipe_id in {"M.LOCAL_PROJECTION.V1", "M.VAR_SYSTEM.V1"}
        ]
        direct_dynamic = any(
            item.get("mapping_tier") == "DIRECT_DYNAMIC"
            and planned_recipe_ids.intersection(item.get("model_recipe_ids", []))
            for item in matched
        )
        if direct_dynamic:
            status = "REGISTERED_DYNAMIC_RESPONSE"
            interpretation_rule = (
                "Use the registered dynamic response path as the conditional estimate; disclose its shock definition and do not upgrade it to causal identification."
            )
        elif dynamic_models:
            status = "MODEL_CONDITIONAL"
            interpretation_rule = (
                "Translate the event through the registered proxy shocks and report the resulting conditional response paths with the proxy assumptions visible."
            )
        else:
            status = "SENSITIVITY_ENVELOPE"
            interpretation_rule = (
                "Answer with registered macro sensitivity axes and explicit event-to-axis assumptions; do not present the envelope as a fitted event-specific effect."
            )
        specification_ids = [
            model.specification_id
            for model in dynamic_models
            if model.specification_id is not None
        ]
        return {
            "status": status,
            "conditional_events": query.conditional_events or [question[:160]],
            "mapping_ids": [item["scenario_mapping_id"] for item in matched],
            "mapping_tiers": [item["mapping_tier"] for item in matched],
            "shock_factor_ids": list(
                dict.fromkeys(factor_id for item in matched for factor_id in item.get("shock_factor_ids", []))
            ),
            "response_factor_ids": list(
                dict.fromkeys(factor_id for item in matched for factor_id in item.get("response_factor_ids", []))
            ),
            "model_recipe_ids": sorted(planned_recipe_ids.intersection(mapping_recipe_ids)),
            "dynamic_response_model_count": len(dynamic_models),
            "identified_shock_specifications": specification_ids,
            "identification_strength": [item["identification_strength"] for item in matched],
            "proxy_assumptions": [item["translation_assumption"] for item in matched],
            "requested_shock": _scenario_magnitude(question),
            "event_specific_effect_is_causal": False,
            "interpretation_rule": interpretation_rule,
        }

    def _default_parameters(self, recipe_id: str, query: StructuredQuery) -> dict[str, Any]:
        horizon_months = query.horizon.maximum
        if query.horizon.unit == "QUARTERS":
            horizon_months *= 3
        elif query.horizon.unit == "YEARS":
            horizon_months *= 12
        elif query.horizon.unit == "WEEKS":
            horizon_months = max(1, round(horizon_months / 4.345))
        elif query.horizon.unit == "DAYS":
            horizon_months = max(1, round(horizon_months / 30.4))
        if recipe_id == "M.DFM_NOWCAST.V1":
            return {"estimation_window_years": 10, "factor_count": 1, "forecast_horizon": min(6, max(1, horizon_months))}
        if recipe_id == "M.VAR_SYSTEM.V1":
            return {"lags": 2, "forecast_horizon": min(12, max(1, horizon_months)), "identification": "REGISTERED_CHOLESKY", "estimation_window_years": 15}
        if recipe_id == "M.LOCAL_PROJECTION.V1":
            return {"response_horizon": 12, "lags": 3, "covariance": "HAC", "shock_scale": 1.0}
        if recipe_id == "M.GROWTH_AT_RISK.V1":
            return {"quantiles": [0.05, 0.25, 0.5, 0.75, 0.95], "forecast_horizon_quarters": min(4, max(1, round(horizon_months / 3))), "estimation_window": "EXPANDING"}
        if recipe_id == "M.PANEL_FE_FIXTURE.V1":
            return {"start_year": 2010, "fixed_effects": "TWO_WAY", "covariance": "CLUSTER_ENTITY"}
        if recipe_id in {"M.DAILY_MARKET_AR.V1", "M.DAILY_MARKET_BRIDGE.V1", "M.DAILY_MARKET_VAR.V1"}:
            if query.horizon.unit == "DAYS":
                requested_days = query.horizon.maximum
            elif query.horizon.unit == "WEEKS":
                requested_days = query.horizon.maximum * 5
            elif query.horizon.unit == "MONTHS":
                requested_days = query.horizon.maximum * 21
            elif query.horizon.unit == "QUARTERS":
                requested_days = query.horizon.maximum * 63
            else:
                requested_days = query.horizon.maximum * 252
            horizon_days = next((item for item in (1, 5, 21, 63) if requested_days <= item), 63)
            if recipe_id == "M.DAILY_MARKET_VAR.V1":
                return {"lags": 5, "forecast_horizon_days": min(horizon_days, 21), "estimation_window_years": 5, "identification": "REGISTERED_CHOLESKY"}
            return {"lags": 5, "forecast_horizon_days": horizon_days, "estimation_window_years": 5, "covariance": "HAC"}
        if recipe_id in {"M.UNIVARIATE_AR.V1", "M.BRIDGE_OLS.V1"}:
            return {"lags": 3, "forecast_horizon": min(6, max(1, horizon_months)), "estimation_window_years": 10}
        raise RegistryError(f"no defaults for {recipe_id}")

    def validate_plan(self, plan: ResearchPlan) -> None:
        self.registry.get("workflows", plan.workflow_id)
        node_map = {node.node_id: self.registry.get("nodes", node.node_id) for node in plan.nodes}
        selected_factors = {(factor.node_id, factor.factor_id) for factor in plan.factors}
        for factor in plan.factors:
            if factor.factor_id not in node_map[factor.node_id]["factor_pool"]:
                raise RegistryError(f"factor {factor.factor_id} not allowed in {factor.node_id}")
        for model in plan.models:
            node = node_map[model.node_id]
            if model.model_recipe_id not in node["model_pool"]:
                raise RegistryError(f"model {model.model_recipe_id} not allowed in {model.node_id}")
            recipe = self.registry.get("models", model.model_recipe_id)
            if not set(model.factor_ids).issubset(set(recipe["factor_pool"])):
                raise RegistryError(f"model {model.model_recipe_id} received illegal factors")
            if len(model.factor_ids) < recipe.get("minimum_factor_count", 1):
                raise RegistryError(f"model {model.model_recipe_id} received too few registered factors")
            if not all((model.node_id, factor_id) in selected_factors for factor_id in model.factor_ids):
                raise RegistryError(f"model {model.model_recipe_id} bypassed factor selection")
            self.registry.validate_parameters(model.model_recipe_id, model.parameters.values)


__all__ = ["ResearchCompiler", "extract_horizon"]
