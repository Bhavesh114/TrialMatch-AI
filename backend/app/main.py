"""
TrialMatch AI FastAPI Application

Main entry point for the backend API server.

Initializes:
- FastAPI app with CORS middleware
- Request logging
- Exception handlers
- Route inclusion
- Startup/shutdown events
- Health checks
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import config
from .routers import extract, screen, report


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Configure application logging"""

    log_level = config.get_log_level()

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at level {config.LOG_LEVEL.value}")
    return logger


logger = setup_logging()


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """

    # [IMPLEMENTATION]: Startup event
    logger.info("=" * 60)
    logger.info("TrialMatch AI Backend Starting")
    logger.info("=" * 60)
    logger.info(f"Configuration: {config}")
    logger.info(f"Environment: {config.RAILWAY_ENV}")
    logger.info(f"CORS Origins: {config.ALLOWED_ORIGINS}")

    # [IMPLEMENTATION]: Validate API key is set
    if not config.ANTHROPIC_API_KEY:
        logger.critical("ANTHROPIC_API_KEY not set. Application cannot start.")
        sys.exit(1)

    logger.info("TrialMatch AI Backend Ready")

    yield  # Application runs here

    # [IMPLEMENTATION]: Shutdown event
    logger.info("=" * 60)
    logger.info("TrialMatch AI Backend Shutting Down")
    logger.info("=" * 60)


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="TrialMatch AI",
    description="Clinical Trial Eligibility Screener",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# [IMPLEMENTATION]: CORS Middleware
# Allow requests from configured frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests and outgoing responses.

    Useful for debugging and monitoring.
    """

    logger.debug(f"{request.method} {request.url.path}")

    response = await call_next(request)

    logger.debug(
        f"{request.method} {request.url.path} → {response.status_code}"
    )

    return response


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors"""
    logger.warning(f"ValueError: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again."}
    )


# ============================================================================
# ROUTE INCLUSION
# ============================================================================

# [IMPLEMENTATION]: Include routers
app.include_router(extract.router)
app.include_router(screen.router)
app.include_router(report.router)


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information"""
    return {
        "service": "TrialMatch AI Backend",
        "version": "1.0.0",
        "docs": "/api/docs",
        "status": "healthy"
    }


@app.get("/health", tags=["health"])
async def health():
    """
    Health check endpoint.

    Used by load balancers and monitoring systems.
    """
    return {
        "status": "healthy",
        "service": "trialmatch-ai",
        "environment": config.RAILWAY_ENV,
        "version": "1.0.0"
    }


@app.get("/config", tags=["config"])
async def get_config():
    """
    Get non-sensitive configuration information.

    Does not expose API keys or secrets.
    """
    return {
        "model": config.CLAUDE_MODEL,
        "max_pdf_size_mb": config.MAX_PDF_SIZE_MB,
        "cors_origins": config.ALLOWED_ORIGINS,
        "environment": config.RAILWAY_ENV,
        "features": {
            "criteria_caching": config.ENABLE_CRITERIA_CACHING,
            "ocr_fallback": config.ENABLE_OCR_FALLBACK
        }
    }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    """
    Run the FastAPI application with uvicorn.

    [IMPLEMENTATION]: In production, use:
    - Railway deployment: uvicorn runs automatically
    - Docker: CMD in Dockerfile specifies uvicorn
    - Local: python -m backend.app.main

    Configuration via environment:
    - PORT (default 8000)
    - HOST (default 0.0.0.0)
    - WORKERS (default 1 for Railway, increase for production)
    """

    import os

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    workers = int(os.getenv("WORKERS", "1"))

    logger.info(f"Starting uvicorn server: {host}:{port} (workers={workers})")

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info"
    )
