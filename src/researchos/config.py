import os
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    database_url: str = "sqlite:///./var/researchos.db"
    blob_root: Path = Path("./var/blobs")
    max_upload_bytes: int = 100 * 1024 * 1024
    inline_jobs: bool = True
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
        return cls(
            environment=os.getenv("RESEARCHOS_ENV", "development"),
            database_url=os.getenv(
                "RESEARCHOS_DATABASE_URL",
                "sqlite:///./var/researchos.db",
            ),
            blob_root=Path(os.getenv("RESEARCHOS_BLOB_ROOT", "./var/blobs")),
            max_upload_bytes=int(os.getenv("RESEARCHOS_MAX_UPLOAD_BYTES", str(100 * 1024 * 1024))),
            inline_jobs=_as_bool(os.getenv("RESEARCHOS_INLINE_JOBS", "true")),
            cors_origins=tuple(
                origin.strip()
                for origin in os.getenv(
                    "RESEARCHOS_CORS_ORIGINS",
                    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3002,http://127.0.0.1:3002,http://localhost:3003,http://127.0.0.1:3003",
                ).split(",")
                if origin.strip()
            ),
        )
