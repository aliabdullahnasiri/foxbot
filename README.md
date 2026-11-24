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

For a stepped stop, repeat `--tp` in profit order, for example
`uv run bot mt5 order buy --entry 2500 --tp 2504 --tp 2508 --tp 2512 --sl 2496 --volume 0.02 --submit`.
The full volume stays open until a broker exit. The final TP and initial SL are attached on entry.
Keep the command running for intermediate stop changes. It polls bid for buys and ask for sells,
moving the stop one level behind the furthest observed intermediate target. TP1 moves the stop to the actual fill price, TP2 moves it to TP1, and later intermediate targets follow the same pattern. Each move must tighten the stop and satisfy broker stop and freeze distances.
A brief crossing between polls can be missed. After interruption or a management error, check
the position in MT5. The last broker-accepted SL and final TP remain active.

If the CLI reports a fill followed by a monitoring error, inspect the existing position in MT5 before taking further action. Repeating the submit command places a new order.

Submitted orders print a fill receipt. Single-target orders show the latest exit-side quote and return. During multi-target stop monitoring, the live table shows the bid for buys or ask for sells, the active stop, and the next TP trigger. The chart plots up to 40 observed quotes from oldest to newest, with the low and high shown below.

Buy and sell commands display a UTC-timestamped order log. During stop monitoring it appears below the chart and records target triggers, broker-confirmed stop updates, and errors.

If a monitor loses terminal IPC during a read, it logs up to three recovery attempts and verifies the original login, server, and position before continuing. Price crossings during the interruption may be missed. If recovery fails, inspect the existing position and its broker-held SL/TP in MT5.
