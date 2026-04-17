# TikTok Video Pipeline — AI-Powered Content Engine

> Automated end-to-end pipeline that transforms a photo + theme into a fully published short-form video across TikTok, YouTube Shorts, Instagram Reels, LinkedIn, and more.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## Architecture

```
Telegram Trigger
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                         │
│                                                             │
│  POST /pipeline/run                                         │
│         │                                                   │
│         ▼                                                   │
│  1. Extract photo + theme from Telegram payload             │
│  2. Upload image → public URL (tmpfiles.org)                │
│  3. Search viral trends (Perplexity Sonar)                  │
│  4. Generate 30-sec script (GPT-4o-mini)                    │
│  5. Synthesize voice (ElevenLabs)                           │
│  6. Upload audio → public URL (tmpfiles.org)                │
│  7. Generate lip-sync video (VEED / FAL.ai Fabric)          │
│  8. Generate caption + hashtags (GPT-4o-mini)               │
│  9. Publish to all platforms (Blotato)                      │
│ 10. Save record → Google Sheets                             │
│ 11. Send final video back via Telegram                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| API Framework | FastAPI + Uvicorn |
| Trend Research | Perplexity Sonar API |
| Script Writing | OpenAI GPT-4o-mini |
| Voice Synthesis | ElevenLabs TTS |
| Video Generation | FAL.ai (VEED Fabric 1.0) |
| Caption Writing | OpenAI GPT-4o-mini |
| Multi-platform Publishing | Blotato API |
| Storage | Google Sheets |
| Notifications | Telegram Bot API |
| Config Management | Pydantic Settings + `.env` |

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/Yassine-Ben-Terras/media-pipeline-automation.git
cd tiktok-pipeline
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your API keys in .env
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs`

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/pipeline/run` | Trigger full pipeline |
| `GET`  | `/api/v1/pipeline/{job_id}` | Poll job status |
| `POST` | `/api/v1/webhook/telegram` | Telegram webhook receiver |
| `GET`  | `/health` | Health check |

---

## ⚙️ Environment Variables

See [`.env.example`](.env.example) for the full list.

| Variable | Description |
|---|---|
| `ELEVENLABS_API_KEY` | ElevenLabs TTS API key |
| `ELEVENLABS_VOICE_ID` | Target voice ID |
| `FAL_API_KEY` | FAL.ai API key (VEED Fabric) |
| `OPENAI_API_KEY` | OpenAI API key |
| `PERPLEXITY_API_KEY` | Perplexity API key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `BLOTATO_API_KEY` | Blotato publishing API key |
| `GOOGLE_SHEETS_ID` | Target Google Sheet ID |

---

## 🗂️ Project Structure

```
tiktok_pipeline/
├── app/
│   ├── main.py                  # FastAPI app factory
│   ├── core/
│   │   ├── config.py            # Pydantic settings
│   │   └── logging.py           # Structured logging
│   ├── api/v1/
│   │   ├── pipeline.py          # Pipeline endpoints
│   │   └── webhook.py           # Telegram webhook
│   ├── services/
│   │   ├── perplexity.py        # Trend research
│   │   ├── openai_service.py    # GPT-4 script + caption
│   │   ├── elevenlabs.py        # Voice synthesis
│   │   ├── fal_ai.py            # Video generation
│   │   ├── blotato.py           # Multi-platform publish
│   │   ├── telegram.py          # Telegram bot
│   │   ├── storage.py           # File upload helpers
│   │   └── sheets.py            # Google Sheets logging
│   ├── models/
│   │   └── job.py               # Job state dataclass
│   └── schemas/
│       └── pipeline.py          # Request/Response models
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

---

## 📄 License

MIT © 2026
