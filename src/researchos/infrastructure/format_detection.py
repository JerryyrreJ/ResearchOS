import zipfile
from pathlib import Path

from researchos.domain.contracts import DetectedFormat
from researchos.domain.enums import FormatKind

_BY_EXTENSION: dict[str, tuple[FormatKind, str]] = {
    ".md": (FormatKind.MARKDOWN, "text/markdown"),
    ".markdown": (FormatKind.MARKDOWN, "text/markdown"),
    ".csv": (FormatKind.CSV, "text/csv"),
    ".docx": (
        FormatKind.DOCX,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    ".xlsx": (
        FormatKind.XLSX,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    ".pdf": (FormatKind.PDF_TEXT, "application/pdf"),
}


def detect_format(path: Path, original_filename: str) -> DetectedFormat:
    extension = Path(original_filename).suffix.lower()
    warnings: list[str] = []

    with path.open("rb") as source:
        prefix = source.read(8192)

    detected = _detect_by_content(path, prefix)
    declared = _BY_EXTENSION.get(extension)

    if detected is None and declared is not None:
        detected = declared
        warnings.append("format inferred from extension because no stronger signature was found")
    elif detected is not None and declared is not None and detected[0] != declared[0]:
        warnings.append(
            f"extension {extension} disagrees with detected content {detected[0].value}"
        )

    if detected is None:
        detected = (FormatKind.UNKNOWN, "application/octet-stream")

    return DetectedFormat(
        kind=detected[0],
        mime_type=detected[1],
        extension=extension,
        warnings=tuple(warnings),
    )


def _detect_by_content(path: Path, prefix: bytes) -> tuple[FormatKind, str] | None:
    if prefix.startswith(b"%PDF-"):
        return FormatKind.PDF_TEXT, "application/pdf"

    if prefix.startswith(b"PK\x03\x04"):
        office = _detect_office_zip(path)
        if office is not None:
            return office

    if _looks_like_text(prefix):
        return None

    return None


def _detect_office_zip(path: Path) -> tuple[FormatKind, str] | None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
    except (OSError, zipfile.BadZipFile):
        return None

    if "[Content_Types].xml" not in names:
        return None
    if any(name.startswith("word/") for name in names):
        return (
            FormatKind.DOCX,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    if any(name.startswith("xl/") for name in names):
        return (
            FormatKind.XLSX,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    return None


def _looks_like_text(prefix: bytes) -> bool:
    if not prefix:
        return True
    try:
        prefix.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False
