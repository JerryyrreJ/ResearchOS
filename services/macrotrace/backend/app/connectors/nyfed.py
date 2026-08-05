from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pandas as pd


class NyFedConnector:
    endpoint = "https://markets.newyorkfed.org/api/rates/all/latest.json"

    def fetch_latest(self, snapshot_id: str) -> tuple[pd.DataFrame, dict]:
        with httpx.Client(timeout=45) as client:
            response = client.get(self.endpoint)
            response.raise_for_status()
            payload = response.json()
        fetched_at = datetime.now(UTC)
        rows: list[dict] = []
        for item in payload.get("refRates", []):
            if item.get("percentRate") is None:
                continue
            rate_type = item["type"]
            rows.append(
                {
                    "source_id": "NYFED",
                    "series_id": rate_type,
                    "label": f"New York Fed {rate_type}",
                    "period": pd.Timestamp(item["effectiveDate"]),
                    "value": float(item["percentRate"]),
                    "unit": "percent",
                    "frequency": "D",
                    "realtime_start": pd.NaT,
                    "realtime_end": pd.NaT,
                    "fetched_at": fetched_at,
                    "snapshot_id": snapshot_id,
                }
            )
        return pd.DataFrame(rows), payload
