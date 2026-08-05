# Integrated Product Status

Updated: 2026-08-05 (Asia/Shanghai)

Current state: `A_B_C_D_INTEGRATED_LOCAL_PRODUCT_READY_FOR_TEAM_REVIEW`

```text
Product mainline: MacroTrace empirical research (Part B)
Supporting layer: immutable data, documents, plugin catalog and lineage (Part A)
Conclusion boundary: evidence-bounded claim/report semantics (Part C)
Browser delivery: MacroTrace primary UI plus optional ResearchOS shell (Part D)
Branch: role/b-data-plugins
Contract impact: NONE — contracts/v1 and fixtures/contracts unchanged
```

## What now works

- The local product opens directly into the mature MacroTrace question interface.
- A research question produces a dense registered graph rather than a few fixture cards.
- The Part A evidence space shows the entire available data universe in grey and highlights
  the datasets/factors selected for the current question.
- AKShare and FRED are selectable server-side plugins; their keys never enter the browser.
- Plugin output becomes a hashed, immutable Role A AssetVersion and can be resolved by Role B
  only through a pinned DataObjectRef.
- The Part B graph retains lanes, mechanisms, factors, specifications, model runs,
  diagnostics, evidence, aggregation and final claims.
- The full MacroTrace report remains the last step after data and empirical inspection.
- One local launcher starts the unified A+B+C API and the primary product page.

## Evidence

- Local official macro store: 76 real series available.
- Registry: 10 lanes, 15 dataset families, 55 factors, 31 mechanisms, 82 model
  specifications and 7 executable model recipes.
- Rebuilt graph from a completed complex growth/recession plan: 375 nodes and 537 edges;
  15 dataset-family nodes remain visible, with 8 routed and 6 grey/unrouted in that example.
- AKShare live smoke: `macro_china_cpi` returned tabular data and obeyed the row cap.
- FRED live smoke: `UNRATE` returned official observations using the ignored local key.
- MacroTrace upstream suite: 65 tests passed.
- Data-plugin API suite: 3 tests passed.
- Unified route smoke: primary page, A API, B API, plugin API and frontend assets all returned
  successfully.

## Known limitations

- A fresh debt/yield end-to-end run exceeded the bounded four-minute integration smoke while
  selecting parameters. The exact test job and its partial nodes/events were removed after the
  check. Existing completed runs remain available for the demo. Long-task latency and recovery
  need a separate performance pass; this is not represented as a successful smoke.
- The shared fixture hash test is line-ending-sensitive on the current Windows checkout: the
  Git blobs match their recorded hashes, while CRLF worktree bytes do not. Frozen fixtures were
  not modified to hide this baseline issue.
- China-specific MacroTrace workflows are not yet registered. AKShare currently expands the A
  evidence universe and Asset path; B still activates only reviewed research recipes.

## Next team action

Review the primary flow with an existing completed job, then decide whether the hackathon demo
should use the completed growth/recession question or the completed fiscal-debt/yield question.
Do not start the live run on stage unless the four-minute latency is acceptable.
