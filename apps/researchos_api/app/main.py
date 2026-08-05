from fastapi import FastAPI

from .api.thesis import router

app = FastAPI(title="ResearchOS Thesis Compiler", version="0.1.0",
              description="Role C: thesis compilation, evidence policy and orchestration")
app.include_router(router)


@app.get("/health")
def health(): return {"status": "ok", "contract_version": "0.1.0-frozen"}
