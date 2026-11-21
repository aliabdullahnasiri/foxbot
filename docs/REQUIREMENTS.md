# FoxBot v1 — Functional Requirements

## Dependencies
Runtime: `telethon`, `httpx`, `pydantic`, `pydantic-settings` or `python-dotenv` (choose one simple config approach), `MetaTrader5` (on Windows). Development: `pytest`, `pytest-asyncio`, `ruff`.

## Telegram
- Authenticate as a user via API ID/hash and local Telethon session; monitor authorized channel only.
- Handle only new messages after listener starts; ignore edits for automatic execution.
- Filter obvious non-signals, preserve source channel/message IDs, and deduplicate durably.
- Handle disconnections without replay-trading history.

## Ollama
- POST to configurable `OLLAMA_BASE_URL` + `/api/chat`, default `http://localhost:11434`.
- Default model `qwen2.5:3b`; JSON output via Ollama `format: "json"` and `stream: false`.
- Require fields `symbol`, `side`, `entry_price`, `stop_loss`, `take_profits`.
- Use exact decimal types in Python after JSON parsing; never use float for sizing calculations.
- Never infer missing numbers. Validate symbol/direction, stop/target geometry, and presence of each extracted numeric price in original source. Reject conflicting messages, ambiguous entries, cancellations, and unsupported pairs.
- Timeout, malformed JSON, model unavailable: log and skip.

## MT5
- Windows terminal prerequisite; `mt5.initialize()` and `mt5.account_info()`.
- Confirm demo account using reliable broker/terminal account mode metadata; if unclear, reject.
- Use configured broker symbol (including suffix) and verify selection and trading constraints.
- Market orders only; TP1 and required SL on initial order.
- For BUY use ASK; for SELL use BID; compare executable quote to signaled entry.
- Validate spread, stops and freeze levels, broker volume min/max/step, free margin, fill type, quote age; run `order_check` and inspect `order_send` retcodes.
- Use a stable magic number and traceable comment/id for reconciliation and one-position policy.

## Risk / state
- Risk 0.5% of current equity per signal; 2% daily-loss cap based on stored starting-day equity.
- Compute prospective stop loss with `mt5.order_calc_profit()` and budget for likely fees/slippage; never exceed cap by lot rounding.
- At most one FoxBot XAUUSD position at once, verify against live MT5 positions.
- Deduplicate `(channel_id,message_id)` via SQLite with durable processing state. Avoid double order on restart or uncertain outcomes.
- Log skipped, parsed, rejected, submitted, and confirmed results.

## Acceptance
- Valid new Telegram signal is extracted and validated, then logged as dry run by default.
- Only after explicit enablement, an eligible signal can submit one MT5 **demo** order with TP1 and SL.
- No real-account orders, stale signals, unknown symbols, ambiguous parsing, over-risk positions, or duplicate submissions.
