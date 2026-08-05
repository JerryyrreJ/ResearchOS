from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver

CONTRACT_DIR = Path(__file__).resolve().parents[4] / "contracts" / "v1"


@lru_cache
def _validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((CONTRACT_DIR / schema_name).read_text(encoding="utf-8"))
    store: dict[str, dict[str, Any]] = {}
    for path in CONTRACT_DIR.glob("*.schema.json"):
        child = json.loads(path.read_text(encoding="utf-8"))
        store[child["$id"]] = child
    return Draft202012Validator(schema, resolver=RefResolver.from_schema(schema, store=store))


def validate_contract(schema_name: str, payload: dict[str, Any]) -> None:
    """Validate an API boundary against the immutable v1 JSON Schema."""
    _validator(schema_name).validate(payload)
