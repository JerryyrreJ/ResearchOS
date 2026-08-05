# Role B Repository Inventory

Date: 2026-08-05 (Asia/Shanghai)

## 1. Repository and branch

- Repository: `JerryyrreJ/AIY_Project` (private; current account has `WRITE` permission)
- Working copy: `E:\aipro\macrotrace\AIY_ResearchOS_B\AIY_Project`
- Branch: `role/b-macrotrace`
- Base branch: `origin/role/d-frontend`
- Base commit: `e0ec0ded1abea1239250c1831b73a84d51fbab5b`
- Remote `integration`: absent as of this inventory
- Remote `role/b-macrotrace`: absent before this branch was created

The previous D checkpoint (`4fbfe60011b5...`) advanced by one commit. The new commit only changes D-owned frontend, design documentation, frontend dependencies, and rendered HTML tests. No frozen contract changed, so the latest D head is an admissible base under the coordination rules.

## 2. Authority and source material

Execution authority, in descending order:

1. Team Master Coordination v1.1;
2. Role B MacroTrace Empirical Handoff v1.1;
3. repository `AGENTS.md` and frozen contracts;
4. the approved Role B implementation plan;
5. AI Pro Factory only as a lightweight evidence and delivery audit.

Original ZIP/DOCX files and their SHA-256 manifest are stored outside Git at `E:\aipro\macrotrace\AIY_ResearchOS_B\_handoff_sources`. The B handoff documents copied into this repository are reference copies; the numbered source documents are not edited.

## 3. Frozen contract verification

- Contract version: `0.1.0-frozen`
- `contracts/v1/CONTRACT_HASHES.sha256`: verified against the latest D base
- Frozen contract files: verified with no drift from the handoff package
- Shared contract fixtures: remain owned by the shared contract layer and will not be modified by Role B

Role B will load and validate the repository's frozen `ToolRequest` and `EvidenceBundle` schemas at runtime. It will not duplicate, loosen, or extend their fields.

## 4. Reusable code

### ResearchOS repository

- Frozen JSON Schemas in `contracts/v1/`
- Shared examples in `fixtures/contracts/`
- Existing D frontend and rendered HTML tests; these are consumers, not Role B implementation targets

### MacroTrace upstream

- Upstream repository: `https://github.com/ZhenyuanPAN822/macrotrace.git`
- Frozen import commit: `d96c8d91131b0eec2b34569976b894ff14381ddd`
- License: MIT
- Existing reusable capabilities: compiler, RegistryStore, workflow/lane/node/factor/model routing, model recipes, diagnostics, Research Graph, DuckDB, artifacts, report pipeline, FastAPI API, tests, and Windows/local startup scripts
- Upstream baseline: 65 tests passed before import in the clean release source

The upstream will be imported with Git subtree into `services/macrotrace/` without restructuring its empirical core.

## 5. Role B owned target paths

- `services/macrotrace/`
- `scripts/macrotrace/`
- `tests/unit/macrotrace_adapter/`
- `tests/integration/macrotrace/`
- `fixtures/evidence/`
- `data/snapshots/macrotrace/`
- `docs/handoffs/B_MacroTrace_Empirical/`
- `docs/handoffs/repo_inventory_B.md`

No A, C, D, shared contract, root CI, or root dependency-policy path is in scope.

## 6. Baseline checks and known conflicts

| Check | Result | Boundary response |
|---|---|---|
| GitHub permission | PASS | HTTPS write dry-run succeeded; no temporary branch was created |
| D `npm run lint` | PASS | No action required |
| D `npm run build` | BASELINE FAIL on Windows | Script uses Unix inline environment-variable syntax; record and notify D, do not modify D-owned `package.json` |
| D `npm test` | BASELINE FAIL on Windows | Test invokes the same failing build script; record and notify D, do not repair across ownership |
| Frozen contract hashes | PASS | Continue without ICR |
| MacroTrace upstream tests | PASS (65) | Re-run after subtree import and after adapter changes |
| `integration` branch | BLOCKED EXTERNAL GATE | Push Role B branch when ready, but do not open an incorrect PR against `master` |

## 7. Risks and controls

- **Contract drift:** validate hashes before implementation; stop and use ICR on any change.
- **Cross-role edits:** stage only explicit Role B paths; never use `git add -A`.
- **Empirical rewrite:** add an adapter around stable MacroTrace; do not create a second engine, graph, or registry.
- **False causal claims:** cap evidence type at the requested level and at the registered recipe level.
- **Hidden failures:** retain failed model runs, diagnostics, limitations, and unsupported coverage.
- **Fixture/live confusion:** label `FIXTURE`, `REAL`, and `OFFLINE_REPLAY` explicitly.
- **Secrets:** never store chat credentials or API keys in files, fixtures, logs, traces, snapshots, or Git history.
- **Premature China route:** do not integrate iFind, AKShare, or China macro until A supplies a frozen `DataObjectRef` and all six gates pass.

## 8. First vertical slice

1. Commit the B handoff and this inventory.
2. Import MacroTrace commit `d96c8d9` with Git subtree and record provenance.
3. Add a fixture-only Tool Adapter under `services/macrotrace/`.
4. Validate every request against frozen `ToolRequest` and every bundle against frozen `EvidenceBundle`.
5. Provide COMPLETE, PARTIAL, and FAILED fixtures, preserving failed nodes and excluding conclusion or trading fields.
6. Expose the four required tool-run routes and an adapter health signal.
7. Run upstream, adapter, contract, and consumer-shape tests; scan the Role B diff for secrets and boundary violations.
8. Push `role/b-macrotrace`. Open the fixed-title Draft PR only after `integration` exists.

## 9. Exact first-slice tests

- verify frozen contract hashes and all eight shared fixtures against their schemas;
- run all imported MacroTrace tests;
- reject malformed requests, extra fields, wrong contract version, and code-like unauthorized fields;
- validate COMPLETE, PARTIAL, and FAILED EvidenceBundles;
- verify failed model runs and limitations remain visible;
- verify forbidden conclusion/rating/signal fields are absent recursively;
- verify evidence type is never upgraded;
- verify request-id idempotency and reject same ID with different content;
- verify graph and artifact endpoints stay within the fixture adapter boundary;
- run repository lint and record the pre-existing Windows build/test limitation;
- scan the explicit Role B diff for secrets and non-owned paths.

## 10. Next consumer test

C must deserialize all three fixture bundles with the frozen schema. D may consume only stable graph/artifact URLs and must not import MacroTrace internal classes.
