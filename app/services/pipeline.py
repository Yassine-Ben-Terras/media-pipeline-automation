"""
app/services/pipeline.py
─────────────────────────
Orchestrates the full TikTok video creation and publishing pipeline.

Pipeline stages (in order):
  1.  Upload image         → public URL
  2.  Search trends        → Perplexity Sonar
  3.  Generate script      → GPT-4o-mini
  4.  Synthesize voice     → ElevenLabs TTS
  5.  Upload audio         → public URL
  6.  Generate video       → FAL.ai VEED Fabric
  7.  Generate caption     → GPT-4o-mini
  8.  Publish              → Blotato (all requested platforms)
  9.  Log to Google Sheets
  10. Send video via Telegram (optional)

Each stage updates the PipelineJob so callers can poll progress.
On any unrecoverable error the job is marked FAILED with a message.
"""

from __future__ import annotations
import asyncio
import httpx
from app.core.logging import get_logger
from app.models.job import PipelineJob
from app.schemas.pipeline import JobStatus, Platform, PipelineResult
from app.services import (
    storage,
    perplexity,
    openai_service,
    elevenlabs,
    fal_ai,
    blotato,
    sheets,
    telegram,
)

logger = get_logger(__name__)


async def _download_image(image_url: str) -> bytes:
    """Fetch image bytes from any public URL."""
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        response = await client.get(image_url)
        response.raise_for_status()
    return response.content


async def run(
    job: PipelineJob,
    image_url: str,
    theme: str,
    platforms: list[Platform],
    notify_chat_id: str | None,
) -> None:
    """
    Execute the full pipeline.

    Designed to be launched as a background task:
        asyncio.create_task(pipeline.run(job, ...))

    Args:
        job:             The PipelineJob instance to update throughout.
        image_url:       Public URL of the source avatar image.
        theme:           Content topic / theme.
        platforms:       Which platforms to publish to.
        notify_chat_id:  If set, send the final video to this Telegram chat.
    """
    job.mark_running()
    result = PipelineResult()

    try:
        # ── Stage 1: Upload image to public URL ───────────────────────────
        job.add_step("upload_image", JobStatus.RUNNING)
        image_bytes = await _download_image(image_url)
        public_image_url = await storage.upload_bytes(
            image_bytes, "avatar.jpg", "image/jpeg"
        )
        job.add_step("upload_image", JobStatus.COMPLETED, public_image_url)
        logger.info("stage_done", stage="upload_image")

        # ── Stage 2: Search viral trends ──────────────────────────────────
        job.add_step("search_trends", JobStatus.RUNNING)
        trends = await perplexity.search_trends(theme)
        job.add_step("search_trends", JobStatus.COMPLETED)
        logger.info("stage_done", stage="search_trends")

        # ── Stage 3: Generate voiceover script ────────────────────────────
        job.add_step("generate_script", JobStatus.RUNNING)
        script = await openai_service.generate_script(theme, trends)
        result.script = script
        job.add_step("generate_script", JobStatus.COMPLETED)
        logger.info("stage_done", stage="generate_script")

        # ── Stage 4: Synthesize voice ─────────────────────────────────────
        job.add_step("synthesize_voice", JobStatus.RUNNING)
        audio_bytes = await elevenlabs.synthesize_voice(script)
        job.add_step("synthesize_voice", JobStatus.COMPLETED)
        logger.info("stage_done", stage="synthesize_voice")

        # ── Stage 5: Upload audio to public URL ───────────────────────────
        job.add_step("upload_audio", JobStatus.RUNNING)
        public_audio_url = await storage.upload_bytes(
            audio_bytes, "voiceover.mp3", "audio/mpeg"
        )
        result.audio_url = public_audio_url
        job.add_step("upload_audio", JobStatus.COMPLETED, public_audio_url)
        logger.info("stage_done", stage="upload_audio")

        # ── Stage 6: Generate lip-sync video ──────────────────────────────
        job.add_step("generate_video", JobStatus.RUNNING)
        video_url = await fal_ai.generate_video(public_image_url, public_audio_url)
        result.video_url = video_url
        job.add_step("generate_video", JobStatus.COMPLETED, video_url)
        logger.info("stage_done", stage="generate_video")

        # ── Stage 7: Generate caption + hashtags ──────────────────────────
        job.add_step("generate_caption", JobStatus.RUNNING)
        caption = await openai_service.generate_caption(theme, trends)
        result.caption = caption
        job.add_step("generate_caption", JobStatus.COMPLETED)
        logger.info("stage_done", stage="generate_caption")

        # ── Stage 8: Publish to social platforms ──────────────────────────
        if platforms:
            job.add_step("publish", JobStatus.RUNNING)
            published = await blotato.publish_to_all(video_url, caption, platforms)
            result.published_to = published
            job.add_step(
                "publish",
                JobStatus.COMPLETED,
                f"Published to: {[p.value for p in published]}",
            )
            logger.info("stage_done", stage="publish", platforms=published)

        # ── Stage 9: Log to Google Sheets ─────────────────────────────────
        row = await sheets.log_run(
            theme=theme,
            script=script,
            caption=caption,
            audio_url=public_audio_url,
            video_url=video_url,
            platforms=[p.value for p in result.published_to],
        )
        result.sheets_row = row

        # ── Stage 10: Notify via Telegram ─────────────────────────────────
        if notify_chat_id:
            job.add_step("telegram_notify", JobStatus.RUNNING)
            video_bytes = await fal_ai.download_video(video_url)
            await telegram.send_video(
                chat_id=notify_chat_id,
                video_bytes=video_bytes,
                caption=caption,
            )
            job.add_step("telegram_notify", JobStatus.COMPLETED)
            logger.info("stage_done", stage="telegram_notify")

        # ── Done ──────────────────────────────────────────────────────────
        job.mark_done(result)
        logger.info(
            "pipeline_complete",
            job_id=job.job_id,
            platforms=result.published_to,
        )

    except Exception as exc:
        logger.exception("pipeline_failed", job_id=job.job_id, error=str(exc))
        job.mark_failed(str(exc))

        # Best-effort sheet failure update
        if result.sheets_row:
            await sheets.update_status(result.sheets_row, "FAILED")
