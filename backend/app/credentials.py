from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import Settings
from .provider_catalog import DATA_SOURCES, LLM_PROVIDERS, data_source, provider


DATA_ENV_KEYS = {
    "FRED": "FRED_API_KEY",
    "BLS": "BLS_API_KEY",
    "EIA": "EIA_API_KEY",
    "BEA": "BEA_API_KEY",
    "CENSUS": "CENSUS_API_KEY",
}


def _masked(value: str) -> str | None:
    if not value:
        return None
    return "********"


def _safe_endpoint(value: str) -> str:
    endpoint = value.strip().rstrip("/")
    if not endpoint:
        raise ValueError("API endpoint is required")
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("API endpoint must be an absolute http(s) URL")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Non-local API endpoints must use HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("Credentials must not be embedded in the API endpoint")
    return endpoint


class LocalCredentialStore:
    """Local-only provider configuration with an opt-in persistent secret file.

    Session credentials stay in memory. Persistent credentials are stored under
    data/private/, a directory excluded from Git and public release archives.
    No method in this class returns a secret through a public status payload.
    """

    def __init__(self, settings: Settings, path: Path | None = None) -> None:
        self.settings = settings
        self.path = path or settings.data_dir / "private" / "provider-config.json"
        self._lock = threading.RLock()
        self._session: dict[str, Any] = {"llm": {}, "data_sources": {}}

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "llm": {}, "data_sources": {}}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema_version": 1, "llm": {}, "data_sources": {}}
        if not isinstance(payload, dict):
            return {"schema_version": 1, "llm": {}, "data_sources": {}}
        payload.setdefault("schema_version", 1)
        payload.setdefault("llm", {})
        payload.setdefault("data_sources", {})
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)
        os.chmod(self.path, 0o600)

    def llm_config(self) -> dict[str, Any]:
        with self._lock:
            persisted = self._read().get("llm", {})
            configured = self._session.get("llm") or persisted
            if configured:
                return deepcopy(configured)
            return {
                "provider": "deepseek",
                "api_format": "openai",
                "model": self.settings.deepseek_model,
                "base_url": self.settings.deepseek_base_url,
                "api_key": self.settings.deepseek_api_key,
                "storage": "environment" if self.settings.deepseek_api_key else "none",
            }

    def save_llm(
        self,
        *,
        provider_id: str,
        model: str,
        base_url: str | None,
        api_key: str | None,
        persist: bool,
    ) -> dict[str, Any]:
        catalog = provider(provider_id)
        selected_model = model.strip()
        if not selected_model:
            raise ValueError("Model ID is required")
        endpoint = _safe_endpoint(base_url or catalog["default_base_url"])
        with self._lock:
            current = self.llm_config()
            reusable_secret = current.get("api_key", "") if current.get("provider") == provider_id else ""
            secret = (api_key or "").strip() or reusable_secret
            if not secret:
                raise ValueError("API key is required")
            record = {
                "provider": provider_id,
                "api_format": catalog["api_format"],
                "model": selected_model,
                "base_url": endpoint,
                "api_key": secret,
                "storage": "persistent" if persist else "session",
            }
            if persist:
                payload = self._read()
                payload["llm"] = record
                self._write(payload)
                self._session["llm"] = {}
            else:
                self._session["llm"] = record
            return self.llm_status()

    def clear_llm_secret(self) -> dict[str, Any]:
        with self._lock:
            self._session["llm"] = {}
            payload = self._read()
            payload["llm"] = {}
            self._write(payload)
            return self.llm_status()

    def llm_status(self) -> dict[str, Any]:
        config = self.llm_config()
        provider_id = config.get("provider", "deepseek")
        catalog = LLM_PROVIDERS.get(provider_id, LLM_PROVIDERS["custom"])
        secret = str(config.get("api_key") or "")
        return {
            "configured": bool(secret and config.get("model") and config.get("base_url")),
            "provider": provider_id,
            "provider_label": catalog["label"],
            "model": config.get("model") or catalog["default_model"],
            "base_url": config.get("base_url") or catalog["default_base_url"],
            "api_key_masked": _masked(secret),
            "storage": config.get("storage", "none"),
        }

    def data_key(self, source_id: str) -> str:
        normalized = source_id.upper()
        with self._lock:
            session = self._session.get("data_sources", {}).get(normalized, {})
            persisted = self._read().get("data_sources", {}).get(normalized, {})
            record = session or persisted
            if record.get("api_key"):
                return str(record["api_key"])
            env_name = DATA_ENV_KEYS.get(normalized)
            return os.getenv(env_name, "") if env_name else ""

    def save_data_key(self, source_id: str, api_key: str, persist: bool) -> dict[str, Any]:
        normalized = source_id.upper()
        catalog = data_source(normalized)
        if not catalog["key_required"]:
            return self.data_status(normalized)
        secret = api_key.strip()
        if not secret:
            raise ValueError(f"{normalized} API key is required")
        record = {"api_key": secret, "storage": "persistent" if persist else "session"}
        with self._lock:
            if persist:
                payload = self._read()
                payload["data_sources"][normalized] = record
                self._write(payload)
                self._session["data_sources"].pop(normalized, None)
            else:
                self._session["data_sources"][normalized] = record
            return self.data_status(normalized)

    def clear_data_key(self, source_id: str) -> dict[str, Any]:
        normalized = source_id.upper()
        data_source(normalized)
        with self._lock:
            self._session["data_sources"].pop(normalized, None)
            payload = self._read()
            payload["data_sources"].pop(normalized, None)
            self._write(payload)
            return self.data_status(normalized)

    def data_status(self, source_id: str) -> dict[str, Any]:
        normalized = source_id.upper()
        catalog = data_source(normalized)
        secret = self.data_key(normalized)
        storage = "none"
        if secret:
            session = self._session.get("data_sources", {}).get(normalized, {})
            persisted = self._read().get("data_sources", {}).get(normalized, {})
            if session.get("api_key"):
                storage = "session"
            elif persisted.get("api_key"):
                storage = "persistent"
            else:
                storage = "environment"
        return {
            "source_id": normalized,
            "configured": True if not catalog["key_required"] else bool(secret),
            "key_required": catalog["key_required"],
            "api_key_masked": _masked(secret),
            "storage": storage,
        }

    def public_status(self) -> dict[str, Any]:
        return {
            "llm": self.llm_status(),
            "data_sources": [self.data_status(source_id) for source_id in DATA_SOURCES],
            "secret_policy": {
                "browser_storage": False,
                "trace_logging": False,
                "session_default": True,
                "persistent_path": "data/private/provider-config.json",
                "persistent_path_is_gitignored": True,
            },
        }
