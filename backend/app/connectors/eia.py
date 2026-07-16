from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pandas as pd

from ..catalog import SeriesSpec


class EiaConnector:
    endpoint = "https://api.eia.gov/v2/petroleum/pri/spt/data/"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("EIA_API_KEY is required")
        self.api_key = api_key

    def fetch_wti(self, spec: SeriesSpec, snapshot_id: str) -> tuple[pd.DataFrame, dict]:
        params = {
            "api_key": self.api_key,
            "frequency": "weekly",
            "data[0]": "value",
            "facets[series][]": spec.series_id,
            "start": spec.start,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": 5000,
        }
        with httpx.Client(timeout=60) as client:
            response = client.get(self.endpoint, params=params)
            response.raise_for_status()
            payload = response.json()
        fetched_at = datetime.now(UTC)
        rows = [
            {
                "source_id": spec.source_id,
                "series_id": spec.series_id,
                "label": spec.label,
                "period": pd.Timestamp(item["period"]),
                "value": float(item["value"]),
                "unit": spec.unit,
                "frequency": spec.frequency,
                "realtime_start": pd.NaT,
                "realtime_end": pd.NaT,
                "fetched_at": fetched_at,
                "snapshot_id": snapshot_id,
            }
            for item in payload.get("response", {}).get("data", [])
            if item.get("value") not in (None, "")
        ]
        return pd.DataFrame(rows), payload

