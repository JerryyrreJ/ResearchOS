from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Protocol

from researchos.domain.enums import FormatKind, FragmentType, RepresentationType


@dataclass(frozen=True)
class StoredBlob:
    sha256: str
    size_bytes: int
    storage_key: str
    path: Path
    was_created: bool


class BlobStore(Protocol):
    def put_stream(self, stream: BinaryIO, *, max_bytes: int) -> StoredBlob: ...

    def put_bytes(self, content: bytes) -> StoredBlob: ...

    def path_for(self, storage_key: str) -> Path: ...


@dataclass(frozen=True)
class DetectedFormat:
    kind: FormatKind
    mime_type: str
    extension: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FragmentDraft:
    fragment_type: FragmentType
    locator: dict[str, Any]
    text_or_value: str
    quality: float = 1.0


@dataclass(frozen=True)
class ParsedDocument:
    representation_type: RepresentationType
    mime_type: str
    canonical_content: bytes
    fragments: tuple[FragmentDraft, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


class ParserAdapter(Protocol):
    kind: FormatKind
    name: str
    version: str

    def parse(self, path: Path) -> ParsedDocument: ...
