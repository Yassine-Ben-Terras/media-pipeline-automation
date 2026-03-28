"""
app/schemas/pipeline.py
───────────────────────
Request and response models for the pipeline API.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, HttpUrl


# ── Enums ─────────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Platform(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    THREADS = "threads"
    BLUESKY = "bluesky"
    PINTEREST = "pinterest"


# ── Request Models ─────────────────────────────────────────────────────────────

class PipelineRunRequest(BaseModel):
    """
    Manually trigger the pipeline without a Telegram message.
    Useful for testing or direct API integration.
    """
    image_url: HttpUrl = Field(..., description="Publicly accessible image URL")
    theme: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Topic or theme for the video (e.g. 'morning productivity tips')",
    )
    platforms: list[Platform] = Field(
        default=[Platform.TIKTOK],
        description="Which platforms to publish to",
    )
    notify_telegram_chat_id: str | None = Field(
        None,
        description="Send the finished video back to this Telegram chat",
    )

    model_config = {"json_schema_extra": {
        "example": {
            "image_url": "https://example.com/photo.jpg",
            "theme": "morning productivity hacks for entrepreneurs",
            "platforms": ["tiktok", "instagram"],
            "notify_telegram_chat_id": "123456789",
        }
    }}


# ── Response Models ────────────────────────────────────────────────────────────

class StepResult(BaseModel):
    step: str
    status: JobStatus
    detail: str | None = None


class PipelineJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    steps: list[StepResult] = Field(default_factory=list)
    result: PipelineResult | None = None
    error: str | None = None


class PipelineResult(BaseModel):
    script: str | None = None
    caption: str | None = None
    audio_url: str | None = None
    video_url: str | None = None
    published_to: list[Platform] = Field(default_factory=list)
    sheets_row: int | None = None


# ── Telegram Webhook Payload ───────────────────────────────────────────────────

class TelegramPhoto(BaseModel):
    file_id: str
    file_unique_id: str
    width: int
    height: int
    file_size: int | None = None


class TelegramMessage(BaseModel):
    message_id: int
    chat: dict[str, Any]
    date: int
    text: str | None = None
    caption: str | None = None
    photo: list[TelegramPhoto] | None = None

    @property
    def theme(self) -> str:
        return self.caption or self.text or "viral content"

    @property
    def largest_photo_file_id(self) -> str | None:
        if not self.photo:
            return None
        return max(self.photo, key=lambda p: p.file_size or 0).file_id


class TelegramWebhookPayload(BaseModel):
    update_id: int
    message: TelegramMessage | None = None


# Rebuild for forward reference
PipelineJobResponse.model_rebuild()
