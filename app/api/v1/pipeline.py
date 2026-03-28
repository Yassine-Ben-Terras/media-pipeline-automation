"""
app/api/v1/pipeline.py
───────────────────────
REST endpoints for triggering and monitoring pipeline jobs.

POST /api/v1/pipeline/run
    Validate request, create a job, fire-and-forget the pipeline,
    and immediately return the job_id so the client can poll.

GET  /api/v1/pipeline/{job_id}
    Return current job status, completed steps, and final result.
"""

from __future__ import annotations
import asyncio
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from app.models.job import create_job, get_job
from app.schemas.pipeline import (
    JobStatus,
    PipelineJobResponse,
    PipelineRunRequest,
    StepResult,
)
from app.services import pipeline as pipeline_service
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


def _job_to_response(job) -> PipelineJobResponse:
    return PipelineJobResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        steps=job.steps,
        result=job.result,
        error=job.error,
    )


@router.post(
    "/run",
    response_model=PipelineJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger the TikTok video pipeline",
    description=(
        "Accepts an image URL and content theme, then asynchronously runs the full "
        "pipeline: trend research → script → voice → video → caption → publish. "
        "Returns immediately with a `job_id` you can poll."
    ),
)
async def run_pipeline(
    body: PipelineRunRequest,
    background_tasks: BackgroundTasks,
) -> PipelineJobResponse:
    job = create_job()
    logger.info(
        "pipeline_enqueued",
        job_id=job.job_id,
        theme=body.theme,
        platforms=[p.value for p in body.platforms],
    )

    background_tasks.add_task(
        pipeline_service.run,
        job=job,
        image_url=str(body.image_url),
        theme=body.theme,
        platforms=body.platforms,
        notify_chat_id=body.notify_telegram_chat_id,
    )

    return _job_to_response(job)


@router.get(
    "/{job_id}",
    response_model=PipelineJobResponse,
    summary="Poll pipeline job status",
    description="Returns current status, completed steps, and final result once done.",
    responses={
        404: {"description": "Job not found"},
    },
)
async def get_pipeline_status(job_id: str) -> PipelineJobResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return _job_to_response(job)
