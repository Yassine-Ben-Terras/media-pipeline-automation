"""
app/services/telegram.py
─────────────────────────
Thin wrapper around the Telegram Bot API for:
  - Fetching file download URLs for photos sent by users
  - Sending completed videos back to the triggering chat
"""

from __future__ import annotations
import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_BASE = "https://api.telegram.org"


def _bot_url(token: str) -> str:
    return f"{_BASE}/bot{token}"


async def get_file_url(file_id: str) -> str:
    """
    Resolve a Telegram file_id to a direct HTTPS download URL.

    Args:
        file_id: Telegram file identifier from an update.

    Returns:
        Full HTTPS URL to download the file.
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{_bot_url(settings.telegram_bot_token)}/getFile",
            params={"file_id": file_id},
        )
        response.raise_for_status()

    file_path: str = response.json()["result"]["file_path"]
    url = f"{_BASE}/file/bot{settings.telegram_bot_token}/{file_path}"
    logger.info("telegram_file_url", file_id=file_id, url=url)
    return url


async def download_file(file_id: str) -> bytes:
    """
    Download a Telegram file by its file_id and return raw bytes.

    Args:
        file_id: Telegram file identifier.

    Returns:
        Raw file bytes.
    """
    url = await get_file_url(file_id)
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url)
        response.raise_for_status()
    return response.content


async def send_video(
    chat_id: str | int,
    video_bytes: bytes,
    caption: str | None = None,
) -> None:
    """
    Send a video file to a Telegram chat.

    Args:
        chat_id: Target Telegram chat ID.
        video_bytes: Raw video bytes.
        caption: Optional message caption.
    """
    settings = get_settings()
    logger.info("sending_telegram_video", chat_id=chat_id, bytes=len(video_bytes))

    files = {"video": ("video.mp4", video_bytes, "video/mp4")}
    data: dict = {"chat_id": str(chat_id)}
    if caption:
        data["caption"] = caption[:1024]  # Telegram caption limit

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{_bot_url(settings.telegram_bot_token)}/sendVideo",
            data=data,
            files=files,
        )
        response.raise_for_status()

    logger.info("telegram_video_sent", chat_id=chat_id)
