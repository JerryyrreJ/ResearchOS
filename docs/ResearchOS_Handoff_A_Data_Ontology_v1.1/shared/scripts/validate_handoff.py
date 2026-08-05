from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / 'contracts' / 'v1'
FIXTURES = ROOT / 'fixtures' / 'contracts'

MAPPING = {
    'sample_data_object_ref.json': 'data_object_ref.schema.json',
    'sample_context_pack.json': 'context_pack.schema.json',
    'sample_thesis_build.json': 'thesis_build.schema.json',
    'sample_tool_request.json': 'tool_request.schema.json',
    'sample_evidence_bundle.json': 'evidence_bundle.schema.json',
    'sample_compile_result.json': 'compile_result.schema.json',
    'sample_ontology_relation.json': 'ontology_relation.schema.json',
    'sample_version_diff.json': 'version_diff.schema.json',
}

def main() -> int:
    for path in sorted(CONTRACTS.glob('*.json')):
        json.loads(path.read_text(encoding='utf-8'))
    for path in sorted(FIXTURES.glob('*.json')):
        json.loads(path.read_text(encoding='utf-8'))

    expected = {}
    for line in (CONTRACTS / 'CONTRACT_HASHES.sha256').read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        expected[name.strip()] = digest
    for name, digest in expected.items():
        actual = hashlib.sha256((CONTRACTS / name).read_bytes()).hexdigest()
        if actual != digest:
            raise SystemExit(f'hash mismatch: {name}')

    try:
        from jsonschema import Draft202012Validator, RefResolver
    except ImportError:
        print('JSON parsed and hashes passed. Install jsonschema for fixture validation.')
        return 0

    store = {}
    for path in CONTRACTS.glob('*.schema.json'):
        schema = json.loads(path.read_text(encoding='utf-8'))
        store[schema['$id']] = schema
        store[path.name] = schema

    for fixture_name, schema_name in MAPPING.items():
        schema = json.loads((CONTRACTS / schema_name).read_text(encoding='utf-8'))
        instance = json.loads((FIXTURES / fixture_name).read_text(encoding='utf-8'))
        resolver = RefResolver.from_schema(schema, store=store)
        Draft202012Validator(schema, resolver=resolver).validate(instance)
        print(f'PASS {fixture_name} -> {schema_name}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
