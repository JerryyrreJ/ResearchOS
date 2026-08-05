from __future__ import annotations

import json
import os
import hashlib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


CONTRACT_VERSION = "0.1.0-frozen"
EVIDENCE_LEVELS = (
    "DESCRIPTIVE",
    "PREDICTIVE",
    "ASSOCIATIONAL",
    "DYNAMIC_ASSOCIATION",
    "STRUCTURAL_PROXY",
    "CAUSAL_IDENTIFIED",
)
FORBIDDEN_CONTROL_KEYS = frozenset(
    {
        "arbitrary_code",
        "code",
        "executable",
        "formula",
        "python",
        "python_code",
        "registry",
        "registry_override",
        "registry_patch",
        "script",
        "sql",
        "sql_query",
    }
)


class ContractViolation(ValueError):
    def __init__(self, contract_name: str, errors: list[str]) -> None:
        super().__init__(f"{contract_name} validation failed")
        self.contract_name = contract_name
        self.errors = tuple(errors)


class UnsafeControlField(ValueError):
    def __init__(self, path: str) -> None:
        super().__init__("ToolRequest contains a forbidden execution-control field")
        self.path = path


def find_researchos_root(start: Path | None = None) -> Path:
    override = os.getenv("RESEARCHOS_REPO_ROOT", "").strip()
    if override:
        root = Path(override).expanduser().resolve()
        if not (root / "contracts" / "v1" / "contract_manifest.json").is_file():
            raise RuntimeError("RESEARCHOS_REPO_ROOT does not contain frozen contracts/v1")
        return root

    current = (start or Path(__file__)).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "contracts" / "v1" / "contract_manifest.json").is_file():
            return candidate
    raise RuntimeError("Unable to locate the ResearchOS repository root")


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Schema must be a JSON object: {path.name}")
    return payload


def _error_path(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    location = path or "$"
    # Do not reflect submitted values into API errors; ToolRequest metadata may
    # contain private research context even though credentials are not allowed.
    return f"{location}: {error.validator} validation failed"


def reject_unsafe_control_fields(payload: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(key).strip().lower().replace("-", "_").replace(" ", "_")
            current = (*path, str(key))
            if normalized in FORBIDDEN_CONTROL_KEYS:
                raise UnsafeControlField(".".join(current))
            reject_unsafe_control_fields(value, current)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            reject_unsafe_control_fields(value, (*path, str(index)))


class FrozenContractRegistry:
    """Loads the repository-owned frozen schemas without duplicating them."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or find_researchos_root()).resolve()
        self.contract_dir = self.repo_root / "contracts" / "v1"
        self._verify_frozen_hashes()
        self.schemas = {
            path.name: _json(path)
            for path in sorted(self.contract_dir.glob("*.schema.json"))
        }
        resources = []
        for schema in self.schemas.values():
            schema_id = schema.get("$id")
            if not schema_id:
                raise RuntimeError("Every frozen schema must declare an $id")
            resources.append((schema_id, Resource.from_contents(schema)))
        self.registry = Registry().with_resources(resources)

    @staticmethod
    def _git_canonical_bytes(path: Path) -> bytes:
        """Hash text contracts as stored in Git, independent of Windows CRLF checkout."""
        return path.read_bytes().replace(b"\r\n", b"\n")

    def _verify_frozen_hashes(self) -> None:
        manifest_path = self.contract_dir / "CONTRACT_HASHES.sha256"
        for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            expected, name = raw_line.split(maxsplit=1)
            path = self.contract_dir / name
            actual = hashlib.sha256(self._git_canonical_bytes(path)).hexdigest()
            if actual != expected:
                raise RuntimeError(f"Frozen contract hash mismatch: {name}")

    def validator(self, schema_name: str) -> Draft202012Validator:
        try:
            schema = self.schemas[schema_name]
        except KeyError as exc:
            raise RuntimeError(f"Frozen schema not found: {schema_name}") from exc
        return Draft202012Validator(
            schema,
            registry=self.registry,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )

    def validate(self, schema_name: str, payload: Any) -> None:
        errors = sorted(
            self.validator(schema_name).iter_errors(payload),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        if errors:
            raise ContractViolation(schema_name, [_error_path(error) for error in errors[:20]])

    def validate_tool_request(self, payload: Any) -> None:
        self.validate("tool_request.schema.json", payload)
        reject_unsafe_control_fields(payload)

    def validate_evidence_bundle(self, payload: Any) -> None:
        self.validate("evidence_bundle.schema.json", payload)


def cap_evidence_type(candidate: str, requested: str) -> str:
    candidate_index = EVIDENCE_LEVELS.index(candidate)
    requested_index = EVIDENCE_LEVELS.index(requested)
    return EVIDENCE_LEVELS[min(candidate_index, requested_index)]
