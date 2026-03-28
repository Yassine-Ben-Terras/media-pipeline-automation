"""
app/services/openai_service.py
───────────────────────────────
Two GPT-4o-mini calls:
  1. generate_script()  — 30-second TikTok voiceover script
  2. generate_caption() — Caption + hashtags for publishing
"""

from __future__ import annotations
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


# ── Script Generation ─────────────────────────────────────────────────────────

_SCRIPT_SYSTEM = (
    "You are an expert TikTok scriptwriter. "
    "You write punchy, engaging scripts optimised for voice synthesis. "
    "Never include stage directions, formatting symbols, or markdown."
)

def _script_user_prompt(theme: str, trends: str, max_seconds: int) -> str:
    return (
        f"Based on these trends:\n{trends}\n\n"
        f"Create a viral {max_seconds}-second maximum TikTok script about: {theme}\n\n"
        "Requirements:\n"
        f"- Maximum {max_seconds} seconds when spoken aloud\n"
        "- Hook in the first 2 seconds\n"
        "- Engaging and conversational tone\n"
        "- Optimised for voice synthesis (no special characters or formatting)\n"
        "- Return ONLY the script text, nothing else"
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def generate_script(theme: str, trends: str) -> str:
    """
    Generate a short TikTok voiceover script.

    Args:
        theme: Video theme / topic.
        trends: Trend research from Perplexity.

    Returns:
        Plain-text script ready for TTS.
    """
    settings = get_settings()
    logger.info("generating_script", theme=theme)

    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SCRIPT_SYSTEM},
            {
                "role": "user",
                "content": _script_user_prompt(
                    theme, trends, settings.script_max_duration_seconds
                ),
            },
        ],
        temperature=0.8,
        max_tokens=400,
    )

    script: str = response.choices[0].message.content.strip()
    logger.info("script_generated", word_count=len(script.split()))
    return script


# ── Caption Generation ────────────────────────────────────────────────────────

_CAPTION_SYSTEM = (
    "You are a social media expert specialising in short-form video captions. "
    "You write captions that maximise reach and engagement on TikTok and Instagram. "
    "Always include trending hashtags."
)

def _caption_user_prompt(theme: str, trends: str) -> str:
    return (
        f"Create an engaging TikTok caption for a video about: {theme}\n\n"
        f"Based on these trends:\n{trends}\n\n"
        "Requirements:\n"
        "- Catchy hook in the first line\n"
        "- Include 5–8 relevant trending hashtags\n"
        "- Keep it concise and engaging\n"
        "- Optimise for the TikTok algorithm\n"
        "- Return ONLY the caption text with hashtags, nothing else"
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def generate_caption(theme: str, trends: str) -> str:
    """
    Generate a TikTok caption with hashtags.

    Args:
        theme: Video theme / topic.
        trends: Trend research from Perplexity.

    Returns:
        Caption string including hashtags.
    """
    settings = get_settings()
    logger.info("generating_caption", theme=theme)

    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _CAPTION_SYSTEM},
            {"role": "user", "content": _caption_user_prompt(theme, trends)},
        ],
        temperature=0.7,
        max_tokens=200,
    )

    caption: str = response.choices[0].message.content.strip()
    logger.info("caption_generated", char_count=len(caption))
    return caption
