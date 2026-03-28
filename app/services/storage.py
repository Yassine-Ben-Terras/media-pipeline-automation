"""
app/services/storage.py
────────────────────────
Upload binary data to a temporary public URL (tmpfiles.org).
The VEED / FAL.ai API requires publicly reachable image + audio URLs.

Returns a direct-download URL in the form:
  https://tmpfiles.org/dl/{id}/{filename}
"""

from __future__ import annotations
import re
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.logging import get_logger

logger = get_logger(__name__)

TMPFILES_UPLOAD_URL = "https://tmpfiles.org/api/v1/upload"
_DL_PATTERN = re.compile(r"^https?://tmpfiles\.org/(\d+)/(.+)$", re.IGNORECASE)


def _to_direct_url(url: str) -> str:
    """Convert tmpfiles share URL to direct-download URL."""
    m = _DL_PATTERN.match(url)
    if m:
        return f"https://tmpfiles.org/dl/{m.group(1)}/{m.group(2)}"
    return url


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def upload_bytes(
    data: bytes,
    filename: str,
    content_type: str,
) -> str:
    """
    Upload raw bytes to tmpfiles.org.

    Args:
        data: Raw binary content.
        filename: Filename hint (e.g. "audio.mp3").
        content_type: MIME type (e.g. "audio/mpeg").

    Returns:
        Direct-download public URL string.

    Raises:
        RuntimeError: If the upload fails after retries.
    """
    logger.info("uploading_file", filename=filename, bytes=len(data))

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            TMPFILES_UPLOAD_URL,
            files={"file": (filename, data, content_type)},
        )
        response.raise_for_status()

    payload = response.json()
    raw_url: str = payload["data"]["url"]
    direct_url = _to_direct_url(raw_url)

    logger.info("file_uploaded", url=direct_url)
    return direct_url
