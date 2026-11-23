# AGENTS.md — Codex instructions for FoxBot

Manual MT5 orders use an operator-supplied lot size on the connected terminal account. Account eligibility, real-mode opt-in, and portfolio risk controls described below apply only to the planned automated workflow. Manual submission requires explicit execution and a checked broker request.

Read `PROJECT_CONTEXT.md`, `docs/REQUIREMENTS.md`, `docs/SAFETY.md`, and `tasks/NEXT.md` before changes. Follow the explicit **minimal-scope** decisions. This file governs the entire repository.

## Working agreement
1. Inspect existing code before editing; preserve working behavior.
2. Implement only the current task. Make small, easy-to-review commits/changes.
3. Use Python 3.12, `uv`, type hints, simple modules, and clear errors.
4. Prefer `async` for Telethon and Ollama; isolate synchronous MT5 calls behind a small adapter so they do not block the event loop.
5. No runtime OpenAI SDK or paid AI integration; Ollama uses native HTTP with `httpx`.
6. Do not introduce a database server, ORM, frontend, Docker, or unnecessary architectural layers.
7. Never commit `.env`, session files, MT5 credentials, trade records, secrets.
8. Check all LLM-extracted fields against the message. LLM output is untrusted.
9. Default to dry run and demo mode. Real MT5 orders require the manual execution command, explicitly selected real mode, and separate opt-in. Never remove hard risk limits to make an order pass.
10. Write relevant tests, run `uv run pytest` and `uv run ruff check .` if installed; report actual results, not guessed results.
11. Update `tasks/NEXT.md` / `tasks/BACKLOG.md` after a completed task, preserving remaining work.

## Commands
```bash
uv sync
uv run bot --help
uv run pytest
uv run ruff check .
```

## Non-negotiable execution controls
Never send an order unless `ENABLE_TRADING=true`, confirmed account mode and identity, separate real-account opt-in when applicable, fresh quote, valid SL, valid order check, acceptable entry deviation/spread, adequate margin, risk at or below the limit including reasonable costs, and duplicate checks all pass. Reconcile uncertain order outcomes; don't blindly resend.

## Definition of done
Implementation + failure handling + focused automated tests + updated docs/task status. List files changed, commands run, and limitations.
