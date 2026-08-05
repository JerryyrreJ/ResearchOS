from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
import pandas as pd

from ..catalog import SeriesSpec


class FredConnector:
    endpoint = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("FRED_API_KEY is required")
        self.api_key = api_key

    def fetch(
        self,
        spec: SeriesSpec,
        snapshot_id: str,
        as_of_date: date | None = None,
    ) -> tuple[pd.DataFrame, dict]:
        params: dict[str, str | int] = {
            "series_id": spec.series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": spec.start,
            "sort_order": "asc",
        }
        if as_of_date:
            params["realtime_start"] = as_of_date.isoformat()
            params["realtime_end"] = as_of_date.isoformat()
        with httpx.Client(timeout=45) as client:
            response = client.get(self.endpoint, params=params)
            response.raise_for_status()
            payload = response.json()

        rows: list[dict] = []
        fetched_at = datetime.now(UTC)
        for item in payload.get("observations", []):
            if item.get("value") in (None, "."):
                continue
            rows.append(
                {
                    "source_id": spec.source_id,
                    "series_id": spec.series_id,
                    "label": spec.label,
                    "period": pd.Timestamp(item["date"]),
                    "value": float(item["value"]),
                    "unit": spec.unit,
                    "frequency": spec.frequency,
                    "realtime_start": pd.Timestamp(item.get("realtime_start")) if item.get("realtime_start") else pd.NaT,
                    "realtime_end": pd.Timestamp(item.get("realtime_end")) if item.get("realtime_end") else pd.NaT,
                    "fetched_at": fetched_at,
                    "snapshot_id": snapshot_id,
                }
            )
        return pd.DataFrame(rows), payload

