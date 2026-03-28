"""
app/core/config.py
──────────────────
Central configuration via Pydantic Settings.
All values are read from environment variables (or a .env file).
"""

from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── AI Services ───────────────────────────────────────────
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field("gpt-4o-mini")

    perplexity_api_key: str = Field(..., description="Perplexity API key")
    perplexity_model: str = Field("sonar")

    elevenlabs_api_key: str = Field(..., description="ElevenLabs API key")
    elevenlabs_voice_id: str = Field(..., description="ElevenLabs voice ID")
    elevenlabs_model_id: str = Field("eleven_multilingual_v2")

    fal_api_key: str = Field(..., description="FAL.ai API key")

    # ── Telegram ──────────────────────────────────────────────
    telegram_bot_token: str = Field(..., description="Telegram bot token")
    telegram_webhook_secret: str | None = Field(None)

    # ── Blotato Publishing ────────────────────────────────────
    blotato_api_key: str = Field(..., description="Blotato API key")
    blotato_tiktok_account_id: str = Field(default="")
    blotato_youtube_account_id: str = Field(default="")
    blotato_instagram_account_id: str = Field(default="")
    blotato_linkedin_account_id: str = Field(default="")
    blotato_twitter_account_id: str = Field(default="")
    blotato_facebook_account_id: str = Field(default="")
    blotato_facebook_page_id: str = Field(default="")
    blotato_threads_account_id: str = Field(default="")
    blotato_bluesky_account_id: str = Field(default="")
    blotato_pinterest_account_id: str = Field(default="")
    blotato_pinterest_board_id: str = Field(default="")

    # ── Google Sheets ─────────────────────────────────────────
    google_sheets_id: str = Field(default="")
    google_service_account_json: str = Field(default="./service_account.json")

    # ── Pipeline Tuning ───────────────────────────────────────
    script_max_duration_seconds: int = Field(30)
    video_resolution: str = Field("480p")
    veed_poll_wait_seconds: int = Field(60)

    # ── App ───────────────────────────────────────────────────
    app_env: str = Field("development")
    log_level: str = Field("INFO")

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "production", "staging"}
        if v.lower() not in allowed:
            raise ValueError(f"app_env must be one of {allowed}")
        return v.lower()

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()  # type: ignore[call-arg]
