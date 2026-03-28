"""
app/api/v1/webhook.py
──────────────────────
Telegram webhook endpoint.

When Telegram sends a message update (user sends photo + caption),
this handler:
  1. Validates the optional HMAC webhook secret header.
  2. Parses the TelegramWebhookPayload.
  3. Downloads the photo via the Bot API.
  4. Uploads the photo to a public URL.
  5. Fires the pipeline as a background task.
  6. Returns 200 immediately (Telegram requires a fast response).

To register this webhook with Telegram:
    POST https://api.telegram.org/bot<TOKEN>/setWebhook
    {"url": "https://your-domain.com/api/v1/webhook/telegram"}
"""

from __future__ import annotations
import hashlib
import hmac
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.job import create_job
from app.schemas.pipeline import Platform, TelegramWebhookPayload
from app.services import pipeline as pipeline_service
from app.services import storage, telegram as tg_service

logger = get_logger(__name__)
router = APIRouter(prefix="/webhook", tags=["Webhook"])

# Default platforms to publish to when triggered from Telegram
DEFAULT_PLATFORMS = [Platform.TIKTOK, Platform.INSTAGRAM]


def _verify_secret(payload: bytes, signature: str | None) -> None:
    """Validate HMAC-SHA256 webhook secret if configured."""
    settings = get_settings()
    if not settings.telegram_webhook_secret:
        return  # Secret not configured — skip verification

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Telegram-Bot-Api-Secret-Token header.",
        )

    expected = hmac.new(
        settings.telegram_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature.lower()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret.",
        )


@router.post(
    "/telegram",
    status_code=status.HTTP_200_OK,
    summary="Telegram bot webhook receiver",
    description=(
        "Receives Telegram updates. When a user sends a photo with a caption, "
        "the pipeline is triggered automatically using the photo as the avatar "
        "and the caption as the content theme."
    ),
)
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    body = await request.body()
    _verify_secret(body, x_telegram_bot_api_secret_token)

    payload = TelegramWebhookPayload.model_validate_json(body)
    message = payload.message

    if not message:
        return {"ok": True, "note": "No message in update — ignored."}

    chat_id = str(message.chat.get("id", ""))

    # Only handle messages with a photo; ignore plain text
    if not message.photo:
        logger.info("webhook_no_photo", chat_id=chat_id)
        return {"ok": True, "note": "No photo — ignored."}

    file_id = message.largest_photo_file_id
    theme = message.theme

    logger.info("webhook_triggered", chat_id=chat_id, theme=theme, file_id=file_id)

    # Download photo and get a public URL before handing off to background task
    image_bytes = await tg_service.download_file(file_id)
    public_image_url = await storage.upload_bytes(image_bytes, "photo.jpg", "image/jpeg")

    job = create_job()
    background_tasks.add_task(
        pipeline_service.run,
        job=job,
        image_url=public_image_url,
        theme=theme,
        platforms=DEFAULT_PLATFORMS,
        notify_chat_id=chat_id,
    )

    logger.info("webhook_job_created", job_id=job.job_id, chat_id=chat_id)
    return {"ok": True, "job_id": job.job_id}
