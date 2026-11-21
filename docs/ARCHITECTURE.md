# Architecture — Minimal FoxBot

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

## Modules
- `main.py`: start services, event lifecycle, graceful shutdown.
- `config.py`: environment parsing and validation.
- `telegram_listener.py`: Telethon auth, channel filter, new-message event handler.
- `signal_parser.py`: Ollama HTTP call, strict JSON schema, original-text verification.
- `models.py`: `Signal` Pydantic model and small result enums.
- `mt5_trader.py`: broker symbol resolution, demo checks, market quote, volume/risk, execution.
- `state.py`: SQLite message claims, processing/outcome records, daily equity snapshot.
- `tests/`: mock external APIs, especially MT5 and Ollama.

## Operational notes
- Use one process and one listener; SQLite unique channel/message ID provides restart protection.
- `MetaTrader5` calls are synchronous; use one serialized worker or `asyncio.to_thread` with careful synchronization to avoid overlapping trade submissions.
- Do not mark uncertain execution as safe to resend. Reconcile using trade history, open positions, magic number and persisted identifiers; require manual intervention if unresolved.
- Recheck safety conditions directly before order submission (TOCTOU protection).
