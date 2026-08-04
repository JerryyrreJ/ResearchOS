# MacroTrace report reverse extraction prompt contract v1

This contract governs a Codex extraction pass that converts one private report page map into one `ReportReverseRecord`. It does not authorize Registry application. MacroTrace does not use word frequency, keyword counts or a generic external summarization API as a substitute for semantic reading.

## Inputs

1. The immutable source identity: file pointer, SHA-256, page count and page basis.
2. The private per-page text map under the gitignored batch workspace.
3. A read-only snapshot of the current Lane, Mechanism, Node, Factor, Dataset, ModelRecipe, ModelSpecification, Route and Report registries.
4. `schemas/report_ingestion.schema.json` and `docs/08_report_ingestion_workflow_v1.md`.

## Required extraction order

1. Reconstruct the report's actual research question. Do not replace it with a more convenient MacroTrace question.
2. Record claims and mechanism statements with typed page evidence.
3. Reconstruct every material path as `question → lane → mechanism → node → variables/factors → data/transforms → method/specification → diagnostics/robustness → output → aggregation role`.
4. Separate variables by empirical role: dependent/outcome, exposure/treatment, instrument, controls, state and weights.
5. Record the estimand, formula, sample, identification strategy, identifying assumptions, diagnostics, robustness and limitations. Use `not stated in report` when absent; never invent a missing item.
6. Compare proposed objects with the existing Registry. Prefer reuse or an UPDATE when the economic object is the same. A new lane requires a documented distinct boundary and at least two reusable workflow paths.
7. Mark free-data feasibility as `AVAILABLE`, `PARTIAL`, `UNAVAILABLE` or `UNKNOWN` based on identifiable data paths. Do not treat a chart image as an executable dataset.
8. Produce only candidate changes. The extraction pass cannot mark its own evidence as reviewer-verified, cannot approve its own output, cannot approve application and cannot supply numeric aggregation weights. A second Codex review pass with a different `review_run_id` re-reads the cited pages and may create a `CODEX` review.

## Evidence discipline

- `EXPLICIT`: the page directly states or displays the proposition.
- `INFERRED`: the proposition is a conservative reconstruction from multiple explicit elements. State the inference in the paraphrase.
- `NOT_STATED`: the item is absent. It can document a limitation but cannot support activation.
- Every evidence item uses file-page numbers by default and records another page basis explicitly when needed.
- Store a paraphrase as the durable artifact. A verbatim quote is optional and limited by Schema to 240 characters.
- A report's coefficient or narrative conclusion is source evidence, not a MacroTrace final claim and not an aggregation weight.

## Forbidden outputs

- No arbitrary Python, SQL, formulas or model parameters outside registered or proposed reviewed objects.
- No invented variable definitions, data series IDs, treatment dates, control groups, fixed effects, standard-error choices or sample windows.
- No causal label when the report only establishes association or prediction.
- No activation based only on method name recognition.
- No silent merge of conflicting lane, factor, model or estimand definitions.
- No long copyrighted passage and no copy of the report in the code repository.

## Output

Return one JSON object conforming to `ReportReverseRecord`. Keep the record at `EXTRACTED` while it is being edited. The state can move to `CANDIDATE` only through the policy-checked transition command. A separate Codex review pass then verifies the pages, method interpretation, Registry match and conflicts. Reproduction and Registry staging happen in later gates. A generic `LLM` or `AUTOMATED` reviewer remains unauthorized.
