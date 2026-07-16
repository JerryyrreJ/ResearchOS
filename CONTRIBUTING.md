# Contributing to MacroTrace

Thank you for improving the white-box macro research compiler.

## Before opening a change

1. Keep the product local-first. Do not add public hosting assumptions to the default path.
2. Never commit credentials, local databases, raw private reports, user questions, generated job artifacts, or personal filesystem paths.
3. Do not let an LLM write or mutate executable model code at runtime.
4. New factors, methods, and routes must be registered, schema-valid, source-backed, and covered by tests.
5. Do not present predictive or associational evidence as identified causality.

## Development

```powershell
.\scripts\setup_mvp.ps1
.\scripts\run_mvp.ps1
```

Run the full verification set before opening a pull request:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall backend
node --check .\frontend\app.js
.\.venv\Scripts\python.exe .\scripts\validate_blueprint.py
```

## Adding a report or paper

Follow `docs/08_report_ingestion_workflow_v1.md`. A source must pass semantic extraction, independent review, citation checks, method-fit review, reproduction feasibility, staged changeset validation, and hash-matched approval before it can modify the live registry.

## Pull requests

Describe:

- the research problem or failure being fixed;
- the registry objects and code paths affected;
- the data and identification assumptions;
- new or changed diagnostics;
- tests and browser states verified;
- limitations that remain.
