from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime
from typing import Callable
from uuid import uuid4

import pandas as pd

from .catalog import (
    BLS_SERIES,
    EIA_SERIES,
    FRED_SERIES,
    TREASURY_SERIES,
    state_panel_specs,
)
from .config import Settings
from .connectors.bls import BlsConnector
from .connectors.common import save_raw_artifact
from .connectors.eia import EiaConnector
from .connectors.fred import FredConnector
from .connectors.nyfed import NyFedConnector
from .connectors.treasury import TreasuryConnector
from .credentials import LocalCredentialStore
from .storage import MacroStore


class SyncService:
    def __init__(
        self,
        settings: Settings,
        store: MacroStore,
        credentials: LocalCredentialStore | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.credentials = credentials

    def _key(self, source_id: str, fallback: str) -> str:
        if self.credentials is None:
            return fallback
        return self.credentials.data_key(source_id)

    def sync_all(
        self,
        as_of_date: date | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> dict:
        snapshot_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
        self.store.begin_sync(snapshot_id)
        counts: dict[str, int] = {}
        errors: list[dict[str, str]] = []

        def announce(message: str) -> None:
            if progress:
                progress(message)

        try:
            fred_frames: list[pd.DataFrame] = []
            fred_key = self._key("FRED", self.settings.fred_api_key)
            fred_specs = FRED_SERIES + state_panel_specs()
            if fred_key:
                fred = FredConnector(fred_key)
                announce(f"Fetching {len(fred_specs)} FRED/ALFRED series")
                with ThreadPoolExecutor(max_workers=6) as executor:
                    future_map = {
                        executor.submit(fred.fetch, spec, snapshot_id, as_of_date): spec
                        for spec in fred_specs
                    }
                    for future in as_completed(future_map):
                        spec = future_map[future]
                        try:
                            frame, payload = future.result()
                            fred_frames.append(frame)
                            save_raw_artifact(
                                self.settings.raw_dir,
                                "FRED",
                                spec.series_id,
                                snapshot_id,
                                {"series_id": spec.series_id, "observation_start": spec.start, "as_of_date": as_of_date},
                                payload,
                            )
                        except Exception as exc:  # noqa: BLE001 - errors are recorded per series
                            errors.append({"source": "FRED", "series_id": spec.series_id, "error": type(exc).__name__})
            else:
                errors.append({"source": "FRED", "series_id": "ALL", "error": "NOT_CONFIGURED"})
            fred_frame = pd.concat(fred_frames, ignore_index=True) if fred_frames else pd.DataFrame()
            counts["FRED"] = self.store.save_observations(fred_frame)

            announce("Fetching BLS inflation, CPS, CES and JOLTS series")
            try:
                frame, payload = BlsConnector(
                    self._key("BLS", self.settings.bls_api_key)
                ).fetch_many(
                    BLS_SERIES, snapshot_id, start_year=2006
                )
                counts["BLS"] = self.store.save_observations(frame)
                save_raw_artifact(
                    self.settings.raw_dir,
                    "BLS",
                    "BLS_CORE_BATCH",
                    snapshot_id,
                    {"series_ids": [spec.series_id for spec in BLS_SERIES], "start_year": 2006},
                    payload,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append({"source": "BLS", "series_id": "BLS_CORE_BATCH", "error": type(exc).__name__})

            announce(f"Fetching {len(EIA_SERIES)} EIA petroleum series")
            eia_count = 0
            eia = EiaConnector(self._key("EIA", self.settings.eia_api_key))
            for spec in EIA_SERIES:
                try:
                    frame, payload = eia.fetch(spec, snapshot_id)
                    eia_count += self.store.save_observations(frame)
                    save_raw_artifact(
                        self.settings.raw_dir,
                        "EIA",
                        spec.series_id,
                        snapshot_id,
                        {"series_id": spec.series_id, "frequency": spec.frequency, "start": spec.start},
                        payload,
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append({"source": "EIA", "series_id": spec.series_id, "error": type(exc).__name__})
            counts["EIA"] = eia_count

            announce("Fetching Treasury debt history")
            try:
                spec = TREASURY_SERIES[0]
                frame, payload = TreasuryConnector().fetch_debt(spec, snapshot_id)
                counts["TREASURY"] = self.store.save_observations(frame)
                save_raw_artifact(
                    self.settings.raw_dir,
                    "TREASURY",
                    spec.series_id,
                    snapshot_id,
                    {"series_id": spec.series_id, "start": spec.start},
                    payload,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append({"source": "TREASURY", "series_id": "DEBT_TO_PENNY_TOTAL", "error": type(exc).__name__})

            announce("Fetching New York Fed reference rates")
            try:
                frame, payload = NyFedConnector().fetch_latest(snapshot_id)
                counts["NYFED"] = self.store.save_observations(frame)
                save_raw_artifact(
                    self.settings.raw_dir,
                    "NYFED",
                    "REFERENCE_RATES_LATEST",
                    snapshot_id,
                    {"route": "rates/all/latest"},
                    payload,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append({"source": "NYFED", "series_id": "REFERENCE_RATES", "error": type(exc).__name__})

            status = "COMPLETE" if not errors else "PARTIAL"
            summary = {
                "snapshot_id": snapshot_id,
                "status": status,
                "as_of_date": as_of_date.isoformat() if as_of_date else date.today().isoformat(),
                "rows_by_source": counts,
                "errors": errors,
                "finished_at": datetime.now(UTC).isoformat(),
            }
            self.store.finish_sync(snapshot_id, status, summary)
            return summary
        except Exception as exc:
            summary = {
                "snapshot_id": snapshot_id,
                "status": "FAILED",
                "rows_by_source": counts,
                "errors": errors + [{"source": "SYNC", "series_id": "ALL", "error": type(exc).__name__}],
            }
            self.store.finish_sync(snapshot_id, "FAILED", summary)
            raise
