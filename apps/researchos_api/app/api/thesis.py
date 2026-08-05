from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from jsonschema import ValidationError as SchemaValidationError

from ..integrations.contracts import validate_contract
from ..integrations.evidence import adapt_evidence_bundle
from ..orchestration.store import store
from ..thesis.compiler import ThesisCompiler
from ..thesis.models import ThesisBuild, VerifyRequest

router = APIRouter(prefix="/v1")
compiler = ThesisCompiler()


@router.post("/theses", status_code=201)
def create_thesis(thesis: ThesisBuild):
    payload = thesis.model_dump()
    try:
        validate_contract("thesis_build.schema.json", payload)
        store.put_thesis(payload)
    except SchemaValidationError as exc:
        raise HTTPException(422, f"frozen contract violation: {exc.message}") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return thesis


def _thesis(thesis_id: str) -> ThesisBuild:
    value = store.get_thesis(thesis_id)
    if not value: raise HTTPException(404, "thesis not found")
    return ThesisBuild.model_validate(value)


@router.post("/theses/{thesis_id}/compile")
def compile_thesis(thesis_id: str):
    thesis = _thesis(thesis_id); job_id = store.job_id(); store.event(job_id, "QUEUED", {"thesis_id": thesis_id})
    store.event(job_id, "COMPILING", {}); prior = store.versions(thesis_id); result = compiler.compile(thesis, parent_build_id=prior[-1]["build_id"] if prior else None)
    validate_contract("compile_result.schema.json", result)
    store.put_build(result); store.event(job_id, "COMPLETE" if result["build_status"] == "SUCCESS" else "FAILED", {"build_id":result["build_id"]})
    tool_request = compiler.tool_request(thesis)
    validate_contract("tool_request.schema.json", tool_request)
    return {"job_id": job_id, "compile_result": result, "tool_request": tool_request}


@router.post("/theses/{thesis_id}/verify")
def verify_thesis(thesis_id: str, body: VerifyRequest):
    thesis = _thesis(thesis_id); evidence = adapt_evidence_bundle(body.evidence_bundle.model_dump())
    existing = store.build_for_evidence(thesis_id, evidence.bundle_id)
    if existing: return {"job_id":None,"compile_result":existing,"idempotent_replay":True}
    prior = store.versions(thesis_id); job_id=store.job_id(); store.event(job_id,"RUNNING_TOOL",{"bundle_id":evidence.bundle_id}); store.event(job_id,"RECOMPILING",{})
    result=compiler.compile(thesis,evidence,prior[-1]["build_id"] if prior else None); validate_contract("compile_result.schema.json",result); store.put_build(result); store.remember_evidence_build(thesis_id,evidence.bundle_id,result["build_id"]); store.event(job_id,"COMPLETE",{"build_id":result["build_id"]})
    return {"job_id":job_id,"compile_result":result,"idempotent_replay":False}


@router.get("/theses/{thesis_id}")
def get_thesis(thesis_id: str): return _thesis(thesis_id)


@router.get("/theses/{thesis_id}/versions")
def versions(thesis_id: str): _thesis(thesis_id); return store.versions(thesis_id)


@router.get("/thesis-versions/{a}/diff/{b}")
def diff(a: str, b: str):
    def resolve(ref: str):
        if ref in store.builds: return store.builds[ref]
        matches = [x for x in store.builds.values() if x["version_id"] == ref]
        return matches[-1] if matches else None
    left,right=resolve(a),resolve(b)
    if not left or not right: raise HTTPException(404,"thesis version/build not found")
    ignored={"build_id","parent_build_id","created_at","result_hash"}
    changed=[k for k in sorted(set(left)|set(right)) if k not in ignored and left.get(k)!=right.get(k)]
    result={"contract_version":"0.1.0-frozen","diff_id":f"DIFF_{uuid4().hex[:12].upper()}","from_version_id":left["version_id"],"to_version_id":right["version_id"],
            "changed_objects":[{"field": key, "from": left.get(key), "to": right.get(key)} for key in changed],"changed_relations":[],"affected_model_runs":[],"affected_claims":[left["thesis_id"]],"reused_refs":sorted(set(left["reused_node_ids"]) & set(right["reused_node_ids"])),"summary":f"Changed fields: {', '.join(changed) if changed else 'none'}","metadata":{"from_build_id":left["build_id"],"to_build_id":right["build_id"]}}
    validate_contract("version_diff.schema.json",result)
    return result


@router.get("/jobs/{job_id}/events")
def job_events(job_id: str):
    if job_id not in store.events: raise HTTPException(404,"job not found")
    def stream():
        for event in store.events[job_id]:
            validate_contract("job_event.schema.json",event)
            yield f"id: {event['sequence']}\nevent: {event['event_type']}\ndata: {json.dumps(event,ensure_ascii=False)}\n\n"
    return StreamingResponse(stream(),media_type="text/event-stream")
