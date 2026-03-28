"""
app/services/fal_ai.py
───────────────────────
Submits an AI avatar lip-sync video job to FAL.ai (VEED Fabric 1.0),
polls until the video is ready, and returns the final video URL.

The VEED Fabric model animates a still image to lip-sync with
an audio track — perfect for AI presenter-style TikTok videos.

Flow:
  1. POST to queue endpoint  → get request_id
  2. Poll status endpoint     → wait until "COMPLETED"
  3. Fetch result endpoint    → extract output video URL
"""

from __future__ import annotations
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

FAL_BASE_URL = "https://queue.fal.run"
FAL_MODEL = "veed/fabric-1.0"
POLL_INTERVAL_SECONDS = 5
MAX_POLL_ATTEMPTS = 60  # 5 min ceiling


# ── Submit ────────────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _submit_job(
    image_url: str,
    audio_url: str,
    resolution: str,
    client: httpx.AsyncClient,
) -> str:
    """Queue a video generation job and return the request_id."""
    settings = get_settings()
    response = await client.post(
        f"{FAL_BASE_URL}/{FAL_MODEL}",
        headers={
            "Authorization": f"Key {settings.fal_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "image_url": image_url,
            "audio_url": audio_url,
            "resolution": resolution,
        },
    )
    response.raise_for_status()
    request_id: str = response.json()["request_id"]
    logger.info("fal_job_submitted", request_id=request_id)
    return request_id


# ── Poll ──────────────────────────────────────────────────────────────────────

async def _poll_until_done(
    request_id: str,
    client: httpx.AsyncClient,
    settings,
) -> None:
    """Block until FAL job status is COMPLETED (or raise on failure)."""
    status_url = f"{FAL_BASE_URL}/{FAL_MODEL}/requests/{request_id}/status"

    for attempt in range(MAX_POLL_ATTEMPTS):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        response = await client.get(
            status_url,
            headers={"Authorization": f"Key {settings.fal_api_key}"},
        )
        response.raise_for_status()
        status = response.json().get("status", "IN_QUEUE")
        logger.debug("fal_poll", attempt=attempt + 1, status=status)

        if status == "COMPLETED":
            return
        if status in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"FAL job {request_id} ended with status: {status}")

    raise TimeoutError(f"FAL job {request_id} did not complete within the allowed time")


# ── Fetch Result ──────────────────────────────────────────────────────────────

async def _fetch_result(
    request_id: str,
    client: httpx.AsyncClient,
    settings,
) -> str:
    """Retrieve the completed job output and return the video URL."""
    result_url = f"{FAL_BASE_URL}/{FAL_MODEL}/requests/{request_id}"
    response = await client.get(
        result_url,
        headers={"Authorization": f"Key {settings.fal_api_key}"},
    )
    response.raise_for_status()
    video_url: str = response.json()["output"]["video_url"]
    logger.info("fal_video_ready", video_url=video_url)
    return video_url


# ── Public Interface ──────────────────────────────────────────────────────────

async def generate_video(image_url: str, audio_url: str) -> str:
    """
    Generate a lip-sync AI avatar video via VEED Fabric on FAL.ai.

    Args:
        image_url: Direct-download URL of the avatar image.
        audio_url: Direct-download URL of the MP3 voiceover.

    Returns:
        URL of the generated video file.

    Raises:
        RuntimeError: If the job fails or times out.
    """
    settings = get_settings()
    logger.info(
        "generating_video",
        image_url=image_url,
        audio_url=audio_url,
        resolution=settings.video_resolution,
    )

    async with httpx.AsyncClient(timeout=120) as client:
        request_id = await _submit_job(
            image_url, audio_url, settings.video_resolution, client
        )
        await _poll_until_done(request_id, client, settings)
        video_url = await _fetch_result(request_id, client, settings)

    return video_url


async def download_video(video_url: str) -> bytes:
    """
    Download a completed video to bytes for Telegram delivery.

    Args:
        video_url: URL returned by generate_video().

    Returns:
        Raw video bytes.
    """
    logger.info("downloading_video", url=video_url)
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        response = await client.get(video_url)
        response.raise_for_status()
    return response.content
