"""
tests/test_schemas.py
──────────────────────
Unit tests for Pydantic schema validation.
"""

import pytest
from pydantic import ValidationError
from app.schemas.pipeline import (
    PipelineRunRequest,
    Platform,
    TelegramMessage,
    TelegramPhoto,
)


# ── PipelineRunRequest ────────────────────────────────────────────────────────

def test_pipeline_request_valid():
    req = PipelineRunRequest(
        image_url="https://example.com/photo.jpg",
        theme="morning productivity",
        platforms=["tiktok", "instagram"],
    )
    assert req.theme == "morning productivity"
    assert Platform.TIKTOK in req.platforms
    assert Platform.INSTAGRAM in req.platforms


def test_pipeline_request_defaults_to_tiktok():
    req = PipelineRunRequest(
        image_url="https://example.com/photo.jpg",
        theme="some theme",
    )
    assert req.platforms == [Platform.TIKTOK]


def test_pipeline_request_rejects_short_theme():
    with pytest.raises(ValidationError):
        PipelineRunRequest(
            image_url="https://example.com/photo.jpg",
            theme="ab",  # too short
        )


def test_pipeline_request_rejects_invalid_url():
    with pytest.raises(ValidationError):
        PipelineRunRequest(image_url="not-a-url", theme="test theme")


# ── TelegramMessage helpers ───────────────────────────────────────────────────

def test_telegram_message_theme_from_caption():
    msg = TelegramMessage(
        message_id=1,
        chat={"id": 123},
        date=0,
        caption="My cool caption",
    )
    assert msg.theme == "My cool caption"


def test_telegram_message_theme_falls_back_to_text():
    msg = TelegramMessage(
        message_id=1,
        chat={"id": 123},
        date=0,
        text="fallback text",
    )
    assert msg.theme == "fallback text"


def test_telegram_message_theme_default():
    msg = TelegramMessage(message_id=1, chat={"id": 123}, date=0)
    assert msg.theme == "viral content"


def test_telegram_message_largest_photo():
    photos = [
        TelegramPhoto(file_id="small", file_unique_id="s", width=100, height=100, file_size=1000),
        TelegramPhoto(file_id="large", file_unique_id="l", width=800, height=800, file_size=50000),
        TelegramPhoto(file_id="medium", file_unique_id="m", width=400, height=400, file_size=10000),
    ]
    msg = TelegramMessage(message_id=1, chat={"id": 123}, date=0, photo=photos)
    assert msg.largest_photo_file_id == "large"


def test_telegram_message_no_photo_returns_none():
    msg = TelegramMessage(message_id=1, chat={"id": 123}, date=0)
    assert msg.largest_photo_file_id is None
