"""Governed report reverse-engineering pipeline.

The package is intentionally build-time only.  Public research jobs consume the
reviewed registries produced by this pipeline; they never ingest report files or
accept arbitrary registry mutations.
"""

from .contracts import ReportReverseRecord
from .policy import ReportPolicyAudit, audit_report_record
from .service import ReportIngestionService

__all__ = [
    "ReportIngestionService",
    "ReportPolicyAudit",
    "ReportReverseRecord",
    "audit_report_record",
]
