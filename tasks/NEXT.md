# Next Coding-Agent Task

**T01 — Create the smallest runnable FoxBot foundation.**

Read `PROJECT_CONTEXT.md`, `AGENTS.md`, `CLAUDE.md`, and `docs/REQUIREMENTS.md`. Inspect the repository first; don't overwrite existing correct work.

Create a Python 3.12 project with `uv`, minimal pinned/locked dependencies, `.env.example`, `.gitignore`, readable `config.py`, a startup `main.py` that prints sanitized startup configuration, and README setup steps for Windows MT5 + local Ollama. Include `ENABLE_TRADING=false` and reject any configuration that would imply live trading. Add basic config tests. Do **not** connect to Telegram or send MT5 orders in this first task.

Run available tests and linting; report exact commands and results. Update `tasks/BACKLOG.md` when T01 is done and replace this file with the next task (T02).

Progress: `.gitignore` is in place for local credentials, Telegram sessions, SQLite state, logs, and Python artifacts. `.env.example` includes the documented settings and defaults to dry run. The scaffold targets Python 3.12 and declares locked runtime and development dependencies, including Celery.

The Telegram worker now follows the EMS package layout. FastAPI application creation and `GET /health` are implemented, with Black added for formatting.

Type checking covers source and tests with the project virtual environment. Telethon async return types and user checks are explicit.

CLI commands use Click. Typed Settings load environment variables and .env values when core configuration is imported, with secret masking and numeric validation.

Celery imports its application class directly so the editor can resolve the constructor.

Telegram integration lives in `bot/core/telegram.py`. The shared Settings instance is exposed by `bot/core/config.py`, following EMS.

Pytest uses function-scoped async fixture loops, and the health test exercises the app directly via HTTPX ASGI transport.

The Telegram monitor uses the shared logger in `bot/core/logger.py`.

Queue workers require an explicit Celery broker URL. The foreground Telegram monitor can run without one.

The async Redis client lives in `bot/core/redis.py`. The Redis dependency also enables Celery to use a Redis broker.

The Telegram monitor accepts new posts from the signed-in account's other devices as well as posts from other accounts.

The async Ollama client and sample extraction guide are in place. T03 still tracks independent verification of the extracted fields against the source.

The shared Rich console is available from `bot.core.console`.

The Ollama client loads its signal extraction instructions from `bot/prompts/signal.md`.

T02 is complete. Ollama output passes through the EMS-style signal data schema before logging. T03 still requires independent source-text verification.
