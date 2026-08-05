from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pandas as pd

from ..catalog import SeriesSpec


class TreasuryConnector:
    endpoint = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny"

    def fetch_debt(self, spec: SeriesSpec, snapshot_id: str) -> tuple[pd.DataFrame, dict]:
        params = {
            "filter": f"record_date:gte:{spec.start}",
            "fields": "record_date,tot_pub_debt_out_amt",
            "sort": "record_date",
            "page[size]": 10000,
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
                "period": pd.Timestamp(item["record_date"]),
                "value": float(item["tot_pub_debt_out_amt"]),
                "unit": spec.unit,
                "frequency": spec.frequency,
                "realtime_start": pd.NaT,
                "realtime_end": pd.NaT,
                "fetched_at": fetched_at,
                "snapshot_id": snapshot_id,
            }
            for item in payload.get("data", [])
        ]
        return pd.DataFrame(rows), payload

