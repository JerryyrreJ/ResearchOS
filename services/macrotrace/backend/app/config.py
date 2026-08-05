from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path) -> None:
    """Load a minimal KEY=VALUE file without logging secret values."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _path_env(name: str, default: Path) -> Path:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    raw_dir: Path
    database_path: Path
    fred_api_key: str
    bls_api_key: str
    eia_api_key: str
    bea_api_key: str
    census_api_key: str
    deepseek_api_key: str
    deepseek_model: str
    deepseek_base_url: str
    runtime_environment: str
    cors_origins: tuple[str, ...]
    serve_frontend: bool
    allow_data_sync: bool
    sync_admin_key: str
    job_rate_limit_per_minute: int
    max_queued_jobs: int
    max_job_workers: int
    artifact_dir: Path
    snapshot_uri: str
    allowed_hosts: tuple[str, ...]
    trust_proxy_headers: bool

    @property
    def has_deepseek(self) -> bool:
        return bool(self.deepseek_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env.local")
    # The integrated ResearchOS launcher keeps shared credentials in one
    # ignored environment file.  Follow that local pointer without ever
    # copying or logging the secret values.
    load_dotenv(Path.cwd() / ".env.local")
    shared_env = os.getenv("RESEARCHOS_ENV_FILE", "").strip()
    if shared_env:
        load_dotenv(Path(shared_env).expanduser())
    data_dir = PROJECT_ROOT / "data"
    raw_dir = data_dir / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    runtime_environment = os.getenv("MACROTRACE_ENV", "local").strip().lower()
    default_allowed_hosts = "*.run.app,localhost,127.0.0.1,testserver" if runtime_environment != "local" else "localhost,127.0.0.1,testserver"
    return Settings(
        project_root=PROJECT_ROOT,
        data_dir=data_dir,
        raw_dir=raw_dir,
        database_path=_path_env("MACROTRACE_DATABASE_PATH", data_dir / "macrotrace.duckdb"),
        fred_api_key=os.getenv("FRED_API_KEY", ""),
        bls_api_key=os.getenv("BLS_API_KEY", ""),
        eia_api_key=os.getenv("EIA_API_KEY", ""),
        bea_api_key=os.getenv("BEA_API_KEY", ""),
        census_api_key=os.getenv("CENSUS_API_KEY", ""),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        runtime_environment=runtime_environment,
        cors_origins=tuple(
            origin.strip()
            for origin in os.getenv(
                "MACROTRACE_CORS_ORIGINS",
                "http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:8000,http://localhost:8000",
            ).split(",")
            if origin.strip()
        ),
        serve_frontend=_bool_env("MACROTRACE_SERVE_FRONTEND", True),
        allow_data_sync=_bool_env("MACROTRACE_ALLOW_DATA_SYNC", True),
        sync_admin_key=os.getenv("MACROTRACE_SYNC_ADMIN_KEY", ""),
        job_rate_limit_per_minute=max(1, int(os.getenv("MACROTRACE_JOB_RATE_LIMIT_PER_MINUTE", "3"))),
        max_queued_jobs=max(1, int(os.getenv("MACROTRACE_MAX_QUEUED_JOBS", "3"))),
        max_job_workers=max(1, int(os.getenv("MACROTRACE_MAX_JOB_WORKERS", "1"))),
        artifact_dir=_path_env("MACROTRACE_ARTIFACT_DIR", PROJECT_ROOT / "artifacts" / "jobs"),
        snapshot_uri=os.getenv("MACROTRACE_SNAPSHOT_URI", "").strip(),
        allowed_hosts=tuple(
            host.strip()
            for host in os.getenv("MACROTRACE_ALLOWED_HOSTS", default_allowed_hosts).split(",")
            if host.strip()
        ),
        trust_proxy_headers=_bool_env("MACROTRACE_TRUST_PROXY_HEADERS", False),
    )
