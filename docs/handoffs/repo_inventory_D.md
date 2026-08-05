# Repository Inventory — Role D

## Repository state

- Repository: `JerryyrreJ/AIY_Project`
- Inventory date: 2026-08-04
- Starting branch and HEAD: `master` at `2f1f173` (`chore: init project with gitignore`)
- Working branch: `role/d-frontend`
- Starting repository contents: `.gitignore` only
- Default remote branch: `master`; the planned `integration` branch did not yet exist at inventory time

## Existing stack and assets

No reusable application, API, frontend, dependency manifest, tests, contracts, or CI existed in the initial checkout. The Role D implementation therefore uses a minimal React 19 / Next-compatible vinext frontend and Cloudflare-compatible build scaffold. The frozen team overlay, contracts, fixtures, product constitution, architecture, and Role D handoff have been imported from `ResearchOS_Team_Master_Coordination_v1.1`.

## Target architecture mapping

- Web product surface: root `app/` (deployment-compatible equivalent of proposed `apps/web/`)
- Frozen contracts: `contracts/v1/`
- Frozen samples: `fixtures/contracts/`
- Role handoff: `docs/handoffs/D_Frontend_Integration/`
- Product and architecture authority: `docs/product/` and `docs/architecture/`
- Frontend acceptance test: `tests/rendered-html.test.mjs`
- Hosting declaration: `.openai/hosting.json`

The root `app/` mapping is intentionally minimal because the selected deployment runtime expects the application entry there. It must not be interpreted as ownership of A/B/C backend paths.

## Reusable code

The original repository had no reusable code. All visible product data in the first slice is mapped from the frozen ThesisBuild, CompileResult, EvidenceBundle, ToolRequest, ContextPack, OntologyRelation, DataObjectRef, and VersionDiff fixtures.

## Assets that must not be removed or rewritten

- `contracts/v1/*`
- `fixtures/contracts/*`
- `docs/product/PRODUCT_CONSTITUTION.md`
- `docs/architecture/ARCHITECTURE.md`
- `AGENTS.md`

## Risks and conflicts

1. The repository uses `master`, while the coordination plan specifies `main` and `integration`.
2. No A/C APIs, B artifact route, or OpenAPI description is present, so the UI remains in explicit Fixture Mode.
3. The original `.gitignore` excluded the entire `docs/` tree; this was corrected because product authority and handoff inventory must be versioned.
4. Root dependency and CI policy are shared surfaces. Future changes need team confirmation.
5. Real integration must preserve backend-owned enums and make unknown values fail visibly.

## First vertical slice

The first slice renders the Thesis Build Console from frozen fixtures, including visible compile failures, a continuous Validation Plan, MacroTrace execution summary, Evidence boundary, semantic Recompile, and Version Diff. A centralized application shell, status system, tables, inspector, keyboard command menu, responsive layout, and reduced-motion support provide the shared design system.

## Exact validation

```bash
cd contracts/v1 && shasum -a 256 -c CONTRACT_HASHES.sha256
npm run build
npm test
npm run lint
```
