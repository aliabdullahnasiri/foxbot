# Architecture — Minimal FoxBot

## Target v1 flow

```text
Authorized Telegram channel
          |
          v
  Telethon NewMessage
          |
          v
  SQLite message claim  ---> duplicate? skip
          |
          v
  Ollama JSON parser (httpx, local)
          |
          v
  Pydantic + source text + price-direction validation
          |
          v
  Dry run? ---------> record decision, stop
          |
          v
  MT5 demo-only checks + market data + deterministic risk
          |
          v
  order_check -> order_send -> reconcile outcome
          |
          v
       SQLite + logs
```

## Current modules

| Path | Responsibility |
| --- | --- |
| `src/bot/core/cli.py` | Click entry point for `uv run bot`, Telegram sign-in, and foreground monitoring |
| `src/bot/__init__.py` and `src/bot/api/` | FastAPI application factory, router registration, and `GET /health` |
| `src/bot/core/settings.py` and `src/bot/core/config.py` | Typed environment settings and the shared settings instance |
| `src/bot/core/telegram.py` and `src/bot/workers/telegram.py` | Telethon client setup, channel filtering, and handling fresh candidate messages |
| `src/bot/core/celery.py` and `src/bot/workers/` | Celery application, task registration, and worker lifecycle |
| `src/bot/core/redis.py` | Async Redis client |
| `src/bot/core/ollama.py` and `src/bot/prompts/signal.md` | Native Ollama HTTP client and extraction prompt |
| `src/bot/schemas/signal/data/signal.py` | Pydantic signal data and price-direction validation |
| `src/bot/services/mt5.py` | Demo and real account access, broker order checks, operator-specified lot volume, SQLite request claims, and reconciliation |
| `tests/` | Automated tests with mocked external integrations |

Use `MT5Service` as a context manager to shut down the terminal connection. Independent source-text verification and SQLite Telegram message claims remain planned. [Implementation backlog](../tasks/BACKLOG.md)

## Operational notes
- Manual market orders enter through `bot mt5-order`. The command uses the connected account, checks the broker request, and persists a request claim before sending. The Telegram monitor logs extractions. Pending-order placement is outside FoxBot v1.
- Use one process and one listener; SQLite unique channel/message ID provides restart protection.
- `MetaTrader5` calls are synchronous; use one serialized worker or `asyncio.to_thread` with careful synchronization to avoid overlapping trade submissions.
- Do not mark uncertain execution as safe to resend. Reconcile using trade history, open positions, magic number and persisted identifiers; require manual intervention if unresolved.
- Recheck safety conditions directly before order submission (TOCTOU protection).
