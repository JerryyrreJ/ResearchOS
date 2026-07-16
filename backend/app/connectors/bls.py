from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pandas as pd

from ..catalog import SeriesSpec


class BlsConnector:
    endpoint = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("BLS_API_KEY is required")
        self.api_key = api_key

    def fetch_many(
        self,
        specs: tuple[SeriesSpec, ...],
        snapshot_id: str,
        start_year: int = 2010,
        end_year: int | None = None,
    ) -> tuple[pd.DataFrame, dict]:
        end_year = end_year or datetime.now(UTC).year
        body = {
            "seriesid": [spec.series_id for spec in specs],
            "startyear": str(start_year),
            "endyear": str(end_year),
            "registrationkey": self.api_key,
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(self.endpoint, json=body)
            response.raise_for_status()
            payload = response.json()
        if payload.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError("BLS request failed")

        spec_map = {spec.series_id: spec for spec in specs}
        rows: list[dict] = []
        fetched_at = datetime.now(UTC)
        for series in payload.get("Results", {}).get("series", []):
            spec = spec_map.get(series.get("seriesID"))
            if spec is None:
                continue
            for item in series.get("data", []):
                period = item.get("period", "")
                if not period.startswith("M") or period == "M13":
                    continue
                try:
                    value = float(item["value"])
                except (TypeError, ValueError):
                    continue
                month = int(period[1:])
                rows.append(
                    {
                        "source_id": spec.source_id,
                        "series_id": spec.series_id,
                        "label": spec.label,
                        "period": pd.Timestamp(year=int(item["year"]), month=month, day=1),
                        "value": value,
                        "unit": spec.unit,
                        "frequency": spec.frequency,
                        "realtime_start": pd.NaT,
                        "realtime_end": pd.NaT,
                        "fetched_at": fetched_at,
                        "snapshot_id": snapshot_id,
                    }
                )
        return pd.DataFrame(rows), payload
