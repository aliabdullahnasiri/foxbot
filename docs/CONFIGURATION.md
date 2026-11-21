# Configuration Guide

Create `.env` locally (never commit). The coding agent should generate `.env.example` containing:

```dotenv
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_CHANNEL=
TELEGRAM_SESSION=foxbot.session

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT_SECONDS=60

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

These price limits are **example configuration values**, not proven broker-safe settings; verify them against the current symbol and volatility. Convert numeric values using `Decimal` when performing risk calculations.

## Setup
1. Install Windows MT5 terminal and sign in to a **demo** account.
2. Install Python 3.12 and `uv`.
3. In the project directory, run `uv sync` to install the locked runtime and development dependencies. MetaTrader 5 is installed on Windows only.
4. Install Ollama and pull model: `ollama pull qwen2.5:3b`.
5. Ensure Ollama is running at configured base URL.
6. Set Telegram API credentials and channel.
7. Start with `ENABLE_TRADING=false`; run `uv run python main.py` and inspect dry-run logs.
8. Enable demo execution *only after* passing tests and manually checking symbols and trade sizes.

Ollama local does not require an API key. Do not add `OPENAI_API_KEY`.
