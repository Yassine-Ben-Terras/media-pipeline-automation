.PHONY: install dev test lint format clean

# ── Setup ──────────────────────────────────────────────────────
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt pytest pytest-asyncio httpx black ruff

# ── Run ────────────────────────────────────────────────────────
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

prod:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# ── Quality ────────────────────────────────────────────────────
test:
	pytest -v

lint:
	ruff check app/ tests/

format:
	black app/ tests/

# ── Telegram webhook registration ──────────────────────────────
set-webhook:
	@echo "Registering Telegram webhook..."
	curl -X POST "https://api.telegram.org/bot$(TELEGRAM_BOT_TOKEN)/setWebhook" \
	  -H "Content-Type: application/json" \
	  -d '{"url": "$(WEBHOOK_URL)/api/v1/webhook/telegram"}'

# ── Cleanup ────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
