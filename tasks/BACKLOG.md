# FoxBot — Implementation Backlog

Use this ordered checklist; update when work is completed. Keep the scope small.

- [ ] **T01 Foundation**: `uv` Python 3.12 project, dependencies, configuration, `.env.example`, `.gitignore`, README.
- [ ] **T02 Domain models**: Pydantic signal model, `Decimal` conversion, input validation.
- [ ] **T03 Ollama**: async native HTTP client, JSON response parsing, source-text checks, timeout/error behavior.
- [x] **T04 Telegram**: Telethon sign-in, configured channel NewMessage handler, no history execution. The Celery monitor logs candidate IDs. Parsing and durable deduplication are tracked in T03 and T05.
- [ ] **T05 SQLite state**: deduplication, processing/execution statuses, daily equity baseline, safe restart logic.
- [ ] **T06 MT5 adapter**: Windows/demo validation, symbol/quotes/constraints/position checks.
- [ ] **T07 Risk sizing**: stop-based `order_calc_profit`, volume-step floor, daily limit, margin and spread.
- [ ] **T08 Order execution**: TP1/SL market order, checks, idempotency, reconciliation of ambiguous result.
- [ ] **T09 Wire together**: main orchestration, dry-run default, clear logs and graceful shutdown.
- [ ] **T10 Tests and documentation**: parser/risk/execution/state tests and README usage.

Do not start a larger feature while the current milestone is incomplete.
