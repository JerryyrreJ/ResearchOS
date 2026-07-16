from __future__ import annotations

import json
import time
from datetime import UTC, date, datetime
from pathlib import Path
from threading import Lock
from typing import Any

import duckdb
import pandas as pd


class MacroStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = Lock()
        self.initialize()

    def connect(self) -> duckdb.DuckDBPyConnection:
        # Windows may briefly deny a second DuckDB handle while another thread
        # commits a write transaction. Research jobs write progress while HTTP
        # requests read status, so retry the short lock window instead of
        # surfacing an intermittent 500 to the frontend.
        last_error: Exception | None = None
        for attempt in range(40):
            try:
                return duckdb.connect(str(self.database_path))
            except (duckdb.IOException, duckdb.BinderException, OSError) as exc:
                last_error = exc
                time.sleep(min(0.2, 0.01 * (attempt + 1)))
        assert last_error is not None
        raise last_error

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS observations (
                    source_id VARCHAR NOT NULL,
                    series_id VARCHAR NOT NULL,
                    label VARCHAR NOT NULL,
                    period DATE NOT NULL,
                    value DOUBLE NOT NULL,
                    unit VARCHAR NOT NULL,
                    frequency VARCHAR NOT NULL,
                    realtime_start DATE,
                    realtime_end DATE,
                    fetched_at TIMESTAMP NOT NULL,
                    snapshot_id VARCHAR NOT NULL
                );
                CREATE INDEX IF NOT EXISTS observations_series_idx
                    ON observations(series_id, snapshot_id, period);

                CREATE TABLE IF NOT EXISTS sync_runs (
                    snapshot_id VARCHAR PRIMARY KEY,
                    started_at TIMESTAMP NOT NULL,
                    finished_at TIMESTAMP,
                    status VARCHAR NOT NULL,
                    summary_json JSON NOT NULL
                );

                CREATE TABLE IF NOT EXISTS research_runs (
                    run_id VARCHAR PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL,
                    question VARCHAR NOT NULL,
                    as_of_date DATE NOT NULL,
                    status VARCHAR NOT NULL,
                    parsed_query_json JSON NOT NULL,
                    plan_json JSON NOT NULL,
                    result_json JSON NOT NULL
                );

                CREATE TABLE IF NOT EXISTS research_jobs (
                    job_id VARCHAR PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    question VARCHAR NOT NULL,
                    as_of_date DATE NOT NULL,
                    display_mode VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    progress DOUBLE NOT NULL,
                    coverage VARCHAR,
                    coverage_score DOUBLE,
                    cancellation_requested BOOLEAN NOT NULL DEFAULT FALSE,
                    query_json JSON,
                    plan_json JSON,
                    graph_json JSON,
                    result_json JSON,
                    trace_json JSON,
                    error_json JSON
                );

                CREATE TABLE IF NOT EXISTS research_events (
                    job_id VARCHAR NOT NULL,
                    sequence BIGINT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    event_type VARCHAR NOT NULL,
                    payload_json JSON NOT NULL,
                    PRIMARY KEY (job_id, sequence)
                );

                CREATE TABLE IF NOT EXISTS research_nodes (
                    job_id VARCHAR NOT NULL,
                    node_id VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    detail_json JSON NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (job_id, node_id)
                );

                CREATE TABLE IF NOT EXISTS research_artifacts (
                    artifact_id VARCHAR PRIMARY KEY,
                    job_id VARCHAR NOT NULL,
                    node_id VARCHAR NOT NULL,
                    artifact_type VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    media_type VARCHAR NOT NULL,
                    sha256 VARCHAR NOT NULL,
                    relative_path VARCHAR NOT NULL,
                    created_at TIMESTAMP NOT NULL
                );
                """
            )

    def save_observations(self, frame: pd.DataFrame) -> int:
        if frame.empty:
            return 0
        columns = [
            "source_id",
            "series_id",
            "label",
            "period",
            "value",
            "unit",
            "frequency",
            "realtime_start",
            "realtime_end",
            "fetched_at",
            "snapshot_id",
        ]
        clean = frame[columns].copy()
        with self._write_lock, self.connect() as connection:
            connection.register("incoming_observations", clean)
            connection.execute(
                "INSERT INTO observations SELECT * FROM incoming_observations"
            )
            connection.unregister("incoming_observations")
        return len(clean)

    def latest_series(self, series_id: str, end_date: date | None = None) -> pd.DataFrame:
        end_date = end_date or date.today()
        with self.connect() as connection:
            return connection.execute(
                """
                WITH eligible AS (
                    SELECT *
                    FROM observations
                    WHERE series_id = ?
                      AND period <= ?
                      AND (
                          (realtime_start IS NOT NULL AND realtime_start <= ?)
                          OR (realtime_start IS NULL AND CAST(fetched_at AS DATE) <= ?)
                      )
                ), selected_snapshot AS (
                    SELECT snapshot_id
                    FROM eligible
                    GROUP BY snapshot_id
                    ORDER BY MAX(realtime_start) DESC NULLS LAST,
                             MAX(fetched_at) DESC,
                             snapshot_id DESC
                    LIMIT 1
                )
                SELECT period, value, source_id, series_id, label, unit, frequency,
                       realtime_start, realtime_end, fetched_at, snapshot_id
                FROM eligible
                WHERE snapshot_id = (SELECT snapshot_id FROM selected_snapshot)
                ORDER BY period
                """,
                [series_id, end_date, end_date, end_date],
            ).fetchdf()

    def has_data(self) -> bool:
        with self.connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] > 0

    def data_status(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            frame = connection.execute(
                """
                WITH latest AS (
                    SELECT series_id, MAX(fetched_at) AS fetched_at
                    FROM observations
                    GROUP BY series_id
                )
                SELECT o.source_id, o.series_id, ANY_VALUE(o.label) AS label,
                       MIN(o.period) AS first_period, MAX(o.period) AS last_period,
                       COUNT(*) AS observations, MAX(o.fetched_at) AS fetched_at
                FROM observations o
                JOIN latest l ON o.series_id = l.series_id AND o.fetched_at = l.fetched_at
                GROUP BY o.source_id, o.series_id
                ORDER BY o.source_id, o.series_id
                """
            ).fetchdf()
        return json.loads(frame.to_json(orient="records", date_format="iso"))

    def series_lineage(self, series_ids: list[str], as_of_date: date | None = None) -> list[dict[str, Any]]:
        if not series_ids:
            return []
        cutoff = as_of_date or date.today()
        lineage: list[dict[str, Any]] = []
        for series_id in sorted(set(series_ids)):
            frame = self.latest_series(series_id, cutoff)
            if frame.empty:
                lineage.append({
                    "series_id": series_id,
                    "as_of_date": cutoff.isoformat(),
                    "status": "NO_ELIGIBLE_POINT_IN_TIME_SNAPSHOT",
                    "point_in_time_eligible": False,
                })
                continue
            first = frame.iloc[0]
            fetched_at = pd.Timestamp(frame["fetched_at"].max())
            realtime_values = frame["realtime_start"].dropna()
            lineage.append({
                "series_id": series_id,
                "source_id": first["source_id"],
                "latest_period": pd.Timestamp(frame["period"].max()).date().isoformat(),
                "fetched_at": fetched_at.isoformat(),
                "snapshot_id": first["snapshot_id"],
                "realtime_start": pd.Timestamp(realtime_values.max()).date().isoformat() if not realtime_values.empty else None,
                "stored_observations": len(frame),
                "as_of_date": cutoff.isoformat(),
                "status": "ELIGIBLE_POINT_IN_TIME_SNAPSHOT",
                "point_in_time_eligible": True,
                "selection_policy": "realtime_start_on_or_before_as_of_else_fetched_on_or_before_as_of",
            })
        return lineage

    def begin_sync(self, snapshot_id: str) -> None:
        with self._write_lock, self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO sync_runs VALUES (?, ?, NULL, 'RUNNING', '{}')",
                [snapshot_id, datetime.now(UTC)],
            )

    def finish_sync(self, snapshot_id: str, status: str, summary: dict[str, Any]) -> None:
        with self._write_lock, self.connect() as connection:
            connection.execute(
                """
                UPDATE sync_runs
                SET finished_at = ?, status = ?, summary_json = ?
                WHERE snapshot_id = ?
                """,
                [datetime.now(UTC), status, json.dumps(summary), snapshot_id],
            )

    def save_research_run(
        self,
        run_id: str,
        question: str,
        as_of_date: date,
        status: str,
        parsed_query: dict[str, Any],
        plan: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        with self._write_lock, self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO research_runs
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run_id,
                    datetime.now(UTC),
                    question,
                    as_of_date,
                    status,
                    json.dumps(parsed_query, ensure_ascii=False),
                    json.dumps(plan, ensure_ascii=False),
                    json.dumps(result, ensure_ascii=False),
                ],
            )

    def get_research_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT run_id, created_at, question, as_of_date, status,
                       parsed_query_json, plan_json, result_json
                FROM research_runs WHERE run_id = ?
                """,
                [run_id],
            ).fetchone()
        if row is None:
            return None
        return {
            "run_id": row[0],
            "created_at": row[1].isoformat(),
            "question": row[2],
            "as_of_date": row[3].isoformat(),
            "status": row[4],
            "parsed_query": json.loads(row[5]),
            "plan": json.loads(row[6]),
            "result": json.loads(row[7]),
        }

    def create_job(
        self,
        job_id: str,
        question: str,
        as_of_date: date,
        display_mode: str,
    ) -> None:
        now = datetime.now(UTC)
        with self._write_lock, self.connect() as connection:
            connection.execute(
                """
                INSERT INTO research_jobs (
                    job_id, created_at, updated_at, question, as_of_date,
                    display_mode, status, progress, cancellation_requested
                ) VALUES (?, ?, ?, ?, ?, ?, 'QUEUED', 0, FALSE)
                """,
                [job_id, now, now, question, as_of_date, display_mode],
            )
        self.append_event(job_id, "JOB_QUEUED", {"status": "QUEUED", "progress": 0})

    def update_job(self, job_id: str, **values: Any) -> None:
        allowed = {
            "status",
            "progress",
            "coverage",
            "coverage_score",
            "query_json",
            "plan_json",
            "graph_json",
            "result_json",
            "trace_json",
            "error_json",
        }
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"unsupported job fields: {sorted(unknown)}")
        if not values:
            return
        assignments = ["updated_at = ?"]
        parameters: list[Any] = [datetime.now(UTC)]
        for key, value in values.items():
            assignments.append(f"{key} = ?")
            if key.endswith("_json") and value is not None and not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            parameters.append(value)
        parameters.append(job_id)
        with self._write_lock, self.connect() as connection:
            connection.execute(
                f"UPDATE research_jobs SET {', '.join(assignments)} WHERE job_id = ?",
                parameters,
            )

    def append_event(self, job_id: str, event_type: str, payload: dict[str, Any]) -> int:
        with self._write_lock, self.connect() as connection:
            current = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM research_events WHERE job_id = ?",
                [job_id],
            ).fetchone()[0]
            sequence = int(current) + 1
            connection.execute(
                "INSERT INTO research_events VALUES (?, ?, ?, ?, ?)",
                [job_id, sequence, datetime.now(UTC), event_type, json.dumps(payload, ensure_ascii=False)],
            )
        return sequence

    def get_events(self, job_id: str, after: int = 0) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT sequence, created_at, event_type, payload_json
                FROM research_events
                WHERE job_id = ? AND sequence > ?
                ORDER BY sequence
                """,
                [job_id, after],
            ).fetchall()
        return [
            {
                "sequence": int(row[0]),
                "created_at": row[1].isoformat(),
                "event_type": row[2],
                "payload": json.loads(row[3]),
            }
            for row in rows
        ]

    def request_cancel(self, job_id: str) -> bool:
        with self._write_lock, self.connect() as connection:
            exists = connection.execute("SELECT COUNT(*) FROM research_jobs WHERE job_id = ?", [job_id]).fetchone()[0]
            if not exists:
                return False
            connection.execute(
                "UPDATE research_jobs SET cancellation_requested = TRUE, updated_at = ? WHERE job_id = ?",
                [datetime.now(UTC), job_id],
            )
        self.append_event(job_id, "CANCEL_REQUESTED", {"status": "CANCEL_REQUESTED"})
        return True

    def is_cancel_requested(self, job_id: str) -> bool:
        with self.connect() as connection:
            row = connection.execute("SELECT cancellation_requested FROM research_jobs WHERE job_id = ?", [job_id]).fetchone()
        return bool(row and row[0])

    @staticmethod
    def _json(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        return value

    def get_job(self, job_id: str, *, include_payloads: bool = False) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT job_id, created_at, updated_at, question, as_of_date,
                       display_mode, status, progress, coverage, coverage_score,
                       cancellation_requested, query_json, plan_json, graph_json,
                       result_json, trace_json, error_json
                FROM research_jobs WHERE job_id = ?
                """,
                [job_id],
            ).fetchone()
        if row is None:
            return None
        result = {
            "job_id": row[0],
            "created_at": row[1].isoformat(),
            "updated_at": row[2].isoformat(),
            "question": row[3],
            "as_of_date": row[4].isoformat(),
            "display_mode": row[5],
            "status": row[6],
            "progress": float(row[7]),
            "coverage": row[8],
            "coverage_score": float(row[9]) if row[9] is not None else None,
            "cancellation_requested": bool(row[10]),
            "error": self._json(row[16]),
        }
        if include_payloads:
            result.update(
                query=self._json(row[11]),
                plan=self._json(row[12]),
                graph=self._json(row[13]),
                result=self._json(row[14]),
                trace=self._json(row[15]),
            )
        return result

    def incomplete_jobs(self) -> list[dict[str, Any]]:
        terminal = ["COMPLETE", "PARTIAL", "FAILED", "CANCELLED"]
        placeholders = ",".join("?" for _ in terminal)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT job_id, question, as_of_date, display_mode
                FROM research_jobs
                WHERE status NOT IN ({placeholders}) AND cancellation_requested = FALSE
                ORDER BY created_at
                """,
                terminal,
            ).fetchall()
        return [
            {"job_id": row[0], "question": row[1], "as_of_date": row[2], "display_mode": row[3]}
            for row in rows
        ]

    def save_node_detail(self, job_id: str, node_id: str, status: str, detail: dict[str, Any]) -> None:
        with self._write_lock, self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO research_nodes
                VALUES (?, ?, ?, ?, ?)
                """,
                [job_id, node_id, status, json.dumps(detail, ensure_ascii=False), datetime.now(UTC)],
            )

    def get_node_detail(self, job_id: str, node_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT status, detail_json, updated_at FROM research_nodes WHERE job_id = ? AND node_id = ?",
                [job_id, node_id],
            ).fetchone()
        if row is None:
            return None
        detail = self._json(row[1])
        detail["node_status"] = row[0]
        detail["updated_at"] = row[2].isoformat()
        return detail

    def save_artifact(self, metadata: dict[str, Any]) -> None:
        created_at = metadata["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        with self._write_lock, self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO research_artifacts
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    metadata["artifact_id"],
                    metadata["job_id"],
                    metadata["node_id"],
                    metadata["artifact_type"],
                    metadata["title"],
                    metadata["media_type"],
                    metadata["sha256"],
                    metadata["relative_path"],
                    created_at,
                ],
            )

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT artifact_id, job_id, node_id, artifact_type, title,
                       media_type, sha256, relative_path, created_at
                FROM research_artifacts WHERE artifact_id = ?
                """,
                [artifact_id],
            ).fetchone()
        if row is None:
            return None
        return {
            "artifact_id": row[0],
            "job_id": row[1],
            "node_id": row[2],
            "artifact_type": row[3],
            "title": row[4],
            "media_type": row[5],
            "sha256": row[6],
            "relative_path": row[7],
            "created_at": row[8].isoformat(),
        }
