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
        )
