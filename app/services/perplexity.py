"""
app/services/perplexity.py
───────────────────────────
Queries Perplexity Sonar to surface the top 3 viral trends
for a given theme. Used to ground the GPT-4 script in real
current content that is performing on TikTok.
"""

from __future__ import annotations
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

PERPLEXITY_BASE_URL = "https://api.perplexity.ai"


def _build_trend_prompt(theme: str) -> str:
    return (
        f"Find the top 3 current viral trends related to: {theme}. "
        "Focus on trending topics, hashtags, and content styles that are performing "
        "well on TikTok right now. Be specific and actionable. "
        "Limit your response strictly to 3 results only — no more."
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def search_trends(theme: str) -> str:
    """
    Fetch top 3 current viral trends for the given theme.

    Args:
        theme: The content topic (e.g. "morning productivity").

    Returns:
        Raw text response from Perplexity describing the trends.

    Raises:
        httpx.HTTPStatusError: On non-2xx responses after retries.
    """
    settings = get_settings()
    logger.info("searching_trends", theme=theme, model=settings.perplexity_model)

    payload = {
        "model": settings.perplexity_model,
        "messages": [
            {"role": "user", "content": _build_trend_prompt(theme)},
        ],
    }

    async with httpx.AsyncClient(
        base_url=PERPLEXITY_BASE_URL,
        headers={
            "Authorization": f"Bearer {settings.perplexity_api_key}",
            "Content-Type": "application/json",
        },
        timeout=30,
    ) as client:
        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()

    data = response.json()
    trends_text: str = data["choices"][0]["message"]["content"]

    logger.info("trends_retrieved", char_count=len(trends_text))
    return trends_text
