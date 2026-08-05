# ResearchOS engineering rules

## Product authority

- The v0.3 product baseline and `docs/M1_ARCHITECTURE.md` govern the deterministic asset foundation.
- Research Ontology owns files, object identity, versions, relations and Context Packs.
- Thesis Compiler owns compile issues, validation plans, evidence-language policy and final conclusion state.
- MacroTrace owns registered empirical execution, diagnostics, robustness and engine evidence.
- Frontend owns presentation, client state, deployment and E2E. It never invents backend semantics.

## Directory ownership

- A: `src/researchos`, `migrations`, and the deterministic asset/query services.
- B: MacroTrace adapter and snapshots.
- C: Thesis compiler and orchestration.
- D: `apps/web`, web deployment, and browser E2E.
- Shared frozen: `contracts/v1`, `fixtures/contracts`, and executable API contracts.

## Non-negotiable invariants

1. Asset and AssetVersion are different identities.
2. AssetVersion content is immutable.
3. Blob deduplication never merges logical Assets.
4. References pin exact version and representation IDs; never persist `latest`.
5. A Fragment always belongs to an exact Representation and AssetVersion.
6. File type, metadata, hashing, parsing and exact duplicate detection are code paths, not AI.
7. Ambiguous logical identity must not be silently merged.
8. Old versions and failed parse runs remain auditable.
9. One failed item must not roll back a whole IngestBatch.
10. Domain code must not depend on FastAPI or a concrete blob provider.

## Scope and integration rules

- M1 owns Workspace, Asset, AssetVersion, Blob, Representation, Fragment,
  IngestBatch, IngestItem, ParseRun and AuditEvent.
- ClassificationAssertion and semantic relations are reserved for M2.
- Commit, Branch, Merge and WorkspaceRevision are out of scope for M1.
- Frontend integration must use API clients and must not access the database directly.
- Fixture, Offline Replay and Real API modes must remain visibly distinct.
- Failed, partial, unsupported, stale and offline states must remain visible.
- No breaking contract change without an approved ICR.

## Quality gates

- Add tests for every invariant change.
- Keep migrations forward-only.
- Use deterministic fixtures.
- Never fabricate successful parser, model or job results.
