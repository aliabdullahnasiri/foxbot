# FoxBot

## Telegram monitor

1. Run `uv sync` from the repository root and copy `.env.example` to `.env`.
2. Fill in `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_CHANNEL`. Use the username or ID of a broadcast channel your Telegram user has joined.
3. Run `uv run bot telegram-login` once to create the local Telegram user session.
4. Run `uv run bot telegram-monitor` to start the registered `telegram.monitor` Celery task in the foreground. Stop with Ctrl+C. Use one monitor per session file.

The foreground command needs no broker. The monitor filters fresh XAUUSD BUY/SELL candidates and logs schema-validated Ollama extractions along with their channel and message IDs. Independent source verification and order execution are tracked in the backlog. [Implementation backlog](tasks/BACKLOG.md)

For a queue-backed Celery worker, set `CELERY_BROKER_URL` in `.env` to a running broker, then start it with `uv run celery -A bot.core.celery:celery_app worker --pool=solo --loglevel=INFO`. FoxBot exits if the broker is unreachable at startup.

## HTTP API

Run `uv run uvicorn bot:main --factory --reload` from the repository root.
`GET /health` returns HTTP 200 with `{"status": "ok"}` for application liveness.

## Manual MT5 orders

Preview a market position with `uv run bot mt5 order buy --volume LOTS --sl STOP --tp TARGET`. Manual orders use the specified lot size on the connected terminal account, including real accounts. [Manual submission](docs/CONFIGURATION.md#manual-mt5-orders)


```bash
uv run bot mt5 order sell --volume 0.02 --sl 3670 --tp 3660 --submit
uv run bot mt5 order list
uv run bot mt5 order list --ticket 12345
uv run bot mt5 order close 12345
uv run bot mt5 order close 12345 --submit
```

Use `uv run bot mt5 order list` to see a table of position tickets, symbols, sides, and lot sizes for the configured symbol, or add `--ticket TICKET` to filter. Preview a full close with `uv run bot mt5 order close TICKET`. Both opening and closing require `--submit` and `ENABLE_TRADING=true` to execute. Use `uv run bot mt5 order --help` to see all commands.


## Project structure

The installable package lives under `src/bot/`. The CLI, configuration, and external clients are under `core/`. Worker tasks live in `workers/`, HTTP routes in `api/`, signal schemas in `schemas/`, extraction prompts in `prompts/`, and the MT5 adapter in `services/`.  [Architecture](docs/ARCHITECTURE.md)

Run `uv run ruff check .`, `uv run black .`, and `uv run pytest` for validation.
