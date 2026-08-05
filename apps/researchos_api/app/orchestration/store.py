from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class MemoryStore:
    def __init__(self) -> None:
        self.theses: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        self.builds: dict[str, dict[str, Any]] = {}
        self.by_thesis: dict[str, list[str]] = defaultdict(list)
        self.events: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.evidence_builds: dict[tuple[str, str], str] = {}

    def put_thesis(self, value: dict[str, Any]) -> bool:
        versions = self.theses[value["thesis_id"]]
        existing = versions.get(value["version_id"])
        if existing is not None and existing != value:
            raise ValueError("immutable thesis version already exists with different content")
        created = existing is None
        versions[value["version_id"]] = deepcopy(value)
        return created

    def get_thesis(self, thesis_id: str, version_id: str | None = None) -> dict[str, Any] | None:
        versions = self.theses.get(thesis_id)
        if not versions: return None
        key = version_id or next(reversed(versions))
        return deepcopy(versions.get(key))
    def put_build(self, value: dict[str, Any]) -> None:
        self.builds[value["build_id"]] = deepcopy(value); self.by_thesis[value["thesis_id"]].append(value["build_id"])
    def versions(self, thesis_id: str) -> list[dict[str, Any]]: return [deepcopy(self.builds[x]) for x in self.by_thesis[thesis_id]]
    def build_for_evidence(self, thesis_id: str, bundle_id: str) -> dict[str, Any] | None:
        build_id = self.evidence_builds.get((thesis_id, bundle_id))
        return deepcopy(self.builds.get(build_id)) if build_id else None
    def remember_evidence_build(self, thesis_id: str, bundle_id: str, build_id: str) -> None:
        self.evidence_builds[(thesis_id, bundle_id)] = build_id
    def event(self, job_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        e={"contract_version":"0.1.0-frozen","job_id":job_id,"sequence":len(self.events[job_id])+1,
           "event_type":event_type,"created_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"payload":payload}
        self.events[job_id].append(e); return e
    @staticmethod
    def job_id() -> str: return f"JOB_{uuid4().hex[:12].upper()}"


store = MemoryStore()
