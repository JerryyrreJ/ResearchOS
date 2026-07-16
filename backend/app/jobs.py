from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from threading import Lock
from typing import Any
from uuid import uuid4

from .engine import JobCancelled, ResearchEngine
from .storage import MacroStore


class ResearchJobManager:
    def __init__(self, engine: ResearchEngine, store: MacroStore, max_workers: int = 2) -> None:
        self.engine = engine
        self.store = store
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="macrotrace-job")
        self._submitted: set[str] = set()
        self._lock = Lock()
        self.recover_interrupted()

    def recover_interrupted(self) -> None:
        for job in self.store.incomplete_jobs():
            self._submit(job["job_id"], job["question"], job["as_of_date"], recovered=True)

    def create(self, question: str, as_of_date: date, display_mode: str) -> dict[str, Any]:
        job_id = "JOB_" + datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid4().hex[:8].upper()
        self.store.create_job(job_id, question, as_of_date, display_mode)
        self._submit(job_id, question, as_of_date)
        return self.store.get_job(job_id) or {"job_id": job_id, "status": "QUEUED"}

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._submitted)

    def _submit(self, job_id: str, question: str, as_of_date: date, recovered: bool = False) -> None:
        with self._lock:
            if job_id in self._submitted:
                return
            self._submitted.add(job_id)
        if recovered:
            self.store.append_event(job_id, "JOB_RECOVERED", {"status": "QUEUED", "reason": "local process restart"})
            self.store.update_job(job_id, status="QUEUED", progress=0)
        self.executor.submit(self._run, job_id, question, as_of_date)

    def _run(self, job_id: str, question: str, as_of_date: date) -> None:
        try:
            def progress(status: str, value: float, detail: dict[str, Any], graph: dict[str, Any] | None) -> None:
                update: dict[str, Any] = {"status": status, "progress": value}
                event_detail = dict(detail)
                plan_snapshot = event_detail.pop("plan_snapshot", None)
                if plan_snapshot is not None:
                    update["plan_json"] = plan_snapshot
                    update["query_json"] = plan_snapshot["query"]
                if graph is not None:
                    update["graph_json"] = graph
                if status in {"COMPLETE", "PARTIAL", "FAILED"}:
                    update["coverage"] = detail.get("coverage")
                    update["coverage_score"] = detail.get("coverage_score")
                self.store.update_job(job_id, **update)
                self.store.append_event(job_id, "JOB_PROGRESS" if status not in {"COMPLETE", "PARTIAL", "FAILED"} else "JOB_TERMINAL", {"status": status, "progress": value, **event_detail})

            result = self.engine.execute(
                job_id,
                question,
                as_of_date,
                progress=progress,
                cancelled=lambda: self.store.is_cancel_requested(job_id),
            )
            self.store.update_job(
                job_id,
                status=result["status"],
                progress=1.0,
                coverage=result["synthesis"]["coverage"],
                coverage_score=result["synthesis"]["coverage_score"],
                query_json=result["query"],
                plan_json=result["plan"],
                graph_json=result["graph"],
                result_json=result,
                trace_json=result["trace"],
            )
            self.store.append_event(
                job_id,
                "JOB_TERMINAL",
                {
                    "status": result["status"],
                    "progress": 1.0,
                    "coverage": result["synthesis"]["coverage"],
                    "coverage_score": result["synthesis"]["coverage_score"],
                    "result_ready": True,
                },
            )
        except JobCancelled:
            self.store.update_job(job_id, status="CANCELLED", error_json={"error_type": "JobCancelled", "message": "Research job cancelled by user."})
            self.store.append_event(job_id, "JOB_TERMINAL", {"status": "CANCELLED", "progress": 1.0})
        except Exception as exc:
            self.store.update_job(job_id, status="FAILED", error_json={"error_type": type(exc).__name__, "message": "Research job failed before producing a valid result."})
            self.store.append_event(job_id, "JOB_TERMINAL", {"status": "FAILED", "progress": 1.0, "error_type": type(exc).__name__})
        finally:
            with self._lock:
                self._submitted.discard(job_id)
