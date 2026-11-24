# FoxBot — Implementation Backlog

Use this ordered checklist; update when work is completed. Keep the scope small.

- [ ] **T01 Foundation**: `uv` Python 3.12 project, dependencies, configuration, `.env.example`, `.gitignore`, README.
- [x] **T02 Domain models**: Pydantic signal model, `Decimal` conversion, input validation.
- [ ] **T03 Ollama**: async native HTTP client, JSON response parsing, source-text checks, timeout/error behavior.
- [x] **T04 Telegram**: Telethon sign-in, configured channel NewMessage handler, no history execution. The Celery monitor logs candidate IDs and schema-validated extractions. Source verification is tracked in T03.
- [ ] **T06 MT5 adapter**: fixed-volume manual market orders use a Pydantic schema and are covered with a mocked bridge. Windows terminal verification remains.
- [ ] **T07 Risk sizing**: implement equity-based sizing and margin controls for Telegram execution.
- [ ] **T08 Order execution**: TP1/SL market order, checks, idempotency, reconciliation of ambiguous result. The manual command supports both modes. Telegram wiring and terminal verification remain.
- [ ] **T09 Wire together**: main orchestration, dry-run default, clear logs and graceful shutdown.
- [ ] **T10 Tests and documentation**: parser/risk/execution/state tests and README usage.

Do not start a larger feature while the current milestone is incomplete.

The packaged CLI provides `mt5 order buy|sell|list|close`, including checked full-position closes by ticket. Manual buy and sell orders support repeated TP levels and foreground stop adjustments. Live terminal verification remains pending.

Manual stop management now trails one level behind each intermediate TP, starting at the actual fill price when TP1 is reached.
