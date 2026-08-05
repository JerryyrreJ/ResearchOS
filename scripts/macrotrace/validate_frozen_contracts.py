from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MACROTRACE_ROOT = REPO_ROOT / "services" / "macrotrace"
if str(MACROTRACE_ROOT) not in sys.path:
    sys.path.insert(0, str(MACROTRACE_ROOT))

from backend.app.researchos_adapter.contracts import FrozenContractRegistry  # noqa: E402


FIXTURE_SCHEMAS = {
    "sample_compile_result.json": "compile_result.schema.json",
    "sample_context_pack.json": "context_pack.schema.json",
    "sample_data_object_ref.json": "data_object_ref.schema.json",
    "sample_evidence_bundle.json": "evidence_bundle.schema.json",
    "sample_ontology_relation.json": "ontology_relation.schema.json",
    "sample_thesis_build.json": "thesis_build.schema.json",
    "sample_tool_request.json": "tool_request.schema.json",
    "sample_version_diff.json": "version_diff.schema.json",
}


def verify_hashes() -> int:
    contract_dir = REPO_ROOT / "contracts" / "v1"
    failures = 0
    for raw_line in (contract_dir / "CONTRACT_HASHES.sha256").read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        expected, name = raw_line.split(maxsplit=1)
        # Frozen hashes describe Git's LF bytes. A Windows checkout may present
        # CRLF in the working tree, which must not be confused with content drift.
        canonical_bytes = (contract_dir / name).read_bytes().replace(b"\r\n", b"\n")
        actual = hashlib.sha256(canonical_bytes).hexdigest()
        if actual != expected:
            print(f"HASH FAIL {name}: expected {expected}, got {actual}")
            failures += 1
        else:
            print(f"HASH PASS {name}")
    return failures


def verify_fixtures() -> int:
    registry = FrozenContractRegistry(REPO_ROOT)
    fixture_dir = REPO_ROOT / "fixtures" / "contracts"
    failures = 0
    for name, schema_name in FIXTURE_SCHEMAS.items():
        try:
            registry.validate(schema_name, json.loads((fixture_dir / name).read_text(encoding="utf-8")))
            print(f"SCHEMA PASS {name} -> {schema_name}")
        except Exception as exc:
            print(f"SCHEMA FAIL {name}: {exc}")
            failures += 1
    return failures


def main() -> int:
    failures = verify_hashes() + verify_fixtures()
    print(f"SUMMARY failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
