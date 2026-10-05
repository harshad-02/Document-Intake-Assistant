"""FastAPI application creation, CORS, and router registration."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import settings
from app.models.api import ErrorDetail, ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Document Intake Assistant",
        description="A conversational assistant for creating fictional Personal Wishes Documents.",
        version="1.0.0",
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    application.include_router(router)

    # Global exception handlers
    @application.exception_handler(422)
    async def validation_error_handler(request: Request, exc):
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message="Request validation failed. Please check your input."
                )
            ).model_dump(),
        )

    @application.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {type(exc).__name__}: {exc}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An unexpected error occurred. Please try again."
                )
            ).model_dump(),
        )

    logger.info(
        f"App started | provider={settings.LLM_PROVIDER} | "
        f"configured={settings.gemini_configured if settings.LLM_PROVIDER == 'gemini' else 'n/a'}"
    )

    return application


app = create_app()
