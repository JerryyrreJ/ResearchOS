from __future__ import annotations

from copy import deepcopy
from typing import Any


LLM_PROVIDERS: dict[str, dict[str, Any]] = {
    "openai": {
        "provider_id": "openai",
        "label": "OpenAI",
        "api_format": "openai",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-5.6-terra",
        "models": [
            {"id": "gpt-5.6", "label": "GPT-5.6 / Sol", "tier": "frontier"},
            {"id": "gpt-5.6-terra", "label": "GPT-5.6 Terra", "tier": "balanced"},
            {"id": "gpt-5.6-luna", "label": "GPT-5.6 Luna", "tier": "economy"},
        ],
        "key_url": "https://platform.openai.com/api-keys",
        "docs_url": "https://developers.openai.com/api/docs/models",
        "key_placeholder": "sk-...",
        "guide_steps": [
            "登录 OpenAI Platform；ChatGPT 订阅与 API 余额是两套独立账户体系。",
            "进入 API Keys 页面，创建一个只用于 MacroTrace 的 Secret Key。",
            "如账户尚未启用 API 计费，先在 Billing 中添加支付方式或余额。",
            "复制密钥并立即填入本窗口；平台通常不会再次显示完整密钥。",
        ],
    },
    "deepseek": {
        "provider_id": "deepseek",
        "label": "DeepSeek",
        "api_format": "openai",
        "default_base_url": "https://api.deepseek.com",
        "default_model": "deepseek-v4-flash",
        "models": [
            {"id": "deepseek-v4-flash", "label": "DeepSeek V4 Flash", "tier": "balanced"},
            {"id": "deepseek-v4-pro", "label": "DeepSeek V4 Pro", "tier": "frontier"},
        ],
        "key_url": "https://platform.deepseek.com/api_keys",
        "docs_url": "https://api-docs.deepseek.com/",
        "key_placeholder": "sk-...",
        "guide_steps": [
            "登录 DeepSeek 开放平台，而不是聊天网页。",
            "在 API Keys 页面创建新密钥，并为账户充值可用余额。",
            "复制密钥填入本窗口；默认使用 V4 Flash，也可选择 V4 Pro。",
            "旧的 deepseek-chat / deepseek-reasoner 将停用，因此本项目不再把它们设为默认选项。",
        ],
    },
    "anthropic": {
        "provider_id": "anthropic",
        "label": "Anthropic / Claude",
        "api_format": "anthropic",
        "default_base_url": "https://api.anthropic.com",
        "default_model": "claude-sonnet-5",
        "models": [
            {"id": "claude-sonnet-5", "label": "Claude Sonnet 5", "tier": "balanced"},
            {"id": "claude-opus-4-8", "label": "Claude Opus 4.8", "tier": "frontier"},
            {"id": "claude-fable-5", "label": "Claude Fable 5", "tier": "frontier"},
            {"id": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5", "tier": "economy"},
        ],
        "key_url": "https://platform.claude.com/settings/keys",
        "docs_url": "https://platform.claude.com/docs/en/about-claude/models/overview",
        "key_placeholder": "sk-ant-...",
        "guide_steps": [
            "登录 Claude Platform；Claude 网页订阅不自动包含 API 额度。",
            "进入 Settings → API Keys，创建一个新的工作区密钥。",
            "确认工作区已设置可用额度和消费限制。",
            "复制密钥填入本窗口；MacroTrace 会使用 Anthropic Messages API。",
        ],
    },
    "google": {
        "provider_id": "google",
        "label": "Google Gemini",
        "api_format": "openai",
        "default_base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-3.5-flash",
        "models": [
            {"id": "gemini-3.5-flash", "label": "Gemini 3.5 Flash", "tier": "balanced"},
            {"id": "gemini-3.1-pro", "label": "Gemini 3.1 Pro", "tier": "frontier-preview"},
            {"id": "gemini-3.1-flash-lite", "label": "Gemini 3.1 Flash-Lite", "tier": "economy"},
            {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "tier": "stable"},
            {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "tier": "stable"},
        ],
        "key_url": "https://aistudio.google.com/app/apikey",
        "docs_url": "https://ai.google.dev/gemini-api/docs/models",
        "key_placeholder": "AIza...",
        "guide_steps": [
            "使用 Google 账号登录 Google AI Studio。",
            "打开 Get API key，选择或创建一个 Google Cloud Project。",
            "创建 Gemini API Key；如所选模型需要计费，按页面提示启用 Billing。",
            "复制密钥填入本窗口；MacroTrace 使用 Google 官方 OpenAI-compatible 端点。",
        ],
    },
    "custom": {
        "provider_id": "custom",
        "label": "自定义 OpenAI-compatible",
        "api_format": "openai",
        "default_base_url": "",
        "default_model": "",
        "models": [],
        "key_url": "",
        "docs_url": "",
        "key_placeholder": "your-api-key",
        "guide_steps": [
            "从服务商文档确认它兼容 POST /chat/completions。",
            "填写完整 Base URL；也可以直接填写以 /chat/completions 结尾的 Endpoint。",
            "填写准确的模型 ID 和该服务商签发的 API Key。",
            "先运行连接测试；若服务商不支持 JSON mode，请改用另一个兼容端点。",
        ],
    },
}


DATA_SOURCES: dict[str, dict[str, Any]] = {
    "FRED": {
        "source_id": "FRED",
        "label": "FRED / ALFRED",
        "institution": "Federal Reserve Bank of St. Louis",
        "key_required": True,
        "active_connector": True,
        "key_url": "https://fredaccount.stlouisfed.org/apikeys",
        "docs_url": "https://fred.stlouisfed.org/docs/api/fred/api_key.html",
        "key_placeholder": "32-character FRED key",
        "coverage": "利率、通胀、增长、金融条件、州级面板与历史 vintage",
        "guide_steps": [
            "注册或登录 FRED Account。",
            "进入 My Account → API Keys（也可直接打开上方申请链接）。",
            "点击 Request API Key，为 MacroTrace 单独创建一个应用密钥。",
            "复制生成的 32 位字母数字密钥，回到本窗口保存并测试。",
        ],
        "legal_note": "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.",
    },
    "BLS": {
        "source_id": "BLS",
        "label": "BLS Public Data API",
        "institution": "U.S. Bureau of Labor Statistics",
        "key_required": True,
        "active_connector": True,
        "key_url": "https://data.bls.gov/registrationEngine/",
        "docs_url": "https://www.bls.gov/developers/api_signature_v2.htm",
        "key_placeholder": "BLS registration key",
        "coverage": "CPI、非农、失业率、工资、JOLTS 与行业劳动力指标",
        "guide_steps": [
            "打开 BLS Registration Engine。",
            "填写 Organization Name 和 Email Address，完成 CAPTCHA。",
            "勾选同意 Terms of Service 并提交。",
            "从 BLS 邮件中复制 Registration Key，回到本窗口保存并测试。",
        ],
        "legal_note": "",
    },
    "EIA": {
        "source_id": "EIA",
        "label": "EIA Open Data",
        "institution": "U.S. Energy Information Administration",
        "key_required": True,
        "active_connector": True,
        "key_url": "https://www.eia.gov/opendata/register.php",
        "docs_url": "https://www.eia.gov/opendata/documentation.php",
        "key_placeholder": "EIA API key",
        "coverage": "WTI、石油、天然气、电力与能源价格数据",
        "guide_steps": [
            "打开 EIA Open Data 注册页。",
            "填写姓名、邮箱、用户类别和使用原因。",
            "阅读并同意 API Terms of Service 后提交。",
            "EIA 会把免费 API Key 发到邮箱；复制后回到本窗口保存并测试。",
        ],
        "legal_note": "",
    },
    "TREASURY": {
        "source_id": "TREASURY",
        "label": "U.S. Treasury Fiscal Data",
        "institution": "U.S. Department of the Treasury",
        "key_required": False,
        "active_connector": True,
        "key_url": "",
        "docs_url": "https://fiscaldata.treasury.gov/api-documentation/",
        "key_placeholder": "",
        "coverage": "联邦债务余额与财政数据",
        "guide_steps": ["无需申请 API Key；MacroTrace 直接调用公开 Fiscal Data API。"],
        "legal_note": "",
    },
    "NYFED": {
        "source_id": "NYFED",
        "label": "New York Fed Markets API",
        "institution": "Federal Reserve Bank of New York",
        "key_required": False,
        "active_connector": True,
        "key_url": "",
        "docs_url": "https://markets.newyorkfed.org/static/docs/markets-api.html",
        "key_placeholder": "",
        "coverage": "SOFR 与纽约联储参考利率",
        "guide_steps": ["无需申请 API Key；MacroTrace 直接调用公开 Markets API。"],
        "legal_note": "",
    },
}


def public_provider_catalog() -> dict[str, list[dict[str, Any]]]:
    return {
        "llm_providers": [deepcopy(item) for item in LLM_PROVIDERS.values()],
        "data_sources": [deepcopy(item) for item in DATA_SOURCES.values()],
    }


def provider(provider_id: str) -> dict[str, Any]:
    try:
        return LLM_PROVIDERS[provider_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported LLM provider: {provider_id}") from exc


def data_source(source_id: str) -> dict[str, Any]:
    try:
        return DATA_SOURCES[source_id.upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported data source: {source_id}") from exc

