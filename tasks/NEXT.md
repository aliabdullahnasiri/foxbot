# Next Coding-Agent Task

**T01 — Create the smallest runnable FoxBot foundation.**

Read `PROJECT_CONTEXT.md`, `AGENTS.md`, `CLAUDE.md`, and `docs/REQUIREMENTS.md`. Inspect the repository first; don't overwrite existing correct work.

Create a Python 3.12 project with `uv`, minimal pinned/locked dependencies, `.env.example`, `.gitignore`, readable `config.py`, a startup `main.py` that prints sanitized startup configuration, and README setup steps for Windows MT5 + local Ollama. Include `ENABLE_TRADING=false` and reject any configuration that would imply live trading. Add basic config tests. Do **not** connect to Telegram or send MT5 orders in this first task.

Run available tests and linting; report exact commands and results. Update `tasks/BACKLOG.md` when T01 is done and replace this file with the next task (T02).

Progress: `.gitignore` is in place for local credentials, Telegram sessions, SQLite state, logs, and Python artifacts. `.env.example` includes the documented settings and defaults to dry run.
