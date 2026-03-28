"""
app/services/sheets.py
───────────────────────
Appends a completed pipeline run record to a Google Sheet
for tracking, analytics, and audit purposes.

Authentication uses a Google Service Account JSON key file.
The path is configured via GOOGLE_SERVICE_ACCOUNT_JSON in .env.

Sheet columns (auto-created on first write):
  Timestamp | Theme | Script | Caption | Audio URL | Video URL | Platforms | Status
"""

from __future__ import annotations
from datetime import datetime, timezone
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_HEADERS = [
    "Timestamp",
    "Theme",
    "Script",
    "Caption",
    "Audio URL",
    "Video URL",
    "Platforms",
    "Status",
]


def _get_worksheet():
    """Return the first worksheet of the configured Google Sheet."""
    import gspread
    from google.oauth2.service_account import Credentials

    settings = get_settings()
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(
        settings.google_service_account_json,
        scopes=scopes,
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(settings.google_sheets_id)
    return sheet.sheet1


async def log_run(
    theme: str,
    script: str,
    caption: str,
    audio_url: str,
    video_url: str,
    platforms: list[str],
    status: str = "DONE",
) -> int | None:
    """
    Append one row to the Google Sheet tracking log.

    Args:
        theme: The video topic.
        script: Generated voiceover script.
        caption: Generated caption with hashtags.
        audio_url: Public URL of the audio file.
        video_url: Public URL of the finished video.
        platforms: List of platforms the video was posted to.
        status: Final job status string.

    Returns:
        Row number of the appended row, or None if sheets is not configured.
    """
    settings = get_settings()
    if not settings.google_sheets_id:
        logger.info("sheets_skipped", reason="GOOGLE_SHEETS_ID not configured")
        return None

    try:
        ws = _get_worksheet()

        # Ensure headers exist in row 1
        existing = ws.row_values(1)
        if existing != _HEADERS:
            ws.insert_row(_HEADERS, index=1)

        row = [
            datetime.now(timezone.utc).isoformat(),
            theme,
            script[:500],       # truncate long scripts
            caption[:300],
            audio_url,
            video_url,
            ", ".join(platforms),
            status,
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        row_number = len(ws.get_all_values())

        logger.info("sheets_row_appended", row=row_number)
        return row_number

    except Exception as exc:
        # Non-fatal: log and continue
        logger.warning("sheets_error", error=str(exc))
        return None


async def update_status(row: int, status: str) -> None:
    """
    Update the Status column for a specific row.

    Args:
        row: 1-based row number in the sheet.
        status: New status string (e.g. "DONE", "FAILED").
    """
    settings = get_settings()
    if not settings.google_sheets_id:
        return

    try:
        ws = _get_worksheet()
        status_col = _HEADERS.index("Status") + 1
        ws.update_cell(row, status_col, status)
        logger.info("sheets_status_updated", row=row, status=status)
    except Exception as exc:
        logger.warning("sheets_update_error", error=str(exc))
