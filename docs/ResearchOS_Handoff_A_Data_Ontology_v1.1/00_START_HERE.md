# 00 — Start Here

## Your role

**Role A — Research Ontology**

Branch:

```text
role/a-ontology
```

## Before writing code

Read in this order:

1. `shared/PRODUCT_CONSTITUTION.md`
2. `shared/ARCHITECTURE.md`
3. `shared/TEAM_OPERATING_CONTRACT.md`
4. `shared/GIT_WORKFLOW.md`
5. `shared/REPO_PREFLIGHT.md`
6. `shared/INTEGRATION_MATRIX.md`
7. `shared/contracts/v1/contract_manifest.json`
8. `01_ROLE_MISSION_AND_BOUNDARIES.md`
9. `02_IMPLEMENTATION_PLAN.md`
10. `07_CODEX_MASTER_PROMPT.md`

Verify contract hashes:

```bash
cd shared/contracts/v1
sha256sum -c CONTRACT_HASHES.sha256
```

If these files are copied into the repository under `docs/handoffs/A_Data_Ontology/`, adjust the path but do not edit the frozen copies.

## First response required from Codex

Before modifying code, return:

```text
1. Repository inventory summary
2. Current branch and HEAD
3. Existing code that can be reused
4. Target paths for this role
5. Contract files verified
6. Risks or conflicts
7. First vertical-slice plan
8. Exact tests to run
```

Then create:

```text
docs/handoffs/repo_inventory_A.md
```

## Execution rules

- Work only in owned paths.
- Use contract Fixtures before real integration.
- Do not change `contracts/v1` without ICR.
- Do not read another module's database.
- Keep failures visible.
- Stop and warn on boundary-crossing human requests.
- Commit in reviewable stages.
- Update `ROLE_STATUS.md` after every milestone.

## Definition of done

This role is complete only after:

- role acceptance tests pass;
- producer and consumer contract tests pass;
- Fixture is available;
- run instructions are documented;
- failure paths are demonstrated;
- PR targets `integration`;
- no unapproved cross-owned files changed.
