"""
app/main.py
────────────
FastAPI application factory.

Run locally:
    uvicorn app.main:app --reload

Production:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hooks."""
    configure_logging()
    settings = get_settings()
    logger.info(
        "app_starting",
        env=settings.app_env,
        log_level=settings.log_level,
    )
    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="TikTok Video Pipeline",
        description=(
            "AI-powered pipeline that turns a photo + theme into a fully published "
            "short-form video across TikTok, YouTube Shorts, Instagram Reels, and more.\n\n"
            "**Stages:** Trend research → Script → Voice synthesis → "
            "Lip-sync video → Caption → Multi-platform publish"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Liveness check")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "env": settings.app_env})

    return app


app = create_app()
