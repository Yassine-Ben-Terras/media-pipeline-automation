"""
app/models/job.py
─────────────────
In-memory job registry.
Swap the _store dict for Redis or a DB in production.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from app.schemas.pipeline import JobStatus, PipelineResult, StepResult


@dataclass
class PipelineJob:
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    steps: list[StepResult] = field(default_factory=list)
    result: PipelineResult | None = None
    error: str | None = None

    def add_step(self, name: str, status: JobStatus, detail: str | None = None) -> None:
        self.steps.append(StepResult(step=name, status=status, detail=detail))
        self.updated_at = datetime.now(timezone.utc)

    def mark_running(self) -> None:
        self.status = JobStatus.RUNNING
        self.updated_at = datetime.now(timezone.utc)

    def mark_done(self, result: PipelineResult) -> None:
        self.status = JobStatus.COMPLETED
        self.result = result
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        self.status = JobStatus.FAILED
        self.error = error
        self.updated_at = datetime.now(timezone.utc)


# Simple in-memory store — replace with Redis/DB for persistence
_store: dict[str, PipelineJob] = {}


def create_job() -> PipelineJob:
    job = PipelineJob()
    _store[job.job_id] = job
    return job


def get_job(job_id: str) -> PipelineJob | None:
    return _store.get(job_id)
