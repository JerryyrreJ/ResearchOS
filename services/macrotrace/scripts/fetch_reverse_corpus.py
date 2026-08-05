"""Deterministically fetch source bytes for a governed reverse-engineering corpus.

This utility performs retrieval only.  It never summarizes, classifies, scores, or
proposes Registry changes.  PDF/HTML bytes and derived plain text remain under a
gitignored data directory; the committed source catalog is the reproducible input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "report_pipeline" / "corpus30" / "source_catalog.json"
DEFAULT_OUTPUT = ROOT / "data" / "report_sources" / "CORPUS30.20260715"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


class _VisibleTextParser(HTMLParser):
    BLOCKED = {"script", "style", "svg", "noscript", "template"}
    BREAKS = {
        "article", "aside", "blockquote", "br", "div", "footer", "h1", "h2", "h3",
        "h4", "h5", "h6", "header", "li", "main", "nav", "ol", "p", "section",
        "table", "td", "th", "tr", "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._blocked_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in self.BLOCKED:
            self._blocked_depth += 1
        elif self._blocked_depth == 0 and lowered in self.BREAKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in self.BLOCKED and self._blocked_depth:
            self._blocked_depth -= 1
        elif self._blocked_depth == 0 and lowered in self.BREAKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._blocked_depth == 0:
            self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts).replace("\xa0", " ")
        lines = [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines()]
        compact: list[str] = []
        for line in lines:
            if line:
                compact.append(line)
            elif compact and compact[-1] != "":
                compact.append("")
        return "\n".join(compact).strip() + "\n"


def _load_catalog(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    ids = [item["source_id"] for item in payload["sources"]]
    if len(ids) != len(set(ids)):
        raise ValueError("source_id values must be unique")
    if len(ids) != 30:
        raise ValueError(f"CORPUS30 catalog must contain exactly 30 sources, found {len(ids)}")
    return payload


def fetch(
    catalog_path: Path,
    output_root: Path,
    selected_ids: set[str] | None,
    *,
    refresh: bool = False,
) -> dict[str, Any]:
    catalog = _load_catalog(catalog_path)
    entries: list[dict[str, Any]] = []
    headers = {
        "User-Agent": "MacroTraceResearchCorpus/1.0 (+local governed research retrieval)",
        "Accept": "application/pdf,text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client:
        for source in catalog["sources"]:
            source_id = source["source_id"]
            if selected_ids and source_id not in selected_ids:
                continue
            started = _utc_now()
            expected_raw = output_root / "sources" / (
                f"{source_id}.pdf" if source["media_type"] == "application/pdf" else f"{source_id}.html"
            )
            expected_analysis = (
                expected_raw
                if source["media_type"] == "application/pdf"
                else output_root / "sources" / f"{source_id}.txt"
            )
            if not refresh and expected_raw.is_file() and expected_analysis.is_file():
                local_body = expected_raw.read_bytes()
                if source["media_type"] != "application/pdf" or local_body.lstrip().startswith(b"%PDF"):
                    entries.append(
                        {
                            "source_id": source_id,
                            "status": "REUSED_LOCAL",
                            "requested_url": source["source_url"],
                            "fetched_at": started,
                            "byte_size": len(local_body),
                            "sha256": _sha256(local_body),
                            "raw_path": str(expected_raw.resolve()),
                            "analysis_path": str(expected_analysis.resolve()),
                        }
                    )
                    continue
            attempts: list[dict[str, str]] = []
            try:
                response = None
                body = b""
                urls = [source["source_url"], *source.get("fallback_urls", [])]
                for candidate_url in urls:
                    try:
                        candidate = client.get(
                            candidate_url,
                            headers={"Referer": source.get("landing_url", candidate_url)},
                        )
                        candidate.raise_for_status()
                        response = candidate
                        body = candidate.content
                        break
                    except Exception as attempt_error:
                        attempts.append(
                            {
                                "url": candidate_url,
                                "error": f"{type(attempt_error).__name__}: {attempt_error}",
                            }
                        )
                if response is None:
                    raise RuntimeError(f"all retrieval representations failed: {attempts}")
                declared = source["media_type"]
                received = response.headers.get("content-type", "").split(";", 1)[0].strip()
                is_pdf = body.lstrip().startswith(b"%PDF")
                if declared == "application/pdf" and is_pdf:
                    source_path = output_root / "sources" / f"{source_id}.pdf"
                    _atomic_write(source_path, body)
                    analysis_path = source_path
                else:
                    if declared == "application/pdf" and not source.get("fallback_urls"):
                        raise ValueError(f"expected PDF magic bytes, received {received or 'unknown'}")
                    source_path = output_root / "sources" / f"{source_id}.html"
                    _atomic_write(source_path, body)
                    encoding = response.encoding or "utf-8"
                    html_text = body.decode(encoding, errors="replace")
                    parser = _VisibleTextParser()
                    parser.feed(html_text)
                    text_payload = parser.text().encode("utf-8")
                    analysis_path = output_root / "sources" / f"{source_id}.txt"
                    _atomic_write(analysis_path, text_payload)
                entries.append(
                    {
                        "source_id": source_id,
                        "status": (
                            "FETCHED"
                            if str(response.url) == source["source_url"] and declared != "application/pdf" or is_pdf
                            else "FETCHED_FALLBACK_REPRESENTATION"
                        ),
                        "requested_url": source["source_url"],
                        "resolved_url": str(response.url),
                        "fetched_at": started,
                        "http_status": response.status_code,
                        "content_type": received,
                        "byte_size": len(body),
                        "sha256": _sha256(body),
                        "raw_path": str(source_path.resolve()),
                        "analysis_path": str(analysis_path.resolve()),
                        "attempts": attempts,
                    }
                )
            except Exception as exc:  # each failure remains visible in the batch manifest
                entries.append(
                    {
                        "source_id": source_id,
                        "status": "FAILED",
                        "requested_url": source["source_url"],
                        "fetched_at": started,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
    manifest = {
        "catalog_id": catalog["catalog_id"],
        "catalog_version": catalog["catalog_version"],
        "generated_at": _utc_now(),
        "catalog_path": str(catalog_path.resolve()),
        "output_root": str(output_root.resolve()),
        "semantic_processing": "NONE_RETRIEVAL_ONLY",
        "entries": entries,
    }
    manifest_path = output_root / "fetch_manifest.json"
    _atomic_write(
        manifest_path,
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch MacroTrace reverse-engineering sources")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ids", nargs="*", help="Optional source IDs; default fetches all 30")
    parser.add_argument("--refresh", action="store_true", help="Refetch even when a validated local snapshot exists")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when any fetch fails")
    args = parser.parse_args()
    result = fetch(
        args.catalog.resolve(),
        args.output_root.resolve(),
        set(args.ids or []) or None,
        refresh=args.refresh,
    )
    successful = {"FETCHED", "FETCHED_FALLBACK_REPRESENTATION", "REUSED_LOCAL"}
    failures = [item for item in result["entries"] if item["status"] not in successful]
    print(json.dumps({"fetched": len(result["entries"]) - len(failures), "failed": failures}, ensure_ascii=False, indent=2))
    if args.strict and failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
