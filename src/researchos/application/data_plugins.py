from __future__ import annotations

import csv
import inspect
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from importlib import import_module, util
from io import BytesIO, StringIO
from typing import Any, Protocol
from urllib import error as url_error
from urllib import parse, request

from sqlalchemy.orm import Session

from researchos.application.data_resolve import build_dataset_ref
from researchos.application.ingest import IngestService
from researchos.config import Settings
from researchos.domain.enums import SourceKind
from researchos.domain.exceptions import NotFoundError, ResearchOSError
from researchos.infrastructure.orm import (
    AssetRecord,
    AssetVersionRecord,
    DataPluginSettingRecord,
    WorkspaceRecord,
)

PLUGIN_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")


class DataPluginError(ResearchOSError):
    pass


class DataPluginUnavailableError(DataPluginError):
    pass


@dataclass(frozen=True)
class PluginDescriptor:
    plugin_id: str
    name: str
    description: str
    credential_kind: str
    license_policy: str
    supports_catalog: bool = True


@dataclass(frozen=True)
class DatasetDescriptor:
    dataset_id: str
    name: str
    description: str
    parameters: list[str]


@dataclass(frozen=True)
class PluginDataset:
    content: bytes
    filename: str
    row_count: int
    truncated: bool
    provenance: dict[str, Any]


class DataPluginProvider(Protocol):
    descriptor: PluginDescriptor

    @property
    def available(self) -> bool: ...

    @property
    def configured(self) -> bool: ...

    def list_datasets(self, query_text: str | None, limit: int) -> list[DatasetDescriptor]: ...

    def fetch(
        self,
        dataset_id: str,
        parameters: dict[str, Any],
        row_limit: int,
    ) -> PluginDataset: ...


class AkshareProvider:
    descriptor = PluginDescriptor(
        plugin_id="akshare",
        name="AKShare",
        description="中国及全球金融、宏观和另类数据；公开函数可按结构化参数导入。",
        credential_kind="NONE",
        license_policy="DERIVED_ONLY",
    )

    @property
    def available(self) -> bool:
        return util.find_spec("akshare") is not None

    @property
    def configured(self) -> bool:
        return self.available

    def _module(self):
        if not self.available:
            raise DataPluginUnavailableError(
                "AKShare is not installed; install the data-plugins extra"
            )
        return import_module("akshare")

    def _functions(self) -> dict[str, Any]:
        module = self._module()
        return {
            name: value
            for name in dir(module)
            if PLUGIN_ID_PATTERN.fullmatch(name)
            and not name.startswith("_")
            and callable(value := getattr(module, name, None))
        }

    def list_datasets(self, query_text: str | None, limit: int) -> list[DatasetDescriptor]:
        query_lower = (query_text or "").lower()
        datasets: list[DatasetDescriptor] = []
        for name, function in sorted(self._functions().items()):
            doc = inspect.getdoc(function) or "AKShare public dataset function"
            first_line = doc.splitlines()[0].strip()[:300]
            if query_lower and query_lower not in f"{name} {first_line}".lower():
                continue
            try:
                parameters = [
                    parameter.name
                    for parameter in inspect.signature(function).parameters.values()
                    if parameter.kind not in {parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD}
                ]
            except (TypeError, ValueError):
                parameters = []
            datasets.append(
                DatasetDescriptor(
                    dataset_id=name,
                    name=name,
                    description=first_line,
                    parameters=parameters,
                )
            )
            if len(datasets) >= limit:
                break
        return datasets

    def fetch(
        self,
        dataset_id: str,
        parameters: dict[str, Any],
        row_limit: int,
    ) -> PluginDataset:
        function = self._functions().get(dataset_id)
        if function is None:
            raise NotFoundError("AKShare dataset function was not found")
        signature = inspect.signature(function)
        unknown = sorted(set(parameters) - set(signature.parameters))
        if unknown:
            raise DataPluginError(f"Unsupported AKShare parameter(s): {', '.join(unknown)}")
        result = function(**parameters)
        if not hasattr(result, "to_csv"):
            raise DataPluginError("AKShare function did not return a tabular result")
        total_rows = len(result)
        truncated = total_rows > row_limit
        frame = result.head(row_limit)
        content = frame.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")
        columns = [str(item) for item in getattr(frame, "columns", [])]
        as_of = _infer_as_of(frame, columns)
        return PluginDataset(
            content=content,
            filename=f"akshare-{dataset_id}.csv",
            row_count=min(total_rows, row_limit),
            truncated=truncated,
            provenance={
                "plugin_id": "akshare",
                "dataset_id": dataset_id,
                "parameters": _json_safe(parameters),
                "fields": columns,
                "time_key": _infer_time_key(columns),
                "frequency": None,
                "as_of_date": as_of,
                "license_policy": self.descriptor.license_policy,
                "schema_version": "akshare-tabular-v1",
                "lineage_refs": [f"PLUGIN:AKSHARE:{dataset_id}"],
            },
        )


class FredProvider:
    descriptor = PluginDescriptor(
        plugin_id="fred",
        name="Federal Reserve FRED",
        description="Federal Reserve Bank of St. Louis economic time series with vintage controls.",
        credential_kind="FRED_API_KEY",
        license_policy="PUBLIC",
    )
    _catalog = {
        "UNRATE": "Civilian unemployment rate",
        "PAYEMS": "Total nonfarm payroll employment",
        "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
        "CPILFESL": "Core Consumer Price Index",
        "PCEPI": "Personal Consumption Expenditures price index",
        "PCEPILFE": "Core PCE price index",
        "GDPC1": "Real Gross Domestic Product",
        "INDPRO": "Industrial Production Index",
        "DGS10": "10-year Treasury constant maturity rate",
        "DFF": "Effective federal funds rate",
        "T10Y2Y": "10-year minus 2-year Treasury spread",
        "BAMLH0A0HYM2": "US high-yield option-adjusted spread",
    }

    def __init__(self, api_key: str | None, timeout_seconds: int) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        return True

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def list_datasets(self, query_text: str | None, limit: int) -> list[DatasetDescriptor]:
        query_lower = (query_text or "").lower()
        rows = []
        for series_id, description in self._catalog.items():
            if query_lower and query_lower not in f"{series_id} {description}".lower():
                continue
            rows.append(
                DatasetDescriptor(
                    dataset_id=series_id,
                    name=series_id,
                    description=description,
                    parameters=[
                        "observation_start",
                        "observation_end",
                        "vintage_date",
                        "units",
                        "frequency",
                        "aggregation_method",
                    ],
                )
            )
        return rows[:limit]

    def fetch(
        self,
        dataset_id: str,
        parameters: dict[str, Any],
        row_limit: int,
    ) -> PluginDataset:
        if not self.configured:
            raise DataPluginUnavailableError("FRED_API_KEY is not configured")
        if not PLUGIN_ID_PATTERN.fullmatch(dataset_id):
            raise DataPluginError("Invalid FRED series identifier")
        allowed = {
            "observation_start",
            "observation_end",
            "vintage_date",
            "units",
            "frequency",
            "aggregation_method",
        }
        unknown = sorted(set(parameters) - allowed)
        if unknown:
            raise DataPluginError(f"Unsupported FRED parameter(s): {', '.join(unknown)}")
        query = {
            "series_id": dataset_id,
            "api_key": self._api_key,
            "file_type": "json",
            **{key: str(value) for key, value in parameters.items() if value not in (None, "")},
        }
        url = "https://api.stlouisfed.org/fred/series/observations?" + parse.urlencode(query)
        try:
            with request.urlopen(
                request.Request(url, headers={"User-Agent": "ResearchOS/0.1 data-plugin"}),
                timeout=self._timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, url_error.URLError, json.JSONDecodeError) as exc:
            raise DataPluginError("FRED request failed without producing an asset") from exc
        observations = list(payload.get("observations") or [])
        selected = observations[:row_limit]
        output = StringIO(newline="")
        fields = ["date", "value", "realtime_start", "realtime_end"]
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for item in selected:
            writer.writerow({field: item.get(field) for field in fields})
        as_of = str(
            parameters.get("vintage_date")
            or parameters.get("observation_end")
            or (selected[-1].get("date") if selected else date.today().isoformat())
        )
        return PluginDataset(
            content=output.getvalue().encode("utf-8-sig"),
            filename=f"fred-{dataset_id}.csv",
            row_count=len(selected),
            truncated=len(observations) > row_limit,
            provenance={
                "plugin_id": "fred",
                "dataset_id": dataset_id,
                "parameters": _json_safe(parameters),
                "fields": fields,
                "time_key": "date",
                "frequency": parameters.get("frequency"),
                "as_of_date": as_of,
                "license_policy": self.descriptor.license_policy,
                "schema_version": "fred-observations-v1",
                "units": {"value": str(parameters.get("units") or "level")},
                "field_types": {"date": "date", "value": "float64"},
                "lineage_refs": [f"PLUGIN:FRED:{dataset_id}"],
            },
        )


class DataPluginRegistry:
    def __init__(self, providers: list[DataPluginProvider]) -> None:
        self._providers = {provider.descriptor.plugin_id: provider for provider in providers}

    def all(self) -> list[DataPluginProvider]:
        return [self._providers[key] for key in sorted(self._providers)]

    def get(self, plugin_id: str) -> DataPluginProvider:
        provider = self._providers.get(plugin_id)
        if provider is None:
            raise NotFoundError("data plugin was not found")
        return provider


def build_data_plugin_registry(settings: Settings) -> DataPluginRegistry:
    return DataPluginRegistry(
        [
            AkshareProvider(),
            FredProvider(settings.fred_api_key, settings.data_plugin_timeout_seconds),
        ]
    )


class DataPluginService:
    def __init__(
        self,
        session: Session,
        registry: DataPluginRegistry,
        ingest_service: IngestService,
        max_rows: int,
    ) -> None:
        self.session = session
        self.registry = registry
        self.ingest_service = ingest_service
        self.max_rows = max_rows

    def list_plugins(self) -> list[dict[str, Any]]:
        settings = {row.plugin_id: row for row in self.session.query(DataPluginSettingRecord).all()}
        return [
            self._view(provider, settings.get(provider.descriptor.plugin_id))
            for provider in self.registry.all()
        ]

    def set_enabled(self, plugin_id: str, enabled: bool, actor_id: str) -> dict[str, Any]:
        provider = self.registry.get(plugin_id)
        if enabled and not provider.configured:
            raise DataPluginUnavailableError(
                f"{provider.descriptor.name} is unavailable or missing local credentials"
            )
        record = self.session.get(DataPluginSettingRecord, plugin_id)
        if record is None:
            record = DataPluginSettingRecord(
                plugin_id=plugin_id,
                enabled=enabled,
                updated_by=actor_id,
            )
            self.session.add(record)
        else:
            record.enabled = enabled
            record.updated_by = actor_id
            record.updated_at = datetime.now(UTC)
        self.session.commit()
        return self._view(provider, record)

    def list_datasets(
        self,
        plugin_id: str,
        query_text: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        provider = self.registry.get(plugin_id)
        if not provider.available:
            raise DataPluginUnavailableError(f"{provider.descriptor.name} is unavailable")
        return [vars(item) for item in provider.list_datasets(query_text, min(limit, 500))]

    def ingest(
        self,
        *,
        plugin_id: str,
        workspace_id: str,
        actor_id: str,
        dataset_id: str,
        parameters: dict[str, Any],
        logical_name: str | None,
        row_limit: int | None,
    ) -> dict[str, Any]:
        if self.session.get(WorkspaceRecord, workspace_id) is None:
            raise NotFoundError("workspace not found")
        provider = self.registry.get(plugin_id)
        setting = self.session.get(DataPluginSettingRecord, plugin_id)
        if setting is None or not setting.enabled:
            raise DataPluginError("data plugin must be enabled before use")
        if not provider.configured:
            raise DataPluginUnavailableError(f"{provider.descriptor.name} is not configured")
        limit = min(max(row_limit or self.max_rows, 1), self.max_rows)
        dataset = provider.fetch(dataset_id, parameters, limit)
        stable_parameters = json.dumps(
            _json_safe(parameters), sort_keys=True, separators=(",", ":")
        )
        source_key = f"plugin:{plugin_id}:{dataset_id}:{stable_parameters}"
        batch = self.ingest_service.create_batch(workspace_id=workspace_id, actor_id=actor_id)
        outcome = self.ingest_service.ingest_item(
            batch_id=batch.id,
            stream=BytesIO(dataset.content),
            original_filename=dataset.filename,
            actor_id=actor_id,
            logical_name=logical_name or f"{provider.descriptor.name} · {dataset_id}",
            source_key=source_key,
            source_kind=SourceKind.CONNECTOR,
            source_metadata=dataset.provenance,
        )
        self.ingest_service.finalize_batch(batch_id=batch.id, actor_id=actor_id)
        if outcome.asset_id is None or outcome.version_id is None:
            raise DataPluginError(outcome.error or "plugin data could not be stored")
        asset = self.session.get(AssetRecord, outcome.asset_id)
        version = self.session.get(AssetVersionRecord, outcome.version_id)
        if asset is None or version is None:
            raise DataPluginError("stored plugin dataset could not be reloaded")
        return {
            "plugin_id": plugin_id,
            "dataset_id": dataset_id,
            "batch_id": batch.id,
            "asset_id": asset.id,
            "version_id": version.id,
            "status": outcome.status,
            "resolution_status": outcome.resolution_status,
            "row_count": dataset.row_count,
            "truncated": dataset.truncated,
            "data_ref": build_dataset_ref(asset, version),
        }

    @staticmethod
    def _view(
        provider: DataPluginProvider,
        setting: DataPluginSettingRecord | None,
    ) -> dict[str, Any]:
        descriptor = provider.descriptor
        return {
            "plugin_id": descriptor.plugin_id,
            "name": descriptor.name,
            "description": descriptor.description,
            "credential_kind": descriptor.credential_kind,
            "license_policy": descriptor.license_policy,
            "supports_catalog": descriptor.supports_catalog,
            "available": provider.available,
            "configured": provider.configured,
            "enabled": bool(setting and setting.enabled),
        }


def _infer_time_key(columns: list[str]) -> str | None:
    candidates = {"date", "日期", "时间", "period", "time", "timestamp"}
    return next((column for column in columns if column.lower() in candidates), None)


def _infer_as_of(frame: Any, columns: list[str]) -> str:
    time_key = _infer_time_key(columns)
    if time_key and len(frame):
        try:
            value = frame[time_key].iloc[-1]
            parsed = str(value)[:10]
            date.fromisoformat(parsed)
            return parsed
        except (KeyError, TypeError, ValueError, AttributeError):
            pass
    return date.today().isoformat()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
