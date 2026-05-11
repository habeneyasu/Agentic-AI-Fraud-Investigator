"""
Agentic AI Fraud Investigator — FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Agentic AI Fraud Investigator API",
                env=settings.environment, version=settings.app_version)
    yield
    logger.info("Shutting down Agentic AI Fraud Investigator API")


app = FastAPI(
    title="Agentic AI Fraud Investigator",
    description="Agentic fraud detection and investigation API with orchestrated evidence agents and HITL workflows.",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": settings.app_version,
            "service": settings.app_name, "env": settings.environment}


@app.get("/", tags=["Root"])
async def root():
    return {"message": settings.app_name, "version": settings.app_version, "docs": "/docs"}


# ── Register routers ──────────────────────────────────────────────────────────
from app.api.alerts import router as alerts_router
from app.api.hitl import router as hitl_router
from app.api.audit import router as audit_router
from app.api.transactions import router as transactions_router
from app.api.kyc import router as kyc_router
from app.api.sanctions import router as sanctions_router
from app.api.triage import router as triage_router
from app.api.investigation import router as investigation_router
from app.api.fraud_memory import router as fraud_memory_router
from app.api.investigate import router as investigate_router

app.include_router(alerts_router, prefix="/v1")
app.include_router(hitl_router)
app.include_router(audit_router)
app.include_router(transactions_router, prefix="/v1")
app.include_router(kyc_router, prefix="/v1")
app.include_router(sanctions_router, prefix="/v1")
app.include_router(triage_router, prefix="/v1")
app.include_router(investigation_router, prefix="/v1")
app.include_router(fraud_memory_router, prefix="/v1")
app.include_router(investigate_router, prefix="/v1")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
