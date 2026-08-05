from enum import StrEnum


class AssetStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class BatchStatus(StrEnum):
    OPEN = "OPEN"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class IngestItemStatus(StrEnum):
    QUEUED = "QUEUED"
    STORED = "STORED"
    DUPLICATE = "DUPLICATE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ParseStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"


class RepresentationType(StrEnum):
    ORIGINAL = "ORIGINAL"
    CANONICAL_TEXT = "CANONICAL_TEXT"
    CANONICAL_TABLE = "CANONICAL_TABLE"


class FragmentType(StrEnum):
    TEXT_BLOCK = "TEXT_BLOCK"
    TABLE_ROW = "TABLE_ROW"
    TABLE_CELL_RANGE = "TABLE_CELL_RANGE"


class ResolutionStatus(StrEnum):
    NEW_ASSET = "NEW_ASSET"
    NEW_VERSION = "NEW_VERSION"
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    AMBIGUOUS_NEW_ASSET = "AMBIGUOUS_NEW_ASSET"


class SourceKind(StrEnum):
    BROWSER_UPLOAD = "BROWSER_UPLOAD"
    CONNECTOR = "CONNECTOR"
    API = "API"


class FormatKind(StrEnum):
    MARKDOWN = "MARKDOWN"
    DOCX = "DOCX"
    XLSX = "XLSX"
    CSV = "CSV"
    PDF_TEXT = "PDF_TEXT"
    UNKNOWN = "UNKNOWN"


class ActorType(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    AI = "AI"
