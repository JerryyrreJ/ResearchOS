from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import get_settings  # noqa: E402
from backend.app.storage import MacroStore  # noqa: E402
from backend.app.sync import SyncService  # noqa: E402


def main() -> None:
    settings = get_settings()
    store = MacroStore(settings.database_path)
    service = SyncService(settings, store)
    summary = service.sync_all(progress=lambda message: print(f"[sync] {message}"))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["status"] == "FAILED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

