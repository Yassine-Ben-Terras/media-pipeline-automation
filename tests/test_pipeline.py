"""
tests/test_pipeline.py
───────────────────────
Unit tests for the pipeline orchestrator.
All external service calls are mocked — no real API keys needed.
"""

from __future__ import annotations
import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from app.models.job import create_job
from app.schemas.pipeline import JobStatus, Platform
from app.services import pipeline as pipeline_service


MOCK_IMAGE_URL = "https://example.com/photo.jpg"
MOCK_THEME = "morning productivity hacks"

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def job():
    return create_job()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _patch_all():
    """Return a dict of patch targets → mock return values."""
    return {
        "app.services.pipeline._download_image":    AsyncMock(return_value=b"img"),
        "app.services.storage.upload_bytes":        AsyncMock(side_effect=[
            "https://pub.example.com/image.jpg",
            "https://pub.example.com/audio.mp3",
        ]),
        "app.services.perplexity.search_trends":    AsyncMock(return_value="Trend 1, Trend 2, Trend 3"),
        "app.services.openai_service.generate_script":  AsyncMock(return_value="Script text here."),
        "app.services.elevenlabs.synthesize_voice": AsyncMock(return_value=b"mp3bytes"),
        "app.services.fal_ai.generate_video":       AsyncMock(return_value="https://cdn.fal.ai/video.mp4"),
        "app.services.openai_service.generate_caption": AsyncMock(return_value="Caption #hashtag"),
        "app.services.blotato.publish_to_all":      AsyncMock(return_value=[Platform.TIKTOK]),
        "app.services.sheets.log_run":              AsyncMock(return_value=2),
        "app.services.fal_ai.download_video":       AsyncMock(return_value=b"videodata"),
        "app.services.telegram.send_video":         AsyncMock(return_value=None),
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_happy_path(job):
    """Full pipeline run should complete with COMPLETED status."""
    patches = _patch_all()
    with (
        patch("app.services.pipeline._download_image", patches["app.services.pipeline._download_image"]),
        patch("app.services.storage.upload_bytes", patches["app.services.storage.upload_bytes"]),
        patch("app.services.perplexity.search_trends", patches["app.services.perplexity.search_trends"]),
        patch("app.services.openai_service.generate_script", patches["app.services.openai_service.generate_script"]),
        patch("app.services.elevenlabs.synthesize_voice", patches["app.services.elevenlabs.synthesize_voice"]),
        patch("app.services.fal_ai.generate_video", patches["app.services.fal_ai.generate_video"]),
        patch("app.services.openai_service.generate_caption", patches["app.services.openai_service.generate_caption"]),
        patch("app.services.blotato.publish_to_all", patches["app.services.blotato.publish_to_all"]),
        patch("app.services.sheets.log_run", patches["app.services.sheets.log_run"]),
        patch("app.services.fal_ai.download_video", patches["app.services.fal_ai.download_video"]),
        patch("app.services.telegram.send_video", patches["app.services.telegram.send_video"]),
    ):
        await pipeline_service.run(
            job=job,
            image_url=MOCK_IMAGE_URL,
            theme=MOCK_THEME,
            platforms=[Platform.TIKTOK],
            notify_chat_id="123456",
        )

    assert job.status == JobStatus.COMPLETED
    assert job.result is not None
    assert job.result.script == "Script text here."
    assert job.result.caption == "Caption #hashtag"
    assert job.result.video_url == "https://cdn.fal.ai/video.mp4"
    assert Platform.TIKTOK in job.result.published_to


@pytest.mark.asyncio
async def test_pipeline_marks_failed_on_error(job):
    """If any stage raises, the job should be marked FAILED."""
    with patch(
        "app.services.pipeline._download_image",
        AsyncMock(side_effect=RuntimeError("Network error")),
    ):
        await pipeline_service.run(
            job=job,
            image_url=MOCK_IMAGE_URL,
            theme=MOCK_THEME,
            platforms=[Platform.TIKTOK],
            notify_chat_id=None,
        )

    assert job.status == JobStatus.FAILED
    assert "Network error" in (job.error or "")


@pytest.mark.asyncio
async def test_pipeline_skips_telegram_when_no_chat_id(job):
    """Pipeline should not call telegram.send_video when notify_chat_id is None."""
    patches = _patch_all()
    mock_send = patches["app.services.telegram.send_video"]

    with (
        patch("app.services.pipeline._download_image", patches["app.services.pipeline._download_image"]),
        patch("app.services.storage.upload_bytes", patches["app.services.storage.upload_bytes"]),
        patch("app.services.perplexity.search_trends", patches["app.services.perplexity.search_trends"]),
        patch("app.services.openai_service.generate_script", patches["app.services.openai_service.generate_script"]),
        patch("app.services.elevenlabs.synthesize_voice", patches["app.services.elevenlabs.synthesize_voice"]),
        patch("app.services.fal_ai.generate_video", patches["app.services.fal_ai.generate_video"]),
        patch("app.services.openai_service.generate_caption", patches["app.services.openai_service.generate_caption"]),
        patch("app.services.blotato.publish_to_all", patches["app.services.blotato.publish_to_all"]),
        patch("app.services.sheets.log_run", patches["app.services.sheets.log_run"]),
        patch("app.services.telegram.send_video", mock_send),
    ):
        await pipeline_service.run(
            job=job,
            image_url=MOCK_IMAGE_URL,
            theme=MOCK_THEME,
            platforms=[Platform.TIKTOK],
            notify_chat_id=None,  # <-- no chat ID
        )

    mock_send.assert_not_called()
    assert job.status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_pipeline_no_platforms_skips_publish(job):
    """An empty platforms list should skip the publish stage entirely."""
    patches = _patch_all()
    mock_publish = patches["app.services.blotato.publish_to_all"]

    with (
        patch("app.services.pipeline._download_image", patches["app.services.pipeline._download_image"]),
        patch("app.services.storage.upload_bytes", patches["app.services.storage.upload_bytes"]),
        patch("app.services.perplexity.search_trends", patches["app.services.perplexity.search_trends"]),
        patch("app.services.openai_service.generate_script", patches["app.services.openai_service.generate_script"]),
        patch("app.services.elevenlabs.synthesize_voice", patches["app.services.elevenlabs.synthesize_voice"]),
        patch("app.services.fal_ai.generate_video", patches["app.services.fal_ai.generate_video"]),
        patch("app.services.openai_service.generate_caption", patches["app.services.openai_service.generate_caption"]),
        patch("app.services.blotato.publish_to_all", mock_publish),
        patch("app.services.sheets.log_run", patches["app.services.sheets.log_run"]),
        patch("app.services.telegram.send_video", patches["app.services.telegram.send_video"]),
    ):
        await pipeline_service.run(
            job=job,
            image_url=MOCK_IMAGE_URL,
            theme=MOCK_THEME,
            platforms=[],  # <-- no platforms
            notify_chat_id=None,
        )

    mock_publish.assert_not_called()
    assert job.status == JobStatus.COMPLETED
