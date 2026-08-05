"""Build a single-repository, privacy-clean MacroTrace server handoff.

The generated package includes code, registries and official data, but creates
a new DuckDB file rather than copying deleted pages from the local runtime DB.
This prevents local research questions and job artifacts from surviving in
unused database pages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT.parents[2] / "release" / "macrotrace-researchos"

SKIP_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "artifacts",
    "release",
    "runtime",
    "output",
    ".playwright-cli",
    ".firecrawl",
}
SKIP_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    "bilingual-github-release-plan.md",
    "github-description.md",
    "github-topics.md",
    "launch-summary.md",
    "readme-claim-check.md",
    "readme-visual-asset-plan.md",
    "readme-visual-design.md",
}
TEXT_SUFFIXES = {
    ".css",
    ".csv",
    ".dockerignore",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS = {
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    "populated credential": re.compile(
        r"(?im)^(?:DEEPSEEK|FRED|BLS|BEA|CENSUS|EIA|TUSHARE|OPENAI|ANTHROPIC)_[A-Z0-9_]*(?:KEY|TOKEN)\s*=\s*[^\s#][^\r\n]{7,}$"
    ),
    "local user path": re.compile(r"(?i)\b[A-Z]:\\(?:Users\\|aipro\\|down\\|xwechat_files\\)"),
}


def _remove_tree(path: Path) -> None:
    if not path.exists():
        return
    for item in path.rglob("*"):
        try:
            item.chmod(stat.S_IWRITE | stat.S_IREAD)
        except OSError:
            pass
    shutil.rmtree(path)


def _should_skip(relative: Path) -> bool:
    if any(part in SKIP_DIRS for part in relative.parts):
        return True
    if relative.name in SKIP_FILES:
        return True
    if relative.name.endswith((".log", ".pyc", ".pyo")):
        return True
    if "data" in relative.parts and "private" in relative.parts:
        return True
    if relative.as_posix() == "data/macrotrace.duckdb":
        return True
    return False


def copy_project(destination: Path) -> None:
    for source in ROOT.rglob("*"):
        relative = source.relative_to(ROOT)
        if _should_skip(relative):
            continue
        target = destination / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def create_clean_database(destination: Path) -> dict[str, int | str]:
    source = ROOT / "data" / "macrotrace.duckdb"
    target = destination / "data" / "macrotrace.duckdb"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise FileNotFoundError(f"Missing source database: {source}")

    connection = duckdb.connect(str(target))
    source_sql = str(source).replace("'", "''")
    connection.execute(f"ATTACH '{source_sql}' AS source_db (READ_ONLY)")
    tables = [
        row[0]
        for row in connection.execute(
            "SELECT table_name FROM duckdb_tables() "
            "WHERE database_name='source_db' AND schema_name='main' ORDER BY table_name"
        ).fetchall()
    ]
    keep_rows = {"observations", "sync_runs"}
    counts: dict[str, int | str] = {}
    for table in tables:
        where = "" if table in keep_rows else " WHERE 1=0"
        connection.execute(
            f'CREATE TABLE "{table}" AS SELECT * FROM source_db.main."{table}"{where}'
        )
        counts[table] = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    connection.execute("DETACH source_db")
    connection.execute("CHECKPOINT")
    connection.close()
    counts["sha256"] = sha256_file(target)
    return counts


def write_public_gitignore(destination: Path) -> None:
    text = """# Secrets: examples are tracked, populated files are not.
.env
.env.*
!.env.local.example
!.env.production.example
data/private/

# Runtime state
runtime/
artifacts/
output/
release/
*.log

# Local tooling
.venv/
__pycache__/
*.pyc
.pytest_cache/
.playwright-cli/
.firecrawl/
dist/
"""
    (destination / ".gitignore").write_text(text, encoding="utf-8")


def scan_text(destination: Path) -> None:
    failures: list[str] = []
    forbidden_names = {".env.local", ".env.production", "provider-config.json"}
    for path in destination.rglob("*"):
        if path.is_file() and path.name in forbidden_names:
            failures.append(f"forbidden file: {path.relative_to(destination)}")
            continue
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                failures.append(f"{label}: {path.relative_to(destination)}")
    if failures:
        raise RuntimeError("Public package scan failed:\n" + "\n".join(sorted(set(failures))))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(destination: Path, database_counts: dict[str, int | str]) -> dict:
    files = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file() or path.name == "release-manifest.json":
            continue
        files.append(
            {
                "path": path.relative_to(destination).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "product": "MacroTrace ResearchOS",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_boundary": "current product only; no git history or runtime artifacts",
        "credential_policy": "names and examples only; no usable credentials",
        "responsive_targets": [360, 390, 680, 820, 900, 1180, 1280, 1440],
        "database": database_counts,
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "files": files,
    }
    (destination / "release-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def create_zip(destination: Path) -> Path:
    archive = destination.parent / f"{destination.name}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7) as bundle:
        for path in sorted(destination.rglob("*")):
            if path.is_file():
                bundle.write(path, Path(destination.name) / path.relative_to(destination))
    return archive


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    destination = args.output.resolve()
    if ROOT == destination or ROOT in destination.parents:
        raise ValueError("Output must be outside the source project")

    _remove_tree(destination)
    destination.mkdir(parents=True)
    copy_project(destination)
    write_public_gitignore(destination)
    database_counts = create_clean_database(destination)
    scan_text(destination)
    manifest = build_manifest(destination, database_counts)
    archive = create_zip(destination)
    print(
        json.dumps(
            {
                "output": str(destination),
                "archive": str(archive),
                "file_count": manifest["file_count"],
                "total_bytes": manifest["total_bytes"],
                "database": database_counts,
                "archive_sha256": sha256_file(archive),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
