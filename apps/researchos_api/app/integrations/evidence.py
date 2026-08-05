from apps.researchos_api.app.thesis.models import EvidenceBundle
from .contracts import validate_contract


def adapt_evidence_bundle(payload: dict) -> EvidenceBundle:
    """Only frozen-contract payloads enter the compiler; no B database access."""
    validate_contract("evidence_bundle.schema.json", payload)
    return EvidenceBundle.model_validate(payload)
