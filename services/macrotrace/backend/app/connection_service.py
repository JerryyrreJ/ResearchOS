from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

import httpx

from .connection_schemas import ConnectionTestResult
from .credentials import LocalCredentialStore
from .llm import DeepSeekClient
from .provider_catalog import data_source


class ConnectionService:
    def __init__(self, credentials: LocalCredentialStore, llm: DeepSeekClient) -> None:
        self.credentials = credentials
        self.llm = llm

    def test_llm(self) -> ConnectionTestResult:
        started = perf_counter()
        output = self.llm.json_completion(
            "Return one JSON object and nothing else.",
            'Return exactly {"macrotrace_connection":"ok"}.',
            max_tokens=80,
        )
        if output.get("macrotrace_connection") != "ok":
            raise RuntimeError("Provider returned an unexpected structured response")
        return ConnectionTestResult(
            ok=True,
            target=self.llm.provider,
            model=self.llm.model,
            latency_ms=round((perf_counter() - started) * 1000),
            detail="结构化输出测试通过。",
        )

    def test_data_source(self, source_id: str) -> ConnectionTestResult:
        normalized = source_id.upper()
        catalog = data_source(normalized)
        key = self.credentials.data_key(normalized)
        if catalog["key_required"] and not key:
            raise RuntimeError(f"{normalized} API key is not configured")
        started = perf_counter()
        if normalized == "FRED":
            self._test_fred(key)
        elif normalized == "BLS":
            self._test_bls(key)
        elif normalized == "EIA":
            self._test_eia(key)
        elif normalized == "TREASURY":
            self._test_treasury()
        elif normalized == "NYFED":
            self._test_nyfed()
        else:
            raise ValueError(f"Unsupported data source: {normalized}")
        return ConnectionTestResult(
            ok=True,
            target=normalized,
            latency_ms=round((perf_counter() - started) * 1000),
            detail="官方接口连接与响应格式检查通过。",
        )

    @staticmethod
    def _test_fred(api_key: str) -> None:
        with httpx.Client(timeout=25) as client:
            response = client.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": "GDP",
                    "api_key": api_key,
                    "file_type": "json",
                    "limit": 1,
                    "sort_order": "desc",
                },
            )
            response.raise_for_status()
            payload = response.json()
        if not payload.get("observations"):
            raise RuntimeError("FRED returned no observations")

    @staticmethod
    def _test_bls(api_key: str) -> None:
        year = datetime.now(UTC).year
        with httpx.Client(timeout=25) as client:
            response = client.post(
                "https://api.bls.gov/publicAPI/v2/timeseries/data/",
                json={
                    "seriesid": ["LNS14000000"],
                    "startyear": str(year - 1),
                    "endyear": str(year),
                    "registrationkey": api_key,
                },
            )
            response.raise_for_status()
            payload = response.json()
        if payload.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError("BLS did not accept the registration key")

    @staticmethod
    def _test_eia(api_key: str) -> None:
        with httpx.Client(timeout=25) as client:
            response = client.get(
                "https://api.eia.gov/v2/petroleum/pri/spt/data/",
                params={
                    "api_key": api_key,
                    "frequency": "weekly",
                    "data[0]": "value",
                    "facets[series][]": "RWTC",
                    "sort[0][column]": "period",
                    "sort[0][direction]": "desc",
                    "length": 1,
                },
            )
            response.raise_for_status()
            payload = response.json()
        if not payload.get("response", {}).get("data"):
            raise RuntimeError("EIA returned no observations")

    @staticmethod
    def _test_treasury() -> None:
        with httpx.Client(timeout=25) as client:
            response = client.get(
                "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny",
                params={"page[size]": 1, "sort": "-record_date"},
            )
            response.raise_for_status()
            payload = response.json()
        if not payload.get("data"):
            raise RuntimeError("Treasury Fiscal Data returned no observations")

    @staticmethod
    def _test_nyfed() -> None:
        with httpx.Client(timeout=25) as client:
            response = client.get("https://markets.newyorkfed.org/api/rates/all/latest.json")
            response.raise_for_status()
            payload = response.json()
        if "refRates" not in payload:
            raise RuntimeError("New York Fed returned an unexpected response")

