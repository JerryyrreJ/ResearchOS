# Data Plugin Implementation Log

Date: 2026-08-05 (Asia/Shanghai)

## What changed

- Added a server-side plugin registry with switchable AKShare and FRED providers.
- Routed plugin output through Role A's existing ingest, content hashing, deduplication,
  immutable AssetVersion and lineage records.
- Implemented the frozen Data Resolve request/response behavior without changing any file
  under `contracts/v1` or `fixtures/contracts`.
- Added a small Role D browser surface for enabling plugins and importing a dataset into the
  current workspace.
- Replaced the stale one-service launcher with a local launcher for the unified A+B+C API and
  browser workspace.

## Security and boundary decisions

- Credentials are read only from the process environment or an ignored local environment file.
- The API reports only whether a credential is configured; it never returns the credential.
- AKShare execution is restricted to a discovered public callable name and structured keyword
  arguments. Browser-provided Python, SQL and formulas are rejected by construction.
- A plugin must be enabled before use. Missing packages, missing credentials and provider
  failures produce explicit errors and do not create placeholder assets.
- MacroTrace must consume the returned pinned DataObjectRef through Data Resolve. Direct
  database access and automatic latest-version substitution remain forbidden.

## Verification evidence

- Real AKShare smoke: `macro_china_cpi` returned a tabular CSV and obeyed the row cap.
- Real FRED smoke: `UNRATE` returned observations from the official API using the existing
  local credential; the key was not printed, persisted or copied into the repository.
- API tests cover plugin state, ingest, immutable deduplication, frozen-schema validation,
  content materialization, resolve success and failure states.
- Frontend lint and Windows-compatible production build pass.
- Frozen contract and fixture directories have no diff.

## Consumer handoff

Role B receives `data_ref` from plugin ingest and sends the same pinned reference to
`POST /api/v1/data/resolve`. A successful response provides the materialized URI, schema,
hash and lineage. Any hash, scope, schema, frequency or as-of mismatch remains visible and
must stop that model input rather than falling back silently.

## Product-mainline update

The product owner subsequently released the A/B/C/D ownership boundaries and changed the demo
story. MacroTrace (B) is now the primary product; A is the evidence-space layer shown before the
empirical graph, C remains the conclusion-language boundary, and D delivers the browser. The
implementation therefore mounts the mature MacroTrace app as the unified local root and reuses
its existing Research Graph and report instead of rebuilding those screens.

The data universe is created before routing. Every registered dataset/factor remains visible in
grey; selected nodes are promoted to planned/running/success states. A completed complex plan
produced 375 nodes and 537 edges with 15 visible dataset families, which materially fixes the
earlier shallow-demo problem.
