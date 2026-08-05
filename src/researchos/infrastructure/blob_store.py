import os
import tempfile
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from researchos.domain.contracts import StoredBlob
from researchos.domain.exceptions import UploadTooLargeError


class LocalContentAddressedBlobStore:
    """Crash-safe local blob store keyed by SHA-256.

    The domain sees complete immutable blobs. A chunked implementation can replace
    this adapter later without changing AssetVersion.
    """

    _chunk_size = 1024 * 1024

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.objects_root = self.root / "objects"
        self.tmp_root = self.root / "tmp"
        self.objects_root.mkdir(parents=True, exist_ok=True)
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    def put_stream(self, stream: BinaryIO, *, max_bytes: int) -> StoredBlob:
        digest = sha256()
        size = 0
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.tmp_root,
                prefix="upload-",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                while chunk := stream.read(self._chunk_size):
                    size += len(chunk)
                    if size > max_bytes:
                        raise UploadTooLargeError(
                            f"upload exceeds configured limit of {max_bytes} bytes"
                        )
                    digest.update(chunk)
                    temporary.write(chunk)
                temporary.flush()
                os.fsync(temporary.fileno())

            content_hash = digest.hexdigest()
            storage_key = self._storage_key(content_hash)
            destination = self.path_for(storage_key)
            destination.parent.mkdir(parents=True, exist_ok=True)

            if destination.exists():
                temporary_path.unlink(missing_ok=True)
                return StoredBlob(
                    sha256=content_hash,
                    size_bytes=size,
                    storage_key=storage_key,
                    path=destination,
                    was_created=False,
                )

            try:
                os.replace(temporary_path, destination)
                was_created = True
            except OSError:
                if not destination.exists():
                    raise
                temporary_path.unlink(missing_ok=True)
                was_created = False

            return StoredBlob(
                sha256=content_hash,
                size_bytes=size,
                storage_key=storage_key,
                path=destination,
                was_created=was_created,
            )
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

    def put_bytes(self, content: bytes) -> StoredBlob:
        return self.put_stream(BytesIO(content), max_bytes=max(len(content), 1))

    def path_for(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if self.root not in candidate.parents:
            raise ValueError("storage key escapes blob root")
        return candidate

    @staticmethod
    def _storage_key(content_hash: str) -> str:
        return f"objects/{content_hash[:2]}/{content_hash[2:4]}/{content_hash}"
