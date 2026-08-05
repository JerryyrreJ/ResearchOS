from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr


class LLMSettingsUpdate(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    model: str = Field(min_length=1, max_length=160)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: SecretStr | None = None
    persist: bool = False


class DataSourceSettingsUpdate(BaseModel):
    api_key: SecretStr = Field()
    persist: bool = False


class ConnectionTestResult(BaseModel):
    ok: bool
    target: str
    latency_ms: int
    detail: str
    model: str | None = None

