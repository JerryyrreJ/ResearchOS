# Role A Interface Guide

## Public models

### DataObjectRef

This is the only portable identity for a data/file object. Never send raw database row IDs without the version and hash.

Mandatory invariants:

```text
object_id stable across versions
version_id immutable
content_hash matches exact bytes of representation
license_policy enforced before materialization
access_scope validated for each request
```

### ContextPack

The pack must pin versions. It cannot contain `"latest"` as a version.

### OntologyRelation

AI proposals remain `AI_PROPOSED` until review. Exact duplicates may be deterministically confirmed if policy allows, but preserve the audit event.

## Data Resolve behavior

### Request

- Validate contract version.
- Validate caller permission.
- Resolve exact object and exact version.
- Check requested fields/frequency.
- Materialize to job-scoped cache.
- Return content hash and lineage.

### Errors

```text
NOT_FOUND
PERMISSION_BLOCKED
SCHEMA_MISMATCH
MATERIALIZATION_FAILED
HASH_MISMATCH
```

Never substitute another dataset silently.

## Object identity rules

- Same bytes: same content hash, may reference existing representation.
- Same logical object with edited content: new version.
- Similar title only: version candidate, not automatic.
- Derived Markdown from DOCX: separate Representation linked to source version.
- Model result: new Object, never append into input object.
