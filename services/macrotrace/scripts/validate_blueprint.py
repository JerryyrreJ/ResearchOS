"""Validate MacroTrace blueprint schemas and cross-registry references."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]


def load(relative_path: str):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def unique(items, key: str, label: str) -> set[str]:
    values = [item[key] for item in items]
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise AssertionError(f"Duplicate {label}: {duplicates}")
    return set(values)


def require_subset(values, allowed: set[str], context: str) -> None:
    missing = sorted(set(values) - allowed)
    if missing:
        raise AssertionError(f"{context} references missing IDs: {missing}")


def main() -> None:
    lane_doc = load("registry/seed/lanes.json")
    workflow_doc = load("registry/seed/workflows.json")
    model_doc = load("registry/seed/model_recipes.json")
    data_doc = load("registry/seed/data_sources.json")
    reports = load("registry/seed/reports.json")

    lanes = lane_doc["items"]
    workflows = workflow_doc["items"]
    models = model_doc["items"]
    sources = data_doc["items"]

    lane_ids = unique(lanes, "lane_id", "lane IDs")
    workflow_ids = unique(workflows, "workflow_id", "workflow IDs")
    model_ids = unique(models, "recipe_id", "recipe IDs")
    source_ids = unique(sources, "source_id", "source IDs")
    report_ids = unique(reports, "report_id", "report IDs")

    report_schema = load("schemas/report_reverse.schema.json")
    research_schema = load("schemas/research_job.schema.json")
    Draft202012Validator.check_schema(report_schema)
    Draft202012Validator.check_schema(research_schema)

    validator = Draft202012Validator(report_schema, format_checker=FormatChecker())
    schema_errors: list[str] = []
    for report in reports:
        for error in validator.iter_errors(report):
            schema_errors.append(
                f"{report.get('report_id', '?')} {list(error.path)}: {error.message}"
            )
    if schema_errors:
        raise AssertionError("Report schema failures:\n" + "\n".join(schema_errors))

    for report in reports:
        require_subset(report["lane_ids"], lane_ids, report["report_id"])
        require_subset(report["workflow_ids"], workflow_ids, report["report_id"])
        for route in report["method_routes"]:
            recipe_id = route.get("recipe_id")
            if recipe_id is not None:
                require_subset([recipe_id], model_ids, f"{report['report_id']} method route")
            invalid_pages = [
                page
                for page in route["source_pages"]
                if page < 1 or page > report["page_count"]
            ]
            if invalid_pages:
                raise AssertionError(
                    f"{report['report_id']} has out-of-range source pages: {invalid_pages}"
                )

    for lane in lanes:
        require_subset(lane["source_report_ids"], report_ids, lane["lane_id"])

    for workflow in workflows:
        require_subset(workflow["lane_ids"], lane_ids, workflow["workflow_id"])
        require_subset(workflow["recipe_ids"], model_ids, workflow["workflow_id"])
        require_subset(
            workflow["source_report_ids"], report_ids, workflow["workflow_id"]
        )

    for model in models:
        require_subset(model["source_report_ids"], report_ids, model["recipe_id"])

    print(
        "Blueprint valid: "
        f"{len(lane_ids)} lanes, "
        f"{len(workflow_ids)} workflows, "
        f"{len(model_ids)} model recipes, "
        f"{len(source_ids)} data sources, "
        f"{len(report_ids)} reports."
    )


if __name__ == "__main__":
    main()
