# FoxBot v1 — Functional Requirements

Manual MT5 orders use an operator-supplied lot size on the connected terminal account. Account eligibility, real-mode opt-in, and portfolio risk controls described below apply only to the planned automated workflow. Manual submission requires explicit execution, a checked broker request, and a durable request ID.

## Dependencies

Python 3.12 and `uv` are required. The package uses Click, FastAPI, Telethon, Celery, Redis, HTTPX, Pydantic, and `mt5linux`. The native `MetaTrader5` dependency is declared for Windows. See the manifest for the complete runtime and development dependencies. [pyproject.toml](../pyproject.toml)

## Application entry points

- `uv run bot mt5-order --help` lists options for manual MT5 orders.
- `uv run bot telegram-login` creates the local Telegram session.
- `uv run bot telegram-monitor` runs the foreground Telegram task without a broker.
- `uv run uvicorn bot:main --factory` serves the FastAPI liveness endpoint at `GET /health`.

The acceptance criteria below describe the target for v1. [Implementation backlog](../tasks/BACKLOG.md)

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
- Confirm the requested account mode and identity using broker/terminal metadata. Real orders require a separately enabled manual submission on the explicitly configured account.
- Use configured broker symbol (including suffix) and verify selection and trading constraints.
- Market orders only; TP1 and required SL on initial order.
- For BUY use ASK; for SELL use BID; compare executable quote to signaled entry.
- Validate spread, stops and freeze levels, broker volume min/max/step, free margin, fill type, quote age; run `order_check` and inspect `order_send` retcodes.
- Use a stable magic number and traceable comment/id for reconciliation and one-position policy.

## Risk / state
- Maximum planned risk is 0.5% of current equity per order.
- Compute prospective stop loss with `mt5.order_calc_profit()` and budget for likely fees/slippage; never exceed cap by lot rounding.
- At most one FoxBot XAUUSD position at once, verify against live MT5 positions.
- Deduplicate `(channel_id,message_id)` via SQLite with durable processing state. Avoid double order on restart or uncertain outcomes.
- Log skipped, parsed, rejected, submitted, and confirmed results.

## Acceptance
- Valid new Telegram signal is extracted and validated, then logged as dry run by default.
- Only after explicit enablement, an eligible signal can submit one MT5 **demo** order with TP1 and SL.
- No automatic real-account orders, stale signals, unknown symbols, ambiguous parsing, over-risk positions, or duplicate submissions.
