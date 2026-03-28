"""
app/services/elevenlabs.py
───────────────────────────
Converts a plain-text script into an MP3 audio file
via the ElevenLabs text-to-speech API.

Returns raw audio bytes (audio/mpeg) that can be uploaded
to a public URL and passed to the video generation step.
"""

from __future__ import annotations
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def synthesize_voice(script: str) -> bytes:
    """
    Convert script text to spoken audio using ElevenLabs TTS.

    Args:
        script: Plain-text TikTok script (no markdown).

    Returns:
        Raw MP3 audio bytes.

    Raises:
        httpx.HTTPStatusError: On API error after retries.
    """
    settings = get_settings()
    logger.info(
        "synthesizing_voice",
        voice_id=settings.elevenlabs_voice_id,
        char_count=len(script),
    )

    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{settings.elevenlabs_voice_id}"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": script,
        "model_id": settings.elevenlabs_model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        audio_bytes = response.content

    logger.info("voice_synthesized", audio_bytes=len(audio_bytes))
    return audio_bytes
