"""FastAPI application for Agentic AI Fraud Investigator."""

from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.logging import get_logger
from app.api.alerts import router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Agentic AI Fraud Investigator API")
    yield
    logger.info("Shutting down Agentic AI Fraud Investigator API")


# Create FastAPI application
app = FastAPI(
    title="Agentic AI Fraud Investigator",
    description="AI-powered fraud detection and investigation system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "request_id": getattr(request.state, "request_id", None)}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "request_id": getattr(request.state, "request_id", None)}
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "Agentic AI Fraud Investigator"
    }


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {"message": "Agentic AI Fraud Investigator API", "version": "1.0.0"}



app.include_router(router, prefix="/api/alerts")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log requests with unique IDs."""
    import uuid
    import time
    
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        request_id=request_id,
        status_code=response.status_code,
        process_time_ms=round(process_time * 1000, 2)
    )
    
    response.headers["X-Request-ID"] = request_id
    return response


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )