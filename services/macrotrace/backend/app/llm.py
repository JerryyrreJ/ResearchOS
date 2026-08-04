from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from typing import Any

import httpx


ConfigResolver = Callable[[], Mapping[str, Any]]


def _json_text(value: str) -> dict[str, Any]:
    text = value.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("LLM response must be a JSON object")
    return payload


def _completion_url(base_url: str, suffix: str) -> str:
    endpoint = base_url.rstrip("/")
    if endpoint.endswith(suffix):
        return endpoint
    return f"{endpoint}{suffix}"


class DeepSeekClient:
    """Dynamically configurable LLM client.

    The historical class name is preserved for compatibility with the compiler
    and existing tests. At runtime it can now resolve OpenAI-compatible,
    Anthropic, DeepSeek, Gemini, or custom local provider configuration.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "deepseek-v4-flash",
        base_url: str = "https://api.deepseek.com",
        *,
        provider: str = "deepseek",
        api_format: str = "openai",
        config_resolver: ConfigResolver | None = None,
    ) -> None:
        self._static = {
            "api_key": api_key,
            "model": model,
            "base_url": base_url,
            "provider": provider,
            "api_format": api_format,
        }
        self._config_resolver = config_resolver

    def _config(self) -> dict[str, Any]:
        if self._config_resolver is None:
            return dict(self._static)
        return {**self._static, **dict(self._config_resolver())}

    @property
    def api_key(self) -> str:
        return str(self._config().get("api_key") or "")

    @property
    def model(self) -> str:
        return str(self._config().get("model") or "")

    @property
    def base_url(self) -> str:
        return str(self._config().get("base_url") or "").rstrip("/")

    @property
    def provider(self) -> str:
        return str(self._config().get("provider") or "custom")

    @property
    def api_format(self) -> str:
        return str(self._config().get("api_format") or "openai")

    @property
    def available(self) -> bool:
        config = self._config()
        return bool(config.get("api_key") and config.get("model") and config.get("base_url"))

    def _openai_json_completion(
        self,
        config: dict[str, Any],
        system: str,
        user: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        provider = str(config.get("provider") or "custom")
        payload: dict[str, Any] = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        if provider == "openai":
            payload["max_completion_tokens"] = max_tokens
        else:
            payload["max_tokens"] = max_tokens
        if provider == "deepseek":
            payload["thinking"] = {"type": "disabled"}
            payload["temperature"] = 0
        elif provider == "custom":
            payload["temperature"] = 0
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=90) as client:
            response = client.post(
                _completion_url(str(config["base_url"]), "/chat/completions"),
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        content = body["choices"][0]["message"]["content"]
        return _json_text(content)

    def _anthropic_json_completion(
        self,
        config: dict[str, Any],
        system: str,
        user: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        payload = {
            "model": config["model"],
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        headers = {
            "x-api-key": str(config["api_key"]),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=90) as client:
            response = client.post(
                _completion_url(str(config["base_url"]), "/v1/messages"),
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        content = "".join(
            str(block.get("text") or "")
            for block in body.get("content", [])
            if block.get("type") == "text"
        )
        return _json_text(content)

    def json_completion(
        self,
        system: str,
        user: str,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        config = self._config()
        if not self.available:
            raise RuntimeError("LLM provider is not configured")
        if config.get("api_format") == "anthropic":
            return self._anthropic_json_completion(config, system, user, max_tokens)
        return self._openai_json_completion(config, system, user, max_tokens)

