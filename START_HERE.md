# Start Here — FoxBot Agent Pack

This ZIP contains **Markdown coding-agent guidance**, not application code. Copy its contents into the root of your `foxbot` repository.

**Codex:** Run `codex` from project root; Codex reads `AGENTS.md`.

**Claude Code:** Run `claude` from project root; Claude reads `CLAUDE.md`.

Suggested instruction for either agent:

> Read AGENTS.md, CLAUDE.md, PROJECT_CONTEXT.md and tasks/NEXT.md. Implement only the next task. Keep FoxBot minimal, local Ollama only, and demo-only MT5 execution disabled by default. Run tests and update the backlog.

## Reading order
1. `PROJECT_CONTEXT.md` — boundaries and purpose.
2. `AGENTS.md` / `CLAUDE.md` — coding conventions.
3. `docs/REQUIREMENTS.md` — required behavior.
4. `docs/SAFETY.md` — trading controls.
5. `tasks/NEXT.md` — immediate task.

## Important
Do not use any old ForexBot 2.0 documents referring to PostgreSQL, FastAPI or an OpenAI API. This FoxBot project is deliberately much smaller.
