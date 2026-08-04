from __future__ import annotations

import json
from dataclasses import replace

import pytest

from backend.app.config import get_settings
from backend.app.credentials import LocalCredentialStore
from backend.app.provider_catalog import public_provider_catalog


def credential_store(tmp_path) -> LocalCredentialStore:
    settings = replace(
        get_settings(),
        data_dir=tmp_path / "data",
        raw_dir=tmp_path / "data" / "raw",
        database_path=tmp_path / "data" / "macrotrace.duckdb",
        deepseek_api_key="",
    )
    return LocalCredentialStore(settings, tmp_path / "private" / "provider-config.json")


def test_session_secret_never_appears_in_public_status(tmp_path) -> None:
    store = credential_store(tmp_path)
    secret = "session-test-secret-123456789"
    store.save_llm(
        provider_id="deepseek",
        model="deepseek-v4-flash",
        base_url=None,
        api_key=secret,
        persist=False,
    )
    public = json.dumps(store.public_status(), ensure_ascii=False)
    assert secret not in public
    assert store.llm_status()["api_key_masked"]
    assert not store.path.exists()


def test_persistent_secret_is_local_and_public_payload_is_masked(tmp_path) -> None:
    store = credential_store(tmp_path)
    secret = "fred-test-secret-123456789"
    store.save_data_key("FRED", secret, persist=True)
    assert secret in store.path.read_text(encoding="utf-8")
    assert secret not in json.dumps(store.public_status(), ensure_ascii=False)
    assert store.data_status("FRED")["storage"] == "persistent"


def test_switching_provider_requires_a_key_for_the_new_provider(tmp_path) -> None:
    store = credential_store(tmp_path)
    store.save_llm(
        provider_id="deepseek",
        model="deepseek-v4-flash",
        base_url=None,
        api_key="deepseek-test-only",
        persist=False,
    )
    with pytest.raises(ValueError, match="API key is required"):
        store.save_llm(
            provider_id="openai",
            model="gpt-5.6-terra",
            base_url=None,
            api_key=None,
            persist=False,
        )


def test_non_local_plain_http_endpoint_is_rejected(tmp_path) -> None:
    store = credential_store(tmp_path)
    with pytest.raises(ValueError, match="HTTPS"):
        store.save_llm(
            provider_id="custom",
            model="private-model",
            base_url="http://example.com/v1",
            api_key="secret",
            persist=False,
        )


def test_catalog_contains_current_models_and_official_data_guides() -> None:
    catalog = public_provider_catalog()
    models = {
        model["id"]
        for item in catalog["llm_providers"]
        for model in item["models"]
    }
    sources = {item["source_id"] for item in catalog["data_sources"]}
    assert {"gpt-5.6-terra", "deepseek-v4-flash", "claude-sonnet-5", "gemini-3.5-flash"} <= models
    assert {"FRED", "BLS", "EIA", "TREASURY", "NYFED"} <= sources
    assert all(item["guide_steps"] for item in catalog["data_sources"])


def test_frontend_does_not_persist_api_keys_in_browser_storage() -> None:
    source = (get_settings().project_root / "frontend" / "app.js").read_text(encoding="utf-8")
    index = (get_settings().project_root / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "macrotrace.history" in source
    assert 'localStorage.setItem("api' not in source
    assert "provider-config.json" in index
    assert 'id="mobileSettingsButton"' in index
    assert '$("#mobileSettingsButton").addEventListener' in source
