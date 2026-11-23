# Configuration Guide

Copy `.env.example` to an untracked local `.env`. Settings load these values from the environment or the local file.

```dotenv
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_CHANNEL=
TELEGRAM_SESSION=foxbot.session

CELERY_BROKER_URL=
REDIS_URL=redis://localhost:6379/0

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT_SECONDS=60

MT5_LOGIN=
MT5_PASSWORD=
MT5_SERVER=
MT5_SYMBOL=XAUUSD
MT5_MAGIC=20261121

RISK_PERCENT=0.5
MAX_DAILY_LOSS_PERCENT=2.0
MAX_ENTRY_DEVIATION=2.0
MAX_SPREAD=0.5
MAX_SIGNAL_AGE_SECONDS=120
MAX_QUOTE_AGE_SECONDS=10
ENABLE_TRADING=false

STATE_DB_PATH=foxbot_state.sqlite3
LOG_LEVEL=INFO
```

For an explicit MT5 login, set `MT5_LOGIN` to the positive numeric ID of the demo account and provide `MT5_PASSWORD` and `MT5_SERVER` together.

These price limits are **example configuration values**, not proven broker-safe settings; verify them against the current symbol and volatility. Convert numeric values using `Decimal` when performing risk calculations.

## Setup

1. Install Python 3.12 and `uv`, then run `uv sync` from the repository root.
2. Start Ollama at the configured URL and pull the configured model, for example with `ollama pull qwen2.5:3b`.
3. Set your Telegram API credentials and channel. Run `uv run bot telegram-login` and then `uv run bot telegram-monitor`.
4. Keep `ENABLE_TRADING=false`. For standalone MT5 adapter checks, use a terminal signed in to a **demo** account. Order submission is pending.

Ollama local does not require an API key. Do not add `OPENAI_API_KEY`.
