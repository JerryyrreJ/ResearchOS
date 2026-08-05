from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from researchos.infrastructure.blob_store import LocalContentAddressedBlobStore
from researchos.infrastructure.orm import AssetRecord, AssetVersionRecord, BlobRecord

FROZEN_CONTRACT_VERSION = "0.1.0-frozen"


def _representation(format_kind: str) -> str:
    return {
        "CSV": "CSV",
        "XLSX": "XLSX",
        "MARKDOWN": "MARKDOWN",
        "DOCX": "DOCX",
        "PDF_TEXT": "PDF",
    }.get(format_kind, "BINARY")


def _schema_from_version(version: AssetVersionRecord) -> dict[str, Any]:
    metadata = dict(version.deterministic_metadata or {})
    provenance = dict(metadata.get("source_provenance") or {})
    header = [str(item) for item in metadata.get("header") or provenance.get("fields") or []]
    time_key = provenance.get("time_key")
    if time_key not in header:
        time_key = next(
            (name for name in header if name.lower() in {"date", "period", "time", "timestamp"}),
            None,
        )
    return {
        "time_key": time_key,
        "entity_keys": list(provenance.get("entity_keys") or []),
        "value_fields": [name for name in header if name != time_key],
        "frequency": provenance.get("frequency"),
        "units": dict(provenance.get("units") or {}),
        "field_types": dict(provenance.get("field_types") or {}),
    }


def build_dataset_ref(asset: AssetRecord, version: AssetVersionRecord) -> dict[str, Any]:
    metadata = dict(version.deterministic_metadata or {})
    provenance = dict(metadata.get("source_provenance") or {})
    lineage = [f"ASSET:{asset.id}"]
    if asset.source_key:
        lineage.append(asset.source_key)
    if version.parent_version_id:
        lineage.append(f"VERSION:{version.parent_version_id}")
    lineage.extend(str(item) for item in provenance.get("lineage_refs") or [])
    return {
        "contract_version": FROZEN_CONTRACT_VERSION,
        "object_id": asset.id,
        "version_id": version.id,
        "object_type": "DATASET",
        "name": asset.logical_name,
        "representation": _representation(version.format_kind),
        "schema_version": str(provenance.get("schema_version") or "data-plugin-v1"),
        "content_hash": version.content_hash,
        "license_policy": str(provenance.get("license_policy") or "INTERNAL_ONLY"),
        "access_scope": f"WORKSPACE:{asset.workspace_id}",
        "content_uri": f"/api/v1/asset-versions/{version.id}/content",
        "as_of_date": provenance.get("as_of_date"),
        "data_schema": _schema_from_version(version),
        "lineage_refs": lineage,
        "metadata": {
            "source_kind": version.source_kind,
            "source_filename": version.source_filename,
            "source_provenance": provenance,
        },
    }


def _error(code: str, message: str, related_refs: list[str]) -> dict[str, Any]:
    return {
        "contract_version": FROZEN_CONTRACT_VERSION,
        "error_code": code,
        "message": message,
        "retryable": False,
        "related_refs": related_refs,
        "details": {},
    }


@dataclass(frozen=True)
class ResolvedContent:
    path: Path
    filename: str
    media_type: str
    content_hash: str


class DataResolveService:
    def __init__(
        self,
        session: Session,
        blob_store: LocalContentAddressedBlobStore,
    ) -> None:
        self.session = session
        self.blob_store = blob_store

    def resolve(self, request: dict[str, Any]) -> dict[str, Any]:
        requested_ref = dict(request["dataset_ref"])
        related = [requested_ref["object_id"], requested_ref["version_id"]]
        base = {
            "contract_version": FROZEN_CONTRACT_VERSION,
            "request_id": request["request_id"],
            "resolved_ref": requested_ref,
            "materialized_uri": None,
            "content_hash": None,
            "resolved_schema": {},
            "lineage": list(requested_ref.get("lineage_refs") or []),
        }
        asset = self.session.get(AssetRecord, requested_ref["object_id"])
        version = self.session.get(AssetVersionRecord, requested_ref["version_id"])
        if asset is None or version is None or version.asset_id != asset.id:
            return {
                **base,
                "status": "NOT_FOUND",
                "error": _error(
                    "DATASET_NOT_FOUND", "Pinned dataset version was not found", related
                ),
            }

        resolved_ref = build_dataset_ref(asset, version)
        base.update(
            resolved_ref=resolved_ref,
            content_hash=version.content_hash,
            resolved_schema=resolved_ref["data_schema"],
            lineage=resolved_ref["lineage_refs"],
        )
        if requested_ref["access_scope"] != resolved_ref["access_scope"]:
            return {
                **base,
                "status": "PERMISSION_BLOCKED",
                "error": _error(
                    "DATASET_PERMISSION_BLOCKED",
                    "Dataset belongs to a different workspace scope",
                    related,
                ),
            }
        if requested_ref["content_hash"] != version.content_hash:
            return {
                **base,
                "status": "FAILED",
                "error": _error(
                    "DATASET_HASH_MISMATCH",
                    "Pinned content hash does not match the stored immutable version",
                    related,
                ),
            }

        as_of = date.fromisoformat(request["as_of_date"])
        ref_as_of = resolved_ref.get("as_of_date")
        if ref_as_of and date.fromisoformat(ref_as_of) > as_of:
            return {
                **base,
                "status": "NOT_FOUND",
                "error": _error(
                    "DATASET_NOT_AVAILABLE_AS_OF",
                    "Dataset snapshot was not available at the requested as-of date",
                    related,
                ),
            }

        required = request["required_schema"]
        resolved_schema = resolved_ref["data_schema"]
        available_fields = {
            item
            for item in [
                resolved_schema.get("time_key"),
                *resolved_schema.get("entity_keys", []),
                *resolved_schema.get("value_fields", []),
            ]
            if item
        }
        missing = sorted(set(required.get("fields") or []) - available_fields)
        frequency = resolved_schema.get("frequency")
        allowed_frequencies = required.get("frequency") or []
        time_key_mismatch = bool(
            required.get("time_key") and required["time_key"] != resolved_schema.get("time_key")
        )
        frequency_mismatch = bool(allowed_frequencies and frequency not in allowed_frequencies)
        if missing or time_key_mismatch or frequency_mismatch:
            return {
                **base,
                "status": "SCHEMA_MISMATCH",
                "error": {
                    **_error(
                        "DATASET_SCHEMA_MISMATCH",
                        "Stored dataset does not satisfy the requested schema",
                        related,
                    ),
                    "details": {
                        "missing_fields": missing,
                        "time_key_mismatch": time_key_mismatch,
                        "frequency_mismatch": frequency_mismatch,
                    },
                },
            }
        return {
            **base,
            "status": "RESOLVED",
            "materialized_uri": resolved_ref["content_uri"],
            "error": None,
        }

    def content(self, version_id: str) -> ResolvedContent | None:
        version = self.session.get(AssetVersionRecord, version_id)
        if version is None:
            return None
        blob = self.session.get(BlobRecord, version.blob_id)
        if blob is None:
            return None
        path = self.blob_store.path_for(blob.storage_key)
        if not path.is_file():
            return None
        return ResolvedContent(
            path=path,
            filename=version.source_filename,
            media_type=version.mime_type,
            content_hash=version.content_hash,
        )
