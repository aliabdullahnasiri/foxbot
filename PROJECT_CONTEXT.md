# FoxBot — Project Context

Manual MT5 orders use an operator-supplied lot size on the connected terminal account. Account eligibility, real-mode opt-in, and portfolio risk controls described below apply only to the planned automated workflow. Manual submission requires explicit execution and a checked broker request.

## Mission
Build **FoxBot**, a minimal Python 3.12 application that listens to exactly one Telegram channel, asks a **locally running Ollama** model to extract forex trading signals, validates the output deterministically, and optionally executes eligible trades through an installed MetaTrader 5 terminal using demo mode by default. The manual MT5 command supports demo and explicitly enabled real accounts.

## Scope (v1)
- Single Windows machine: Telegram listener, Ollama, Python process, and installed MetaTrader 5 terminal.
- One Telegram channel; only newly received messages, no historical automatic execution.
- XAUUSD BUY/SELL only, including configurable broker symbol suffixes such as `XAUUSD.m`.
- Extract entry, SL, and multiple TPs; execute at market only when current price is near stated entry, using **TP1**.
- Use Pydantic for output schemas and strict source-text verification. AI does **not** decide risk or trading actions.
- Risk from equity: 0.5% per signal; maximum one FoxBot XAUUSD position; hard stop loss.
- Disabled execution by default (`ENABLE_TRADING=false`), with dry-run logs.
- Standard-library logging; tests with mocked integrations.

## Explicit Non-goals
No web dashboard, PostgreSQL, SQLAlchemy, Docker, paid AI APIs, backtesting, pending orders, multi-account trading, multi-channel ingestion, TP2/TP3 management, auto-trading edited messages, automated real-account trading, or automatic strategy optimization.

The Telegram monitor is a registered Celery task and can run in the foreground without a broker. Queue workers use an explicitly configured broker.


## Technology
Python 3.12 and `uv`, Click for the CLI, FastAPI for liveness, Telethon and Celery for the Telegram monitor, an optional Redis queue broker. Ollama uses native `/api/chat` through `httpx`. Pydantic validates configuration and signal data. The MT5 adapter uses `mt5linux` to access the terminal. Tests use pytest.

## Target v1 flow
1. Telethon event handler receives a fresh message from the configured channel.
3. Send text to Ollama; require JSON; parse and independently verify against source message.
4. Reject unsuitable or stale signals and invalid SL/TP direction.
5. If execution disabled, print a detailed dry-run decision.
6. If enabled, confirm demo MT5 account, quote freshness, spread, entry tolerance, one-position policy, and risk-based lot size.
7. `order_check()` then `order_send()`; display the result and check broker history before any retry.

## Example message
```text
NEW TRADE IDEA

XAUUSD SELL 3523

TP 1 3519
TP 2 3518
TP 3 3500

SL @ 3540
```
Expected extraction: XAUUSD, SELL, entry 3523, stop 3540, TPs [3519, 3518, 3500]. This is an example, not a recommendation to trade.

## Important distinctions
The provider's claimed win rate is unverified. **Entry price is not current market price.** Execute a *market* order only if current executable quote is within configured tolerance; otherwise skip. Spread and deviation are quoted in **price units**, not pips. Broker min lots, contract sizes, stop levels, fill policy, commissions, slippage, and account settings must be obtained/checked at runtime.

## Project source layout
```text
foxbot/
├── src/
│   └── bot/
│       ├── __init__.py        # FastAPI application factory
│       ├── api/               # Router registration and GET /health
│       ├── core/              # CLI, settings, clients, and Celery setup
│       ├── models/            # Package reserved for domain models
│       ├── prompts/           # Ollama signal extraction prompt
│       ├── schemas/           # Pydantic signal data
│       ├── services/          # Synchronous MT5 adapter
│       └── workers/           # Celery task base and Telegram monitor
├── tests/
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── PROJECT_CONTEXT.md
├── docs/
└── tasks/
```
Run `uv run bot --help` for CLI commands or `uv run uvicorn bot:main --factory` to serve `GET /health`. The foreground monitor logs schema-validated Ollama extractions. Telegram source verification and order execution are tracked in the backlog. Use `uv run bot mt5-order --help` for manual MT5 orders. [Implementation backlog](tasks/BACKLOG.md)
