# Draft PR 1 — Role B MacroTrace

## Title

`feat(macrotrace): import stable upstream and expose fixture tool adapter`

## Target and state

- Head: `role/b-macrotrace`
- Base: `integration`
- State: Draft PR #2 open — `https://github.com/JerryyrreJ/AIY_Project/pull/2`
- Contract impact: `NONE`
- Open only after the D/shared baseline inherited by B is present in `integration` and the three-dot PR diff contains only B-owned paths.

## Summary

This PR imports the stable MacroTrace v0.4.0 upstream as the registered ResearchOS empirical tool and exposes the first fixture-only Tool Adapter. It preserves the existing empirical compiler, registries, model recipes, diagnostics, Research Graph, artifacts, report pipeline, and tests; it does not create a second empirical engine or change any frozen contract.

## Role and owned paths

Role: B — MacroTrace Empirical Tool

Owned paths in this PR:

- `services/macrotrace/`
- `scripts/macrotrace/`
- `tests/unit/macrotrace_adapter/`
- `tests/integration/macrotrace/`
- `fixtures/evidence/`
- `docs/handoffs/B_MacroTrace_Empirical/`
- `docs/handoffs/repo_inventory_B.md`

No A, C, D, `contracts/v1`, or `fixtures/contracts` change is part of the intended PR diff.

## Upstream provenance

- Upstream: `https://github.com/ZhenyuanPAN822/macrotrace.git`
- Imported commit: `d96c8d91131b0eec2b34569976b894ff14381ddd`
- Import method: Git subtree
- License: MIT
- Empirical-core rewrite: none

## Adapter endpoints

- `POST /v1/tool-runs/macrotrace`
- `GET /v1/tool-runs/{id}`
- `GET /v1/tool-runs/{id}/graph`
- `GET /v1/tool-runs/{id}/artifacts`

POST accepts only frozen `ToolRequest 0.1.0-frozen`. Nested EvidenceBundles are separately validated against frozen `EvidenceBundle 0.1.0-frozen`.

## Fixture and failure behavior

- COMPLETE, PARTIAL, and FAILED core fixtures are committed.
- CANCELLED, UNSUPPORTED, and OUT_OF_SCOPE mappings are covered.
- Failed model runs, blocking diagnostics, limitations, and falsifiers remain visible.
- Evidence types are capped and cannot be upgraded by natural-language interpretation.
- `conclusion_state`, supported probability, investment rating, and buy/sell signal are absent.
- Fixture artifacts are path-contained and never returned as oversized inline content.
- Every response is explicitly labeled `FIXTURE`; no fixture is presented as live empirical output.

## Validation

- Frozen contract hashes: 13/13 PASS
- Shared contract fixtures: 8/8 PASS
- MacroTrace upstream suite after adapter: 65/65 PASS
- Role B adapter suite: 33/33 PASS
- Python compilation: PASS
- Owned-path audit: PASS
- Secret scan: PASS
- Tracked Python cache scan: PASS

The D frontend baseline lint passed. Its Windows build/test command uses Unix inline environment-variable syntax; this pre-existing D-owned issue is recorded but not modified by Role B.

## Producer and consumers

- Producer into B: C sends frozen ToolRequest fixtures in this slice.
- Consumer C: deserialize COMPLETE, PARTIAL, and FAILED EvidenceBundles without inventing or upgrading semantics.
- Consumer D: use stable graph and artifact URLs; do not import MacroTrace internal classes.

## Known non-goals

- No REAL execution or direct A database access.
- No `/v1/data/resolve` substitute.
- No US golden-route run or Offline Replay in this PR.
- No iFind, AKShare, China macro, credential, or API-key integration.
- No frozen contract, root CI, root dependency policy, A, C, or D edit.

## Merge gate

Do not merge until C validates all three core EvidenceBundle fixtures and D confirms the graph/artifact boundary. After merge, Role B may begin the separately reviewed Data Resolve and REAL/Offline delivery unit.

Independent pre-review evidence: `role/c-thesis@41546b4` successfully deserialized the COMPLETE, PARTIAL, and FAILED B fixtures, and all 15 C tests passed in an isolated worktree. This does not replace C owner confirmation on the PR.
