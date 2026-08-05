# ResearchOS Fixture Tool Adapter

This adapter is the first integration slice around the stable MacroTrace engine. It validates the repository-owned frozen contracts and returns deterministic fixtures; it does not execute empirical models yet.

## Mode and boundary

- Mode is always `FIXTURE` in this slice.
- Arbitrary Python, SQL, formulas, scripts, and Registry overrides are rejected.
- `engine_claim` is evidence for Role C; it is not a ResearchOS conclusion state.
- Failed model runs and limitations remain visible.
- No credential, API key, or chat-supplied secret is accepted or stored.

## Routes

```text
POST /v1/tool-runs/macrotrace
GET  /v1/tool-runs/{id}
GET  /v1/tool-runs/{id}/graph
GET  /v1/tool-runs/{id}/artifacts
```

POST accepts only `ToolRequest 0.1.0-frozen`. The optional test selector `metadata.fixture_scenario` is restricted to `COMPLETE`, `PARTIAL`, `FAILED`, `CANCELLED`, `UNSUPPORTED`, or `OUT_OF_SCOPE`; it never alters code, formulas, models, or Registry state.

The tool-run response is an adapter envelope. Its nested `evidence_bundle` is separately validated against frozen `EvidenceBundle 0.1.0-frozen`.

## Local run

From `services/macrotrace` with the project dependencies installed:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Use `fixtures/contracts/sample_tool_request.json` as the POST body. No live data or provider credential is required for the fixture slice.

## Provenance

- MacroTrace upstream: `https://github.com/ZhenyuanPAN822/macrotrace.git`
- Imported commit: `d96c8d91131b0eec2b34569976b894ff14381ddd`
- License: MIT
- Local changes: ResearchOS adapter, fixture bundles, tests, and integration documentation only
