# CLAUDE.md — Claude Code instructions for FoxBot

Manual MT5 orders use an operator-supplied lot size on the connected terminal account. Account eligibility, real-mode opt-in, and portfolio risk controls described below apply only to the planned automated workflow. Manual submission requires explicit execution and a checked broker request.

You are implementing **FoxBot**, not the older full ForexBot platform. Read `PROJECT_CONTEXT.md`, `docs/REQUIREMENTS.md`, `docs/SAFETY.md`, and `tasks/NEXT.md` first. `AGENTS.md` contains shared repository rules; follow them too.

## Principles
- One Python process, one Telegram channel, one Windows MT5 terminal, local Ollama, no web app.
- Simple functions and few files over abstract factories and premature extensibility.
- Telethon for new-message listening; Ollama HTTP JSON extraction; deterministic verification; MT5 order checks and risk sizing.
- Keep `ENABLE_TRADING=false` unless the operator changes it explicitly.
- LLM is a parser only, not a financial decision maker or risk engine.
- Never convert unclear signals into trades. Fail closed.
- Do not add OpenAI API usage, authentication headers/secrets unless Ollama endpoint configuration explicitly requires them.
- Add tests and document what was actually validated.

## Implementation cycle
1. Read the project context and current task.
2. Briefly state intended edits.
3. Implement the smallest coherent working slice.
4. Test; if tests cannot run, explain why.
5. Update tasks and summarize changed files and remaining concerns.

## Security
Do not print or commit Telegram API credentials, session data, `.env`, MT5 credentials, or tokens. Real-account orders require manual submission, explicitly selected real mode, a verified configured account, and separate opt-in.

## Reference
Read `docs/ARCHITECTURE.md`, `docs/CONFIGURATION.md`, and `docs/TESTING.md` for integration details.
