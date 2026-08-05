from __future__ import annotations

from datetime import UTC, date, datetime

import pandas as pd

from backend.app.storage import MacroStore


def test_job_event_node_and_artifact_lifecycle(tmp_path) -> None:
    store = MacroStore(tmp_path / "jobs.duckdb")
    store.create_job("JOB_TEST", "US inflation?", date(2026, 7, 13), "ACADEMIC")
    store.update_job("JOB_TEST", status="VALIDATING_PLAN", progress=.45, plan_json={"workflow_id": "WF.TEST"}, graph_json={"nodes": [], "edges": []})
    event_sequence = store.append_event("JOB_TEST", "JOB_PROGRESS", {"status": "VALIDATING_PLAN"})
    assert event_sequence == 2
    assert store.get_events("JOB_TEST", after=1)[0]["payload"]["status"] == "VALIDATING_PLAN"
    store.save_node_detail("JOB_TEST", "N1", "SUCCESS", {"title": "Model", "table": {}})
    assert store.get_node_detail("JOB_TEST", "N1")["title"] == "Model"
    store.save_artifact({"artifact_id": "ART1", "job_id": "JOB_TEST", "node_id": "N1", "artifact_type": "JSON", "title": "Result", "media_type": "application/json", "sha256": "0" * 64, "relative_path": "JOB_TEST/N1/result.json", "created_at": "2026-07-13T00:00:00+00:00"})
    assert store.get_artifact("ART1")["sha256"] == "0" * 64
    job = store.get_job("JOB_TEST", include_payloads=True)
    assert job["status"] == "VALIDATING_PLAN"
    assert job["plan"]["workflow_id"] == "WF.TEST"


def test_point_in_time_snapshot_selection_never_falls_forward(tmp_path) -> None:
    store = MacroStore(tmp_path / "vintage.duckdb")
    rows = pd.DataFrame([
        {"source_id": "FRED", "series_id": "X", "label": "X", "period": date(2024, 1, 1), "value": 1.0, "unit": "index", "frequency": "Q", "realtime_start": date(2025, 1, 1), "realtime_end": date(2025, 12, 31), "fetched_at": datetime(2026, 7, 13, tzinfo=UTC), "snapshot_id": "HISTORICAL_VINTAGE"},
        {"source_id": "FRED", "series_id": "X", "label": "X", "period": date(2024, 1, 1), "value": 9.0, "unit": "index", "frequency": "Q", "realtime_start": date(2026, 1, 1), "realtime_end": date(9999, 12, 31), "fetched_at": datetime(2026, 7, 13, tzinfo=UTC), "snapshot_id": "REVISED_VINTAGE"},
        {"source_id": "BLS", "series_id": "Y", "label": "Y", "period": date(2024, 1, 1), "value": 7.0, "unit": "index", "frequency": "M", "realtime_start": pd.NaT, "realtime_end": pd.NaT, "fetched_at": datetime(2026, 7, 13, tzinfo=UTC), "snapshot_id": "FUTURE_FETCH"},
        {"source_id": "FRED", "series_id": "Z", "label": "Z", "period": date(2024, 1, 1), "value": 8.0, "unit": "index", "frequency": "Q", "realtime_start": date(2026, 1, 1), "realtime_end": date(9999, 12, 31), "fetched_at": datetime(2024, 12, 31, tzinfo=UTC), "snapshot_id": "CONTRADICTORY_METADATA"},
    ])
    store.save_observations(rows)

    historical = store.latest_series("X", date(2025, 6, 1))
    assert historical.iloc[0]["snapshot_id"] == "HISTORICAL_VINTAGE"
    assert historical.iloc[0]["value"] == 1.0
    assert store.latest_series("Y", date(2025, 6, 1)).empty
    assert store.latest_series("Z", date(2025, 6, 1)).empty
    lineage = store.series_lineage(["X", "Y"], date(2025, 6, 1))
    assert next(item for item in lineage if item["series_id"] == "X")["point_in_time_eligible"] is True
    assert next(item for item in lineage if item["series_id"] == "Y")["status"] == "NO_ELIGIBLE_POINT_IN_TIME_SNAPSHOT"
