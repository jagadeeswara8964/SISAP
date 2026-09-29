"""SISAP - Smart Indian Standards Advisor for Procurement.

FastAPI application entrypoint.

Run from the ``backend`` directory:
    uvicorn main:app --reload
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router
from config import settings
from services.analysis_service import analysis_service
from services.standards_service import standards_service
from utils import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the dataset and build the FAISS index once at startup."""
    started = time.time()
    try:
        if not standards_service.count():
            standards_service.load_dataset()
        analysis_service.initialise()
        logger.info("startup complete in %.1fs", time.time() - started)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("startup initialisation failed: %s", exc)
    yield
    logger.info("SISAP shutting down")


app = FastAPI(
    title="SISAP API",
    description=(
        "Smart Indian Standards Advisor for Procurement - an explainable standards "
        "recommendation engine for tender and specification analysis (SIH26108)."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return a readable 422 for malformed requests."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "The request could not be validated. Check the request body and field names.",
            "code": "validation_error",
            "errors": [
                {"field": ".".join(str(part) for part in error.get("loc", [])), "message": error.get("msg", "")}
                for error in exc.errors()
            ],
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred.", "code": "internal_error"},
    )


@app.get("/", tags=["root"])
async def root() -> dict:
    return {
        "name": settings.app_name,
        "full_name": "Smart Indian Standards Advisor for Procurement",
        "version": settings.app_version,
        "problem_statement": "SIH26108 - AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications",
        "theme": "Smart Automation",
        "docs": "/api/docs",
        "health": "/api/health",
        "demo_mode": settings.demo_mode,
    }


app.include_router(router)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
