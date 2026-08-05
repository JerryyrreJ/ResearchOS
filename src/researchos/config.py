import os
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip().strip('"').strip("'")
    return values


def _local_env() -> dict[str, str]:
    values = _read_env_file(Path(".env.local"))
    configured_path = os.getenv("RESEARCHOS_ENV_FILE") or values.get("RESEARCHOS_ENV_FILE")
    if configured_path:
        values.update(_read_env_file(Path(configured_path).expanduser()))
    return values


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    database_url: str = "sqlite:///./var/researchos.db"
    blob_root: Path = Path("./var/blobs")
    max_upload_bytes: int = 100 * 1024 * 1024
    inline_jobs: bool = True
    fred_api_key: str | None = None
    data_plugin_max_rows: int = 100_000
    data_plugin_timeout_seconds: int = 45
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3003",
    )

    @classmethod
    def from_env(cls) -> "Settings":
        local = _local_env()

        def value(name: str, default: str | None = None) -> str | None:
            return os.getenv(name) or local.get(name) or default

        return cls(
            environment=value("RESEARCHOS_ENV", "development") or "development",
            database_url=value(
                "RESEARCHOS_DATABASE_URL",
                "sqlite:///./var/researchos.db",
            )
            or "sqlite:///./var/researchos.db",
            blob_root=Path(value("RESEARCHOS_BLOB_ROOT", "./var/blobs") or "./var/blobs"),
            max_upload_bytes=int(
                value("RESEARCHOS_MAX_UPLOAD_BYTES", str(100 * 1024 * 1024))
                or str(100 * 1024 * 1024)
            ),
            inline_jobs=_as_bool(value("RESEARCHOS_INLINE_JOBS", "true") or "true"),
            fred_api_key=value("FRED_API_KEY"),
            data_plugin_max_rows=int(
                value("RESEARCHOS_DATA_PLUGIN_MAX_ROWS", "100000") or "100000"
            ),
            data_plugin_timeout_seconds=int(
                value("RESEARCHOS_DATA_PLUGIN_TIMEOUT_SECONDS", "45") or "45"
            ),
            cors_origins=tuple(
                origin.strip()
                for origin in (
                    value(
                        "RESEARCHOS_CORS_ORIGINS",
                        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3002,http://127.0.0.1:3002,http://localhost:3003,http://127.0.0.1:3003",
                    )
                    or ""
                ).split(",")
                if origin.strip()
            ),
        )
