# FoxBot

## Telegram monitor

1. Run `uv sync` from the repository root and copy `.env.example` to `.env`.
2. Fill in `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_CHANNEL`. Use the username or ID of a broadcast channel your Telegram user has joined.
3. Run `uv run bot telegram-login` once to create the local Telegram user session.
4. Run `uv run bot telegram-monitor` to start the registered `telegram.monitor` Celery task in the foreground. Stop with Ctrl+C. Use one monitor per session file.

The foreground command needs no broker. The monitor logs channel and message IDs for fresh XAUUSD BUY/SELL candidates. Signal parsing, durable deduplication, and order execution are separate backlog items.

For a queue-backed Celery worker, set `CELERY_BROKER_URL` in `.env` to a running broker, then start it with `uv run celery -A bot.core.celery:celery_app worker --pool=solo --loglevel=INFO`. FoxBot exits if the broker is unreachable at startup.

## HTTP API

Run `uv run uvicorn bot:main --factory --reload` from the repository root.
`GET /health` returns HTTP 200 with `{"status": "ok"}` for application liveness.

Application creation follows the EMS `App.create()` and router registration pattern.
`bot/core/` contains configuration, Celery setup, CLI commands, and Telegram
client and sign-in code. `bot/workers/` contains the async task base,
registration metaclass, and monitor. Routes live under `bot/api/routers/`.

Run `uv run ruff check .`, `uv run black .`, and `uv run pytest` for validation.
