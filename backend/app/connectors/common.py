from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def save_raw_artifact(
    raw_root: Path,
    source_id: str,
    series_id: str,
    snapshot_id: str,
    request: dict[str, Any],
    response: Any,
) -> Path:
    now = datetime.now(UTC)
    folder = raw_root / f"source={source_id.lower()}" / f"ingest_date={now.date().isoformat()}"
    folder.mkdir(parents=True, exist_ok=True)
    safe_request = {key: value for key, value in request.items() if "key" not in key.lower() and "userid" not in key.lower()}
    digest = hashlib.sha256(
        json.dumps(safe_request, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:12]
    path = folder / f"{series_id}_{snapshot_id}_{digest}.json"
    payload = {
        "source_id": source_id,
        "series_id": series_id,
        "snapshot_id": snapshot_id,
        "ingested_at": now.isoformat(),
        "request": safe_request,
        "response": response,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
    return path

