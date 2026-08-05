from __future__ import annotations

import asyncio
import hmac
from io import BytesIO
import json
import time
from collections import defaultdict, deque
from datetime import date
from threading import Lock
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader

from .config import get_settings
from .connection_schemas import DataSourceSettingsUpdate, LLMSettingsUpdate
from .connection_service import ConnectionService
from .credentials import LocalCredentialStore
from .engine import ResearchEngine
from .jobs import ResearchJobManager
from .schemas import ResearchJobCreate, ResearchRequest
from .storage import MacroStore
from .sync import SyncService
from .provider_catalog import public_provider_catalog
from .daily_brief import DailyBriefService
from .researchos_adapter import router as researchos_adapter_router
from .researchos_adapter import service as researchos_adapter_service


settings = get_settings()
store = MacroStore(settings.database_path)
credential_store = LocalCredentialStore(settings)
sync_service = SyncService(settings, store, credential_store)
engine = ResearchEngine(settings, store, credential_store)
connection_service = ConnectionService(credential_store, engine.llm)
daily_brief_service = DailyBriefService(settings.data_dir / "daily_brief", engine.llm)
job_manager = ResearchJobManager(engine, store, max_workers=settings.max_job_workers)

production_mode = settings.runtime_environment != "local"
app = FastAPI(
    title="MacroTrace",
    version="0.4.0",
    description="A registry-constrained, white-box empirical research compiler.",
    docs_url=None if production_mode else "/docs",
    redoc_url=None if production_mode else "/redoc",
    openapi_url=None if production_mode else "/openapi.json",
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Last-Event-ID", "X-MacroTrace-Admin-Key"],
)
app.include_router(researchos_adapter_router)

frontend_dir = settings.project_root / "frontend"
if settings.serve_frontend and frontend_dir.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")


class JobRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, client_id: str) -> bool:
        now = time.monotonic()
        with self._lock:
            events = self._events[client_id]
            while events and now - events[0] >= self.window_seconds:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


job_rate_limiter = JobRateLimiter(settings.job_rate_limit_per_minute)


def client_id(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    if settings.trust_proxy_headers:
        # This opt-in is safe only when the deployment edge strips client-supplied
        # forwarding headers and Uvicorn trusts a known proxy boundary.
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        return forwarded or peer
    return peer


@app.middleware("http")
async def release_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if production_mode:
        response.headers.setdefault("Cache-Control", "no-store")
    return response


def require_job(job_id: str, *, payloads: bool = False) -> dict:
    job = store.get_job(job_id, include_payloads=payloads)
    if job is None:
        raise HTTPException(status_code=404, detail="Research job not found")
    return job


def require_local_configuration_access(request: Request) -> None:
    """Keep credential-management endpoints bound to the local workbench."""
    peer = request.client.host if request.client else ""
    if peer not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Provider settings are available only from the local machine.")
    origin = request.headers.get("origin")
    if origin:
        host = (urlparse(origin).hostname or "").lower()
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise HTTPException(status_code=403, detail="Cross-origin provider configuration is blocked.")


def connection_error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in {401, 403}:
            detail = "认证失败：请检查 API Key、账户权限和余额。"
        elif status == 404:
            detail = "接口或模型不存在：请检查 Endpoint 与模型 ID。"
        elif status == 429:
            detail = "服务商限流或余额不足，请稍后重试并检查账户额度。"
        else:
            detail = f"服务商返回 HTTP {status}；密钥内容未写入日志。"
    elif isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        detail = "连接超时：请检查网络、Endpoint 或服务商状态。"
    elif isinstance(exc, ValueError):
        detail = str(exc)
    else:
        detail = "连接测试失败：请检查配置、网络和服务商账户状态。"
    return HTTPException(status_code=400, detail=detail)


@app.get("/api/health")
@app.get("/v1/health")
def health() -> dict:
    llm_status = credential_store.llm_status()
    return {
        "status": "ok",
        "version": "0.4.0",
        "database_ready": store.has_data(),
        "llm_configured": llm_status["configured"],
        "llm_provider": llm_status["provider"],
        "llm_model": llm_status["model"],
        "deepseek_configured": llm_status["configured"] and llm_status["provider"] == "deepseek",
        "deepseek_model": llm_status["model"] if llm_status["provider"] == "deepseek" else None,
        "registry": engine.registry.summary(),
        "researchos_adapter": researchos_adapter_service.health(),
    }


@app.get("/v1/settings/catalog")
def settings_catalog(request: Request) -> dict:
    require_local_configuration_access(request)
    return public_provider_catalog()


@app.get("/v1/settings/status")
def settings_status(request: Request) -> dict:
    require_local_configuration_access(request)
    return credential_store.public_status()


@app.put("/v1/settings/llm")
def update_llm_settings(payload: LLMSettingsUpdate, request: Request) -> dict:
    require_local_configuration_access(request)
    try:
        return credential_store.save_llm(
            provider_id=payload.provider,
            model=payload.model,
            base_url=payload.base_url,
            api_key=payload.api_key.get_secret_value() if payload.api_key else None,
            persist=payload.persist,
        )
    except Exception as exc:
        raise connection_error(exc) from None


@app.post("/v1/settings/llm/test")
def test_llm_settings(request: Request) -> dict:
    require_local_configuration_access(request)
    try:
        return connection_service.test_llm().model_dump()
    except Exception as exc:
        raise connection_error(exc) from None


@app.delete("/v1/settings/llm")
def clear_llm_settings(request: Request) -> dict:
    require_local_configuration_access(request)
    return credential_store.clear_llm_secret()


@app.put("/v1/settings/data-sources/{source_id}")
def update_data_source_settings(
    source_id: str,
    payload: DataSourceSettingsUpdate,
    request: Request,
) -> dict:
    require_local_configuration_access(request)
    try:
        return credential_store.save_data_key(
            source_id,
            payload.api_key.get_secret_value(),
            payload.persist,
        )
    except Exception as exc:
        raise connection_error(exc) from None


@app.post("/v1/settings/data-sources/{source_id}/test")
def test_data_source_settings(source_id: str, request: Request) -> dict:
    require_local_configuration_access(request)
    try:
        return connection_service.test_data_source(source_id).model_dump()
    except Exception as exc:
        raise connection_error(exc) from None


@app.delete("/v1/settings/data-sources/{source_id}")
def clear_data_source_settings(source_id: str, request: Request) -> dict:
    require_local_configuration_access(request)
    try:
        return credential_store.clear_data_key(source_id)
    except Exception as exc:
        raise connection_error(exc) from None


@app.get("/api/data/status")
@app.get("/v1/data/status")
def data_status() -> dict:
    rows = store.data_status()
    return {
        "ready": bool(rows),
        "series_count": len(rows),
        "sources": sorted({row["source_id"] for row in rows}),
        "series": rows,
    }


@app.post("/api/data/sync")
@app.post("/v1/data/sync")
def sync_data(
    as_of_date: date | None = None,
    admin_key: str | None = Header(default=None, alias="X-MacroTrace-Admin-Key"),
) -> dict:
    if not settings.allow_data_sync:
        raise HTTPException(status_code=403, detail="Runtime data sync is disabled; publish a reviewed snapshot instead.")
    if settings.runtime_environment != "local":
        if not settings.sync_admin_key or not hmac.compare_digest(admin_key or "", settings.sync_admin_key):
            raise HTTPException(status_code=403, detail="A valid data-sync admin key is required.")
    return sync_service.sync_all(as_of_date=as_of_date)


@app.get("/v1/registry")
def registry_summary() -> dict:
    return engine.registry.summary()


@app.get("/api/registry/modules")
def legacy_modules_registry() -> dict:
    return {
        "items": [
            {
                "module_id": item["recipe_id"],
                "description": item["method"],
                "status": item["status"],
                "evidence_type": item["evidence_type"],
            }
            for item in engine.registry.all("models")
        ],
        "arbitrary_code_allowed": False,
        "deprecated": True,
    }


@app.get("/api/examples")
@app.get("/v1/examples")
def examples() -> dict:
    return {
        "questions": [
            "未来三个月美国经济是在重新加速还是继续走弱，主要驱动因素是什么？",
            "明天标普500指数更可能上涨还是下跌，利率、盈利与风险偏好如何共同影响？",
            "当前美国通胀是否正在回升，这会如何影响利率与美股风格？",
            "未来一个月原油期货更可能上涨还是下跌，供需、库存与美元分别贡献多少？",
            "美国半导体行业景气是否继续上行，盈利与估值能否支撑相对收益？",
            "未来一到三个月美国通胀是否会加速，这会不会推动10年期美债收益率上升？",
        ]
    }


class DailyBriefQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    excerpt: str = Field(min_length=8, max_length=1800)


@app.get("/api/daily-brief")
@app.get("/v1/daily-brief")
def daily_brief() -> dict:
    """Return the last source-backed brief without forcing network traffic."""
    return daily_brief_service.latest()


@app.post("/api/daily-brief/refresh")
@app.post("/v1/daily-brief/refresh")
def refresh_daily_brief(lookback_hours: int = 72) -> dict:
    """Search registered public sources and compile a traceable daily brief."""
    if not 12 <= lookback_hours <= 168:
        raise HTTPException(status_code=422, detail="检索窗口必须在 12 到 168 小时之间。")
    return daily_brief_service.generate(lookback_hours)


@app.post("/api/daily-brief/research-question")
@app.post("/v1/daily-brief/research-question")
def daily_brief_research_question(payload: DailyBriefQuestionRequest) -> dict:
    """Compile a selected report excerpt into a research-worthy empirical question."""
    try:
        return daily_brief_service.research_question(payload.excerpt)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/documents/read-pdf")
@app.post("/v1/documents/read-pdf")
async def read_pdf_document(file: UploadFile = File(...)) -> dict:
    """Extract a local PDF in memory for the research reader; the file is never persisted."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="请选择 PDF 文件。")
    content = await file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF 不能超过 20 MB。")
    try:
        reader = PdfReader(BytesIO(content))
        pages = [
            {"page": index + 1, "text": (page.extract_text() or "").strip()}
            for index, page in enumerate(reader.pages[:120])
        ]
    except Exception as exc:
        raise HTTPException(status_code=422, detail="PDF 无法解析，可能是加密文件或扫描图片。") from exc
    pages = [page for page in pages if page["text"]]
    if not pages:
        raise HTTPException(status_code=422, detail="没有提取到可选择的文字；扫描版 PDF 暂未启用 OCR。")
    return {"filename": file.filename, "page_count": len(reader.pages), "pages": pages, "persisted": False}


@app.post("/v1/research-jobs", status_code=202)
def create_research_job(payload: ResearchJobCreate, request: Request) -> dict:
    if not store.has_data():
        raise HTTPException(status_code=409, detail="Data warehouse is empty. Run POST /v1/data/sync first.")
    if not job_rate_limiter.allow(client_id(request)):
        raise HTTPException(status_code=429, detail="Research-job rate limit exceeded. Retry after one minute.")
    if job_manager.active_count >= settings.max_queued_jobs:
        raise HTTPException(status_code=429, detail="Research queue is full. Retry after an active job finishes.")
    return job_manager.create(
        payload.question,
        payload.as_of_date or date.today(),
        payload.display_mode,
    )


@app.get("/v1/research-jobs/{job_id}")
def research_job(job_id: str) -> dict:
    return require_job(job_id)


@app.get("/v1/research-jobs/{job_id}/graph")
def research_graph(job_id: str) -> dict:
    job = require_job(job_id, payloads=True)
    if job.get("graph") is None:
        return {"schema_version": "0.2.0", "job_id": job_id, "nodes": [], "edges": [], "status": job["status"]}
    return job["graph"]


@app.get("/v1/research-jobs/{job_id}/plan")
def research_plan(job_id: str) -> dict:
    job = require_job(job_id, payloads=True)
    if job.get("plan") is None:
        raise HTTPException(status_code=409, detail=f"Research plan is not available while status is {job['status']}")
    return job["plan"]


@app.get("/v1/research-jobs/{job_id}/result")
def research_result(job_id: str) -> dict:
    job = require_job(job_id, payloads=True)
    if job.get("result") is None:
        raise HTTPException(status_code=409, detail=f"Research result is not available while status is {job['status']}")
    return job["result"]


@app.get("/v1/research-jobs/{job_id}/trace")
def research_trace(job_id: str) -> dict:
    job = require_job(job_id, payloads=True)
    return {
        "job_id": job_id,
        "status": job["status"],
        "trace": job.get("trace") or [],
        "events": store.get_events(job_id),
        "immutable_after_terminal": job["status"] in {"COMPLETE", "PARTIAL", "FAILED", "CANCELLED"},
    }


@app.get("/v1/research-jobs/{job_id}/nodes/{node_id:path}")
def research_node(job_id: str, node_id: str) -> dict:
    require_job(job_id)
    detail = store.get_node_detail(job_id, node_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Research graph node detail not found")
    return engine.explain_node_detail(job_id, node_id, detail)


@app.get("/v1/research-jobs/{job_id}/events")
async def research_events(
    job_id: str,
    request: Request,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    require_job(job_id)
    try:
        initial_sequence = int(last_event_id or 0)
    except ValueError:
        initial_sequence = 0

    async def stream():
        sequence = initial_sequence
        idle_ticks = 0
        while True:
            if await request.is_disconnected():
                return
            events = store.get_events(job_id, after=sequence)
            for event in events:
                sequence = event["sequence"]
                payload = json.dumps(event, ensure_ascii=False)
                yield f"id: {sequence}\nevent: {event['event_type'].lower()}\ndata: {payload}\n\n"
            job = store.get_job(job_id)
            if job and job["status"] in {"COMPLETE", "PARTIAL", "FAILED", "CANCELLED"} and not events:
                yield f"event: stream_complete\ndata: {json.dumps({'job_id': job_id, 'status': job['status']})}\n\n"
                return
            idle_ticks += 1
            if idle_ticks % 20 == 0:
                yield f": heartbeat {sequence}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/v1/research-jobs/{job_id}/cancel", status_code=202)
def cancel_research_job(job_id: str) -> dict:
    job = require_job(job_id)
    if job["status"] in {"COMPLETE", "PARTIAL", "FAILED", "CANCELLED"}:
        return {"job_id": job_id, "status": job["status"], "cancel_requested": False}
    if not store.request_cancel(job_id):
        raise HTTPException(status_code=404, detail="Research job not found")
    return {"job_id": job_id, "status": job["status"], "cancel_requested": True}


@app.get("/v1/artifacts/{artifact_id}")
def artifact(artifact_id: str) -> FileResponse:
    metadata = store.get_artifact(artifact_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    try:
        path = engine.artifacts.path_for(metadata["relative_path"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid artifact path") from exc
    if not path.exists():
        raise HTTPException(status_code=410, detail="Artifact metadata exists but the local file is missing")
    return FileResponse(path, media_type=metadata["media_type"], filename=path.name, headers={"ETag": metadata["sha256"]})


@app.post("/api/research", deprecated=True)
def legacy_research(request: ResearchRequest) -> dict:
    if settings.runtime_environment != "local":
        raise HTTPException(status_code=410, detail="Legacy synchronous research is disabled in release deployments.")
    if not store.has_data():
        raise HTTPException(status_code=409, detail="Data warehouse is empty. Run POST /v1/data/sync first.")
    return engine.run(request.question, as_of_date=request.as_of_date, horizon_months=request.horizon_months)


@app.get("/api/research/{run_id}", deprecated=True)
def legacy_research_run(run_id: str) -> dict:
    result = store.get_research_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Research run not found")
    return result


@app.get("/")
def index() -> FileResponse:
    if not settings.serve_frontend:
        raise HTTPException(status_code=404, detail="Frontend is deployed separately in this environment")
    path = frontend_dir / "index.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Frontend not built")
    return FileResponse(path)
