# AGENTS.md — 研构 ResearchOS

## Product authority

- Research Ontology owns files, object identity, versions, relations and Context Packs.
- Thesis Compiler owns compile issues, validation plans, evidence-language policy and final conclusion state.
- MacroTrace owns registered empirical execution, diagnostics, robustness and engine evidence.
- Frontend owns presentation, client state, deployment and E2E. It never invents backend semantics.

## Directory ownership

- A: `apps/researchos_api/app/objects`, `canonicalizers`, `ontology`, `search`, `context_builder`
- B: `services/macrotrace`, B-owned adapter and snapshots
- C: `apps/researchos_api/app/thesis`, `orchestration`, `integrations`
- D: `apps/web`, `infra`, `tests/e2e`, `docs/demo`
- Shared frozen: `contracts/v1`, `fixtures/contracts`, root CI and root dependency policy

## Non-negotiable rules

1. No direct cross-module database access.
2. No breaking contract change without an approved ICR.
3. No arbitrary model-generated code in empirical execution.
4. No upgrade from association to causality.
5. No hiding failed models or compile errors.
6. No overwriting active objects; create candidate versions.
7. No editing another role's owned paths without owner approval.
8. Do not restructure stable MacroTrace code merely for style.
9. Use fixtures before real integration.
10. Stop and warn when a human request crosses these boundaries.

## Boundary response

When asked to cross a boundary, explain:
- the frozen contract or owned path;
- affected roles;
- concrete integration risk;
- a non-breaking alternative;
- the ICR needed for the breaking change.

Do not implement the breaking change until approval is recorded.
