from io import BytesIO
from pathlib import Path

import pytest

from researchos.domain.exceptions import UploadTooLargeError
from researchos.infrastructure.blob_store import LocalContentAddressedBlobStore


def test_content_addressed_store_deduplicates(tmp_path: Path) -> None:
    store = LocalContentAddressedBlobStore(tmp_path / "blobs")
    first = store.put_stream(BytesIO(b"same"), max_bytes=100)
    second = store.put_stream(BytesIO(b"same"), max_bytes=100)

    assert first.sha256 == second.sha256
    assert first.path == second.path
    assert first.was_created is True
    assert second.was_created is False
    assert first.path.read_bytes() == b"same"


def test_upload_limit_removes_partial_file(tmp_path: Path) -> None:
    store = LocalContentAddressedBlobStore(tmp_path / "blobs")
    with pytest.raises(UploadTooLargeError):
        store.put_stream(BytesIO(b"too large"), max_bytes=3)

    assert list((tmp_path / "blobs" / "tmp").iterdir()) == []
