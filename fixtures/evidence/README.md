# MacroTrace Evidence Fixtures

These bundles are deterministic contract fixtures for the first ResearchOS integration slice. They contain no live empirical result and must always be presented with `mode: FIXTURE` and `fixture_only: true`.

- `evidence_bundle_complete.json`: all registered fixture routes complete.
- `evidence_bundle_partial.json`: one route completes and one failed route remains visible.
- `evidence_bundle_failed.json`: the registered route fails and no engine claim is emitted.

At request time the adapter replaces request identity, input object references, falsifier requirements, evidence-level cap, and canonical result hash. Artifact bodies are never inlined by the fixture adapter.
