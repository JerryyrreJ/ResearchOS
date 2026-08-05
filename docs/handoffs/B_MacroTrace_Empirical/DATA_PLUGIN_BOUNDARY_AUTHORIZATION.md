# Data Plugin Boundary Authorization

Date: 2026-08-05 (Asia/Shanghai)

## Human authorization

The product owner explicitly authorized Role B to extend the Role A data-acquisition surface so
MacroTrace can obtain research datasets before the full research-file corpus exists.

## Narrow scope

- Add selectable AKShare and FRED data-source plugins.
- Store every fetched table through A's existing immutable Asset and AssetVersion model.
- Implement the already-frozen `DataResolveRequest/Response` behavior at `/api/v1/data/resolve`.
- Add a minimal D-owned selector/import surface that consumes these additive endpoints.
- Keep all credentials local and server-side.

## Boundaries that remain frozen

- No change to any file in `contracts/v1` or `fixtures/contracts`.
- No direct B access to A's database.
- No arbitrary Python, SQL, or model-generated code execution.
- No automatic latest-version substitution: B must pin object ID, version ID, and content hash.
- No claim that AKShare or FRED data are live when a plugin is disabled, unavailable, or replayed.

## Contract impact

`NONE` for frozen contracts. The plugin catalog and ingestion endpoints are additive local
application APIs. The `/data/resolve` implementation conforms to the existing
`0.1.0-frozen` schema.

## Ownership after this slice

The files remain owned by their original roles. This is a narrowly delegated implementation,
not a permanent transfer of Role A or Role D ownership to Role B.
