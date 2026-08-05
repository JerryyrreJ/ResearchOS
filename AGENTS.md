# ResearchOS engineering rules

## Authority

The v0.3 product baseline is the product authority. docs/M1_ARCHITECTURE.md
freezes how this codebase implements its deterministic asset foundation.

## Non-negotiable invariants

1. Asset and AssetVersion are different identities.
2. AssetVersion content is immutable.
3. Blob deduplication never merges logical Assets.
4. References pin exact version and representation IDs; never persist "latest".
5. A Fragment always belongs to an exact Representation and AssetVersion.
6. File type, metadata, hashing, parsing and exact duplicate detection are code paths, not AI.
7. Ambiguous logical identity must not be silently merged.
8. Old versions and failed parse runs remain auditable.
9. One failed item must not roll back a whole IngestBatch.
10. Domain code must not depend on FastAPI or a concrete blob provider.

## Scope

- M1 owns Workspace, Asset, AssetVersion, Blob, Representation, Fragment,
  IngestBatch, IngestItem, ParseRun and AuditEvent.
- ClassificationAssertion and semantic relations are reserved for M2.
- Commit, Branch, Merge and WorkspaceRevision are out of scope.
- Chunk-level delta storage is a future storage implementation and must not leak
  into the M1 domain contract.

## Quality gates

- Add tests for every invariant change.
- Keep migrations forward-only.
- Use deterministic fixtures.
- Never fabricate successful parser or job results.
