"""
app/services/blotato.py
────────────────────────
Publishes video content to multiple social platforms via the Blotato API.

Supported platforms:
  TikTok · YouTube · Instagram · LinkedIn · Twitter/X
  Facebook · Threads · Bluesky · Pinterest

Each platform has its own account ID config and optional extra fields
(YouTube title/privacy, Facebook page ID, Pinterest board ID).
"""

from __future__ import annotations
import asyncio
import httpx
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.pipeline import Platform

logger = get_logger(__name__)

BLOTATO_BASE_URL = "https://api.blotato.com/v1"


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


# ── Upload ────────────────────────────────────────────────────────────────────

async def upload_media(video_url: str) -> str:
    """
    Upload video to Blotato's media store and return the media_id.

    Args:
        video_url: Public URL of the video file.

    Returns:
        Blotato media_id string.
    """
    settings = get_settings()
    logger.info("blotato_upload_media", url=video_url)

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{BLOTATO_BASE_URL}/media",
            headers=_headers(settings.blotato_api_key),
            json={"media_url": video_url},
        )
        response.raise_for_status()

    media_id: str = response.json()["media_id"]
    logger.info("blotato_media_uploaded", media_id=media_id)
    return media_id


# ── Per-Platform Payloads ─────────────────────────────────────────────────────

def _build_payload(
    platform: Platform,
    media_id: str,
    caption: str,
    settings,
) -> dict:
    """Build the platform-specific publish payload."""
    base = {
        "platform": platform.value,
        "content": {"text": caption, "media_ids": [media_id]},
    }

    match platform:
        case Platform.TIKTOK:
            base["account_id"] = settings.blotato_tiktok_account_id
        case Platform.YOUTUBE:
            base["account_id"] = settings.blotato_youtube_account_id
            base["youtube_options"] = {
                "title": caption[:100],
                "privacy_status": "public",
                "notify_subscribers": True,
            }
        case Platform.INSTAGRAM:
            base["account_id"] = settings.blotato_instagram_account_id
        case Platform.LINKEDIN:
            base["account_id"] = settings.blotato_linkedin_account_id
        case Platform.TWITTER:
            base["account_id"] = settings.blotato_twitter_account_id
        case Platform.FACEBOOK:
            base["account_id"] = settings.blotato_facebook_account_id
            base["facebook_page_id"] = settings.blotato_facebook_page_id
        case Platform.THREADS:
            base["account_id"] = settings.blotato_threads_account_id
        case Platform.BLUESKY:
            base["account_id"] = settings.blotato_bluesky_account_id
        case Platform.PINTEREST:
            base["account_id"] = settings.blotato_pinterest_account_id
            base["pinterest_board_id"] = settings.blotato_pinterest_board_id

    return base


# ── Publish ───────────────────────────────────────────────────────────────────

async def _publish_to_platform(
    platform: Platform,
    media_id: str,
    caption: str,
    settings,
    client: httpx.AsyncClient,
) -> bool:
    """
    Publish to a single platform. Returns True on success, False on error.
    Non-critical: failures are logged but do not abort the pipeline.
    """
    payload = _build_payload(platform, media_id, caption, settings)
    try:
        response = await client.post(
            f"{BLOTATO_BASE_URL}/posts",
            headers=_headers(settings.blotato_api_key),
            json=payload,
        )
        response.raise_for_status()
        logger.info("published", platform=platform.value)
        return True
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "publish_failed",
            platform=platform.value,
            status=exc.response.status_code,
            body=exc.response.text[:200],
        )
        return False


async def publish_to_all(
    video_url: str,
    caption: str,
    platforms: list[Platform],
) -> list[Platform]:
    """
    Upload video once, then publish concurrently to all requested platforms.

    Args:
        video_url: Public video URL.
        caption: Caption with hashtags.
        platforms: Which platforms to target.

    Returns:
        List of platforms that were successfully published to.
    """
    settings = get_settings()
    media_id = await upload_media(video_url)

    async with httpx.AsyncClient(timeout=60) as client:
        tasks = [
            _publish_to_platform(p, media_id, caption, settings, client)
            for p in platforms
        ]
        results = await asyncio.gather(*tasks)

    successful = [p for p, ok in zip(platforms, results) if ok]
    logger.info("publishing_complete", total=len(platforms), ok=len(successful))
    return successful
