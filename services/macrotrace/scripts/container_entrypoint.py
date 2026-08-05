"""Prepare the persistent runtime directory and start the production API."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEED_DATABASE = ROOT / "data" / "macrotrace.duckdb"
RUNTIME_DATABASE = Path(
    os.environ.get("MACROTRACE_DATABASE_PATH", "/app/runtime/macrotrace.duckdb")
)
ARTIFACT_DIR = Path(os.environ.get("MACROTRACE_ARTIFACT_DIR", "/app/runtime/artifacts"))


def prepare_runtime() -> None:
    RUNTIME_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    if not RUNTIME_DATABASE.exists():
        if not SEED_DATABASE.exists():
            raise FileNotFoundError(f"Seed database is missing: {SEED_DATABASE}")
        shutil.copy2(SEED_DATABASE, RUNTIME_DATABASE)


def main() -> None:
    prepare_runtime()
    host = os.environ.get("HOST", "0.0.0.0")
    port = os.environ.get("PORT", "8000")
    argv = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        host,
        "--port",
        port,
        "--workers",
        "1",
        "--proxy-headers",
    ]
    os.execv(sys.executable, argv)


if __name__ == "__main__":
    main()
