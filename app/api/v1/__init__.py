"""app/api/v1/__init__.py — Aggregate all v1 routers."""
from fastapi import APIRouter
from app.api.v1.pipeline import router as pipeline_router
from app.api.v1.webhook import router as webhook_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(pipeline_router)
api_router.include_router(webhook_router)
